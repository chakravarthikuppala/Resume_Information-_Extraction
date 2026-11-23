# Resume Information Extraction

Resume Information Extraction is a Flask-based web application that uploads PDF, DOCX, or TXT resumes and converts unstructured resume content into structured information. It uses **spaCy**, regular expressions, and rule-based section detection to extract the candidate's name, contact details, skills, education, experience, projects, certifications, languages, and career summary.

The application provides a simple browser interface, JSON-formatted extraction results, and a downloadable output. It is designed for resume screening, applicant tracking, and learning natural language processing workflows.

# Tech Stack

1. **Python**
2. **Flask**
3. **spaCy**
4. **pdfplumber**
5. **python-docx**
6. **HTML, CSS, and JavaScript**

# Project Structure

```blash
Resume information extraction/
├── app.py                  # Flask application and API routes
├── requirements.txt        # Python dependencies
├── run.bat                 # Windows setup and launch script
├── README.md               # Project documentation
├── .gitignore              # Git ignored files
│
├── nlp/
│   ├── __init__.py         # NLP package initialization
│   ├── text_extract.py     # PDF, DOCX, and TXT text extraction
│   ├── engine.py           # spaCy, EntityRuler, and PhraseMatcher setup
│   ├── rules.py            # Regex and section-detection rules
│   └── extractor.py        # Main resume extraction pipeline
│
├── templates/
│   └── index.html          # Browser interface template
│
├── static/
│   ├── css/
│   │   └── style.css       # Application styling
│   └── js/
│       └── app.js          # Upload, API, rendering, and download logic
│
├── sample/
│   └── sample_resume.txt   # Built-in example resume
│
└── uploads/                # Temporary uploaded resume storage
```

## Pipeline

1. **Upload resume** — searchable PDF, DOCX, or TXT (`.doc` is not supported)
2. **Extract text** — `pdfplumber` / `python-docx`
3. **Identify important fields** — spaCy NER, EntityRuler, PhraseMatcher, regex
4. **Organize extraction** — section heading rules group education, experience, skills, and more
5. **Display structured output** — web UI plus downloadable JSON



## Fields

Name, emails, phones, location, LinkedIn, GitHub, summary, skills, education, experience, projects, certifications, languages, and spaCy entities.

## Run locally

Use **Python 3.11** (spaCy does not yet run on 3.15).

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Or double-click `run.bat`.

Open local host. Use **Try sample resume** or upload your own file.

Scanned/image-only PDFs do not contain extractable text and currently need to be converted to a searchable PDF or DOCX before upload.

## Upload project files to GitHub

### Upload files from the GitHub website

1. Create a repository on GitHub.
2. Open the repository and select **Add file** -> **Upload files**.
3. Drag the project files or folders into the upload area.
4. Add a commit message and select **Commit changes**.

Do not upload personal resumes containing sensitive information. Uploaded resume files in this project are stored only temporarily and are deleted after extraction.

### Upload files using Git

From the project folder:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Replace `USERNAME` with your GitHub username and `REPOSITORY` with the repository name.

## Approach

- **spaCy `en_core_web_sm`**: PERSON, ORG, GPE, DATE
- **EntityRuler**: degree patterns
- **PhraseMatcher**: skill gazetteer
- **Regex**: email, phone, URLs, years, date ranges
- **Heading rules**: SUMMARY, EXPERIENCE, EDUCATION, SKILLS, PROJECTS, CERTIFICATIONS, LANGUAGES
