"""Parses and validates the LLM's structured JSON response — the one
place a citation is checked against what was actually retrieved before
it is ever shown to a user. `validate_citations` is the security-
relevant function here: a citation id the model invented (out of range,
wrong type, duplicated) is silently dropped, never trusted (this
phase's explicit "validates that cited source identifiers belong to the
retrieved evidence, not model-invented URLs or identifiers").
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.ai.retrieval import RetrievedChunk


@dataclass(frozen=True, slots=True)
class ParsedLLMResponse:
    answer: str
    raw_citation_ids: list[object]
    self_reported_grounded: bool


def parse_llm_response(raw_text: str) -> ParsedLLMResponse | None:
    """`None` on any parse/shape failure — callers treat that as
    ungrounded (this phase's "avoid presenting unsupported statements as
    facts": a response this module can't even parse safely is never
    shown as-is)."""

    text = raw_text.strip()
    # Defensive: tolerate the model wrapping the JSON in a markdown code
    # fence despite the system prompt's "no other text" instruction —
    # never execute or evaluate anything, just locate the outermost
    # braces of the first JSON object.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None

    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    answer = payload.get("answer")
    citation_ids = payload.get("citation_ids")
    grounded = payload.get("grounded")
    if not isinstance(answer, str) or not isinstance(citation_ids, list):
        return None

    return ParsedLLMResponse(
        answer=answer,
        raw_citation_ids=citation_ids,
        self_reported_grounded=bool(grounded) if isinstance(grounded, bool) else False,
    )


@dataclass(frozen=True, slots=True)
class ValidatedCitation:
    citation_id: int
    chunk: RetrievedChunk


def validate_citations(
    parsed: ParsedLLMResponse, evidence: list[RetrievedChunk]
) -> list[ValidatedCitation]:
    """Evidence ids are 1-indexed (`app.ai.prompting.build_evidence_block`).
    Order-preserving, deduplicated, and strictly bounds-checked — an id
    of `0`, a negative number, a float, a string, or anything beyond
    `len(evidence)` is dropped rather than raising, since a malformed
    model output should degrade the answer's grounding, not crash the
    request."""

    validated: list[ValidatedCitation] = []
    seen: set[int] = set()
    for raw_id in parsed.raw_citation_ids:
        if not isinstance(raw_id, int) or isinstance(raw_id, bool):
            continue
        if raw_id < 1 or raw_id > len(evidence) or raw_id in seen:
            continue
        seen.add(raw_id)
        validated.append(ValidatedCitation(citation_id=raw_id, chunk=evidence[raw_id - 1]))
    return validated
