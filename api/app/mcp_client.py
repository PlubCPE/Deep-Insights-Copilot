import os
import httpx

MCP_URL = os.getenv("MCP_URL", "http://mcp_server:9000")

async def call_tool(tool_name: str, params: dict, timeout: float = 30.0):
    """
    Call the MCP server's /tools/call endpoint.
    Expects JSON: {"tool": "<toolname>", "params": { ... }}
    """
    payload = {"tool": tool_name, "params": params}
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{MCP_URL}/tools/call", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
