"""Citation parsing/validation — the security-relevant boundary that
rejects a fabricated or out-of-range citation id rather than trusting
model output (docs/AI_ARCHITECTURE.md §6/§7).
"""

import uuid

from app.ai.citations import parse_llm_response, validate_citations
from app.ai.enums import RetrievalMatchType
from app.ai.retrieval import RetrievedChunk
from app.sources.enums import VerificationStatus


def _chunk(entity_id: uuid.UUID | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        entity_type="job",
        entity_id=entity_id or uuid.uuid4(),
        chunk_text="Some chunk text.",
        title="Test Job (Fixture)",
        route="/jobs/test-job",
        source_organization="Test Board — Not Real",
        source_title="Test Notice — Not Real",
        source_url="https://example-test.invalid/notice",
        verification_status=VerificationStatus.VERIFIED,
        last_verified_at=None,
        score=1.0,
        match_type=RetrievalMatchType.LEXICAL,
    )


class TestParseLLMResponse:
    def test_parses_a_well_formed_response(self) -> None:
        raw = '{"answer": "Some answer.", "citation_ids": [1, 2], "grounded": true}'
        parsed = parse_llm_response(raw)
        assert parsed is not None
        assert parsed.answer == "Some answer."
        assert parsed.raw_citation_ids == [1, 2]
        assert parsed.self_reported_grounded is True

    def test_tolerates_surrounding_prose_or_code_fences(self) -> None:
        raw = 'Here you go:\n```json\n{"answer": "A.", "citation_ids": [1], "grounded": true}\n```'
        parsed = parse_llm_response(raw)
        assert parsed is not None
        assert parsed.answer == "A."

    def test_returns_none_for_invalid_json(self) -> None:
        assert parse_llm_response("not json at all") is None

    def test_returns_none_when_answer_field_missing(self) -> None:
        assert parse_llm_response('{"citation_ids": [1]}') is None

    def test_returns_none_when_citation_ids_is_not_a_list(self) -> None:
        assert parse_llm_response('{"answer": "A.", "citation_ids": "1"}') is None

    def test_returns_none_for_non_object_json(self) -> None:
        assert parse_llm_response("[1, 2, 3]") is None

    def test_missing_grounded_field_defaults_to_false(self) -> None:
        parsed = parse_llm_response('{"answer": "A.", "citation_ids": []}')
        assert parsed is not None
        assert parsed.self_reported_grounded is False


class TestValidateCitations:
    def test_keeps_a_citation_id_within_range(self) -> None:
        evidence = [_chunk(), _chunk()]
        parsed = parse_llm_response('{"answer": "A.", "citation_ids": [1]}')
        assert parsed is not None

        validated = validate_citations(parsed, evidence)

        assert len(validated) == 1
        assert validated[0].citation_id == 1
        assert validated[0].chunk is evidence[0]

    def test_drops_an_out_of_range_citation_id(self) -> None:
        evidence = [_chunk()]
        parsed = parse_llm_response('{"answer": "A.", "citation_ids": [1, 2, 99]}')
        assert parsed is not None

        validated = validate_citations(parsed, evidence)

        assert [v.citation_id for v in validated] == [1]

    def test_drops_a_fabricated_non_integer_citation_id(self) -> None:
        evidence = [_chunk()]
        parsed = parse_llm_response(
            '{"answer": "A.", "citation_ids": [1, "https://fake.invalid/source", null, 1.5]}'
        )
        assert parsed is not None

        validated = validate_citations(parsed, evidence)

        assert [v.citation_id for v in validated] == [1]

    def test_drops_a_zero_or_negative_citation_id(self) -> None:
        evidence = [_chunk()]
        parsed = parse_llm_response('{"answer": "A.", "citation_ids": [0, -1, 1]}')
        assert parsed is not None

        validated = validate_citations(parsed, evidence)

        assert [v.citation_id for v in validated] == [1]

    def test_booleans_are_never_treated_as_citation_ids(self) -> None:
        # bool is a subclass of int in Python — must be excluded
        # explicitly, or `True` would silently behave as citation id 1.
        evidence = [_chunk()]
        parsed = parse_llm_response('{"answer": "A.", "citation_ids": [true, false]}')
        assert parsed is not None

        validated = validate_citations(parsed, evidence)

        assert validated == []

    def test_deduplicates_a_repeated_citation_id(self) -> None:
        evidence = [_chunk(), _chunk()]
        parsed = parse_llm_response('{"answer": "A.", "citation_ids": [1, 1, 2]}')
        assert parsed is not None

        validated = validate_citations(parsed, evidence)

        assert [v.citation_id for v in validated] == [1, 2]

    def test_empty_evidence_rejects_every_citation(self) -> None:
        parsed = parse_llm_response('{"answer": "A.", "citation_ids": [1]}')
        assert parsed is not None

        assert validate_citations(parsed, []) == []
