from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.auth.mock_client import MockAuthClient
from app.core.auth.grpc_client import GrpcAuthClient

if settings.AUTH_PROVIDER == "grpc":
    _auth_client = GrpcAuthClient(
        target=settings.AUTH_GRPC_TARGET,
        timeout_seconds=settings.AUTH_GRPC_TIMEOUT_SECONDS,
    )
else:
    _auth_client = MockAuthClient()


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Thiếu Bearer token")

    token = credentials.credentials
    result = _auth_client.validate_token(token)

    if not result.is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")
    return {
        "user_id": result.user_id,
        "roles": result.roles
    }


def require_roles(allowed_roles: list[str]):
    def checker(principal=Depends(get_current_principal)):
        user_roles = principal.get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Không có quyền truy cập. Cần một trong các role: {allowed_roles}",
            )
        return principal
    return checker


RequireAdmin = Depends(require_roles(["admin"]))
RequireAdminOrUser = Depends(require_roles(["admin", "user"]))