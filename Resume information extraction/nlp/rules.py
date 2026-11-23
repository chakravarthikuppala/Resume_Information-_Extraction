"""Rule resources: gazetteers, regexes, and section headings."""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:\b(?:\+91[\s-]?)?[6-9]\d{9}\b|"
    r"\b(?:\+\d{1,3}[\s-]?)?\d{10,13}\b)",
    re.I,
)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+/?", re.I)
URL_RE = re.compile(r"https?://[^\s)]+", re.I)
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
DATE_RANGE_RE = re.compile(
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?"
    r"(?:19|20)\d{2}\s*[-–—to]+\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?"
    r"(?:(?:19|20)\d{2}|Present|Current|Now)",
    re.I,
)

SECTION_ALIASES = {
    "summary": ("summary", "profile", "objective", "about", "professional summary"),
    "experience": (
        "experience",
        "experiences",
        "work experience",
        "work experiences",
        "work experience history",
        "employment",
        "employment history",
        "professional experience",
        "professional history",
        "work history",
        "career history",
        "career",
    ),
    "education": (
        "education",
        "education details",
        "education history",
        "education qualification",
        "education qualifications",
        "education and training",
        "educational background",
        "educational qualification",
        "educational qualifications",
        "academic",
        "academics",
        "academic background",
        "academic details",
        "academic history",
        "academic qualification",
        "academic qualifications",
        "qualifications",
        "qualification details",
    ),
    "skills": (
        "skills",
        "technical skills",
        "core skills",
        "competencies",
        "expertise",
        "technologies",
        "tech stack",
    ),
    "projects": (
        "projects",
        "selected projects",
        "personal projects",
        "academic projects",
        "key projects",
    ),
    "certifications": (
        "certifications",
        "certificates",
        "licenses",
        "licenses and certifications",
        "certifications and licenses",
        "professional certifications",
    ),
    "languages": ("language", "languages", "spoken language", "spoken languages"),
    "achievements": ("achievements", "awards", "honors", "accomplishments"),
}

DEGREE_PATTERNS = [
    r"\bPh\.?D\.?\b",
    r"\bM\.?S\.?\b",
    r"\bM\.?Sc\.?\b",
    r"\bM\.?Tech\.?\b",
    r"\bMBA\b",
    r"\bMCA\b",
    r"\bB\.?S\.?\b",
    r"\bB\.?Sc\.?\b",
    r"\bB\.?E\.?\b",
    r"\bB\.?Tech\.?\b",
    r"\bB[- ]Tech(?:\s*\([^)]*\))?\b",
    r"\bDiploma\b",
    r"\bBCA\b",
    r"\bBachelor(?:'s)?(?:\s+of\s+(?:Science|Arts|Engineering|Technology|Business))?\b",
    r"\bMaster(?:'s)?(?:\s+of\s+(?:Science|Arts|Engineering|Technology|Business))?\b",
    r"\bAssociate(?:'s)?\s+Degree\b",
    r"\bHigh School Diploma\b",
]
DEGREE_RE = re.compile("|".join(DEGREE_PATTERNS), re.I)

JOB_TITLE_HINTS = (
    "engineer",
    "developer",
    "scientist",
    "analyst",
    "manager",
    "intern",
    "consultant",
    "architect",
    "designer",
    "specialist",
    "lead",
    "director",
    "officer",
    "administrator",
    "researcher",
    "programmer",
    "associate",
    "coordinator",
    "head",
    "founder",
    "intern",
)

SKILL_GAZETTEER = [
    # Programming
    "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Go", "Golang",
    "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL",
    "HTML", "CSS", "Bash", "Shell", "PowerShell",
    # Frameworks / libraries
    "spaCy", "NLTK", "Hugging Face", "Transformers", "PyTorch", "TensorFlow",
    "Keras", "scikit-learn", "NumPy", "Pandas", "OpenCV", "Flask", "Django",
    "FastAPI", "Streamlit", "React", "Angular", "Vue", "Node.js", "Express",
    "Spring", "Spring Boot", ".NET", "Laravel", "Bootstrap", "Tailwind",
    # Data / NLP
    "Natural Language Processing", "NLP", "Named Entity Recognition", "NER",
    "Machine Learning", "Deep Learning", "Computer Vision", "Data Analysis",
    "Data Visualization", "ETL", "Feature Engineering", "BERT", "GPT",
    "Information Extraction", "Text Classification", "Regex", "PhraseMatcher",
    "EntityRuler",
    # Cloud / DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "Git",
    "GitHub", "GitLab", "CI/CD", "Jenkins", "Linux", "Terraform",
    # Databases
    "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Redis", "Oracle", "Snowflake",
    "Elasticsearch", "Firebase",
    # Tools
    "Jira", "Figma", "Tableau", "Power BI", "Excel", "Postman", "VS Code",
    "Jupyter", "Spark", "Hadoop",
    # Soft / domain
    "Agile", "Scrum", "REST API", "GraphQL", "Microservices", "OOP",
    "Unit Testing", "Leadership", "Communication", "Problem Solving",
]

DEGREE_RULER_PATTERNS = [
    {"label": "DEGREE", "pattern": [{"TEXT": {"REGEX": r"^B\.?Tech\.?$"}}]},
    {"label": "DEGREE", "pattern": [{"TEXT": {"REGEX": r"^M\.?Tech\.?$"}}]},
    {"label": "DEGREE", "pattern": [{"TEXT": {"REGEX": r"^B\.?E\.?$"}}]},
    {"label": "DEGREE", "pattern": [{"LOWER": "bachelor"}, {"LOWER": "of"}, {"IS_TITLE": True}]},
    {"label": "DEGREE", "pattern": [{"LOWER": "master"}, {"LOWER": "of"}, {"IS_TITLE": True}]},
    {"label": "DEGREE", "pattern": [{"LOWER": "mba"}]},
    {"label": "DEGREE", "pattern": [{"LOWER": "phd"}]},
    {"label": "DEGREE", "pattern": [{"LOWER": "ph.d"}]},
]
