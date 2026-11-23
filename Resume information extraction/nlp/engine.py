"""NLP backend: spaCy when the runtime allows it, rules otherwise."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from nlp.rules import DEGREE_RULER_PATTERNS, SKILL_GAZETTEER  # noqa: F401


@dataclass
class SimpleSpan:
    text: str
    label_: str
    start: int = 0


@dataclass
class SimpleSent:
    text: str


@dataclass
class SimpleDoc:
    text: str
    ents: list[SimpleSpan] = field(default_factory=list)
    sents: list[SimpleSent] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


@dataclass
class EngineInfo:
    name: str
    using_spacy: bool
    note: str


@lru_cache(maxsize=1)
def engine_info() -> EngineInfo:
    try:
        nlp = _load_spacy()
        nlp("spaCy backend check")
        return EngineInfo("spaCy + rules", True, "en_core_web_sm NER, EntityRuler, PhraseMatcher")
    except Exception as exc:  # noqa: BLE001
        return EngineInfo(
            "rule-based fallback",
            False,
            f"spaCy could not start ({exc.__class__.__name__}). Using gazetteers, regex, and section rules.",
        )


def analyze(text: str) -> SimpleDoc:
    if engine_info().using_spacy:
        return _analyze_spacy(text)
    return _analyze_rules(text)


@lru_cache(maxsize=1)
def _load_spacy():
    import spacy
    from spacy.matcher import PhraseMatcher

    nlp = spacy.load("en_core_web_sm")
    if "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
        ruler.add_patterns(DEGREE_RULER_PATTERNS)
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("SKILL", [nlp.make_doc(skill) for skill in SKILL_GAZETTEER])
    nlp.skill_matcher = matcher
    return nlp


def _analyze_spacy(text: str) -> SimpleDoc:
    nlp = _load_spacy()
    doc = nlp(text[:100_000])
    skills = []
    for _, start, end in nlp.skill_matcher(doc):
        span = doc[start:end].text.strip()
        if span:
            skills.append(span)
    return SimpleDoc(
        text=doc.text,
        ents=[SimpleSpan(ent.text, ent.label_, ent.start) for ent in doc.ents],
        sents=[SimpleSent(sent.text) for sent in doc.sents],
        skills=skills,
    )


ORG_RE = re.compile(
    r"\b((?:National|Indian)\s+Institute\s+of\s+Technology(?:\s+[A-Za-z]+)?|"
    r"[A-Z][A-Za-z0-9&.\-]+(?:\s+[A-Z][A-Za-z0-9&.\-]+){0,5}\s+"
    r"(?:Inc|Ltd|LLC|Labs|Analytics|University|Institute|College|Corporation|"
    r"Technologies|Systems|Pvt\.?|Limited))\b"
)
GPE_RE = re.compile(
    r"\b(Bengaluru|Bangalore|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|"
    r"Ahmedabad|Jaipur|Noida|Gurgaon|Gurugram|India|United States|USA|"
    r"New York|San Francisco|London|Singapore|Remote)\b",
    re.I,
)


def _analyze_rules(text: str) -> SimpleDoc:
    ents: list[SimpleSpan] = []
    for match in ORG_RE.finditer(text):
        ents.append(SimpleSpan(match.group(0), "ORG", match.start()))
    for match in GPE_RE.finditer(text):
        ents.append(SimpleSpan(match.group(1), "GPE", match.start()))

    lower = text.lower()
    skills = []
    for skill in sorted(SKILL_GAZETTEER, key=len, reverse=True):
        pattern = rf"(?<![\w+#]){re.escape(skill.lower())}(?![\w+#])"
        if re.search(pattern, lower):
            skills.append(skill)

    sents = [SimpleSent(part.strip()) for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
    return SimpleDoc(text=text, ents=ents, sents=sents, skills=skills)
