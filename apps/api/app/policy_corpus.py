from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

from app.domain import RecommendationOutcome

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class PolicyDocument:
    source: str
    title: str
    tags: tuple[str, ...]
    keywords: tuple[str, ...]
    recommended_outcome: RecommendationOutcome
    escalation_required: bool
    body: str


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    source: str
    title: str
    section: str
    excerpt: str
    tags: tuple[str, ...]
    keywords: tuple[str, ...]
    recommended_outcome: RecommendationOutcome
    escalation_required: bool


@dataclass(frozen=True, slots=True)
class PolicyCorpusSummary:
    policy_dir: str
    document_count: int
    chunk_count: int
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_dir": self.policy_dir,
            "document_count": self.document_count,
            "chunk_count": self.chunk_count,
            "sources": list(self.sources),
        }


DEFAULT_POLICY_DIR = Path(__file__).resolve().parent.parent / "policies"


def _normalize_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        tokens.update(_WORD_RE.findall(value.lower()))
    return tokens


def _parse_csv_field(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_frontmatter(content: str, source_path: Path) -> tuple[dict[str, str], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"policy document {source_path} must start with frontmatter")

    frontmatter: dict[str, str] = {}
    body_start: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        if stripped == "---":
            body_start = index + 1
            break
        if not stripped:
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter entry in {source_path}: {line!r}")
        key, raw_value = line.split(":", 1)
        frontmatter[key.strip().lower()] = raw_value.strip()

    if body_start is None:
        raise ValueError(f"policy document {source_path} is missing a closing frontmatter fence")

    body = "\n".join(lines[body_start:]).strip()
    if not body:
        raise ValueError(f"policy document {source_path} has no body content")
    return frontmatter, body


def _parse_recommended_outcome(value: str, source_path: Path) -> RecommendationOutcome:
    try:
        return RecommendationOutcome(value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"policy document {source_path} has invalid recommended_outcome {value!r}") from exc


def _read_policy_document(path: Path) -> PolicyDocument:
    frontmatter, body = _parse_frontmatter(path.read_text(encoding="utf-8"), path)
    try:
        source = frontmatter["source"]
        title = frontmatter["title"]
        tags = _parse_csv_field(frontmatter.get("tags", ""))
        keywords = _parse_csv_field(frontmatter.get("keywords", ""))
        recommended_outcome = _parse_recommended_outcome(frontmatter["recommended_outcome"], path)
        escalation_required = frontmatter.get("escalation_required", "false").lower() == "true"
    except KeyError as exc:  # pragma: no cover - invalid document metadata is a build-time failure
        raise ValueError(f"policy document {path} is missing required metadata: {exc.args[0]}") from exc

    return PolicyDocument(
        source=source,
        title=title,
        tags=tags,
        keywords=keywords,
        recommended_outcome=recommended_outcome,
        escalation_required=escalation_required,
        body=body,
    )


def _section_chunks(document: PolicyDocument) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    lines = document.body.splitlines()
    current_section = "Overview"
    current_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_lines
        section_text = "\n".join(current_lines).strip()
        if section_text:
            paragraphs = [paragraph.strip().replace("\n", " ") for paragraph in section_text.split("\n\n") if paragraph.strip()]
            excerpt = " ".join(paragraphs[:2]) if paragraphs else section_text.replace("\n", " ")
            chunks.append(
                PolicyChunk(
                    source=document.source,
                    title=document.title,
                    section=current_section,
                    excerpt=excerpt[:260],
                    tags=document.tags,
                    keywords=document.keywords,
                    recommended_outcome=document.recommended_outcome,
                    escalation_required=document.escalation_required,
                )
            )
        current_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            continue
        if stripped.startswith("## "):
            flush_section()
            current_section = stripped[3:].strip() or "Overview"
            continue
        current_lines.append(line)

    flush_section()
    return chunks


@lru_cache(maxsize=4)
def build_policy_corpus(policy_dir: str | Path = DEFAULT_POLICY_DIR) -> tuple[PolicyChunk, ...]:
    directory = Path(policy_dir)
    if not directory.exists():
        return ()

    documents = [
        _read_policy_document(path)
        for path in sorted(directory.glob("*.md"))
        if path.is_file()
    ]

    chunks: list[PolicyChunk] = []
    for document in documents:
        chunks.extend(_section_chunks(document))

    return tuple(chunks)


@lru_cache(maxsize=4)
def load_policy_documents(policy_dir: str | Path = DEFAULT_POLICY_DIR) -> tuple[PolicyDocument, ...]:
    directory = Path(policy_dir)
    if not directory.exists():
        return ()

    documents = [
        _read_policy_document(path)
        for path in sorted(directory.glob("*.md"))
        if path.is_file()
    ]
    return tuple(documents)


@lru_cache(maxsize=4)
def policy_corpus_summary(policy_dir: str | Path = DEFAULT_POLICY_DIR) -> PolicyCorpusSummary:
    directory = Path(policy_dir)
    documents = load_policy_documents(directory)
    chunks = build_policy_corpus(directory)
    return PolicyCorpusSummary(
        policy_dir=str(directory),
        document_count=len(documents),
        chunk_count=len(chunks),
        sources=tuple(document.source for document in documents),
    )
