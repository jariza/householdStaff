import logging

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.store.base import BaseStore

from longTermMemory import search_long_term_memory
from mcp_catalog import load_tools_from_mcp_server

from .commonPrompts import EMPTY_PRELOAD_MEM

logger = logging.getLogger(__name__)

# Base class for generic agent
class BaseAgent:
    # Description of the agent, to be send to a LLM, required only if delegable is True
    description: str = ""
    # Can an agent delegate on this one?
    delegable: bool = True

    @classmethod
    def delegatable_agents(cls):
        delegatables = {}
        for agent_class in BaseAgent.__subclasses__():
            if agent_class.delegable:
                agent_name = agent_class.__name__.removesuffix("Agent")
                delegatables[agent_name] = agent_class.description
        return delegatables

    # Initialization
    # engine: answer engine (aka LLM)
    # base_tools, list of base tools to bind the the agent
    def __init__(self, engine, base_tools: list[BaseTool] | None = None):
        self.agentName = type(self).__name__.removesuffix("Agent") # The name of the derived class is the name of the agent
        self.engine = engine
        self.base_tools = base_tools or []
        self.tools_from_mcp = []

    # Search into the long term memory
    # message: message to search
    # config: app config details
    # store: long term memory storage
    # Returns the search result
    async def _preload_memory(self, message, config: RunnableConfig, store: BaseStore) -> str:
        user_id = config.get("configurable", {}).get("user_id")
        memory_namespace = (user_id, self.agentName)
        message_txt = self.engine.extract_text(message)
        return await search_long_term_memory(message=message_txt, memory_namespace=memory_namespace, store=store, emptyMsg=EMPTY_PRELOAD_MEM)

    async def _get_active_tools(self, mcp_server_list: list[str], config: RunnableConfig) -> list[BaseTool]:
        mcp_manager = config.get("configurable", {}).get("mcp_manager")
        # Get the list of MCP tools every time so we know it's fresh
        mcp_tools = list(self.base_tools)
        for mcp_server in mcp_server_list:
            mcp_tools += await load_tools_from_mcp_server(mcp_server, mcp_manager)

        return mcp_tools