"""Vertex that reads conversation memory and prepares context for LLM vertices."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from vertex_flow.memory.memory import Memory
from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import CONVERSATION_HISTORY, VERTEX_TYPE_MEMORY
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.vertex import Vertex

logging = LoggerUtil.get_logger(__name__)


class MemoryReaderVertex(Vertex[Dict[str, Any]]):
    """Fetches recent history and selected context fields for a user.

    Output schema:
        {
            "user_id": str,
            "history_records": List[dict],  # Raw records as stored in memory
            "conversation_history": List[dict],  # Chronological messages for LLMVertex
            "context_values": Dict[str, Any],  # Selected ctx_* entries
        }
    """

    def __init__(
        self,
        *,
        id: str,
        memory: Memory,
        name: Optional[str] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        user_id_key: str = "user_id",
        history_len: int = 20,
        ctx_keys: Optional[List[str]] = None,
        default_user_id: str = "anonymous",
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            task_type=VERTEX_TYPE_MEMORY,
            task=None,
            params={},
            variables=variables or [],
        )
        self.memory = memory
        self.user_id_key = user_id_key
        self.history_len = history_len
        self.ctx_keys = ctx_keys or []
        self.default_user_id = default_user_id

    # ------------------------------------------------------------------
    # Execution lifecycle
    # ------------------------------------------------------------------
    def execute(self, inputs: Optional[Dict[str, Any]] = None, context: WorkflowContext[Dict[str, Any]] = None):
        resolved_inputs = self.resolve_dependencies(inputs=inputs) if self.variables else {}
        payload: Dict[str, Any] = {}
        payload.update(resolved_inputs or {})
        payload.update(inputs or {})

        user_id = self._resolve_user_id(payload, context)

        history_records = self._load_history(user_id)
        conversation_history = self._build_conversation(history_records)
        ctx_values = self._load_ctx_values(user_id)

        self.output = {
            "user_id": user_id,
            "history_records": history_records,
            CONVERSATION_HISTORY: conversation_history,
            "context_values": ctx_values,
        }
        return self.output

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_history(self, user_id: str) -> List[Dict[str, Any]]:
        if self.history_len <= 0:
            return []
        try:
            return self.memory.recent_history(user_id, n=self.history_len)
        except Exception as exc:  # pragma: no cover - defensive logging
            logging.error(f"MemoryReaderVertex[{self.id}] failed to load history: {exc}")
            return []

    def _build_conversation(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        for record in reversed(records):  # chronological order
            role = record.get("role", "user")
            content = self._extract_text(record.get("content"))
            if not content:
                continue
            messages.append({"role": role, "content": content})
        return messages

    def _load_ctx_values(self, user_id: str) -> Dict[str, Any]:
        values: Dict[str, Any] = {}
        for key in self.ctx_keys:
            try:
                value = self.memory.ctx_get(user_id, key)
            except Exception as exc:  # pragma: no cover - defensive logging
                logging.error(f"MemoryReaderVertex[{self.id}] failed to load ctx '{key}': {exc}")
                continue
            if value is not None:
                values[key] = value
        return values

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            if "text" in content:
                return str(content.get("text", ""))
            if "content" in content:
                return self._extract_text(content.get("content"))
            return json.dumps(content, ensure_ascii=False)
        if isinstance(content, list):
            parts = [self._extract_text(item) for item in content]
            return " ".join(part for part in parts if part)
        if content is None:
            return ""
        return str(content)

    def _resolve_user_id(
        self,
        payload: Dict[str, Any],
        context: Optional[WorkflowContext[Dict[str, Any]]],
    ) -> str:
        if self.user_id_key and self.user_id_key in payload:
            return str(payload[self.user_id_key])

        if context:
            user_params = context.get_user_parameters()
            if self.user_id_key in user_params:
                return str(user_params[self.user_id_key])
            if "user_id" in user_params:
                return str(user_params["user_id"])

        return self.default_user_id
