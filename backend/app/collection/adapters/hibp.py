"""HIBP (Have I Been Pwned) API Collector Adapter using HTTPX."""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Set, Optional, List
import httpx
from fastapi import HTTPException

from app.collection.adapters.base import BaseCollectorAdapter
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput
from app.collection.schemas import HibpBreachItem, HibpLookupResult
from app.core.config import settings

logger = logging.getLogger("zaprica.collection.hibp")


class HibpCollectorAdapter(BaseCollectorAdapter):
    """Have I Been Pwned API Collector querying email breach records."""

    BASE_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"

    @property
    def tool_id(self) -> str:
        return "hibp"

    @property
    def name(self) -> str:
        return "Have I Been Pwned Breach Intelligence"

    @property
    def description(self) -> str:
        return "Queries the commercial Have I Been Pwned API v3 for known security breach exposures for an email."

    @property
    def collector_type(self) -> CollectorType:
        return CollectorType.API

    @property
    def supported_target_types(self) -> Set[TargetType]:
        return {TargetType.EMAIL}

    @property
    def requires_api_key(self) -> bool:
        return True

    def is_available(self) -> Tuple[bool, str]:
        if not settings.HIBP_API_KEY:
            return False, "HIBP_API_KEY is not configured in server environment"
        return True, ""

    def validate_target(self, target: str) -> None:
        email = target.strip().lower()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) or email.startswith("-"):
            raise HTTPException(status_code=400, detail=f"Invalid email address format for breach lookup: '{target}'")

    async def execute(
        self,
        target: str,
        options: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> RawCollectorOutput:
        self.validate_target(target)
        email = target.strip().lower()

        available, note = self.is_available()
        if not available:
            return RawCollectorOutput(
                tool_id=self.tool_id,
                tool_version="1.0.0",
                status=CollectorStatus.UNAVAILABLE,
                target=email,
                target_type=TargetType.EMAIL,
                warnings=[note],
                errors=["API key not configured"],
                raw_bytes=b"{}",
                stdout="",
                parsed_data={"email": email, "breaches": [], "status": "unavailable"},
                is_synthetic=False,
                collected_at=datetime.now(timezone.utc),
            )

        headers = {
            "hibp-api-key": settings.HIBP_API_KEY,
            "user-agent": "ZAPRICA-OSINT-Platform/1.0",
            "accept": "application/json",
        }

        url = f"{self.BASE_URL}/{email}"
        params = {"truncateResponse": "false"}

        start_time = time.monotonic()
        warnings: List[str] = []
        errors: List[str] = []
        breaches: List[HibpBreachItem] = []
        raw_bytes = b"[]"
        exit_code = 0
        status = CollectorStatus.SUCCESS

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code == 404:
                    # Clean: email has no known breaches
                    raw_bytes = b"[]"
                    breaches = []
                    status = CollectorStatus.SUCCESS

                elif response.status_code == 429:
                    retry_after = response.headers.get("retry-after", "few")
                    errors.append(f"HIBP rate limit exceeded. Retry after {retry_after} seconds.")
                    status = CollectorStatus.TIMED_OUT
                    raw_bytes = response.content

                elif response.status_code in (401, 403):
                    errors.append("HIBP API key rejected or unauthorized.")
                    status = CollectorStatus.FAILED
                    raw_bytes = response.content

                else:
                    response.raise_for_status()
                    raw_bytes = response.content
                    data = response.json()
                    if isinstance(data, list):
                        for b in data:
                            breaches.append(HibpBreachItem(
                                name=b.get("Name", "Unknown"),
                                title=b.get("Title", b.get("Name", "Unknown")),
                                domain=b.get("Domain", ""),
                                breach_date=b.get("BreachDate", "Unknown"),
                                added_date=b.get("AddedDate"),
                                pwn_count=b.get("PwnCount", 0),
                                data_classes=b.get("DataClasses", []),
                                is_verified=b.get("IsVerified", False),
                                is_fabricated=b.get("IsFabricated", False),
                                is_sensitive=b.get("IsSensitive", False),
                            ))

        except httpx.TimeoutException:
            errors.append("Connection to HIBP API timed out after 20 seconds.")
            status = CollectorStatus.TIMED_OUT
            exit_code = 124
        except httpx.HTTPStatusError as e:
            errors.append(f"HTTP error from HIBP API: {e.response.status_code}")
            status = CollectorStatus.FAILED
            exit_code = 1
        except Exception as e:
            errors.append(f"Unexpected network error communicating with HIBP: {str(e)}")
            status = CollectorStatus.FAILED
            exit_code = 1

        duration_ms = int((time.monotonic() - start_time) * 1000)

        result_payload = HibpLookupResult(
            email=email,
            breaches=breaches,
            breach_count=len(breaches),
            status="ok" if not errors else "error",
        )

        return RawCollectorOutput(
            tool_id=self.tool_id,
            tool_version="1.0.0",
            status=status,
            target=email,
            target_type=TargetType.EMAIL,
            raw_bytes=raw_bytes,
            stdout=raw_bytes.decode("utf-8", errors="replace"),
            stderr="\n".join(errors),
            exit_code=exit_code,
            execution_duration_ms=duration_ms,
            warnings=warnings,
            errors=errors,
            parsed_data=result_payload.model_dump(),
            is_synthetic=False,
            collected_at=datetime.now(timezone.utc),
        )

