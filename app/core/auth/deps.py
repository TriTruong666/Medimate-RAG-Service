from typing import Optional
import logging

from fastapi import Depends, HTTPException, status
from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.auth.mock_client import MockAuthClient
from app.core.auth.grpc_client import GrpcAuthClient

logger = logging.getLogger(__name__)
auth_provider = (settings.AUTH_PROVIDER or "mock").lower()

if auth_provider == "grpc":
    _auth_client = GrpcAuthClient(
        target=settings.AUTH_GRPC_TARGET,
        timeout_seconds=settings.AUTH_GRPC_TIMEOUT_SECONDS,
    )
else:
    _auth_client = MockAuthClient()

logger.info("Auth provider initialized: %s", auth_provider)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
):
    if settings.ENVIRONMENT == "dev":
        return {"user_id": "dev_user", "roles": ["admin"]}

    if not credentials:
        logger.warning("Auth failed: missing bearer credentials provider=%s", auth_provider)
        raise HTTPException(status_code=401, detail="Thiếu Bearer token")

    token = credentials.credentials
    logger.debug(
        "Auth validate started provider=%s scheme=%s token_length=%d",
        auth_provider,
        credentials.scheme,
        len(token),
    )
    result = _auth_client.validate_token(token)

    if not result.is_valid:
        logger.warning(
            "Auth failed: token invalid provider=%s token_length=%d",
            auth_provider,
            len(token),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")

    logger.debug(
        "Auth success provider=%s user_id=%s roles=%s",
        auth_provider,
        result.user_id,
        result.roles,
    )
    return {
        "user_id": result.user_id,
        "roles": result.roles
    }


def require_roles(allowed_roles: list[str]):
    def checker(principal=Depends(get_current_principal)):
        if settings.ENVIRONMENT == "dev":
            return principal

        user_roles = principal.get("roles", [])
        if not any(role in user_roles for role in allowed_roles):
            logger.warning(
                "Auth failed: insufficient role provider=%s user_id=%s user_roles=%s allowed_roles=%s",
                auth_provider,
                principal.get("user_id"),
                user_roles,
                allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Không có quyền truy cập. Cần một trong các role: {allowed_roles}",
            )
        return principal
    return checker


RequireAdmin = Depends(require_roles(["admin"]))
RequireAdminOrUser = Depends(require_roles(["admin", "user"]))