import asyncio
from contextlib import AsyncExitStack
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.store.base import BaseStore
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os
import sys
from typing import Any, Dict
import yaml

logger = logging.getLogger(__name__)

MCP_CATALOG_NAMESPACE = ("0", "mcpcatalog")

# Avoid re-opening MCP servers
class MCPSessionManager:
    def __init__(self, yaml_path: str):
        self.active_servers: dict[str, dict[str, Any]] = {}
        self.servers_config = _load_mcp_catalog_config(yaml_path)

    # Return tools from memory if server is already running, start the process otherwise
    async def get_or_load_tools(self, server_name: str) -> list[BaseTool]:

        # Server is running, return tools
        if server_name in self.active_servers:
            return self.active_servers[server_name]["tools"]

        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", server_name] + (self.servers_config[server_name] or []),
        )

        server_stack = AsyncExitStack()
        try:
            read, write = await server_stack.enter_async_context(stdio_client(parameters))
            session = await server_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            tools = await load_mcp_tools(session)
            
            self.active_servers[server_name] = {
                "tools": tools,
                "stack": server_stack
            }
            return tools
        except Exception:
            await server_stack.aclose()
            raise

    # Closes all processes
    async def close_all(self):
        for server_name, server_data in list(self.active_servers.items()):
            try:
                # Attempt a graceful session close if available
                if "session" in server_data:
                    await server_data["session"].close()
            except Exception:
                pass
            
            try:
                # Close the exit stack while making expected AnyIO task mismatch errors silent
                await server_data["stack"].aclose()
            except RuntimeError as e:
                if "different task" in str(e):
                    logger.debug(f"Expected task mismatch while closing MCP {server_name}: {e}")
                else:
                    logger.error(f"Error closing MCP server {server_name}: {e}")
            except Exception as e:
                logger.error(f"Error closing MCP server {server_name}: {e}")

        self.active_servers.clear()

# Load MCP catalog yaml file
def _load_mcp_catalog_config(yaml_path: str) -> Dict[str, Any]:
    if not os.path.exists(yaml_path):
        logger.warning(f"MCP catalog file {yaml_path} not found. Proceeding with empty MCP catalog.")
        return {}

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error parsing YAML file {yaml_path}: {e}. Proceeding with empty MCP catalog.")
        return {}

    if not isinstance(data, dict):
        logger.warning(f"MCP catalog file {yaml_path} is empty or not a valid dictionary. Proceeding with empty MCP catalog.")
        return {}

    servers_config = {}
    for item in data.get("mcp_servers", []):
        if isinstance(item, str):
            server = item
            extra_args = []
        elif isinstance(item, dict):
            server = item["server"]
            if not server:
                logger.warning(f"Skipping invalid server item missing server key: {item}")
                continue
            extra_args = item.get("args", [])
        else:
            continue
        servers_config[server] = extra_args
        
    return servers_config

# Load MCP catalog from yaml file
async def populate_mcp_catalog(yaml_path: str, store: BaseStore):

    # Clean up current catalog
    items_existentes = await store.asearch(MCP_CATALOG_NAMESPACE, query="")
    for item in items_existentes:
        await store.adelete(MCP_CATALOG_NAMESPACE, item.key)

    servers_config = _load_mcp_catalog_config(yaml_path)

    # Populate MCP catalog
    for server, extra_args in servers_config.items():

        parameters = StdioServerParameters(command=sys.executable, args=["-m", server] + extra_args)

        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                for tool in tools:
                    await store.aput(
                        namespace = MCP_CATALOG_NAMESPACE,
                        key = f"{server}__{tool.name}",
                        value = {"description": tool.description, "server": server}
                    )

# Search server from MCP catalog
# Returns the name of the server, empty string if no server was found
async def search_server_mcp_catalog(seach_text: str, store: BaseStore) -> str:
    # Loading all tool set from a MCP server so results are limited to 1
    results = await store.asearch(MCP_CATALOG_NAMESPACE, query=seach_text, limit=1)
    logger.debug("Raw search results: %r", results)

    if not results or results[0].score < 0.3:
        return ""

    return results[0].value.get("server")

async def load_tools_from_mcp_server(server_name: str, mcp_manager: MCPSessionManager) -> list[BaseTool]:
    if mcp_manager:
        return await mcp_manager.get_or_load_tools(server_name)
    else:
        logger.error("No mcp_manager instance provided.")
        return []
