"""Synthetic resume for tests: no real person's data and no PDF file left behind."""
import io
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def synthetic_resume_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    content = DecodedStreamObject()
    content.set_data(b'BT /F1 12 Tf 50 700 Td (Synthetic Test Candidate - Python, SQL, Flask. Backend API project.) Tj ET')
    page[NameObject('/Contents')] = content
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


STRUCTURED_PROFILE = {
    'candidate_profile': {'inferred_seniority': 'Junior', 'primary_domain': 'Software Engineering', 'career_trajectory': 'Backend development'},
    'executive_summary': 'Candidate has Python, SQL, and Flask skills. They built a backend API project.',
    'core_competencies': {'technical_skills': ['Python', 'SQL'], 'domain_knowledge': ['Backend development'], 'tools_and_frameworks': ['Flask']},
    'professional_experience': [],
    'academic_and_project_portfolio': [{'title': 'Backend API', 'type': 'Project', 'description': 'Flask API project'}],
}
