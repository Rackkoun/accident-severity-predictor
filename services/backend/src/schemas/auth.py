"""
User schemas for authentication and authorization.
"""

from pydantic import BaseModel


class UserCredentials(BaseModel):
    """User credentials model for Basic Auth."""

    username: str
    password: str
    role: str
