"""Resume extraction (PDF) and structured OpenAI parsing for the live inference pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError, PyPdfError


DEFAULT_MODEL = os.getenv("OPENAI_RESUME_MODEL", "gpt-4o-2024-08-06")


class UnreadablePDFError(Exception):
    """Raised when a PDF cannot be opened or yields no extractable text."""


class CandidateProfile(BaseModel):
    inferred_seniority: str
    primary_domain: str
    career_trajectory: str


class CoreCompetencies(BaseModel):
    technical_skills: list[str]
    domain_knowledge: list[str]
    tools_and_frameworks: list[str]


class ProfessionalExperience(BaseModel):
    title: str
    organization: str
    duration: str
    responsibilities: list[str]


class AcademicOrProjectItem(BaseModel):
    title: str
    type: str
    description: str


class ResumeProfile(BaseModel):
    candidate_profile: CandidateProfile
    executive_summary: str = Field(description="2-3 sentences summarizing the candidate.")
    core_competencies: CoreCompetencies
    professional_experience: list[ProfessionalExperience]
    academic_and_project_portfolio: list[AcademicOrProjectItem]


def extract_text_from_pdf(pdf_path: str | os.PathLike[str]) -> str:
    """Extract raw text from every page of a PDF resume.

    Raises:
        UnreadablePDFError: If the file is missing, encrypted, corrupt, or empty of text.
    """
    path = Path(pdf_path)

    if not path.is_file():
        raise UnreadablePDFError(f"PDF not found: {path}")

    try:
        reader = PdfReader(str(path))
    except (PdfReadError, PyPdfError, OSError, ValueError) as exc:
        raise UnreadablePDFError(f"Unable to read PDF '{path}': {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        try:
            unlocked = reader.decrypt("")
        except Exception as exc:
            raise UnreadablePDFError(f"PDF is encrypted and cannot be opened: {path}") from exc
        if not unlocked:
            raise UnreadablePDFError(f"PDF is encrypted and cannot be opened: {path}")

    pages: list[str] = []
    page_number = 0
    try:
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append(page_text)
    except (PdfReadError, PyPdfError, Exception) as exc:
        location = f"page {page_number}" if page_number else "the document"
        raise UnreadablePDFError(
            f"Failed extracting text from {location} of '{path}': {exc}"
        ) from exc

    text = "\n".join(pages).strip()
    if not text:
        raise UnreadablePDFError(
            f"No extractable text found in '{path}'. The file may be scanned or image-only."
        )

    return text


def structure_resume_text(
    resume_text: str,
    *,
    client: OpenAI | None = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Send resume text to OpenAI and return the target resume JSON schema as a dict."""
    if not resume_text or not resume_text.strip():
        raise ValueError("Resume text is empty; cannot structure an empty document.")

    openai_client = client or OpenAI()
    completion = openai_client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured candidate profiles from resume text. "
                    "Use only information present in the resume. Do not invent employers, "
                    "dates, or skills. Infer seniority, primary domain, and career trajectory "
                    "from the evidence in the document. Executive summary must be 2-3 sentences."
                ),
            },
            {
                "role": "user",
                "content": resume_text,
            },
        ],
        response_format=ResumeProfile,
    )

    message = completion.choices[0].message
    if message.refusal:
        raise ValueError(f"OpenAI refused to parse the resume: {message.refusal}")
    if message.parsed is None:
        raise ValueError("OpenAI did not return a parsed resume profile.")

    return message.parsed.model_dump()


def parse_resume(pdf_path: str | os.PathLike[str], **kwargs) -> dict:
    """Run extraction then structuring. Intended for Flask and other callers."""
    resume_text = extract_text_from_pdf(pdf_path)
    return structure_resume_text(resume_text, **kwargs)


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF resume and structure it with OpenAI."
    )
    parser.add_argument("pdf_path", help="Path to the resume PDF")
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Print raw extracted text and skip the OpenAI structuring step.",
    )
    args = parser.parse_args()

    try:
        if args.extract_only:
            print(extract_text_from_pdf(args.pdf_path))
            return 0
        profile = parse_resume(args.pdf_path)
    except UnreadablePDFError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(profile, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
