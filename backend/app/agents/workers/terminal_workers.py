"""Dedicated Terminal Workers supervised by the Terminal Head Agent."""

from typing import Dict, Any, List
from app.terminal.terminal_manager import terminal_manager, TerminalTaskExecutionResult


class CliOsintWorker:
    """Worker for executing authorized command-line OSINT inquiry tools."""

    @classmethod
    async def run(cls, task_id: str, tool_id: str, arguments: Dict[str, Any]) -> TerminalTaskExecutionResult:
        return await terminal_manager.execute_task(
            task_id=task_id,
            tool_id=tool_id,
            arguments=arguments,
        )


class NetworkIntelligenceWorker:
    """Worker for network intelligence tools (DNS, WHOIS, TLS Certificate analysis)."""

    @classmethod
    async def run_dns(cls, task_id: str, domain: str, record_type: str = "A") -> TerminalTaskExecutionResult:
        return await terminal_manager.execute_task(
            task_id=task_id,
            tool_id="dns_lookup",
            arguments={"target": domain, "record_type": record_type},
        )

    @classmethod
    async def run_whois(cls, task_id: str, domain: str) -> TerminalTaskExecutionResult:
        return await terminal_manager.execute_task(
            task_id=task_id,
            tool_id="whois_lookup",
            arguments={"target": domain},
        )


class MetadataAnalysisWorker:
    """Worker for file and document metadata analysis (e.g. exiftool)."""

    @classmethod
    async def extract_metadata(cls, task_id: str, file_path_or_url: str) -> TerminalTaskExecutionResult:
        return await terminal_manager.execute_task(
            task_id=task_id,
            tool_id="metadata_extractor",
            arguments={"target": file_path_or_url},
        )


class FileDocumentProcessingWorker:
    """Worker for parsing, classifying, and extracting textual entities from raw investigation documents."""

    @classmethod
    async def process_document(cls, task_id: str, file_uri: str) -> Dict[str, Any]:
        result = await terminal_manager.execute_task(
            task_id=task_id,
            tool_id="metadata_extractor",
            arguments={"target": file_uri},
        )
        return {
            "file_uri": file_uri,
            "status": result.status,
            "stdout": result.stdout,
            "exit_code": result.exit_code,
        }
