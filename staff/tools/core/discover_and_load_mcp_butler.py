from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState, InjectedStore
from langgraph.store.base import BaseStore
from langgraph.types import Command

from mcp_catalog import search_server_mcp_catalog


@tool
async def discover_and_load_mcp_butler(capability_needed: str, mcp_current_list: Annotated[list, InjectedState("mcpServersInUseByButler")], store: Annotated[BaseStore, InjectedStore()], tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """Find and activate an external MCP tool from the catalog when no active tool matches the request.
    
    Describe the capability in capability_needed using English keywords for optimal search accuracy (e.g., 'weather forecast', 'fetch url', 'timezone convert').
    """

    mcp_server = await search_server_mcp_catalog(capability_needed, store)

    if not mcp_server:
        return Command(update={
                "messagesButler": [ToolMessage(content = "No relevant MCP server was found in the catalog.", tool_call_id = tool_call_id)]
            })
    elif mcp_server in mcp_current_list:
        return Command(update={
                "messagesButler": [ToolMessage(content = f"MCP server '{mcp_server}' is already loaded and active.", tool_call_id = tool_call_id)]
            })
    else:
        mcp_current_list.append(mcp_server)
        return Command(update={
                "messagesButler": [ToolMessage(content = f"New MCP server loaded successfully: {mcp_server}", tool_call_id = tool_call_id)],
                "mcpServersInUseByButler" : mcp_current_list
            })
