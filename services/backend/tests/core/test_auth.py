import bcrypt

from services.backend.src.core.auth import verify_password


class TestVerifyPassword:
    def test_verify_password_success(self):
        hashed = bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode()

        assert verify_password("secret123", hashed) is True

    def test_verify_password_failure(self):
        hashed = bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode()
        assert verify_password("wrongpassword", hashed) is False
