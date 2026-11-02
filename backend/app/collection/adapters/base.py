"""Abstract Base Class for DCE (Data Collection Engine) Adapters."""

import abc
import time
from typing import Dict, Any, Tuple, Set, Optional
from datetime import datetime, timezone
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput


class BaseCollectorAdapter(abc.ABC):
    """Abstract interface that all DCE collectors (CLI, API, and Synthetic) must implement."""

    @property
    @abc.abstractmethod
    def tool_id(self) -> str:
        """Unique identifier matching TIMS tool registry (e.g. 'whois_lookup', 'dns_lookup', 'hibp')."""
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable display name."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Description of the collection capability."""
        pass

    @property
    @abc.abstractmethod
    def collector_type(self) -> CollectorType:
        """Execution mechanism: CLI (Docker sandbox), API (HTTPX client), or SYNTHETIC."""
        pass

    @property
    @abc.abstractmethod
    def supported_target_types(self) -> Set[TargetType]:
        """Accepted target identifier categories (domain, ip, email, username)."""
        pass

    @property
    def requires_approval(self) -> bool:
        """Whether human administrator approval is required prior to job execution."""
        return False

    @property
    def requires_api_key(self) -> bool:
        """Whether a configured API credential is required."""
        return False

    def is_available(self) -> Tuple[bool, str]:
        """Checks whether the adapter is ready to execute in current environment."""
        return True, ""

    @abc.abstractmethod
    def validate_target(self, target: str) -> None:
        """Validates that target matches expected format and does not contain illegal patterns."""
        pass

    @abc.abstractmethod
    async def execute(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RawCollectorOutput:
        """Executes collection and returns a standardized RawCollectorOutput."""
        pass

