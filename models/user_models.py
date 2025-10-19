from pydantic import BaseModel
from typing import Optional

class SignUpSchema(BaseModel):
    email: str
    password: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    nickname: Optional[str] = None
    role_id: Optional[str] = None

class LoginSchema(BaseModel):
    email: str
    password: str

class UserProfileModel(BaseModel):
    id: str
    user_id: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    nickname: Optional[str] = None
    role_id: Optional[str] = None
    deleted: Optional[bool] = False

    def to_dict(self):
        return self.dict(exclude_none=True)
