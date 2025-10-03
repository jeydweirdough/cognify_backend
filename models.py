from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ------------------------
# Utility
# ------------------------
def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ------------------------
# API Schemas (for requests)
# ------------------------
class SignUpSchema(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    role_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "StrongPassword@123",
                "first_name": "John",
                "last_name": "Doe",
                "nickname": "Johnny",
                "role_id": "role123",
                "major_id": "major456"
            }
        }


class LoginSchema(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "StrongPassword@123"
            }
        }


# ------------------------
# Firestore Models (ERD)
# ------------------------
class RolePermissionModel(BaseModel):
    id: Optional[str] = None
    role_id: Optional[str] = None
    action: str

    def to_dict(self) -> Dict[str, Any]:
        return {"role_id": self.role_id, "action": self.action}

    @classmethod
    def from_dict(cls, d: Dict[str, Any], doc_id: Optional[str] = None):
        return cls(id=doc_id, role_id=d.get("role_id"), action=d.get("action", ""))


class RoleModel(BaseModel):
    id: Optional[str] = None
    name: str
    permissions: Optional[List[RolePermissionModel]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, Any],
        doc_id: Optional[str] = None,
        permissions: Optional[List[RolePermissionModel]] = None,
    ):
        return cls(id=doc_id, name=d.get("name", ""), permissions=permissions)


class UserProfileModel(BaseModel):
    id: Optional[str] = None   # Firestore doc id (same as Firebase UID)
    user_id: str               # Firebase Auth UID
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    update_at: str = Field(default_factory=_now_iso)
    deleted: bool = False
    role_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "middle_name": self.middle_name,
            "last_name": self.last_name,
            "nickname": self.nickname,
            "update_at": self.update_at,
            "deleted": self.deleted,
            "role_id": self.role_id,

        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], doc_id: Optional[str] = None):
        return cls(
            id=doc_id,
            user_id=d["user_id"],
            first_name=d.get("first_name"),
            middle_name=d.get("middle_name"),
            last_name=d.get("last_name"),
            nickname=d.get("nickname"),
            update_at=d.get("update_at", _now_iso()),
            deleted=d.get("deleted", False),
            role_id=d.get("role_id"),
        )
