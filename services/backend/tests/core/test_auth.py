"""Tests for authentication utilities."""

import bcrypt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from services.backend.src.config.settings import Settings
from services.backend.src.core.auth import get_current_user, require_admin
from services.backend.src.schemas.auth import UserCredentials


def _hash(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        admin_password="admin_pwd",
        user_password="user_pwd",
    )


class TestGetCurrentUser:
    def test_valid_admin(self, settings: Settings) -> None:
        creds = HTTPBasicCredentials(username="admin", password="admin_pwd")
        user = get_current_user(creds, settings)
        assert user.username == "admin"
        assert user.role == "admin"

    def test_valid_datascientest(self, settings: Settings) -> None:
        creds = HTTPBasicCredentials(username="datascientest", password="user_pwd")
        user = get_current_user(creds, settings)
        assert user.username == "datascientest"
        assert user.role == "user"

    def test_wrong_password(self, settings: Settings) -> None:
        creds = HTTPBasicCredentials(username="admin", password="wrong")
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds, settings)
        assert exc.value.status_code == 401

    def test_unknown_user(self, settings: Settings) -> None:
        creds = HTTPBasicCredentials(username="unknown", password="pwd")
        with pytest.raises(HTTPException) as exc:
            get_current_user(creds, settings)
        assert exc.value.status_code == 401


class TestRequireAdmin:
    def test_admin_ok(self) -> None:
        user = UserCredentials(username="admin", password="x", role="admin")
        result = require_admin(user)
        assert result.username == "admin"

    def test_admin_forbidden(self) -> None:
        user = UserCredentials(username="datascientest", password="x", role="user")
        with pytest.raises(HTTPException) as exc:
            require_admin(user)
        assert exc.value.status_code == 403
