from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from typing import Annotated

from longTermMemory import search_long_term_memory

@tool
def search_memory_butler(search_text: str, config: RunnableConfig, store: Annotated[BaseStore, InjectedStore()]) -> str:
    """Search the butler's long-term memory."""

    user_id = config.get("configurable", {}).get("user_id")
    memory_namespace = (user_id, "butler")
    return search_long_term_memory(search_text, memory_namespace, store=store, emptyMsg="No relevant information was found in the memory.")
