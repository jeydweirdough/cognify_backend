from core.firebase import db
from database.models import get_current_iso_time, TimestampModel
from typing import List, Optional, Dict, Any, Type, TypeVar
from pydantic import BaseModel

# --- Generic Type for Pydantic Models ---
# This allows our service to work with any class that inherits from BaseModel
ModelType = TypeVar("ModelType", bound=BaseModel)

# --- Generic Firestore Model Service Class ---
class FirestoreModelService:
    """
    A generic reusable service for Firestore CRUD operations
    that automatically handles Pydantic model validation.
    """
    def __init__(self, collection_name: str, model: Type[ModelType]):
        self.collection_name = collection_name
        self.model: Type[ModelType] = model
        self.db = db.collection(self.collection_name)

    def get_all(self) -> List[ModelType]:
        """Fetches all documents and parses them into model objects."""
        items = []
        # Check if the model has a 'deleted' field to filter by it
        has_deleted_field = "deleted" in self.model.model_fields
        
        query = self.db
        if has_deleted_field:
            query = query.where("deleted", "!=", True)
            
        stream = query.stream()
        for doc in stream:
            data = doc.to_dict()
            data["id"] = doc.id  # Add the document ID to the data
            items.append(self.model.model_validate(data))
        return items

    def get(self, doc_id: str) -> Optional[ModelType]:
        """Fetches a single document and parses it into a model object."""
        doc = self.db.document(doc_id).get()
        if not doc.exists:
            return None
        
        data = doc.to_dict()
        data["id"] = doc.id  # Add the document ID
        return self.model.model_validate(data)

    def create(self, data: ModelType, doc_id: Optional[str] = None):
        """
        Creates a new document from a model object.
        If doc_id is provided, it's used. Otherwise, Firestore auto-generates one.
        """
        # Exclude 'id' field if it exists, as it's not part of the doc data
        data_dict = data.model_dump(exclude_none=True, exclude={"id"})
        
        if doc_id:
            # Set with a specific ID
            return self.db.document(doc_id).set(data_dict)
        else:
            # Let Firestore auto-generate the ID
            return self.db.add(data_dict)

    def delete(self, doc_id: str):
        """
        Soft-deletes a document if the model supports it (has TimestampModel fields).
        Otherwise, performs a hard delete.
        """
        # Check if our model inherits from TimestampModel
        if issubclass(self.model, TimestampModel):
            payload = {
                "deleted": True, 
                "deleted_at": get_current_iso_time()
            }
            return self.db.document(doc_id).update(payload)
        else:
            # Fallback to hard delete if the model doesn't support it
            return self.db.document(doc_id).delete()

    def update(self, doc_id: str, data: Dict[str, Any]):
        """
        Updates a document with new data from a dictionary.
        Automatically handles 'updated_at' timestamp if the model supports it.
        """
        # Check if our model inherits from TimestampModel
        if issubclass(self.model, TimestampModel):
            # Only add updated_at if it's not already being set manually
            if "updated_at" not in data:
                data["updated_at"] = get_current_iso_time()
        
        return self.db.document(doc_id).update(data)

    # --- You can add other useful methods here ---
    def where(self, field: str, operator: str, value: Any) -> List[ModelType]:
        """Performs a simple 'where' query and parses results."""
        items = []
        stream = self.db.where(field, operator, value).stream()
        for doc in stream:
            data = doc.to_dict()
            data["id"] = doc.id
            items.append(self.model.model_validate(data))
        return items