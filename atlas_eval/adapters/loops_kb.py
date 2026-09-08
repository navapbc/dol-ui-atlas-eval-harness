"""The LOOPS KB transport: import the served pipeline, ask it directly.

Every LOOPS number recorded so far was produced by hand, one question at a
time, because this file did not exist. That is why the comparison against
Quick rests on two questions while forty-eight written ones sit unused --
not because the questions are bad, but because nothing could drive them.

Three decisions are worth defending, since each one had a plausible
alternative that would have made the resulting scores less trustworthy.

**It imports `tools/loops_kb_mcp.py` and calls the tool function, rather
than speaking MCP over stdio to a subprocess.** What is under evaluation is
retrieval and synthesis, not the MCP framing, and the framing is the one
layer with no bearing on answer quality. Importing keeps the real query
expansion, the real rank fusion, the real document summary headers and the
real synthesis prompt in the path, while removing a subprocess whose
failures would be indistinguishable from bad answers. If the transport
itself ever needs testing, that is a second adapter, not a flag on this one.

**It redirects the Q&A store.** The served module persists every ask to a
single default SQLite file, which is also the file the usage and cost
figures are read from. A fifty-question sweep at five repetitions is 250
rows; mixed into real usage they are unseparable after the fact. So this
sets `LOOPS_KB_DB` to a run-scoped path *before* importing the module,
because the module resolves its store path at import time. The eval store
is still a complete trace -- queries, fused chunks, scores, token counts --
it is just a trace of the benchmark rather than of production.

**It never authenticates.** Expired credentials surface as
`AUTH_REQUIRED`, exactly like a Quick session that needs a login, and the
operator resolves it. An adapter that silently refreshed a session would
make "the run worked" and "the run worked against the corpus we thought"
into the same observation.

One limitation is structural and is recorded in `snapshot()` rather than
worked around: **this backend has no conversation.** Each question is an
independent call with no memory of the previous answer. Five questions
across v3, v4 and v7 declare an `after` dependency and only mean something
as a follow-up. They are still asked in the resolved order -- order is
cheap and harmless -- but a reviewer comparing them against a conversational
backend is comparing different things, so the ids are named in the snapshot
and travel with the run record.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path

from atlas_eval.adapters.base import AskResult, Response, TransportError
from atlas_eval.models import Question

DEFAULT_REPO = Path.home() / "dev" / "loops-knowledge-base"

# Substrings that mean "the credential chain has nothing usable", as opposed to
# any other boto3 failure. Matched case-insensitively against the exception
# text because botocore raises several distinct classes for one situation.
_AUTH_MARKERS = (
    "expiredtoken",
    "token has expired",
    "unable to locate credentials",
    "nocredentials",
    "invalidclienttokenid",
    "accessdenied",
    "sso session",
)

_TIMEOUT_MARKERS = ("timeout", "timed out", "read timeout", "connecttimeout")

# What the served module returns when fusion admitted nothing at all. Recorded
# as a real answer, not an error: an empty retrieval IS the system's behaviour
# on that question and a gap probe may well deserve credit for it.
NO_SOURCES = "No relevant sources found in the knowledge base."


def _classify(error: BaseException) -> tuple[str, str]:
    """Map a served-pipeline exception onto a stable TransportError code."""
    text = f"{type(error).__name__}: {error}".lower()
    if any(marker in text for marker in _AUTH_MARKERS):
        return "AUTH_REQUIRED", f"{type(error).__name__}: {error}"
    if any(marker in text for marker in _TIMEOUT_MARKERS):
        return "TIMEOUT", f"{type(error).__name__}: {error}"
    return "PARSE_FAILED", f"{type(error).__name__}: {error}"


def load_served_module(repo: Path, eval_db: Path):
    """Import `tools/loops_kb_mcp.py` with the store pointed at `eval_db`.

    The module reads its configuration, including the store path, at import
    time, so the environment has to be set first. `tools/` goes on the path
    because the module imports its corpus and store helpers by bare name.
    """
    tools = repo / "tools"
    target = tools / "loops_kb_mcp.py"
    if not target.is_file():
        raise TransportError("PARSE_FAILED", f"served module not found at {target}")

    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))

    previous = os.environ.get("LOOPS_KB_DB")
    os.environ["LOOPS_KB_DB"] = str(eval_db)
    try:
        spec = importlib.util.spec_from_file_location("loops_kb_mcp_eval", target)
        module = importlib.util.module_from_spec(spec)
        sys.modules["loops_kb_mcp_eval"] = module
        spec.loader.exec_module(module)
    except Exception as error:  # noqa: BLE001 - re-raised as a transport code
        code, detail = _classify(error)
        raise TransportError(code, f"importing served module: {detail}") from error
    finally:
        if previous is None:
            os.environ.pop("LOOPS_KB_DB", None)
        else:
            os.environ["LOOPS_KB_DB"] = previous

    if str(getattr(module, "DB_PATH", "")) != str(eval_db):
        raise TransportError(
            "PARSE_FAILED",
            "served module ignored LOOPS_KB_DB; refusing to write benchmark rows "
            f"to {getattr(module, 'DB_PATH', '<unset>')}",
        )
    return module


def _callable_tool(module, name: str):
    """Return the plain function behind an `@mcp.tool()` decorated name."""
    tool = getattr(module, name, None)
    if tool is None:
        raise TransportError("PARSE_FAILED", f"served module exposes no {name}")
    # FastMCP versions differ: some leave the function, some wrap it.
    for attribute in ("fn", "func", "__wrapped__"):
        candidate = getattr(tool, attribute, None)
        if callable(candidate):
            return candidate
    if callable(tool):
        return tool
    raise TransportError("PARSE_FAILED", f"{name} is not callable")


def split_answer_and_citations(raw: str) -> tuple[str, list[str]]:
    """Separate the synthesized answer from its trailing source list.

    The served tool appends `Sources:` followed by one `[n] <uri>` line per
    fused chunk. Note what that means for scoring: the footer lists everything
    RETRIEVED, not everything used, so a citation check against it measures
    retrieval and nothing more. The split is done here so the scorer sees the
    answer prose alone and cannot accidentally credit a document that appears
    only in the footer.
    """
    marker = "\n\nSources:\n"
    index = raw.rfind(marker)
    if index == -1:
        return raw.strip(), []

    body = raw[:index].strip()
    citations: list[str] = []
    for line in raw[index + len(marker) :].splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        _, _, uri = line.partition("] ")
        uri = uri.strip()
        if uri:
            citations.append(uri.rsplit("/", 1)[-1])
    return body, citations


class LoopsKbBackend:
    """Backend that asks the served LOOPS KB pipeline, one call per question."""

    name = "loops-kb"
    transport = "bedrock-kb"

    def __init__(
        self,
        *,
        eval_db: Path | str,
        repo: Path | str = DEFAULT_REPO,
        num_results: int = 10,
    ) -> None:
        self.repo = Path(repo).expanduser().resolve()
        self.eval_db = Path(eval_db).expanduser().resolve()
        self.num_results = int(num_results)
        self._module = None
        self._ask = None

    def _ensure_loaded(self):
        if self._module is None:
            self._module = load_served_module(self.repo, self.eval_db)
            self._ask = _callable_tool(self._module, "ask_knowledge_base")
        return self._module

    def snapshot(self) -> dict:
        """Every knob that changes what an answer means. Read-only."""
        module = self._ensure_loaded()
        head = self._git_head()
        return {
            "backend": self.name,
            "transport": self.transport,
            "repo": str(self.repo),
            "repo_head": head,
            "kb_id": module.KB_ID,
            "corpus_digest": module.CORPUS_DIGEST,
            "region": module.REGION,
            "synthesis_model": module.MODEL,
            "expansion_model": module.EXPANSION_MODEL,
            "search_type": "HYBRID",
            "num_results": self.num_results,
            "retrieval_depth": module.RETRIEVAL_DEPTH,
            "max_expansions": module.MAX_EXPANSIONS,
            "max_chunks_per_doc": module.MAX_CHUNKS_PER_DOC,
            "rrf_k": module.RRF_K,
            "original_query_weight": module.ORIGINAL_QUERY_WEIGHT,
            "evidence_chars": module.EVIDENCE_CHARS,
            "doc_summaries_enabled": module.DOC_SUMMARIES,
            "eval_store": str(self.eval_db),
            # Read this before comparing per-question scores against a
            # conversational backend. See the module docstring.
            "conversation": "none: each question is an independent call",
            "trace": "full per-call trace in eval_store (queries, fused chunks, usage)",
        }

    def _git_head(self) -> str | None:
        head = self.repo / ".git" / "HEAD"
        try:
            content = head.read_text().strip()
        except OSError:
            return None
        if content.startswith("ref: "):
            ref = self.repo / ".git" / content[5:]
            try:
                return ref.read_text().strip()
            except OSError:
                return None
        return content

    def ask(self, questions: list[Question]) -> AskResult:
        """Ask every question in the given order. One call each, no memory."""
        self._ensure_loaded()
        responses: list[Response] = []
        for question in questions:
            asked_at = datetime.now()
            try:
                raw = self._ask(question=question.text, num_results=self.num_results)
            except TransportError:
                raise
            except Exception as error:  # noqa: BLE001 - mapped to a stable code
                code, detail = _classify(error)
                # Stop the run rather than record a blank: a credential or
                # timeout failure partway through would otherwise look like the
                # system declining to answer.
                raise TransportError(code, f"{question.id}: {detail}") from error

            answer, citations = split_answer_and_citations(raw or "")
            responses.append(
                Response(
                    question_id=question.id,
                    answer=answer,
                    asked_at=asked_at,
                    citations=citations,
                )
            )

        missing = [q.id for q in questions if not any(r.question_id == q.id for r in responses)]
        return AskResult(
            responses=responses,
            conversation_id=None,  # structural: this backend has no conversation
            complete=not missing,
            failure=("no answer for: " + ", ".join(missing)) if missing else None,
        )
