from dataclasses import dataclass
from typing import List


@dataclass
class TokenValidationResult:
    is_valid: bool
    user_id: str
    roles: List[str]