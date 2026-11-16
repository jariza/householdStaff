from pathlib import Path


# Persistence resources creation
# stack, stack that manages the lifecycle of async resources
# embeddings, embeddings to use in the store
# persis_memory, if True persis to memory
# data_dir, data dir
async def create_persistence_resources(stack, embeddings, persist_memory, data_dir: Path):
    if persist_memory:
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.store.memory import InMemoryStore
        checkpointer = InMemorySaver()

        store = InMemoryStore(
            index={
                "embed": embeddings.embed_documents,
                "dims": 384,
                "fields": ["texto", "description"]
            }
        )
    else:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        from langgraph.store.sqlite.aio import AsyncSqliteStore
        checkpointer = await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(
                str(data_dir / "langgraph_checkpoint.db")
            )
        )

        store = await stack.enter_async_context(
            AsyncSqliteStore.from_conn_string(
                str(data_dir / "langgraph_store.db"),
                index={
                    "embed": embeddings.embed_documents,
                    "dims": 384,
                    "fields": ["texto", "description"]
                }
            )
        )

        await store.setup()

    return checkpointer, store