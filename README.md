# k8s aggregator MCP server

A frontend MCP (Model Context Protocol) server that dynamically discovers
tools exposed by per-node backend MCP servers running on a Kubernetes cluster
and re-exposes them as a single, unified API. Each tool is augmented with a
`node` parameter so callers can target a specific Kubernetes node.

## Architecture

The system is composed of two layers:

1. **Backend (DaemonSet)** -- A lightweight MCP server deployed as a Kubernetes
   DaemonSet. One pod runs on every node with `hostNetwork` and `hostPID`
   access, exposing node-level information over HTTP.

2. **Frontend (this server)** -- A single-replica Deployment that acts as the
   public entry point. On startup it connects to one of the backend pods,
   discovers all available tools, and registers them on its own MCP server
   with an extra `node` parameter injected into each tool's schema.

When a client calls a tool, the frontend resolves the target node to the
corresponding backend pod IP via the Kubernetes Endpoints API and proxies the
call to that specific pod.

```
Client
  |
  v
Frontend MCP server (port 9029)
  |  -- resolves node name to pod IP via Endpoints --
  v
Backend MCP pod on the target node (port XXXX)
```

## Tool discovery

Tool discovery is a one-time operation that runs at startup:

1. The frontend queries the `backend-mcp-service` Endpoints object (configurable)
   to find the IP of the first available backend pod.
2. It connects to that pod's MCP endpoint and calls `list_tools`.
3. For each tool returned, it creates a wrapper that:
   - Preserves the original tool name, description, and parameter schema.
   - Prepends a required `node` parameter (the Kubernetes node name).
   - Routes the call to the correct backend pod at invocation time.

If no backend endpoints are available at startup, the frontend refuses to
start.

## Configuration

The following environment variables can be used to override defaults:

| Variable            | Description                              | Default                |
|---------------------|------------------------------------------|------------------------|
| `SERVICE_NAME`      | Name of the backend headless Service     | `backend-mcp-service`  |
| `SERVICE_NAMESPACE` | Namespace of the backend Service         | `mcp-server`           |
| `BACKEND_PORT`      | Port the backend MCP servers listen on   | `9028`                 |
| `FRONTEND_PORT`     | Port the frontend MCP server listens on  | `9029`                 |

## Prerequisites

- Python >= 3.12
- A Kubernetes cluster with the backend DaemonSet and headless Service deployed
- RBAC permissions for the frontend's ServiceAccount to `get` the
  `backend-mcp-service` Endpoints resource. In the example provided in the
  `deploy/` directory, this is done using a custom ClusterRole.

## Running locally

```bash
pip install -r requirements.txt
python server.py
```

The server will attempt to load an in-cluster Kubernetes config first, falling
back to your local `~/.kube/config`.

## Deployment

The frontend is typically deployed as a Kubernetes Deployment with a
ClusterIP Service and (on OpenShift) a Route for external access. See the
`deploy/` directory for manifests.

A `Makefile` is provided for convenience, with tools to build/push the container
image, and then deploy/undeploy de MCP server.

An example backend MCP server providing a simple tool and deployment is located
in the `backend/` directory.

## Dependencies

- [FastMCP](https://gofastmcp.com/) (>= 3.0.0b2) -- MCP server and client framework
- [kubernetes](https://github.com/kubernetes-client/python) -- Kubernetes API client
- [pydantic](https://docs.pydantic.dev/) -- Used for parameter schema generation
