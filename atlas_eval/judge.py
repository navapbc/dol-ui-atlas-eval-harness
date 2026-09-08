"""LLM-as-judge scoring for a completed run.

`Rubric` in scoring.py has always had a `scored_by` field documented as holding
"a model id such as claude-opus-5, or a person's name for a hand-scored row".
The five dimensions were there, the provenance slot was there, and nothing ever
filled them from a model -- every rubric score to date was drafted by hand
outside the harness and, correctly, never imported. This module fills that slot
in a way that keeps the distinction between a machine draft and a human
judgement intact.

Four decisions shape it.

**Scores go to their own file, never into scores.csv.** A judge writes
`rubric-<judge>.csv` inside the run directory. scores.csv holds deterministic
results and whatever a person entered; a model must not be able to overwrite
either. Merging is a separate, deliberate step by someone who looked.

**The judge scores one answer against criteria, not two answers against each
other.** Pairwise comparison is the obvious design and it imports a known
defect: judges favour whichever answer they see first, so every comparison
needs order-swapping and twice the calls to cancel a bias that absolute scoring
never introduces. Scoring each answer on its own also means a run can be judged
the day it happens, without waiting for a comparator run to exist.

**Blinding is structural, not promised.** The prompt is built from the question,
the bank's criteria, and the answer text. The backend name, transport, run id
and config snapshot are never passed in, so there is no wording for a judge to
pick up on -- and no way for a future edit to accidentally leak it without
changing this module's signature.

**The judge can dispute the answer key.** The v7-Q2 ground truth is QUICK's own
output, and it conflates two files: the raw COBOL for DXCBD06E mentions
PAYUPD4F six times and PAYVSAM not once. A judge told to score against that key
would mark a correct answer wrong. So it gets an explicit channel to say the
expected answer looks unsupported, and that channel is a separate column rather
than a note nobody greps.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from atlas_eval.models import Question
from atlas_eval.rubric_entry import RUBRIC_ENTRY_COLUMNS
from atlas_eval.scoring import RUBRIC_DIMENSIONS, Rubric

# Bump when the prompt or the dimension definitions change. It lands in
# scored_by, so a score can always be traced to the exact instructions that
# produced it: "anthropic.claude-opus-5@judge-v1".
PROMPT_VERSION = "judge-v1"

# Sourced from scoring.py rather than restated: a dimension added there
# must not silently go unjudged here.
DIMENSIONS = RUBRIC_DIMENSIONS

SYSTEM_PROMPT = """\
You are grading one answer produced by a retrieval system over a corpus of
COBOL/mainframe analysis documents for a state unemployment insurance system.

Score five dimensions, each 0, 1 or 2:

- citations: are the cited documents the ones that actually support the claims?
  2 = support is present and specific. 1 = partly supported, or padded with
  documents that do not bear on the answer. 0 = unsupported or fabricated.
- correctness: are the substantive claims right? 2 = every critical fact
  correct. 1 = broadly right with a material omission or error. 0 = wrong on a
  critical fact.
- gap_honesty: how does it handle what the corpus does not contain? 2 = states
  the boundary explicitly and does not fill it. 1 = hedges vaguely. 0 = invents
  a confident answer for something absent. An honest "the sources do not cover
  this" scores 2 here even when correctness is low.
- scope_discipline: does it answer the question asked without drifting into
  adjacent material? 2 = on target. 0 = mostly off target.
- clarity: could an engineer act on it? 2 = clear and specific. 0 = confusing
  or evasive. Confident prose around a wrong claim is not clarity.

Judge only what the answer says against the criteria given. Do not reward
length, formatting or confidence.

If the expected answer supplied to you appears itself unsupported or internally
inconsistent, say so in ground_truth_concern and score the answer on the
evidence rather than on agreement with the key. Leave ground_truth_concern
empty when you have no such concern.

Reply with one JSON object and nothing else:
{"citations": 0-2, "correctness": 0-2, "gap_honesty": 0-2,
 "scope_discipline": 0-2, "clarity": 0-2,
 "notes": "<two sentences maximum, naming the specific defect or strength>",
 "ground_truth_concern": "<empty string, or what looks wrong with the key>"}
