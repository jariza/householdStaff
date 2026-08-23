from langgraph.store.base import BaseStore
import logging

logger = logging.getLogger(__name__)

# Search into the long term memory
# message: message to search
# memory_namespace: memory namespace to use
# store: long term memory storage
# emptyMsg: message return in case of no findings
# Returns the search result
def search_long_term_memory(message: str, memory_namespace, store: BaseStore, emptyMsg: str) -> str:
    logger.debug("Searching in long term memory, namespace %s, message: %s", memory_namespace, message)
    raw_results = store.search(memory_namespace, query=message, limit=2)
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