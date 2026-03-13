import grpc

from app.contracts import auth_pb2, auth_pb2_grpc
from app.core.auth.client import AuthClient
from app.core.auth.types import TokenValidationResult


class GrpcAuthClient(AuthClient):
    def __init__(self, target: str, timeout_seconds: float = 2.0):
        self.target = target
        self.timeout_seconds = timeout_seconds

    def validate_token(self, token: str) -> TokenValidationResult:
        try:
            with grpc.insecure_channel(self.target) as channel:
                stub = auth_pb2_grpc.AuthServiceStub(channel)
                req = auth_pb2.ValidateTokenRequest(token=token)
                resp = stub.ValidateToken(req, timeout=self.timeout_seconds)
                return TokenValidationResult(
                    is_valid=resp.is_valid,
                    user_id=resp.user_id,
                    roles=list(resp.roles)
                )
        except grpc.RpcError as e:
            return TokenValidationResult(
                is_valid=False,
                user_id="",
                roles=[]
            )