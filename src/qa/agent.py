"""The Agentic Q&A loop.

``QAAgent.ask`` runs: retrieve -> judge sufficiency -> (optionally widen the
query and retrieve again) -> generate a cited answer -> verify the answer is
actually grounded in what was retrieved. If at any point there is nothing to
ground an answer in, it returns an explicit refusal instead of guessing —
that refusal is the correct, successful outcome for an unanswerable
question, not an error.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol

from src.memory.exceptions import HindsightError
from src.memory.store import HindsightStore

from .exceptions import QAError, RetrievalError
from .retriever import STOPWORDS, QASource, Retriever, meaningful_tokens, tokenize

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(r"\[([A-Za-z0-9_]+)\]")


class SupportsGenerate(Protocol):
    """Minimal shape an LLM adapter must satisfy to be used for generation."""

    def invoke(self, prompt: str) -> Any:  # pragma: no cover - protocol
        ...


@dataclass
class QAAnswer:
    """The outcome of one `QAAgent.ask` call."""

    question: str
    answer: str
    sources: List[QASource] = field(default_factory=list)
    grounded: bool = False
    refused: bool = False
    refusal_reason: Optional[str] = None
    rounds_used: int = 0
    queries_tried: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": [{"id": s.id, "title": s.title, "score": s.score,
                        "project_id": s.project_id} for s in self.sources],
            "grounded": self.grounded,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            "rounds_used": self.rounds_used,
            "queries_tried": self.queries_tried,
        }


def _refusal(question: str, reason: str, sources: Optional[List[QASource]] = None,
             rounds_used: int = 0, queries_tried: Optional[List[str]] = None) -> QAAnswer:
    return QAAnswer(
        question=question,
        answer="我在当前知识库里没有找到足以支撑答案的资料,不进行猜测。" + reason,
        sources=sources or [],
        grounded=False,
        refused=True,
        refusal_reason=reason,
        rounds_used=rounds_used,
        queries_tried=queries_tried or [question],
    )


class QAAgent:
    """Retrieval-augmented Q&A agent over a :class:`HindsightStore`.

    ``llm`` is optional: anything exposing ``.invoke(prompt) -> str`` (e.g. a
    LangChain chat model from ``src.utils.llm_provider.get_llm_model``). Without one,
    the agent still answers, but only by *extracting* the top-scoring source
    verbatim rather than synthesizing free text — correctness takes priority
    over fluency when there is no model to check its own citations.
    """

    #: Minimum per-source overlap score to consider a retrieval "sufficient"
    #: evidence rather than a guess.
    MIN_SCORE = 0.2

    #: Minimum fraction of the answer's own (non-stopword) tokens that must
    #: also appear in the content of the sources it cites. A citation alone
    #: proves nothing — a model can attach a real [memory_id] to a claim that
    #: id's content never supports — so groundedness also requires the
    #: answer text to actually overlap with what was cited.
    MIN_CONTENT_SUPPORT = 0.3

    def __init__(self, store: Optional[HindsightStore] = None,
                 llm: Optional[SupportsGenerate] = None):
        self.store = store or HindsightStore()
        self.retriever = Retriever(self.store)
        self.llm = llm

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def ask(self, question: str, project_id: Optional[str] = None,
            max_rounds: int = 2, top_k: int = 5) -> QAAnswer:
        question = (question or "").strip()
        if not question:
            raise QAError("question must not be empty")

        try:
            sources_by_id = {}
            queries_tried: List[str] = []
            current_query = question
            rounds_used = 0

            for round_idx in range(max(1, max_rounds)):
                rounds_used += 1
                queries_tried.append(current_query)
                hits = self.retriever.retrieve(current_query, project_id=project_id,
                                                top_k=top_k)
                for hit in hits:
                    existing = sources_by_id.get(hit.id)
                    if existing is None or hit.score > existing.score:
                        sources_by_id[hit.id] = hit

                if self._has_sufficient_evidence(sources_by_id):
                    break

                next_query = self._widen_query(question, current_query, sources_by_id)
                if not next_query or next_query in queries_tried:
                    break
                current_query = next_query

            if not sources_by_id:
                return _refusal(question, "知识库中没有任何资料与问题相关。",
                                rounds_used=rounds_used, queries_tried=queries_tried)

            ranked = sorted(sources_by_id.values(), key=lambda s: s.score, reverse=True)

            if not self._has_sufficient_evidence(sources_by_id):
                return _refusal(
                    question,
                    f"检索到 {len(ranked)} 条相关资料,但相关度均低于阈值"
                    f"({self.MIN_SCORE}),可能是问题超出了知识库覆盖范围。",
                    sources=ranked[:top_k], rounds_used=rounds_used,
                    queries_tried=queries_tried)

            answer_text, cited_ids = self._generate(question, ranked[:top_k])
            grounded, reason = self._check_grounded(answer_text, cited_ids, sources_by_id)

            if not grounded:
                return _refusal(question, reason, sources=ranked[:top_k],
                                rounds_used=rounds_used, queries_tried=queries_tried)

            return QAAnswer(
                question=question,
                answer=answer_text,
                sources=[sources_by_id[cid] for cid in cited_ids if cid in sources_by_id],
                grounded=True,
                refused=False,
                rounds_used=rounds_used,
                queries_tried=queries_tried,
            )
        except QAError:
            raise
        except HindsightError as exc:
            raise RetrievalError("the memory store failed during Q&A",
                                  detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - last-resort guard, see memory.store.guard
            logger.exception("Unexpected QA agent failure")
            raise QAError("unexpected failure while answering the question",
                          detail=str(exc)) from exc

    # ------------------------------------------------------------------ #
    # Sufficiency / query widening
    # ------------------------------------------------------------------ #
    def _has_sufficient_evidence(self, sources_by_id: dict) -> bool:
        if not sources_by_id:
            return False
        return max(s.score for s in sources_by_id.values()) >= self.MIN_SCORE

    def _widen_query(self, original_question: str, current_query: str,
                      sources_by_id: dict) -> Optional[str]:
        """Build a second-round query from the question's content words.

        Drops question particles / stopwords so round 2 searches on nouns
        and named entities rather than repeating a query that already
        returned weak evidence.
        """
        tokens = [t for t in tokenize(original_question)
                 if t not in STOPWORDS and len(t) > 1]
        if not tokens:
            return None
        widened = " ".join(dict.fromkeys(tokens))  # dedupe, preserve order
        if widened == current_query:
            return None
        return widened

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def _generate(self, question: str, sources: List[QASource]) -> tuple:
        if self.llm is not None:
            try:
                return self._generate_with_llm(question, sources)
            except Exception as exc:  # noqa: BLE001 - fall back rather than hard-fail
                logger.warning("LLM generation failed, falling back to extractive "
                               "answer: %s", exc)
        return self._generate_extractive(question, sources)

    def _generate_with_llm(self, question: str, sources: List[QASource]) -> tuple:
        context = "\n\n".join(s.as_prompt_block() for s in sources)
        prompt = (
            "你是一个只能依据给定资料回答问题的助手。严格规则:\n"
            "1. 只使用下面“资料”中的信息作答,不要使用你自己的知识或猜测。\n"
            "2. 每一条你写下的事实陈述后面,必须用形如 [memory_id] 的引用标注来源。\n"
            "3. 如果资料不足以回答问题,直接回复“资料不足,无法回答”,不要编造。\n\n"
            f"资料:\n{context}\n\n"
            f"问题:{question}\n\n"
            "请作答(记得每条事实都要标注引用):"
        )
        result = self.llm.invoke(prompt)
        text = getattr(result, "content", result)
        text = str(text)
        cited_ids = _CITATION_RE.findall(text)
        return text, cited_ids

    def _generate_extractive(self, question: str, sources: List[QASource]) -> tuple:
        """No-LLM fallback: quote the top source(s) verbatim with citations.

        This is deliberately unfancy — it can never hallucinate because it
        never generates free text, only copies retrieved content back out
        with its citation attached.
        """
        lines = []
        cited_ids = []
        for src in sources:
            if src.score < self.MIN_SCORE:
                continue
            snippet = src.content.strip()
            if not snippet:
                # An empty-content memory has nothing to quote; citing it
                # with no text would look like a grounded answer while
                # actually asserting nothing. Let the no-citation refusal
                # path handle this instead.
                continue
            if len(snippet) > 600:
                snippet = snippet[:600].rstrip() + "…"
            lines.append(f"{snippet} {src.citation_tag()}")
            cited_ids.append(src.id)
            if len(cited_ids) >= 3:
                break
        text = "\n\n".join(lines) if lines else "资料不足,无法回答。"
        return text, cited_ids

    # ------------------------------------------------------------------ #
    # Groundedness verification
    # ------------------------------------------------------------------ #
    def _check_grounded(self, answer_text: str, cited_ids: List[str],
                        sources_by_id: dict) -> tuple:
        if "资料不足" in answer_text and not cited_ids:
            return False, "模型自身判断资料不足以回答。"
        if not cited_ids:
            return False, "答案没有包含任何 [memory_id] 引用,拒绝作为已核实答案返回。"
        unknown = [cid for cid in cited_ids if cid not in sources_by_id]
        if unknown:
            return False, f"答案引用了未被检索到的来源 {unknown},可能是编造的引用。"

        # Citing a real id is necessary but not sufficient: verify the
        # answer's own content actually overlaps with what the cited
        # sources say, so an arbitrary claim glued to a real [memory_id]
        # does not pass as grounded.
        answer_tokens = meaningful_tokens(tokenize(_CITATION_RE.sub("", answer_text)))
        if not answer_tokens:
            return False, "答案除引用标记外没有可核实的内容。"
        cited_content_tokens = set()
        for cid in cited_ids:
            src = sources_by_id.get(cid)
            if src:
                cited_content_tokens.update(tokenize(f"{src.title} {src.content}"))
        supported = [t for t in answer_tokens if t in cited_content_tokens]
        support_ratio = len(supported) / len(answer_tokens)
        if support_ratio < self.MIN_CONTENT_SUPPORT:
            return False, (
                f"答案文本与其引用来源的内容重合度过低"
                f"({support_ratio:.2f} < {self.MIN_CONTENT_SUPPORT}),"
                f"引用可能与实际陈述的内容无关。")
        return True, ""
