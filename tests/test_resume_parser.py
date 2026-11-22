"""Unit tests for resume PDF extraction and profile normalization."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.resume_parser import (
    UnreadablePDFError,
    _normalize_profile,
    extract_text_from_pdf,
    parse_resume,
    structure_resume_text,
)

IDEAL_JOB_DESCRIPTION = (
    "Machine Learning Engineer responsible for production NLP and ranking systems. "
    "Required stack: Python, PyTorch, TensorFlow, React, PostgreSQL, AWS, and "
    "JavaScript. Design retrieval pipelines, train ranking models, evaluate search "
    "quality, and ship APIs used by job-matching products. Own feature stores, "
    "embedding indexes, and offline evaluation. Collaborate with backend engineers "
    "on Flask services and data contracts. Write tests, monitor latency, and "
    "document model cards. Experience with information retrieval, resume parsing, "
    "and semantic search is expected. Convert research prototypes into reliable "
    "batch and online inference. Communicate tradeoffs on accuracy, cost, and "
    "latency. This role targets a mid-level engineer with several years of applied "
    "machine learning delivery, not a research-only posting."
)


def _structured_profile(**overrides) -> dict:
    profile = {
        "candidate_profile": {
            "inferred_seniority": "Mid-level",
            "primary_domain": "Machine Learning",
            "career_trajectory": "Intern to ML engineer.",
        },
        "executive_summary": "ML engineer with production ranking experience.",
        "core_competencies": {
            "technical_skills": ["Python", "python", "JavaScript"],
            "domain_knowledge": ["Machine Learning", "python"],
            "tools_and_frameworks": ["PostgreSQL", "React"],
        },
        "professional_experience": [
            {
                "title": "ML Engineer",
                "organization": "Acme",
                "duration": "2022–2025",
                "responsibilities": ["Shipped ranking models"],
            },
            {
                "title": "Intern",
                "organization": "Acme",
                "duration": "2021–2022",
                "responsibilities": ["Supported data pipelines"],
            },
        ],
        "academic_and_project_portfolio": [],
        "total_years_experience": 4.5,
        "ideal_job_description": IDEAL_JOB_DESCRIPTION,
    }
    profile.update(overrides)
    return profile


def test_extract_text_from_valid_pdf(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock resume")

    class FakePage:
        def extract_text(self) -> str:
            return "Senior Python Engineer\nAcme Corp"

    class FakeReader:
        is_encrypted = False
        pages = [FakePage()]

    monkeypatch.setattr("services.resume_parser.PdfReader", lambda _path: FakeReader())

    text = extract_text_from_pdf(pdf_path)

    assert "Senior Python Engineer" in text
    assert "Acme Corp" in text


def test_extract_text_from_missing_pdf(tmp_path: Path) -> None:
    missing_path = tmp_path / "does-not-exist.pdf"

    with pytest.raises(UnreadablePDFError, match="not found"):
        extract_text_from_pdf(missing_path)


def test_extract_text_from_encrypted_pdf(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "encrypted.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 encrypted")

    class FakeEncryptedReader:
        is_encrypted = True
        pages = []

        def decrypt(self, _password: str) -> int:
            return 0

    monkeypatch.setattr(
        "services.resume_parser.PdfReader", lambda _path: FakeEncryptedReader()
    )

    with pytest.raises(UnreadablePDFError, match="encrypted"):
        extract_text_from_pdf(pdf_path)


def test_extract_text_from_unreadable_pdf(tmp_path: Path) -> None:
    unreadable_path = tmp_path / "broken.pdf"
    unreadable_path.write_text("this is not a valid pdf")

    with pytest.raises(UnreadablePDFError):
        extract_text_from_pdf(unreadable_path)


def test_normalize_profile_dedupes_skills_case_insensitively() -> None:
    normalized = _normalize_profile(_structured_profile())

    assert normalized["resume_skills"] == [
        "Python",
        "JavaScript",
        "Machine Learning",
        "PostgreSQL",
        "React",
    ]


def test_normalize_profile_resume_skills_matches_skills() -> None:
    normalized = _normalize_profile(_structured_profile())

    assert normalized["resume_skills"] == normalized["skills"]


def test_normalize_profile_experience_years_uses_total_years() -> None:
    normalized = _normalize_profile(_structured_profile(total_years_experience=4.5))

    assert len(normalized["professional_experience"]) == 2
    assert normalized["experience_years"] == 4.5
    assert normalized["experience_years"] != len(normalized["professional_experience"])


def test_normalize_profile_experience_years_defaults_when_missing() -> None:
    profile = _structured_profile()
    del profile["total_years_experience"]

    normalized = _normalize_profile(profile)

    assert normalized["experience_years"] == 0.0


def test_parse_resume_surfaces_schema_fields_with_openai_mocked(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock resume")
    monkeypatch.setattr(
        "services.resume_parser.extract_text_from_pdf",
        lambda _pdf: "Jane Doe, Python, React.js",
    )

    parsed_profile = SimpleNamespace(
        refusal=None,
        parsed=SimpleNamespace(model_dump=lambda: _structured_profile()),
    )
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=parsed_profile)]
    )

    result = parse_resume(pdf_path, client=fake_client)

    fake_client.beta.chat.completions.parse.assert_called_once()
    assert result["total_years_experience"] == 4.5
    assert result["experience_years"] == 4.5
    assert result["ideal_job_description"] == IDEAL_JOB_DESCRIPTION
    assert "resume_skills" in result
    assert result["resume_skills"] == result["skills"]
    assert result["resume_skills"][0] == "Python"


def test_structure_resume_text_uses_hyde_and_skill_prompt() -> None:
    parsed_profile = SimpleNamespace(
        refusal=None,
        parsed=SimpleNamespace(model_dump=lambda: _structured_profile()),
    )
    fake_client = MagicMock()
    fake_client.beta.chat.completions.parse.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=parsed_profile)]
    )

    structure_resume_text("resume text", client=fake_client)

    kwargs = fake_client.beta.chat.completions.parse.call_args.kwargs
    system_prompt = kwargs["messages"][0]["content"]
    assert "non-overlapping" in system_prompt
    assert "React.js" in system_prompt
    assert "ideal_job_description" in system_prompt
    assert "256-token" in system_prompt
    assert kwargs["response_format"].__name__ == "ResumeProfile"
