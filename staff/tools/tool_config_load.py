import logging

from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

# Search into tools the configuration memory
# toolname: name of the tool using the configuration
# is_encrypted: search in the encrypted configuration or not
# store: long term memory storage
# Returns the configuration, None if no configuration was found
async def tool_config_load(user_id: int, toolname: str, is_encrypted: bool, store: BaseStore) -> str:
    logger.debug("Searching in configuration memory, tool %s, in_encrypted: %s", toolname, is_encrypted)
    memory_name = "toolconfigenc" if is_encrypted else "toolconfigplain"
    item = await store.aget((user_id, memory_name, memory_name), toolname)
    logger.debug("Configuration found: %s", item["config"])
    return item["config"]