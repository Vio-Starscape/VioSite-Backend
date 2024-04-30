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

    @validator("avatar", pre=True, always=True)
    def set_avatar(cls, v, values):
        if v is None:
            return None
        user_id = values.get("id")
        if user_id is None:
            return None
        return f"https://cdn.discordapp.com/avatars/{user_id}/{v}.png?size=512"

class UserPermissions(BaseModel):
    user: User
    evaluation: bool = False
    undercut: bool = False
    scraper: bool = False
    admin: bool = False
    owner: bool = False

class Scraper(BaseModel):
    name: str
    active: bool
    yoinked: bool

    def mongo_dump(self):
        return {
            "_id": self.name,
            "active": self.active,
            "yoinked": self.yoinked
        }
    
    @classmethod
    def mongo_load(cls, data):
        return Scraper(
            name=data["_id"],
            active=data["active"],
            yoinked=data["yoinked"]
        )