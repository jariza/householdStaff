import logging

from langchain_core.tools import BaseTool
from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

TOOLS_CONFIG_NAMESPACE = "toolconfig"
TOOLS_CONFIG_SCHEMA_NAMESPACE = ("toolconfigschema", "0", "toolconfigschema")
TOOLS_PROTECTED_SUBNAMESPACE = "enc"

# Search into tools the configuration memory
# toolname: name of the tool using the configuration
# is_encrypted: search in the encrypted configuration or not
# store: long term memory storage
# Returns the configuration, None if no configuration was found
async def tool_config_load(user_id: int, toolname: str, is_encrypted: bool, store: BaseStore) -> str:
    logger.debug("Searching in configuration memory, tool %s, in_encrypted: %s", toolname, is_encrypted)
    memory_subname = "enc" if is_encrypted else "plain"
    item = await store.aget(("toolconfig", user_id, memory_subname), toolname)
    logger.debug("Configuration found: %s", item["config"])
    return item["config"]

def tool_config_spec(spec: dict):
    allowed_spec_keys = {"plain", "enc"}

    if not isinstance(spec, dict) or not spec:
        raise ValueError("config_spec must be a non-empty dictionary.")

    invalid_keys = set(spec.keys()) - allowed_spec_keys
    if invalid_keys:
        raise ValueError(
            f"Invalid config_spec keys: {invalid_keys}. Only {allowed_spec_keys} are allowed."
        )

    def decorator(target):
        # If already wrapped with @tool, point to the underlying sync (.func) or async (.coroutine) function
        fn = getattr(target, "func", None) or getattr(target, "coroutine", None) or target
        fn.tool_config_spec = spec
        return target

    return decorator

# Stores tool configs in store
async def populate_tool_specs(tools: list[BaseTool], store: BaseStore) -> None:
    # Delete all existing schemas in the registry namespace
    existing_items = await store.asearch(TOOLS_CONFIG_SCHEMA_NAMESPACE)
    for item in existing_items:
        await store.adelete(TOOLS_CONFIG_SCHEMA_NAMESPACE, item.key)

    # Populate schemas for currently configured tools
    for t in tools:
        fn = getattr(t, "func", t)
        spec = getattr(fn, "tool_config_spec", None)
        if spec:
            await store.aput(
                namespace=TOOLS_CONFIG_SCHEMA_NAMESPACE,
                key=t.name,
                value={
                    "name": t.name,
                    "description": t.description,
                    "tool_config_spec": spec,
                },
            )