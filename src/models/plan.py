"""Plan contract for Q CodeAnzenn MVP.

This model intentionally rejects any absolute or ambiguous path form.
All operation paths must be workspace-relative.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ALLOWED_OPS = {"list_dir", "read_file", "create_file", "patch_file"}
_WIN_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_PREFIX = re.compile(r"^(\\\\|//)")


class PlanStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RequestedBy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    telegram_user_id: int = Field(ge=1)
    chat_id: int = Field(ge=1)


class PolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1, max_length=64)
    allowed_path_prefixes: list[str] = Field(min_length=1)
    network_ops: bool = False
    shell_exec: bool = False


class RiskReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    level: RiskLevel
    reasons: list[str] = Field(default_factory=list)
    blocked: bool


class PlanOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op_id: str = Field(pattern=r"^op_[A-Za-z0-9_-]{1,32}$")
    type: Literal["list_dir", "read_file", "create_file", "patch_file"]
    path: str
    content: Optional[str] = None
    patch: Optional[str] = None

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        raw = value.strip()
        if not raw:
            raise ValueError("path must not be empty")
        if _WIN_DRIVE_PREFIX.match(raw):
            raise ValueError("absolute Windows path is not allowed")
        if raw.startswith("/") or raw.startswith("\\"):
            raise ValueError("absolute path is not allowed")
        if _UNC_PREFIX.match(raw):
            raise ValueError("UNC path is not allowed")

        normalized = raw.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized == ".":
            return normalized
        if ":" in normalized:
            raise ValueError("path must not contain drive-like separator ':'")
        if any(c in normalized for c in ("<", ">", "*", "?", "|", "\"")):
            raise ValueError("path contains blocked wildcard or placeholder character")

        parts = normalized.split("/")
        if any(p in ("", ".") for p in parts):
            raise ValueError("path has empty or self-reference segments")
        if ".." in parts:
            raise ValueError("parent traversal is not allowed")
        return normalized

    @model_validator(mode="after")
    def validate_payload_by_type(self) -> "PlanOp":
        if self.type == "create_file":
            if self.content is None or self.content == "":
                raise ValueError("create_file requires content")
            if self.patch is not None:
                raise ValueError("create_file must not include patch")
        elif self.type == "patch_file":
            if self.patch is None or self.patch == "":
                raise ValueError("patch_file requires patch")
            if self.content is not None:
                raise ValueError("patch_file must not include content")
        else:
            if self.content is not None or self.patch is not None:
                raise ValueError("read/list operations must not include content or patch")

        if self.type not in ALLOWED_OPS:
            raise ValueError("operation type is not allowed")
        return self


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(pattern=r"^pln_[A-Za-z0-9_-]{6,64}$")
    short_token: str = Field(pattern=r"^[A-Za-z0-9]{6,12}$")
    status: PlanStatus = PlanStatus.PENDING_APPROVAL

    requested_by: RequestedBy
    request_text: str = Field(min_length=1, max_length=4000)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime

    policy_snapshot: PolicySnapshot
    ops: list[PlanOp] = Field(min_length=1, max_length=200)
    risk: RiskReport

    @model_validator(mode="after")
    def validate_dates(self) -> "Plan":
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        return self

    @field_validator("ops")
    @classmethod
    def ensure_workspace_relative_ops(cls, ops: list[PlanOp]) -> list[PlanOp]:
        for op in ops:
            if op.path == ".":
                if op.type != "list_dir":
                    raise ValueError("'.' path is only allowed for list_dir")
        return ops
