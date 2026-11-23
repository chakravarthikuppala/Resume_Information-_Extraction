import unittest
from io import BytesIO

from app import app
from nlp.engine import _analyze_rules
from nlp.extractor import extract_from_text
from nlp.text_extract import SUPPORTED_EXTENSIONS


SAMPLE = """Aarav Mehta
Bengaluru, India
aarav.mehta@email.com | +91 98765 43210

SUMMARY
NLP engineer who builds information extraction pipelines.

EXPERIENCE
NLP Engineer, Horizon Analytics
Jan 2023 - Present
- Designed a resume parser that extracts contact, skills, education, and work history.

EDUCATION
B.Tech in Computer Science, National Institute of Technology Karnataka
2018 - 2022

PROJECTS
Resume Information Extraction
- End-to-end NLP pipeline: upload, text extraction, field identification.

CERTIFICATIONS
AWS Certified Cloud Practitioner

LANGUAGES
English, Hindi
"""


class ResumeExtractionTests(unittest.TestCase):
    def test_extracts_core_fields_without_swapping_or_bullet_leakage(self):
        result = extract_from_text(SAMPLE)

        self.assertEqual(result["name"], "Aarav Mehta")
        self.assertEqual(result["contact"]["emails"], ["aarav.mehta@email.com"])
        self.assertEqual(result["experience"][0]["title"], "NLP Engineer")
        self.assertEqual(result["experience"][0]["company"], "Horizon Analytics")
        self.assertEqual(
            result["education"][0]["field"],
            "Computer Science",
        )
        self.assertEqual(
            result["education"][0]["institution"],
            "National Institute of Technology Karnataka",
        )
        self.assertEqual(result["projects"], ["Resume Information Extraction"])
        self.assertEqual(result["certifications"], ["AWS Certified Cloud Practitioner"])
        self.assertEqual(result["languages"], ["English", "Hindi"])
        self.assertNotIn("98765 43210", result["entities"].get("DATE", []))
        self.assertNotIn("Docker", result["entities"].get("PERSON", []))
        self.assertNotIn("Hindi", result["entities"].get("PERSON", []))
        self.assertNotIn("PhraseMatcher", result["entities"].get("ORG", []))
        self.assertNotIn("F1", result["entities"].get("GPE", []))

    def test_extracts_education_from_common_heading_and_order_variations(self):
        resume = """Jane Doe
EDUCATIONAL QUALIFICATIONS
Example University
Bachelor of Science in Computer Science
2020 - 2024

ACADEMIC DETAILS
M.Sc. Data Analytics | Other University | 2024 - 2026
"""

        result = extract_from_text(resume)

        self.assertEqual(len(result["education"]), 2)
        self.assertEqual(result["education"][0]["degree"], "Bachelor of Science")
        self.assertEqual(result["education"][0]["field"], "Computer Science")
        self.assertEqual(result["education"][0]["institution"], "Example University")
        self.assertEqual(result["education"][0]["year"], "2020-2024")
        self.assertEqual(result["education"][1]["degree"], "M.Sc.")
        self.assertEqual(result["education"][1]["field"], "Data Analytics")
        self.assertEqual(result["education"][1]["institution"], "Other University")
        self.assertEqual(result["education"][1]["year"], "2024-2026")

    def test_extracts_education_when_heading_and_degree_share_a_line(self):
        result = extract_from_text(
            "Jane Doe\nEDUCATION: B.Sc. Computer Science, Example University, 2019 - 2022"
        )

        self.assertEqual(len(result["education"]), 1)
        self.assertEqual(result["education"][0]["degree"], "B.Sc.")
        self.assertEqual(result["education"][0]["field"], "Computer Science")
        self.assertEqual(result["education"][0]["institution"], "Example University")
        self.assertEqual(result["education"][0]["year"], "2019-2022")

    def test_extracts_degree_when_heading_is_missing_and_school_precedes_it(self):
        result = extract_from_text(
            "Jane Doe\nIIT Madras\nB.Tech in Electrical Engineering\n2018 - 2022"
        )

        self.assertEqual(len(result["education"]), 1)
        self.assertEqual(result["education"][0]["degree"], "B.Tech")
        self.assertEqual(result["education"][0]["field"], "Electrical Engineering")
        self.assertEqual(result["education"][0]["institution"], "IIT Madras")

    def test_splits_section_headings_embedded_in_table_like_rows(self):
        resume = """Jane Doe
EDUCATIONAL QUALIFICATIONS | B.Sc. Computer Science, Example University, 2019 - 2022
PROFESSIONAL HISTORY | Data Analyst, Example Corp | Jan 2023 - Present
SELECTED PROJECTS | Sales Dashboard
LICENSES AND CERTIFICATIONS | AWS Certified Cloud Practitioner
SPOKEN LANGUAGES | English, Hindi
"""

        result = extract_from_text(resume)

        self.assertIn("education", result["sections_found"])
        self.assertIn("experience", result["sections_found"])
        self.assertEqual(result["education"][0]["institution"], "Example University")
        self.assertEqual(result["education"][0]["year"], "2019-2022")
        self.assertEqual(result["experience"][0]["title"], "Data Analyst")
        self.assertEqual(result["experience"][0]["company"], "Example Corp")
        self.assertEqual(result["projects"], ["Sales Dashboard"])
        self.assertEqual(result["certifications"], ["AWS Certified Cloud Practitioner"])
        self.assertEqual(result["languages"], ["English", "Hindi"])

    def test_empty_or_unreadable_document_is_not_a_successful_empty_result(self):
        with self.assertRaisesRegex(ValueError, "No readable text was found"):
            extract_from_text(" \n\t ")

    def test_api_reports_empty_document_as_a_client_error(self):
        response = app.test_client().post(
            "/api/extract",
            data={"resume": (BytesIO(b" \n\t "), "empty.txt")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("No readable text was found", response.get_json()["error"])

    def test_api_reports_malformed_pdf_as_a_client_error(self):
        response = app.test_client().post(
            "/api/extract",
            data={"resume": (BytesIO(b"not a PDF"), "broken.pdf")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("valid, unencrypted PDF", response.get_json()["error"])

    def test_legacy_doc_is_not_advertised_as_supported(self):
        self.assertNotIn(".doc", SUPPORTED_EXTENSIONS)

    def test_rule_fallback_does_not_match_single_letter_skills_inside_words(self):
        doc = _analyze_rules("The candidate worked on Docker and C++ projects.")

        self.assertIn("Docker", doc.skills)
        self.assertIn("C++", doc.skills)
        self.assertNotIn("C", doc.skills)


if __name__ == "__main__":
    unittest.main()
