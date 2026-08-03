"""Authentication and authorization utilities."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from services.backend.src.config.settings import Settings, get_settings
from services.backend.src.schemas.auth import UserCredentials

security = HTTPBasic()


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """Verify a plaintext password against a bcrypt hash."""
#     return bcrypt.checkpw(
#         plain_password.encode("utf-8"),
#         hashed_password.encode("utf-8"),
#     )


def get_current_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserCredentials:
    """Authenticate user and return UserCredentials."""
    users = {
        "admin": UserCredentials(username="admin", password=settings.admin_password, role="admin"),
        "datascientest": UserCredentials(username="datascientest", password=settings.user_password, role="user"),
    }
    user = users.get(credentials.username)

    if user is None or credentials.password != user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user


def require_admin(
    user: Annotated[UserCredentials, Depends(get_current_user)],
) -> UserCredentials:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
