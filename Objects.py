from pydantic import BaseModel, BeforeValidator, validator
from typing import List, Optional
from datetime import datetime, timedelta

class Token(BaseModel):
    access_token: str
    expires_in: int
    expires_at: datetime = None
    refresh_token: str

    @validator("expires_at", pre=True, always=True)
    def set_expires_at(cls, v, values):
        return datetime.now() + timedelta(seconds=values["expires_in"])

class User(BaseModel):
    id: int
    username: str
    discriminator: str
    global_name: str = None
    avatar: str = None

class UserPermissions(BaseModel):
    user: User
    evaluation: bool = False
    undercut: bool = False
    scraper: bool = False
    admin: bool = False
    owner: bool = False
