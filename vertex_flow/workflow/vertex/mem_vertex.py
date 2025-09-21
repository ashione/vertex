"""Memory-aware vertex that wraps history persistence and LLM-based summarisation."""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Union

from vertex_flow.memory.memory import Memory
from vertex_flow.utils.logger import LoggerUtil
from vertex_flow.workflow.constants import CONVERSATION_HISTORY, MODEL, SYSTEM, USER, VERTEX_TYPE_MEMORY
from vertex_flow.workflow.context import WorkflowContext
from vertex_flow.workflow.vertex.llm_vertex import LLMVertex
from vertex_flow.workflow.vertex.vertex import Vertex

try:  # Optional import: ChatModel is only needed when summary rules are configured
    from vertex_flow.workflow.chat import ChatModel
except ImportError:  # pragma: no cover - ChatModel import should normally succeed
    ChatModel = Any  # type: ignore


logging = LoggerUtil.get_logger(__name__)


MatchPredicate = Callable[[Dict[str, Any], List[Dict[str, Any]], str], bool]


@dataclass
class SummaryRule:
    """Rule definition for conditional summarisation."""

    name: str
    memory_key: str
    prompt_template: str
    match: Union[str, Sequence[str], Dict[str, Sequence[str]], MatchPredicate, None] = None
    system_prompt: str = (
        "You are a memory assistant. Summarise the provided conversation into concise facts"
        ", keeping only actionable and durable information."
    )
    options: Optional[Dict[str, Any]] = None
    write_strategy: str = "ctx"  # ctx | history
    ttl_sec: Optional[int] = None
    context_keys: Sequence[str] = field(default_factory=tuple)

    def should_write_to_history(self) -> bool:
        return self.write_strategy == "history"


