"""
Jnkn AI Context Server.
Exposes the core Jnkn logic via Model Context Protocol (MCP).
"""

from fastmcp import FastMCP

mcp = FastMCP("Jnkn Context Service")


@mcp.tool()
def get_status() -> str:
    return "Jnkn AI is online and connected to Core."


if __name__ == "__main__":
    mcp.run()
