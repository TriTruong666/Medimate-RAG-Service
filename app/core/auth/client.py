from app.core.auth.types import TokenValidationResult


class AuthClient:
    def validate_token(self, token: str) -> TokenValidationResult:
        raise NotImplementedError