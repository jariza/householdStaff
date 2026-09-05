from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import uuid

router = APIRouter(prefix="/store", tags=["Store CRUD"])


# Helper function to perform a GET operation compatible with both sync (InMemoryStore) and async (AsyncSqliteStore) stores.
async def _store_get(store, namespace: tuple, key: str):
    if hasattr(store, "aget"):
        return await store.aget(namespace, key)
    return store.get(namespace, key)


# Helper function to perform a PUT operation compatible with both sync (InMemoryStore) and async (AsyncSqliteStore) stores.
async def _store_put(store, namespace: tuple, key: str, value: dict):
    if hasattr(store, "aput"):
        await store.aput(namespace, key, value)
    else:
        store.put(namespace, key, value)


# Helper function to perform a LIST/SEARCH operation compatible with both sync (InMemoryStore) and async (AsyncSqliteStore) stores.
async def _store_search(store, namespace: Optional[tuple] = None, limit: int = 10, offset: int = 0):
    prefix = namespace if namespace is not None else ()
    
    if hasattr(store, "asearch"):
        return await store.asearch(prefix, limit=limit, offset=offset)
    return store.search(prefix, limit=limit, offset=offset)

# Helper function to perform a DELETE operation compatible with both sync (InMemoryStore) and async (AsyncSqliteStore) stores.
async def _store_delete(store, namespace: tuple, key: str):
    if hasattr(store, "adelete"):
        await store.adelete(namespace, key)
    else:
        store.delete(namespace, key)


# Pydantic schemas for request and response validation
class StoreItemCreate(BaseModel):
    namespace: List[str] = Field(description="Namespace structure as a list of strings")
    key: Optional[str] = Field(None,  description="Optional unique key. If omitted, a UUIDv4 will be automatically generated.")
    texto: str = Field()
class StoreItemResponse(BaseModel):
    namespace: List[str]
    key: str
    value: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Create or update an item in the LangGraph store. Generates a UUID if no key is provided.
# curl -X PUT -H "Content-Type: application/json" -d '{"namespace": ["1", "butler"], "texto": "El usuario prefiere el café solo y sin azúcar por las mañanas."}' "http://127.0.0.1:8000/store"
@router.put("", response_model=Dict[str, str], summary="Create or update an item")
async def put_item(item: StoreItemCreate, request: Request):
    store = request.app.state.store
    ns_tuple = tuple(item.namespace)
    
    # Generate UUID if key was not provided by user
    item_key = item.key if item.key else str(uuid.uuid4())
    value = {"texto": item.texto}
    
    await _store_put(store, ns_tuple, item_key, value)
    
    return {
        "status": "success", 
        "message": f"Item stored successfully in namespace {ns_tuple}.",
        "key": item_key
    }


# Retrieve all items in the store across all namespaces with pagination support.
# curl -X GET "http://127.0.0.1:8000/store/all"
# curl -X GET "http://127.0.0.1:8000/store/all?limit=10&offset=5"
@router.get("/all", response_model=List[StoreItemResponse], summary="Get all items in the store")
async def get_all_items(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip for pagination")
):
    store = request.app.state.store
    
    # Passing an empty tuple () as namespace fetches all items across all namespaces
    results = await _store_search(store, namespace=(), limit=limit, offset=offset)
    
    return [
        StoreItemResponse(
            namespace=list(item.namespace),
            key=item.key,
            value=item.value,
            created_at=item.created_at.isoformat() if getattr(item, "created_at", None) else None,
            updated_at=item.updated_at.isoformat() if getattr(item, "updated_at", None) else None,
        )
        for item in results
    ]


# Retrieve a single item from the store by its namespace and key.
# curl -X GET "http://127.0.0.1:8000/store/item?namespace=1&namespace=butler&key=preferencia01"
@router.get("/item", response_model=StoreItemResponse, summary="Get an item by Key")
async def get_item(
    request: Request,
    namespace: List[str] = Query(),
    key: str = Query()
):
    store = request.app.state.store
    ns_tuple = tuple(namespace)
    
    item = await _store_get(store, ns_tuple, key)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{key}' not found in namespace {ns_tuple}")
    
    return StoreItemResponse(
        namespace=list(item.namespace),
        key=item.key,
        value=item.value,
        created_at=item.created_at.isoformat() if getattr(item, "created_at", None) else None,
        updated_at=item.updated_at.isoformat() if getattr(item, "updated_at", None) else None,
    )


# Delete a specific item from the long-term memory store.
# curl -X DELETE "http://127.0.0.1:8000/store/item?namespace=1&namespace=butler&key=preferencia01"
@router.delete("/item", response_model=Dict[str, str], summary="Delete an item")
async def delete_item(
    request: Request,
    namespace: List[str] = Query(),
    key: str = Query()
):
    store = request.app.state.store
    ns_tuple = tuple(namespace)
    
    existing_item = await _store_get(store, ns_tuple, key)
    if not existing_item:
        raise HTTPException(status_code=404, detail=f"Item '{key}' not found in namespace {ns_tuple}")
        
    await _store_delete(store, ns_tuple, key)
    return {"status": "success", "message": f"Item '{key}' deleted from namespace {ns_tuple}."}