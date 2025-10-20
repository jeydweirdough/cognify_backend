from pydantic import BaseModel
from typing import Optional

class SignUpSchema(BaseModel):
    email: str
    password: str

class LoginSchema(BaseModel):
    email: str
    password: str

class UserProfileModel(BaseModel):
    id: str
    user_id: str
    email: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    role_id: Optional[str] = None
    deleted: Optional[bool] = False

    def to_dict(self):
        return self.dict(exclude_none=True)
