import grpc
import logging

from app.contracts import auth_pb2, auth_pb2_grpc
from app.core.auth.client import AuthClient
from app.core.auth.types import TokenValidationResult

logger = logging.getLogger(__name__)


class GrpcAuthClient(AuthClient):
    def __init__(self, target: str, timeout_seconds: float = 2.0):
        self.target = target
        self.timeout_seconds = timeout_seconds
        self.channel = None
        self.stub = None

    def validate_token(self, token: str) -> TokenValidationResult:
        try:
            logger.debug(
                "Calling AuthService.ValidateToken target=%s timeout=%.2fs token_length=%d",
                self.target,
                self.timeout_seconds,
                len(token),
            )
            with grpc.insecure_channel(self.target) as channel:
                stub = auth_pb2_grpc.AuthServiceStub(channel)
                req = auth_pb2.ValidateTokenRequest(token=token)
                resp = stub.ValidateToken(req, timeout=self.timeout_seconds)
                logger.debug(
                    "AuthService.ValidateToken responded target=%s is_valid=%s user_id=%s roles=%s",
                    self.target,
                    resp.is_valid,
                    resp.user_id,
                    list(resp.roles),
                )
                return TokenValidationResult(
                    is_valid=resp.is_valid,
                    user_id=resp.user_id,
                    roles=list(resp.roles)
                )
        except grpc.RpcError as e:
            logger.error(
                "AuthService.ValidateToken rpc error target=%s status=%s details=%s",
                self.target,
                e.code(),
                e.details(),
            )
            return TokenValidationResult(
                is_valid=False,
                user_id="",
                roles=[]
            )