# Example MCP server for k8s aggregator MCP

This is a very simple example used to illustrate the capabilities of the
k8s aggregator MCP server. Initially, it exposed a single tool `get_cpuinfo`
used to get the /proc/cpuinfo output from the node. More tools can be added
in the future.

The MCP server is deployed as a DaemonSet to a Kubernetes/OpenShift cluster,
and then exposed internally to the cluster using a headless service.

## Deployment

The MCP Server is typically deployed as a Kubernetes Deployment with a
Service. See the `deploy/` directory for manifests.

A `Makefile` is provided for convenience, with tools to build/push the container
image, and then deploy/undeploy the MCP server.

## Running locally

```bash
pip install -r requirements.txt
python lowlevel.py
```

## Dependencies

- [FastMCP](https://gofastmcp.com/) (>= 3.0.0b2) -- MCP server and client framework
