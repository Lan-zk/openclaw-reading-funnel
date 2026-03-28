"""Base adapter interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..models import RawFeedItem, SourceDescriptor, SourceSyncPlan


@dataclass(slots=True)
class AdapterFailure(Exception):
    failure_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


@dataclass(slots=True)
class FetchRequest:
    source_id: str
    adapter_type: str
    url: str
    headers: dict[str, str]
    query: dict[str, Any]
    timeout_seconds: int
    plan_id: str
    cursor: dict[str, Any] | None
    mock_response: Any = None
    mock_error: dict[str, Any] | None = None


class BaseAdapter(ABC):
    adapter_type: str = ""

    @abstractmethod
    def validate_source_config(self, source_config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_fetch_request(self, descriptor: SourceDescriptor, plan: SourceSyncPlan) -> FetchRequest:
        raise NotImplementedError

    @abstractmethod
    def fetch_batch(self, request: FetchRequest) -> Any:
        raise NotImplementedError

    @abstractmethod
    def convert_response_to_feed_items(
        self,
        descriptor: SourceDescriptor,
        response: Any,
    ) -> tuple[list[RawFeedItem], dict[str, Any] | None]:
        raise NotImplementedError
