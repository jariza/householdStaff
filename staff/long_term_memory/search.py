import logging

from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

# Search into the long term memory
# message: message to search
# user_id: user ID
# agent_name: name of the agent searching in memory
# store: long term memory storage
# emptyMsg: message return in case of no findings
# Returns the search result
async def search_long_term_memory(message: str, user_id: str, agent_name: str, store: BaseStore, emptyMsg: str) -> str:
    logger.debug("Searching in long term memory, agent %s, message: %s", agent_name, message)
    raw_results = await store.asearch((user_id, "longterm", agent_name), query=message, limit=2)
    logger.debug("Raw search results: %r", raw_results)

    # Filter the raw results based on score
    results = [
        r.value["texto"] for r in raw_results
        if r.score is not None and r.score >= 0.3
    ]
    logger.debug("Search results: %r", results)

    # Return result
    if len(results) == 0:
        return emptyMsg
    else:
        return '\n'.join(results)
