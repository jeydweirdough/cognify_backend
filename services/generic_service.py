# services/generic_service.py
from core.firebase import db
from database.models import get_current_iso_time, TimestampModel
from typing import List, Optional, Dict, Any, Type, TypeVar, Literal, Tuple
from pydantic import BaseModel, ValidationError
import asyncio
from google.cloud.firestore_v1.base_query import FieldFilter
# --- NEW: Import for cursor pagination ---
from google.cloud.firestore_v1.document import DocumentSnapshot
from fastapi import HTTPException, status

# Generic types for our models
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class FirestoreModelService:
    """
    A generic reusable *async* service for Firestore CRUD operations
    that automatically handles Pydantic model validation, timestamps,
    and soft-delete/restore functionality.
    
    UPDATED: Now supports cursor-based pagination and permanent purge.
    """
    def __init__(self, collection_name: str, model: Type[ModelType]):
        self.collection_name = collection_name
        self.model: Type[ModelType] = model
        self.db = db.collection(self.collection_name)
        self._has_timestamps = issubclass(self.model, TimestampModel)

    async def get_all(
        self, 
        deleted_status: Literal["non-deleted", "deleted-only", "all"] = "non-deleted",
        limit: int = 20,
        start_after: Optional[str] = None
    ) -> Tuple[List[ModelType], Optional[str]]:
        """
        Fetches documents with an option to filter by deleted status
        and support for pagination.
        
        Returns a tuple: (list_of_items, last_document_id)
        """
        def _get_all_sync():
            items = []
            query = self.db
            
            if self._has_timestamps:
                # This query is efficient because it's only on one field
                if deleted_status == "non-deleted":
                    query = query.where(filter=FieldFilter("deleted", "!=", True))
                elif deleted_status == "deleted-only":
                    query = query.where(filter=FieldFilter("deleted", "==", True))
            
            # --- NEW: Pagination Logic ---
            if start_after:
                try:
                    start_doc = self.db.document(start_after).get()
                    if start_doc.exists:
                        query = query.start_after(start_doc)
                except Exception as e:
                    print(f"Warning: Invalid start_after document ID '{start_after}': {e}")
            
            # Apply limit and get the documents
            docs = list(query.limit(limit).stream())
            # --- END: Pagination Logic ---
            
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                try:
                    items.append(self.model.model_validate(data))
                except ValidationError as e:
                    print(f"Warning: Skipping document {doc.id} in 'get_all' due to validation error: {e}")
            
            # Get the ID of the last document for the next cursor
            last_doc_id = docs[-1].id if docs else None
            return items, last_doc_id
        
        return await asyncio.to_thread(_get_all_sync)

    async def get(
        self, 
        doc_id: str, 
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """Fetches a single document by ID, with an option to include deleted."""
        def _get_sync():
            doc = self.db.document(doc_id).get()
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            if (data.get("deleted") == True and 
                not include_deleted and 
                self._has_timestamps):
                return None
                
            data["id"] = doc.id
            
            try:
                return self.model.model_validate(data)
            except ValidationError as e:
                print(f"Warning: Document {doc_id} failed validation and will be skipped. Error: {e}")
                return None
        
        return await asyncio.to_thread(_get_sync)

    async def create(self, data: CreateSchemaType, doc_id: Optional[str] = None) -> ModelType:
        """Creates a new document from a 'Base' model."""
        def _create_sync():
            data_dict = data.model_dump(exclude_none=True)
            
            if self._has_timestamps:
                data_dict["created_at"] = get_current_iso_time()
                data_dict["deleted"] = False
            
            if doc_id:
                new_doc_ref = self.db.document(doc_id)
                new_doc_ref.set(data_dict)
            else:
                new_doc_ref = self.db.add(data_dict)[1]
            
            created_doc = new_doc_ref.get()
            response_data = created_doc.to_dict()
            response_data["id"] = created_doc.id
            return self.model.model_validate(response_data)
            
        return await asyncio.to_thread(_create_sync)

    async def delete(self, doc_id: str):
        """Soft-deletes a document (if supported), otherwise hard-deletes."""
        def _delete_sync():
            doc_ref = self.db.document(doc_id)
            if not doc_ref.get().exists:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
            
            if self._has_timestamps:
                payload = {"deleted": True, "deleted_at": get_current_iso_time()}
                doc_ref.update(payload)
            else:
                doc_ref.delete()
            return True
        
        return await asyncio.to_thread(_delete_sync)

    async def restore(self, doc_id: str) -> ModelType:
        """Restores a soft-deleted document."""
        def _restore_sync():
            doc_ref = self.db.document(doc_id)
            if not doc_ref.get().exists:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
            
            if not self._has_timestamps:
                 raise HTTPException(status.HTTP_400_BAD_REQUEST, "This model does not support restore")

            payload = {
                "deleted": False,
                "deleted_at": None,
                "updated_at": get_current_iso_time()
            }
            doc_ref.update(payload)
            
            restored_doc = doc_ref.get()
            response_data = restored_doc.to_dict()
            response_data["id"] = restored_doc.id
            return self.model.model_validate(response_data)
        
        return await asyncio.to_thread(_restore_sync)


    async def update(self, doc_id: str, data: UpdateSchemaType) -> ModelType:
        """Updates a document from a 'Base' or 'Update' model (partial update)."""
        def _update_sync():
            doc_ref = self.db.document(doc_id)
            if not doc_ref.get().exists:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
            
            data_dict = data.model_dump(exclude_unset=True) 

            if self._has_timestamps and "updated_at" not in data_dict:
                data_dict["updated_at"] = get_current_iso_time()
            
            doc_ref.update(data_dict)
            
            updated_doc = doc_ref.get()
            response_data = updated_doc.to_dict()
            response_data["id"] = updated_doc.id
            return self.model.model_validate(response_data)
        
        return await asyncio.to_thread(_update_sync)

    async def where(
        self, 
        field: str, 
        operator: str, 
        value: Any, 
        limit: int = 20, 
        start_after: Optional[str] = None
    ) -> Tuple[List[ModelType], Optional[str]]:
        """
        Performs an efficient 'where' query that ALSO filters for
        non-deleted items at the database level and supports pagination.
        
        Returns a tuple: (list_of_items, last_document_id)
        """
        def _where_sync():
            items = []
            
            # 1. Start the query on the field you requested
            query = self.db.where(filter=FieldFilter(field, operator, value))
            
            # 2. Add the 'deleted' filter to the DATABASE QUERY
            if self._has_timestamps:
                query = query.where(filter=FieldFilter("deleted", "!=", True))
            
            # --- NEW: Pagination Logic ---
            if start_after:
                try:
                    start_doc = self.db.document(start_after).get()
                    if start_doc.exists:
                        query = query.start_after(start_doc)
                except Exception as e:
                    print(f"Warning: Invalid start_after document ID '{start_after}': {e}")
            
            docs = list(query.limit(limit).stream())
            # --- END: Pagination Logic ---
                           
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                try:
                    items.append(self.model.model_validate(data))
                except ValidationError as e:
                    print(f"Warning: Skipping document {doc.id} in 'where' query due to validation error: {e}")
            
            last_doc_id = docs[-1].id if docs else None
            return items, last_doc_id
        
        return await asyncio.to_thread(_where_sync)

    # ---
    # --- NEW FUNCTION 1: PERMANENTLY DELETE BY ID ---
    # ---
    async def delete_permanent(self, doc_id: str) -> bool:
        """
        PERMANENTLY deletes a single document by its ID.
        This is irreversible and does not respect soft-delete.
        """
        def _delete_permanent_sync():
            doc_ref = self.db.document(doc_id)
            if doc_ref.get().exists:
                doc_ref.delete()
                return True
            return False # Document didn't exist
        
        return await asyncio.to_thread(_delete_permanent_sync)

    # ---
    # --- NEW FUNCTION 2: PERMANENTLY DELETE BY QUERY ---
    # ---
    async def purge_where(self, field: str, operator: str, value: Any) -> int:
        """
        PERMANENTLY deletes all documents matching a query.
        This is irreversible and is used to clean up orphaned data.
        
        Returns:
            int: The number of documents deleted.
        """
        def _purge_where_sync():
            query = self.db.where(filter=FieldFilter(field, operator, value))
            
            deleted_count = 0
            docs = list(query.stream()) # Get all docs at once
            
            if not docs:
                return 0
                
            batch = db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
                
                # Firestore batches have a 500 operation limit
                if deleted_count % 499 == 0:
                    batch.commit()
                    batch = db.batch()
            
            batch.commit() # Commit any remaining
            return deleted_count

        try:
            deleted_count = await asyncio.to_thread(_purge_where_sync)
            print(f"Purged {deleted_count} docs from '{self.collection_name}' where {field} {operator} {value}")
            return deleted_count
        except Exception as e:
            print(f"Error purging {self.collection_name} for {value}: {e}")
            return 0