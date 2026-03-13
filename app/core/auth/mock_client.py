from app.core.auth.client import AuthClient
from app.core.auth.types import TokenValidationResult


class MockAuthClient(AuthClient):
    def validate_token(self, token: str) -> TokenValidationResult:
        if token == "demo-admin":
            return TokenValidationResult(
                is_valid = True,
                user_id = "admin-1",
                roles = ["admin"]
            )
        if token == "demo-user":
            return TokenValidationResult(
                is_valid = True,
                user_id = "user-1",
                roles = ["user"]
            )
        return TokenValidationResult(
            is_valid = False,
            user_id = "",
            roles = []
        )