class MemVertex(Vertex[Dict[str, Any]]):
    """Vertex responsible for persisting conversation history and conditional summaries.

    Inputs (resolved via workflow variables or direct inputs) may contain:
        - user_id: Identifier used as memory key (fallback to context user parameters).
        - records: Iterable of message dicts {role, type?, content} to persist.
        - latest_user_message / latest_assistant_message: convenience fields converted to records.
        - conversation_history: historical messages used for summarisation context.

    Output:
        {"user_id": str, "records_written": int, "summaries": List[Dict[str, str]]}
    """

    def __init__(
        self,
        *,
        id: str,
        memory: Memory,
        model: Optional[ChatModel] = None,
        rules: Optional[Sequence[SummaryRule]] = None,
        name: Optional[str] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        user_id_key: str = "user_id",
        history_maxlen: int = 200,
        params: Optional[Dict[str, Any]] = None,
        default_user_id: str = "anonymous",
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            task_type=VERTEX_TYPE_MEMORY,
            task=None,
            params=params or {},
            variables=variables or [],
        )
        self.memory = memory
        self.model = model
        self.rules: List[SummaryRule] = list(rules or [])
        self.user_id_key = user_id_key
        self.history_maxlen = history_maxlen
        self.default_user_id = default_user_id

        if self.rules and self.model is None:
            raise ValueError("MemVertex requires an LLM model when summary rules are provided.")

    # ------------------------------------------------------------------
    # Execution lifecycle
    # ------------------------------------------------------------------
    def execute(self, inputs: Optional[Dict[str, Any]] = None, context: WorkflowContext[Dict[str, Any]] = None):
        resolved_inputs = self.resolve_dependencies(inputs=inputs) if self.variables else {}
        payload: Dict[str, Any] = {}
        payload.update(resolved_inputs or {})
        payload.update(inputs or {})

        user_id = self._resolve_user_id(payload, context)
        records = self._collect_records(payload)

        records_written = self._append_history(user_id, records)

        summaries = self._maybe_summarise(user_id, payload, records)

        self.output = {
            "user_id": user_id,
            "records_written": records_written,
            "summaries": summaries,
        }
        return self.output

    # ------------------------------------------------------------------
    # History handling
    # ------------------------------------------------------------------
    def _append_history(self, user_id: str, records: List[Dict[str, Any]]) -> int:
        count = 0
        for record in records:
            role = record.get("role")
            if not role:
                continue
            mtype = record.get("type", "text")
            content = self._ensure_dict_content(record.get("content"))
            try:
                self.memory.append_history(user_id, role, mtype, content, maxlen=self.history_maxlen)
                count += 1
            except Exception as exc:  # pragma: no cover - defensive logging
                logging.error(f"MemVertex[{self.id}] failed to append history: {exc}")
        return count

    def _ensure_dict_content(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            return {"text": content}
        if content is None:
            return {"text": ""}
        try:
            json.dumps(content)
            return {"value": content}
        except TypeError:
            return {"text": str(content)}

    def _collect_records(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        # Preferred explicit records input
        candidate_records = payload.get("records")
        if isinstance(candidate_records, dict):
            normalised = self._normalise_record(candidate_records)
            if normalised:
                records.append(normalised)
        elif isinstance(candidate_records, Iterable) and not isinstance(candidate_records, (str, bytes)):
            for item in candidate_records:
                normalised = self._normalise_record(item)
                if normalised:
                    records.append(normalised)

        # Convenience fields
        user_msg = payload.get("latest_user_message")
        if user_msg is not None:
            records.append({"role": "user", "type": "text", "content": user_msg})

        assistant_msg = payload.get("latest_assistant_message")
        if assistant_msg is not None:
            records.append({"role": "assistant", "type": "text", "content": assistant_msg})

        return [self._normalise_record(rec) for rec in records if self._normalise_record(rec)]

    def _normalise_record(self, record: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(record, dict):
            return None
        role = record.get("role")
        if not role:
            return None
        content = record.get("content")
        normalised = {
            "role": role,
            "type": record.get("type", "text"),
            "content": self._ensure_dict_content(content),
        }
        return normalised

    # ------------------------------------------------------------------
    # Summarisation
    # ------------------------------------------------------------------
    def _maybe_summarise(
        self,
        user_id: str,
        payload: Dict[str, Any],
        records: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        if not self.rules:
            return []

        corpus = self._build_corpus(payload, records)
        if not corpus:
            return []

        summaries: List[Dict[str, str]] = []
        for rule in self.rules:
            if not self._rule_matches(rule, payload, records, corpus):
                continue
            summary = self._call_model(rule, corpus, payload)
            if not summary:
                continue
            if self._write_summary(rule, user_id, summary):
                summaries.append({"rule": rule.name, "summary": summary})

        return summaries

    def _build_corpus(self, payload: Dict[str, Any], records: List[Dict[str, Any]]) -> str:
        fragments: List[str] = []

        def push(role: str, text: str):
            text = text.strip()
            if text:
                fragments.append(f"{role}: {text}")

        history = payload.get(CONVERSATION_HISTORY)
        if isinstance(history, Iterable):
            for msg in history:
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role", "unknown")
                text = self._extract_text(msg.get("content"))
                push(role, text)

        for record in records:
            role = record.get("role", "unknown")
            text = self._extract_text(record.get("content"))
            push(role, text)

        for key in payload.get("summary_context", []) if isinstance(payload.get("summary_context"), list) else []:
            if isinstance(key, str):
                push("context", key)

        if isinstance(payload.get("summary_context"), str):
            push("context", payload["summary_context"])

        for key in payload.get("context", []) if isinstance(payload.get("context"), list) else []:
            if isinstance(key, str):
                push("context", key)

        if isinstance(payload.get("context"), str):
            push("context", payload["context"])

        return "\n".join(fragments)

    def _rule_matches(
        self,
        rule: SummaryRule,
        payload: Dict[str, Any],
        records: List[Dict[str, Any]],
        corpus: str,
    ) -> bool:
        matcher = rule.match
        if matcher is None:
            return True

        if callable(matcher):
            try:
                return bool(matcher(payload, records, corpus))
            except Exception as exc:  # pragma: no cover - defensive
                logging.error(f"MemVertex[{self.id}] matcher '{rule.name}' failed: {exc}")
                return False

        corpus_lower = corpus.lower()

        if isinstance(matcher, str):
            return matcher.lower() in corpus_lower

        if isinstance(matcher, Sequence):
            return any(str(token).lower() in corpus_lower for token in matcher)

        if isinstance(matcher, dict):
            any_tokens = matcher.get("any", [])
            all_tokens = matcher.get("all", [])
            if any_tokens and not any(str(token).lower() in corpus_lower for token in any_tokens):
                return False
            if all_tokens and not all(str(token).lower() in corpus_lower for token in all_tokens):
                return False
            return bool(any_tokens or all_tokens)

        return False

    def _call_model(self, rule: SummaryRule, corpus: str, payload: Dict[str, Any]) -> str:
        if self.model is None:
            return ""

        contextual_fragments = [corpus]
        for key in rule.context_keys:
            value = payload.get(key)
            if isinstance(value, str):
                contextual_fragments.append(f"{key}: {value}")
            elif isinstance(value, (int, float)):
                contextual_fragments.append(f"{key}: {value}")
            elif value is not None:
                contextual_fragments.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")

        compiled_context = "\n".join(contextual_fragments)
        prompt = rule.prompt_template.format(context=compiled_context)
        params: Dict[str, Any] = {
            MODEL: self.model,
            SYSTEM: rule.system_prompt,
            USER: [prompt],
        }
        if rule.options:
            params.update(rule.options)

        summary_vertex = LLMVertex(
            id=f"{self.id}_{rule.name}_summary",
            params=params,
        )

        try:
            result = summary_vertex.chat({}, context=WorkflowContext())
        except Exception as exc:  # pragma: no cover - LLM failures should not crash workflow
            logging.error(f"MemVertex[{self.id}] summary call failed: {exc}")
            return ""

        return self._extract_text(result)

    def _write_summary(self, rule: SummaryRule, user_id: str, summary: str) -> bool:
        summary = summary.strip()
        if not summary:
            return False

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        record = {
            "summary": summary,
            "rule": rule.name,
            "vertex": self.id,
            "timestamp": timestamp,
        }

        try:
            if rule.should_write_to_history():
                self.memory.append_history(user_id, "system", "summary", record, maxlen=self.history_maxlen)
            else:
                existing = self.memory.ctx_get(user_id, rule.memory_key)
                if isinstance(existing, dict) and existing.get("summary") == summary:
                    return False
                self.memory.ctx_set(user_id, rule.memory_key, record, ttl_sec=rule.ttl_sec)
        except Exception as exc:  # pragma: no cover - safety net
            logging.error(f"MemVertex[{self.id}] failed to persist summary: {exc}")
            return False

        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
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
