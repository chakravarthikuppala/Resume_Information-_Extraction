"""spaCy + rule-based resume information extraction.

Pipeline:
  1. Receive raw resume text
  2. Split into labeled sections (rules)
  3. Identify fields with spaCy NER / EntityRuler / PhraseMatcher, plus regex
  4. Organize into a structured record
  5. Return JSON for the UI
"""

from __future__ import annotations

import re
from typing import Any

from nlp.engine import analyze, engine_info
from nlp.rules import (
    DATE_RANGE_RE,
    DEGREE_RE,
    EMAIL_RE,
    GITHUB_RE,
    JOB_TITLE_HINTS,
    LINKEDIN_RE,
    PHONE_RE,
    SECTION_ALIASES,
    SKILL_GAZETTEER,
    URL_RE,
    YEAR_RE,
)
from nlp.text_extract import extract_text

SPOKEN_LANGUAGES = {
    "english",
    "hindi",
    "spanish",
    "french",
    "german",
    "mandarin",
    "chinese",
    "japanese",
    "korean",
    "arabic",
    "portuguese",
    "bengali",
    "tamil",
    "telugu",
    "marathi",
    "urdu",
    "italian",
    "russian",
}


def extract_resume(path: str, filename: str | None = None) -> dict[str, Any]:
    raw_text = extract_text(path)
    return extract_from_text(raw_text, filename=filename)


