# services/generic_service.py
from core.firebase import db
from database.models import get_current_iso_time, TimestampModel
from typing import List, Optional, Dict, Any, Type, TypeVar, Literal
from pydantic import BaseModel, ValidationError
import asyncio
from google.cloud.firestore_v1.base_query import FieldFilter
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
    """
    def __init__(self, collection_name: str, model: Type[ModelType]):
        self.collection_name = collection_name
        self.model: Type[ModelType] = model
        self.db = db.collection(self.collection_name)
        self._has_timestamps = issubclass(self.model, TimestampModel)

    async def get_all(
        self, 
        deleted_status: Literal["non-deleted", "deleted-only", "all"] = "non-deleted"
    ) -> List[ModelType]:
        """Fetches documents with an option to filter by deleted status."""
        def _get_all_sync():
            items = []
            query = self.db
            
            if self._has_timestamps:
                # This query is fine because it's only on one field
                if deleted_status == "non-deleted":
                    query = query.where(filter=FieldFilter("deleted", "!=", True))
                elif deleted_status == "deleted-only":
                    query = query.where(filter=FieldFilter("deleted", "==", True))
            
            for doc in query.stream():
                data = doc.to_dict()
                data["id"] = doc.id
                try:
                    items.append(self.model.model_validate(data))
                except ValidationError as e:
                    print(f"Warning: Skipping document {doc.id} in 'get_all' due to validation error: {e}")
            return items
        
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
            
            # This is a Python conditional, it's fast and requires no index
            if (data.get("deleted") == True and 
                not include_deleted and 
                self._has_timestamps):
                return None
                
            data["id"] = doc.id
            
            try:
                return self.model.model_validate(data)
            except ValidationError as e:
                # This catches the "bad data" error (e.g. missing 'user_id' field)
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

    async def where(self, field: str, operator: str, value: Any) -> List[ModelType]:
        """
        Performs a 'where' query and filters for non-deleted items in Python
        to avoid composite indexes.
        """
        def _where_sync():
            items = []
            # --- 1. REMOVED THE COMPOSITE QUERY ---
            # This query is simple and does not require a composite index.
            query = self.db.where(filter=FieldFilter(field, operator, value))
                           
            for doc in query.stream():
                data = doc.to_dict()
                
                # --- 2. ADDED CONDITIONAL AS REQUESTED ---
                # This check happens in Python, *after* fetching.
                # It avoids the composite index entirely.
                if self._has_timestamps and data.get("deleted") == True:
                    continue # Skip this document
                
                data["id"] = doc.id
                try:
                    items.append(self.model.model_validate(data))
                except ValidationError as e:
                    print(f"Warning: Skipping document {doc.id} in 'where' query due to validation error: {e}")
            return items
        
        return await asyncio.to_thread(_where_sync)