"""Unit tests for resume PDF extraction."""

from pathlib import Path

import pytest

from services.resume_parser import UnreadablePDFError, extract_text_from_pdf


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