def extract_from_text(raw_text: str, filename: str | None = None) -> dict[str, Any]:
    cleaned = _normalize_text(raw_text)
    if not cleaned:
        raise ValueError(
            "No readable text was found. If this is a scanned PDF, convert it to a "
            "searchable PDF or DOCX before uploading."
        )
    doc = analyze(cleaned)
    info = engine_info()
    sections = _split_sections(cleaned)

    contact = _extract_contact(cleaned, doc)
    skills = _extract_skills(doc, sections.get("skills", ""))
    education = _extract_education(sections.get("education", ""), doc)
    experience = _extract_experience(sections.get("experience", ""), doc)
    projects = _extract_bullet_items(sections.get("projects", ""))
    certifications = _extract_bullet_items(sections.get("certifications", ""))
    languages = _extract_languages(sections.get("languages", ""), skills)
    summary = _extract_summary(sections, contact)

    return {
        "name": contact.get("name"),
        "contact": contact,
        "summary": summary,
        "skills": skills,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
        "languages": languages,
        "sections_found": sorted(k for k, v in sections.items() if v.strip()),
        "entities": _collect_entities(doc),
        "engine": {"name": info.name, "using_spacy": info.using_spacy, "note": info.note},
        "source_file": filename,
        "raw_text": cleaned,
        "char_count": len(cleaned),
        "word_count": len(cleaned.split()),
    }


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r",(?=[A-Za-z])", ", ", text)
    text = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", text)

    aliases = sorted(
        (
            (alias, key)
            for key, values in SECTION_ALIASES.items()
            for alias in values
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, _ in aliases:
        compact = re.sub(r"\s+", "", alias)
        if compact != alias:
            text = re.sub(re.escape(compact), alias, text, flags=re.I)
    return text.strip()


def _split_sections(text: str) -> dict[str, str]:
    buckets: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.split("\n"):
        markers = _section_markers(line)
        if not markers:
            buckets.setdefault(current, []).append(line)
            continue

        prefix = line[:markers[0][0]].strip(" \t|:;,-•")
        if prefix:
            buckets.setdefault(current, []).append(prefix)
        for index, (start, end, key) in enumerate(markers):
            current = key
            buckets.setdefault(current, [])
            content_end = markers[index + 1][0] if index + 1 < len(markers) else len(line)
            content = line[end:content_end].strip(" \t|:;,-•")
            if content:
                buckets[current].append(content)
    return {k: "\n".join(v).strip() for k, v in buckets.items()}


def _section_markers(line: str) -> list[tuple[int, int, str]]:
    aliases = sorted(
        (
            (alias, key)
            for key, values in SECTION_ALIASES.items()
            for alias in values
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    alternatives = "|".join(
        re.escape(alias).replace(r"\ ", r"\s+") for alias, _ in aliases
    )
    pattern = re.compile(rf"(?<!\w)(?P<label>{alternatives})(?!\w)", re.I)
    alias_to_key = {alias.lower(): key for alias, key in aliases}
    markers: list[tuple[int, int, str]] = []
    for match in pattern.finditer(line):
        label = match.group("label")
        prefix = line[:match.start()]
        stripped_prefix = prefix.strip(" \t|:;,-•0123456789.")
        is_uppercase_heading = label.isupper()
        starts_line = not stripped_prefix
        follows_delimiter = bool(prefix.rstrip().endswith(("|", ":", ";")))
        if not (starts_line or follows_delimiter or is_uppercase_heading):
            continue
        key = alias_to_key.get(re.sub(r"\s+", " ", label.lower()))
        if key:
            markers.append((match.start(), match.end(), key))
    return markers


def _heading_key(line: str) -> str | None:
    compact = re.sub(r"[^a-zA-Z ]", " ", line).strip().lower()
    compact = re.sub(r"\s+", " ", compact)
    if not compact or len(compact) > 40:
        return None
    for key, aliases in SECTION_ALIASES.items():
        if compact in aliases:
            return key
    return None


def _looks_like_name(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if EMAIL_RE.search(line) or PHONE_RE.search(line) or URL_RE.search(line):
        return False
    if _heading_key(line):
        return False
    tokens = [t for t in re.split(r"\s+", line) if t]
    if not (1 <= len(tokens) <= 5):
        return False
    letters = sum(ch.isalpha() for ch in line)
    return letters / max(len(line), 1) > 0.6 and tokens[0][0].isupper()


def _extract_contact(text: str, doc) -> dict[str, Any]:
    emails = sorted(set(EMAIL_RE.findall(text)))
    linkedin = _first_match(LINKEDIN_RE, text)
    github = _first_match(GITHUB_RE, text)

    phones = []
    for match in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", match)
        if 10 <= len(digits) <= 13:
            phones.append(match.strip())
    phones = list(dict.fromkeys(phones))

    name = None
    header_lines = [ln.strip() for ln in text.split("\n")[:12] if ln.strip()]
    for line in header_lines:
        if _looks_like_name(line):
            name = line
            break
    if not name:
        for ent in doc.ents:
            if ent.label_ == "PERSON" and ent.start < 80:
                name = ent.text.strip()
                break

    location = None
    for ent in doc.ents:
        if ent.label_ in {"GPE", "LOC"}:
            location = ent.text.strip()
            break

    websites = [
        url
        for url in URL_RE.findall(text)
        if "linkedin.com" not in url.lower() and "github.com" not in url.lower()
    ]

    return {
        "name": name,
        "emails": emails,
        "phones": phones,
        "location": location,
        "linkedin": linkedin,
        "github": github,
        "websites": websites[:5],
    }


def _extract_skills(doc, skills_section: str) -> list[str]:
    found = list(doc.skills)
    if skills_section:
        extra = re.split(r"[,•|/;\n]+", skills_section)
        for item in extra:
            token = item.strip(" -•\t")
            if 1 < len(token) <= 40 and not _heading_key(token):
                found.append(token)

    canonical = []
    seen = set()
    for skill in found:
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        canonical.append(skill)
    return canonical[:60]


def _extract_education(section: str, doc) -> list[dict[str, str]]:
    if not section:
        section = doc.text
    blocks = _education_blocks(section)
    records = []
    for block in blocks:
        degree_match = DEGREE_RE.search(block)
        degree = degree_match.group(0).strip() if degree_match else None
        if degree:
            degree = {
                "b.sc": "B.Sc.",
                "m.sc": "M.Sc.",
                "b.s": "B.S.",
                "m.s": "M.S.",
                "b.e": "B.E.",
                "b.tech": "B.Tech",
                "m.tech": "M.Tech",
            }.get(degree.lower().rstrip("."), degree)
        years = YEAR_RE.findall(block)
        year = "-".join(years[:2]) if years else None
        field = None
        institution = None
        lines = [line.strip(" -•\t") for line in block.splitlines() if line.strip()]
        degree_line = next((line for line in lines if DEGREE_RE.search(line)), "")
        if degree_line:
            match = DEGREE_RE.search(degree_line)
            remainder = degree_line[match.end():].strip(" .,:;|-")
            remainder = re.sub(r"^(?:in|of)\s+", "", remainder, flags=re.I)
            remainder = re.sub(r"\s+from\s+", " | ", remainder, flags=re.I)
            parts = [part.strip(" .,:;|-") for part in re.split(r"\s*[|,;]\s*", remainder)]
            parts = [part for part in parts if part and not YEAR_RE.fullmatch(part)]
            if parts:
                if _looks_like_institution(parts[0]):
                    institution = parts[0]
                    field = parts[1] if len(parts) > 1 else None
                else:
                    field = parts[0]
                    institution = next(
                        (part for part in parts[1:] if _looks_like_institution(part)),
                        parts[1] if len(parts) > 1 else None,
                    )

        if not institution:
            institution = next(
                (line.strip(" ,-|") for line in lines if line != degree_line and _looks_like_institution(line)),
                None,
            )
        if not field:
            field = next(
                (
                    line.strip(" ,-|")
                    for line in lines
                    if line != degree_line
                    and not YEAR_RE.search(line)
                    and not _looks_like_institution(line)
                    and not re.search(r"\b(?:gpa|cgpa|grade|score|percentage|graduated)\b", line, re.I)
                ),
                None,
            )
        if degree or institution:
            records.append(
                {
                    "degree": degree,
                    "field": field,
                    "institution": institution,
                    "year": year,
                    "raw": block.strip(),
                }
            )
    return records[:8]


def _education_blocks(section: str) -> list[str]:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    blocks: list[str] = []
    current: list[str] = []
    preceding_institution: str | None = None

    for line in lines:
        heading = _heading_key(line)
        if heading:
            if heading != "education" and current:
                blocks.append("\n".join(current))
                current = []
            preceding_institution = None
            continue
        if DEGREE_RE.search(line):
            if current:
                blocks.append("\n".join(current))
            current = ([preceding_institution] if preceding_institution else []) + [line]
            preceding_institution = None
            continue
        if current:
            current.append(line)
        elif _looks_like_institution(line):
            preceding_institution = line

    if current:
        blocks.append("\n".join(current))
    return blocks


def _looks_like_institution(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:university|universit(?:y|ies)|college|institute|school|"
            r"polytechnic|academy|campus|IIT|NIT|IIIT|BITS|MIT|VIT)\b",
            text,
            re.I,
        )
    )


def _extract_experience(section: str, doc) -> list[dict[str, Any]]:
    if not section:
        return []
    blocks = _chunk_blocks(section)
    jobs = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        dates = _first_match(DATE_RANGE_RE, block) or ", ".join(YEAR_RE.findall(block)[:2])
        metadata = []
        highlights = []
        for line in lines:
            date_match = DATE_RANGE_RE.search(line)
            if date_match:
                line = (
                    line[:date_match.start()] + line[date_match.end():]
                ).strip(" ,-|")
            if not line or YEAR_RE.fullmatch(line):
                continue
            if line.lstrip().startswith(("-", "*", "•")):
                highlights.append(line.lstrip("-*• \t"))
            elif not highlights:
                metadata.append(line.strip(" -•\t"))
            else:
                highlights.append(line.strip())

        title, company = _split_experience_header(metadata)
        jobs.append(
            {
                "title": title,
                "company": company,
                "dates": dates or None,
                "highlights": [line for line in highlights if len(line) > 25][:8],
            }
        )
    return jobs[:10]


def _split_experience_header(lines: list[str]) -> tuple[str | None, str | None]:
    if not lines:
        return None, None

    header = lines[0]
    parts = re.split(r"\s+(?:at|@)\s+|[,|–—]\s*", header, maxsplit=1, flags=re.I)
    if len(parts) == 1:
        parts = re.split(r"\s+-\s+", header, maxsplit=1)
    if len(parts) == 2:
        first, second = (part.strip(" ,-|") for part in parts)
        first_is_title = any(hint in first.lower() for hint in JOB_TITLE_HINTS)
        second_is_title = any(hint in second.lower() for hint in JOB_TITLE_HINTS)
        if first_is_title != second_is_title:
            return (first, second) if first_is_title else (second, first)
        return first, second

    title = next(
        (line for line in lines[:3] if any(hint in line.lower() for hint in JOB_TITLE_HINTS)),
        lines[0],
    )
    company = next((line for line in lines[:3] if line != title), None)
    return title, company


def _extract_bullet_items(section: str) -> list[str]:
    if not section:
        return []
    items = []
    for line in section.split("\n"):
        line = line.strip(" \t")
        line = line.lstrip("-*• ").strip()
        if len(line) > 8:
            items.append(line)
    return items[:12]


def _extract_languages(section: str, skills: list[str]) -> list[str]:
    found = []
    source = section if section else " ".join(skills)
    for token in re.split(r"[,;/|\n]+", source):
        word = token.strip().lower()
        if word in SPOKEN_LANGUAGES:
            found.append(token.strip().title())
    return list(dict.fromkeys(found))


def _extract_summary(sections: dict[str, str], contact: dict[str, Any]) -> str | None:
    if sections.get("summary"):
        text = re.sub(r"\s+", " ", sections["summary"]).strip()
        return text[:800]
    header = sections.get("header", "")
    lines = [
        ln.strip()
        for ln in header.split("\n")
        if ln.strip()
        and ln.strip() != contact.get("name")
        and not EMAIL_RE.search(ln)
        and not PHONE_RE.search(ln)
    ]
    prose = " ".join(ln for ln in lines if len(ln) > 40)
    return prose[:800] or None


def _collect_entities(doc) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for ent in doc.ents:
        if ent.label_ not in {"PERSON", "ORG", "GPE", "LOC", "DATE", "DEGREE"}:
            continue
        text = ent.text.strip()
        if not text or "\n" in text or _heading_key(text):
            continue
        normalized = re.sub(r"[^a-z0-9+#.]+", " ", text.lower()).strip()
        if text.endswith((",", ":")) or re.fullmatch(r"[a-z]\d+", normalized):
            continue
        if normalized in SPOKEN_LANGUAGES or _looks_like_skill_entity(normalized):
            continue
        if ent.label_ == "DATE" and PHONE_RE.search(text):
            continue
        bucket = grouped.setdefault(ent.label_, [])
        if text not in bucket:
            bucket.append(text)
    for key in grouped:
        grouped[key] = grouped[key][:12]
    return grouped


def _looks_like_skill_entity(text: str) -> bool:
    for skill in SKILL_GAZETTEER:
        candidate = re.escape(skill.lower())
        if re.search(rf"(?<![\w+#]){candidate}(?![\w+#])", text):
            return True
        if re.search(rf"(?<![\w+#]){re.escape(text)}(?![\w+#])", skill.lower()):
            return True
    return False


def _chunk_blocks(section: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", section.strip())
    if len(parts) == 1:
        lines = [ln for ln in section.split("\n") if ln.strip()]
        parts = []
        current: list[str] = []
        for line in lines:
            if current and not line.strip().startswith(("•", "-", "*")) and len(line) < 80:
                if any(hint in line.lower() for hint in JOB_TITLE_HINTS) or DEGREE_RE.search(line):
                    parts.append("\n".join(current))
                    current = [line]
                    continue
            current.append(line)
        if current:
            parts.append("\n".join(current))
    return [p.strip() for p in parts if p.strip()]


def _first_match(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text or "")
    return match.group(0).strip() if match else None
