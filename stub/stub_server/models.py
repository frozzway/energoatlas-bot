from pydantic import BaseModel


class AuthModel(BaseModel):
    login: str
    password: str
