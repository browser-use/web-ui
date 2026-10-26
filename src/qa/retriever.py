"""Lexical retrieval over the Hindsight store.

Stdlib-only, dependency-free scoring so the agent works with no embedding
model and no network access: a simple term-overlap score over Latin tokens
plus CJK bigrams (Hindsight content is sometimes Chinese — see CLAUDE.md),
with a light boost for tag and title matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.memory.exceptions import HindsightError, NotFoundError
from src.memory.store import HindsightStore

from .exceptions import RetrievalError

_LATIN_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RE = re.compile(r"[一-鿿]+")

# Low-content Chinese/English question particles. Shared by the retriever's
# scoring (they must not count as retrieval evidence — a question that is
# nothing but "什么是" + a term the KB doesn't have would otherwise still
# score high enough to pass MIN_SCORE) and by the agent's query-widening.
STOPWORDS = {
    "什么", "是", "的", "吗", "呢", "如何", "怎么", "怎样", "为什么", "哪个", "哪些",
    "what", "is", "are", "the", "a", "an", "how", "why", "does", "do", "to", "of",
}


def meaningful_tokens(tokens: List[str]) -> List[str]:
    """Drop stopwords, but never return an empty list for a non-empty input.

    A query that happens to be made entirely of stopwords (e.g. a bare "是
    什么") still needs *something* to score against, so it falls back to the
    original tokens rather than making every retrieval score zero.
    """
    filtered = [t for t in tokens if t not in STOPWORDS]
    return filtered or list(tokens)


def tokenize(text: str) -> List[str]:
    """Split text into lowercase Latin word tokens plus CJK bigrams.

    A pure word-boundary tokenizer misses CJK text entirely (no spaces), so
    any run of CJK characters is additionally split into overlapping
    bigrams, which gives reasonable recall for short Chinese phrases without
    pulling in a real segmenter.
    """
    if not text:
        return []
    tokens = [t.lower() for t in _LATIN_TOKEN_RE.findall(text)]
    for run in _CJK_RE.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


@dataclass
class QASource:
    """One retrieved memory, scored against a query."""

    id: str
    project_id: str
    title: str
    content: str
    type: str
    tags: List[str] = field(default_factory=list)
    score: float = 0.0

    def citation_tag(self) -> str:
        return f"[{self.id}]"

    def as_prompt_block(self) -> str:
        return (f"{self.citation_tag()} {self.title}\n"
                f"type={self.type} tags={','.join(self.tags) or '-'}\n"
                f"{self.content}")


class Retriever:
    """Ranks Hindsight memories against a free-text query."""

    def __init__(self, store: HindsightStore):
        self.store = store

    def retrieve(self, query: str, project_id: Optional[str] = None,
                 top_k: int = 5) -> List[QASource]:
        top_k = max(0, top_k)
        q_tokens = tokenize(query)
        if not q_tokens or top_k == 0:
            return []
        q_set = set(meaningful_tokens(q_tokens))
        needle = (query or "").strip().lower()

        try:
            # One pass over every in-scope memory: the exact-phrase
            # substring check is computed inline against the same text
            # already tokenized for scoring, rather than issuing a separate
            # `store.search()` call that would re-list every project's
            # memories from disk a second time.
            project_ids = ([project_id] if project_id
                           else [p.id for p in self.store.list_projects()])
            pool: Dict[str, object] = {}
            for pid in project_ids:
                try:
                    for mem in self.store.list_memories(pid):
                        pool.setdefault(mem.id, mem)
                except NotFoundError:
                    continue
        except HindsightError as exc:
            raise RetrievalError("could not read the memory store while retrieving",
                                  detail=str(exc)) from exc

        scored: List[QASource] = []
        for mem in pool.values():
            # Newline-separated, matching store.search()'s own separator —
            # joining with plain spaces could let a substring match span the
            # title/content boundary (e.g. title ending "...foo" + content
            # starting "bar..." reading as "foobar") that wouldn't have
            # matched either field on its own.
            full_text = f"{mem.title}\n{mem.content}\n{' '.join(mem.tags)}"
            h_set = set(tokenize(full_text))
            if not h_set:
                continue
            overlap = q_set & h_set
            if not overlap:
                # No tokenized evidence at all: in particular, this excludes
                # a needle that only matches as a substring *inside* a
                # larger token (e.g. query "cat" inside content
                # "concatenate") — tokenize() never splits "concatenate"
                # into "cat", so that's not real word-level evidence, only
                # an accident of Python's `in` operator.
                continue
            is_substring_hit = bool(needle) and needle in full_text.lower()
            # Overlap ratio against the query (recall-oriented) with a small
            # title-match and exact-phrase-hit bonus.
            score = len(overlap) / max(len(q_set), 1)
            if any(t in tokenize(mem.title) for t in overlap):
                score += 0.25
            if is_substring_hit:
                score += 0.5
            scored.append(QASource(id=mem.id, project_id=mem.project_id,
                                    title=mem.title, content=mem.content,
                                    type=mem.type, tags=list(mem.tags),
                                    score=round(score, 4)))
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:top_k]
