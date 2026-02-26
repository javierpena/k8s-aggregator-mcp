from typing import Any
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("demo")

# Constants

@mcp.tool()
def get_cpuinfo() -> Any:
    """
    Get the /proc/cpuinfo output from the node

    """

    with open("/proc/cpuinfo") as fp:
        cpuinfo = fp.read()

    return cpuinfo


def run():
    mcp.run(transport="http", host="0.0.0.0", port=9028)


if __name__ == "__main__":
    run()
