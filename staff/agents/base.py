from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
import logging
from .commonPrompts import EMPTY_PRELOAD_MEM
from longTermMemory import search_long_term_memory

logger = logging.getLogger(__name__)

# Base class for generic agent
class BaseAgent:
    # Initialization
    # engine: answer engine (aka LLM)
    def __init__(self, engine):
        self.agentName = type(self).__name__ # The name of the derived class is the name of the agent
        self.engine = engine

    # Search into the long term memory
    # message: message to search
    # config: app config details
    # store: long term memory storage
    # Returns the search result
    def _preload_memory(self, message: str, config: RunnableConfig, store: BaseStore) -> str:
        user_id = config.get("configurable", {}).get("user_id")
        memory_namespace = (user_id, self.agentName)
        return search_long_term_memory(message=message, memory_namespace=memory_namespace, store=store, emptyMsg=EMPTY_PRELOAD_MEM)
