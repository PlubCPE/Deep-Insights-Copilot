import os
import httpx


MCP_URL = os.getenv("MCP_URL", "http://localhost:9000")


async def call_tool(tool_name: str, params: dict):
async with httpx.AsyncClient() as client:
resp = await client.post(f"{MCP_URL}/tools/call", json={"tool": tool_name, "params": params}, timeout=30.0)
resp.raise_for_status()
return resp.json()