"""


class JudgeError(Exception):
    """A judgment could not be obtained or could not be trusted."""


class JudgeApiError(JudgeError):
    """The model endpoint rejected the request.

    Separate from an unparseable reply because the two want opposite handling.
    A malformed object is worth retrying and worth tolerating -- one bad reply
    in fifty should not discard the batch. An API rejection is a bad model id,
    a missing permission or a throttle: every remaining question fails
    identically, so continuing produces fifty skipped rows and a report that
    looks like a result.
    """


@dataclass
class Judgment:
    question_id: str
    rubric: Rubric
    ground_truth_concern: str = ""
    raw: str = ""

    @property
    def total(self) -> int:
        return sum(getattr(self.rubric, d) or 0 for d in DIMENSIONS)


@dataclass
class JudgeReport:
    judge: str
    judgments: list[Judgment] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(j.total for j in self.judgments)

    @property
    def available(self) -> int:
        return len(self.judgments) * 2 * len(DIMENSIONS)

    @property
    def concerns(self) -> list[Judgment]:
        return [j for j in self.judgments if j.ground_truth_concern.strip()]


def build_prompt(question: Question, answer: str) -> str:
    """Assemble the user turn. Carries no backend, run or transport identity."""
    parts = [
        f"QUESTION\n{question.text}",
        f"EXPECTED STANCE\n{question.expected_stance.value}",
        f"EXPECTED ANSWER (the key; may itself be wrong)\n{question.ground_truth}",
    ]
    if question.partial_credit:
        parts.append(f"PARTIAL CREDIT GUIDANCE\n{question.partial_credit}")
    checks = question.checks
    required = list(getattr(checks, "required_all", []) or [])
    forbidden = list(getattr(checks, "forbidden", []) or [])
    if required:
        parts.append("MUST BE PRESENT\n" + ", ".join(required))
    if forbidden:
        parts.append("MUST NOT BE PRESENT\n" + ", ".join(forbidden))
    parts.append(f"ANSWER UNDER REVIEW\n{answer}")
    return "\n\n".join(parts)


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def parse_judgment(question_id: str, raw: str, scored_by: str) -> Judgment:
    """Turn a judge's reply into a validated Judgment.

    Tolerant of a fenced or prose-wrapped object, strict about the values: a
    dimension outside 0-2 or a non-integer is an error, not something to clamp.
    A silently clamped score is indistinguishable from a real one later.
    """
    match = _JSON_BLOCK.search(raw or "")
    if not match:
        raise JudgeError(f"{question_id}: judge reply contained no JSON object")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        raise JudgeError(f"{question_id}: judge reply was not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise JudgeError(f"{question_id}: judge reply was not a JSON object")

    values: dict[str, int] = {}
    for dimension in DIMENSIONS:
        if dimension not in payload:
            raise JudgeError(f"{question_id}: judge omitted {dimension}")
        value = payload[dimension]
        if isinstance(value, bool) or not isinstance(value, int):
            raise JudgeError(
                f"{question_id}: {dimension} must be an integer 0-2, got {value!r}"
            )
        if not 0 <= value <= 2:
            raise JudgeError(f"{question_id}: {dimension} out of range 0-2: {value}")
        values[dimension] = value

    notes = payload.get("notes") or ""
    concern = payload.get("ground_truth_concern") or ""
    return Judgment(
        question_id=question_id,
        rubric=Rubric(**values, notes=str(notes).strip() or None, scored_by=scored_by),
        ground_truth_concern=str(concern).strip(),
        raw=raw,
    )


class BedrockJudge:
    """A judge backed by one Bedrock model. `client` is injectable for tests."""

    def __init__(self, model_id: str, client=None, region: str = "us-east-1",
                 profile: str | None = None, max_attempts: int = 2) -> None:
        self.model_id = model_id
        self.max_attempts = max(1, int(max_attempts))
        self._client = client
        self._region = region
        self._profile = profile

    @property
    def scored_by(self) -> str:
        return f"{self.model_id}@{PROMPT_VERSION}"

    def _runtime(self):
        if self._client is None:
            import boto3

            session = (
                boto3.Session(profile_name=self._profile) if self._profile else boto3.Session()
            )
            self._client = session.client("bedrock-runtime", region_name=self._region)
        return self._client

    def judge_one(self, question: Question, answer: str) -> Judgment:
        prompt = build_prompt(question, answer)
        last: JudgeError | None = None
        for _ in range(self.max_attempts):
            try:
                response = self._converse(prompt)
            except JudgeError:
                # An API rejection is deterministic -- a bad model id or a
                # missing permission fails identically on every retry, so
                # retrying only spends calls. Raise it as-is; the CLI prints a
                # message rather than a botocore traceback.
                raise
            try:
                return parse_judgment(question.id, self._text(response), self.scored_by)
            except JudgeError as error:
                last = error
        raise last or JudgeError(f"{question.id}: judge produced no usable reply")

    @staticmethod
    def _text(response: dict) -> str:
        return "".join(
            block.get("text", "") for block in response["output"]["message"]["content"]
        )

    def _converse(self, prompt: str) -> dict:
        # temperature 0 where the model still accepts it: as deterministic as
        # the API allows, though never a guarantee of identical output, which
        # is why the protocol repeats runs rather than trusting the parameter.
        # Newer models reject it outright ("`temperature` is deprecated for
        # this model"), so fall back once to sending no temperature at all
        # rather than pinning this to whichever generation shipped last.
        attempts = [{"maxTokens": 1024, "temperature": 0}, {"maxTokens": 1024}]
        try:
            for index, config in enumerate(attempts):
                try:
                    return self._runtime().converse(
                        modelId=self.model_id,
                        system=[{"text": SYSTEM_PROMPT}],
                        messages=[{"role": "user", "content": [{"text": prompt}]}],
                        inferenceConfig=config,
                    )
                except Exception as error:  # noqa: BLE001 - inspected below
                    deprecated = "temperature" in str(error) and "deprecat" in str(error)
                    if deprecated and index + 1 < len(attempts):
                        continue
                    raise
            raise JudgeApiError(f"judge model {self.model_id}: no usable inference config")
        except Exception as error:  # noqa: BLE001 - surfaced as a JudgeError
            hint = ""
            if "on-demand throughput isn" in str(error):
                # The bare model id from list-foundation-models is not
                # invocable; on-demand needs the inference profile.
                hint = (
                    f" -- {self.model_id} needs an inference profile id; try "
                    f"us.{self.model_id}"
                )
            raise JudgeApiError(
                f"judge model {self.model_id} rejected the request: "
                f"{type(error).__name__}: {error}{hint}"
            ) from error


def judge_run(
    judge: BedrockJudge,
    questions: list[Question],
    answers: dict[str, str],
    *,
    strict: bool = False,
) -> JudgeReport:
    """Judge every question that has an answer.

    A single unusable reply is recorded as skipped rather than discarding the
    whole batch, unless `strict`. Judging a fifty-question run costs real money
    and time; losing all of it to one malformed object is worse than a report
    that names what is missing.
    """
    report = JudgeReport(judge=judge.scored_by)
    for question in questions:
        answer = answers.get(question.id)
        if not answer:
            report.skipped.append(f"{question.id}: no answer in run")
            continue
        try:
            report.judgments.append(judge.judge_one(question, answer))
        except JudgeApiError:
            # Always fatal. See JudgeApiError.
            raise
        except JudgeError as error:
            if strict:
                raise
            report.skipped.append(str(error))
    return report


def fill_export_csv(in_path: Path, out_path: Path, report: JudgeReport) -> int:
    """Fill a `rubric export` CSV with the judge's scores.

    Deliberately fills an existing export rather than writing its own file.
    rubric_entry.py notes that the first fourteen columns are read positionally
    by an external chart, so inventing a column order here would work locally
    and break something downstream. Filling the export also means question_id,
    type, verification_status and deterministic_pass come from the harness
    rather than being recomputed, and the result drops straight into
    `atlas-eval rubric import` after a person has read it.

    A judge never writes a verification status. Rows it could not score keep
    their empty dimensions so the gap is visible instead of implied.
    """
    if out_path.name == "scores.csv":
        raise JudgeError(
            "refusing to write judge output to scores.csv: deterministic and "
            "human scores live there and a model must not overwrite them"
        )
    with in_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or ())
        rows = list(reader)
    if tuple(fieldnames) != RUBRIC_ENTRY_COLUMNS:
        raise JudgeError(
            f"{in_path} is not a rubric export: expected columns "
            f"{RUBRIC_ENTRY_COLUMNS}, got {tuple(fieldnames)}"
        )

    by_id = {j.question_id: j for j in report.judgments}
    filled = 0
    for row in rows:
        judgment = by_id.get(row["question_id"])
        if judgment is None:
            continue
        for dimension in DIMENSIONS:
            row[dimension] = getattr(judgment.rubric, dimension)
        note = judgment.rubric.notes or ""
        if judgment.ground_truth_concern:
            # Folded into notes rather than given its own column, for the
            # positional-read reason above. Prefixed so it can be found.
            note = f"KEY-DISPUTE: {judgment.ground_truth_concern} | {note}".strip(" |")
        row["notes"] = note
        row["scored_by"] = judgment.rubric.scored_by or ""
        filled += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return filled


def format_report(report: JudgeReport, questions: list[Question]) -> str:
    """A short operator summary. Deliberately does not print a pass/fail."""
    lines = [
        f"judge: {report.judge}",
        f"scored: {len(report.judgments)} of {len(questions)} questions",
        f"rubric total: {report.total}/{report.available}",
    ]
    if report.concerns:
        lines.append("")
        lines.append("answer keys the judge disputes:")
        for judgment in report.concerns:
            lines.append(f"  {judgment.question_id}: {judgment.ground_truth_concern}")
    if report.skipped:
        lines.append("")
        lines.append("not scored:")
        lines += [f"  {item}" for item in report.skipped]
    lines.append("")
    lines.append(
        "These are machine-drafted scores. Nothing here is a human judgement "
        "and no question's verification status changed."
    )
    return "\n".join(lines)
