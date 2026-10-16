from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from typing import Annotated

from longTermMemory import search_long_term_memory

@tool
async def search_memory_butler(search_text: str, config: RunnableConfig, store: Annotated[BaseStore, InjectedStore()]) -> str:
    """Search long-term memory for relevant background information, user preferences, or past interactions when the immediate context is insufficient."""

    user_id = config.get("configurable", {}).get("user_id")
    memory_namespace = (user_id, "butler")
    return await search_long_term_memory(search_text, memory_namespace, store=store, emptyMsg="No relevant information was found in the memory.")
