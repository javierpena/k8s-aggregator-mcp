from fastmcp import FastMCP, Client
from typing import Annotated, Any
from pydantic import Field
import asyncio
import inspect
import os

from kubernetes import client, config

# Initialize FastMCP server
mcp = FastMCP("k8s-aggregator-mcp")

SERVICE_NAME = os.environ.get("SERVICE_NAME", "backend-mcp-service")
SERVICE_NAMESPACE = os.environ.get("SERVICE_NAMESPACE", "mcp-server")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "9028"))
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", "9029"))

JSON_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _load_k8s_config():
    """Load Kubernetes configuration (in-cluster or local kubeconfig)."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def get_node_ip(node: str) -> str:
    """Discover the IP address for a node by looking up the
    backend mcp-service Endpoints in the specified namespace."""

    _load_k8s_config()

    v1 = client.CoreV1Api()
    endpoints = v1.read_namespaced_endpoints(
        name=SERVICE_NAME,
        namespace=SERVICE_NAMESPACE,
    )

    for subset in endpoints.subsets or []:
        for address in subset.addresses or []:
            if address.node_name == node:
                return address.ip

    raise ValueError(
        f"No endpoint found for node '{node}' in {SERVICE_NAME}"
    )


def _get_first_endpoint_ip() -> str:
    """Return the IP of the first endpoint address in the service."""

    _load_k8s_config()

    v1 = client.CoreV1Api()
    endpoints = v1.read_namespaced_endpoints(
        name=SERVICE_NAME,
        namespace=SERVICE_NAMESPACE,
    )

    for subset in endpoints.subsets or []:
        for address in subset.addresses or []:
            return address.ip

    raise RuntimeError(
        f"No endpoints available for {SERVICE_NAME}. "
        "Cannot discover tools — is the backend DaemonSet running?"
    )


def _python_type(json_type: str):
    """Map a JSON Schema type string to a Python type."""
    return JSON_TYPE_MAP.get(json_type, Any)


def _build_handler(tool_name: str, tool_description: str, input_schema: dict):
    """Return an async handler whose signature matches the backend tool
    plus an extra leading *node* parameter."""

    properties = input_schema.get("properties", {})
    required_params = set(input_schema.get("required", []))

    # The closure captures *tool_name* by value (function argument).
    async def _handler(**kwargs):
        node = kwargs.pop("node")
        ip = get_node_ip(node)
        url = f"http://{ip}:{BACKEND_PORT}/mcp/"
        async with Client(url) as remote:
            result = await remote.call_tool(tool_name, kwargs)
        if result.data != None:
            return result.data
        else:
            return result.content[0].text

    # Build a proper inspect.Signature so FastMCP generates the
    # correct JSON schema (including parameter descriptions).

    params: list[inspect.Parameter] = []
    annotations: dict[str, Any] = {}

    # 'node' is always the first required parameter
    node_ann = Annotated[
        str, Field(description="The name of the Kubernetes node to target.")
    ]
    params.append(
        inspect.Parameter(
            "node", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=node_ann
        )
    )
    annotations["node"] = node_ann

    # Original backend parameters
    for pname, pschema in properties.items():
        py_type = _python_type(pschema.get("type", "string"))
        desc = pschema.get("description", "")
        ann = Annotated[py_type, Field(description=desc)] if desc else py_type

        default = (
            inspect.Parameter.empty
            if pname in required_params
            else pschema.get("default")
        )
        params.append(
            inspect.Parameter(
                pname,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=ann,
                default=default,
            )
        )
        annotations[pname] = ann

    _handler.__signature__ = inspect.Signature(params)
    _handler.__annotations__ = annotations
    _handler.__name__ = tool_name
    _handler.__qualname__ = tool_name
    _handler.__doc__ = tool_description

    return _handler


async def _discover_tools() -> list:
    """Connect to the first backend pod and list its MCP tools."""
    ip = _get_first_endpoint_ip()
    url = f"http://{ip}:{BACKEND_PORT}/mcp/"
    print(f"Discovering tools from backend at {url} ...")
    async with Client(url) as remote:
        return await remote.list_tools()


def _register_tools(tools) -> None:
    """Wrap each backend tool and register it on the frontend server."""
    for tool in tools:
        handler = _build_handler(
            tool.name,
            tool.description or "",
            tool.inputSchema or {"type": "object", "properties": {}},
        )
        mcp.tool()(handler)
        print(f"  registered tool: {tool.name}")


def run():
    # 1. Discover tools from the first available backend pod
    tools = asyncio.run(_discover_tools())
    if not tools:
        raise RuntimeError("No tools discovered from the backend MCP server.")

    print(f"Discovered {len(tools)} tool(s) from backend.")
    _register_tools(tools)

    # 2. Start the frontend server
    mcp.run(transport="http", host="0.0.0.0", port=FRONTEND_PORT)


if __name__ == "__main__":
    run()
