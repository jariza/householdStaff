# Persistence resources creation
# stack, stack that manages the lifecycle of async resources
# embeddings, embeddings to use in the store
# debug, debug flag
async def create_persistence_resources(stack, embeddings, debug):
    if debug:
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.store.memory import InMemoryStore
        checkpointer = InMemorySaver()

        store = InMemoryStore(
            index={
                "embed": embeddings.embed_documents,
                "dims": 384,
                "fields": ["texto"]
            }
        )
    else:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        from langgraph.store.sqlite.aio import AsyncSqliteStore
        checkpointer = await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(
                "langgraph_checkpoint.db"
            )
        )

        store = await stack.enter_async_context(
            AsyncSqliteStore.from_conn_string(
                "langgraph_store.db",
                index={
                    "embed": embeddings.embed_documents,
                    "dims": 384,
                    "fields": ["texto"]
                }
            )
        )

        await store.setup()

    return checkpointer, store