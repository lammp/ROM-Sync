r"""Deterministic Memory hook — raises REFLECTIVE QUESTIONS at the right moments.

Design intent: the hook must NOT assert facts or auto-inject memory. It
inserts a *subjective request* — a self-question — so the model reflects and
decides for itself whether to consult or capture Repository Memory. This is
exactly what you want from an LLM: prompt it to question itself at the right
cadence. Crude keyword detection is therefore fine — we are ASKING a
question, not asserting a conclusion, so being roughly right is enough; the
model makes the judgment.

  SessionStart      -> states the standing reflective posture + fact count.
  UserPromptSubmit  -> injects one compact self-check: consult memory if this is
                       ambiguous / a design|investigation|verification start;
                       and, when the wording suggests it, asks whether to
                       capture a fact (a challenge to a prior outcome, or a
                       CLAUDE.md clarification).

The hook NEVER blocks or errors the prompt: any failure exits 0 silently, and
trivial prompts get nothing (no noise).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Hook stdout is consumed by Claude Code as UTF-8; a Windows console is often
# cp1252, so force UTF-8 (errors=replace) or a non-ASCII char would raise and —
# caught by the safety wrapper — silently drop the whole nudge.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Wording that HINTS at a memory-creation moment. Not a verdict — just enough to
# raise the question. Tune to taste.
_CHALLENGE = (
    "that's wrong", "thats wrong", "that is wrong", "that's not right",
    "incorrect", "you shouldn't have", "why did you", "i disagree",
    "that's not what", "you missed", "this is a bug", "that's a bug",
    "should have", "not what i", "my intent was", "actually",
)
_CLARIFY = ("claude.md", "constitution", "legislation", "the rule",
            "what i meant", "to clarify", "clarify", "i meant")

# Skip nudging on trivial acknowledgements / very short prompts.
_TRIVIAL = {"yes", "no", "ok", "okay", "thanks", "thank you", "go", "proceed",
            "continue", "sure", "yep", "do it", "push", "commit"}


def _emit(lines: list[str]) -> None:
    if lines:
        print("\n".join(lines))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    event = data.get("hook_event_name", "")

    # --- PreToolUse: make "never hand-edit memory/" an enforced rule --------
    # The Constitution says all memory changes go through memory.py, and until
    # now nothing stopped a direct write. A rule the tooling does not enforce is
    # a rule that gets broken during exactly the hurried moment it exists for.
    # Deny with a reason, so the model is redirected rather than merely refused.
    if event == "PreToolUse":
        tool = data.get("tool_name", "")
        if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
            target = str(data.get("tool_input", {}).get("file_path", "")).replace("\\", "/")
            protected = ("/memory/" in target and target.endswith(".md")) \
                or target.endswith("/MEMORY.md")
            if protected:
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"{target} is Common Law and is written only through "
                            "the OKF gate. Hand-editing skips schema validation "
                            "and leaves MEMORY.md stale. Use: python "
                            "scripts/memory.py create|update|supersede|delete, "
                            "then reindex. MEMORY.md is generated — edit the fact, "
                            "not the index."),
                    }}))
        return

    # --- Stop: session boundary, and the whole automated cycle --------------
    # Stop cannot inject context, so logging is all it is good for as far as the
    # model is concerned — but a boundary is what turns a flat list of searches
    # into "searches per session". It is also the right place to do WORK: the
    # session is over, nothing is waiting, and nothing here costs anyone context.
    if event == "Stop":
        try:
            import memory as mem
            mem.log_query("session", "", {}, [])
            mem.cycle("stop")     # dreams if due; queues promote candidates
        except Exception:
            pass
        return

    if event == "SessionStart":
        lines: list[str] = []
        try:
            import memory as mem
            docs = mem.load_all()
            n = len(mem.active(docs))
            op = mem.open_cases(docs)
            prec = mem.precedents(docs)
        except Exception as exc:
            # Report the failure, never a zero. Saying "0 atomic fact(s)" when
            # the truth is "I could not read them" is the exact failure this
            # repository has recorded in the platform it studies: filling the
            # expected output shape from an empty result, so a broken run reads
            # as a healthy one. A missing dependency must look like a missing
            # dependency.
            _emit([
                "Repository Memory (Common Law) COULD NOT BE READ — "
                f"{type(exc).__name__}: {exc}. Memory is unavailable this "
                "session: do not treat an empty search as evidence that nothing "
                "was recorded. Most often this is a missing dependency on the "
                "interpreter the hook runs: try `pip install pyyaml`, and check "
                "that the `python` on PATH is the one the framework expects."])
            return

        # startup | resume | clear | compact. After a compaction the model is
        # mid-task and has just lost its standing context, so it needs the
        # settled readings and the query rule back — not the onboarding posture
        # it already received once this session.
        trigger = str(data.get("trigger", "startup")).lower()
        if trigger == "compact":
            lines.append(
                f"Context was compacted. Repository Memory still holds {n} fact(s) "
                f"and {len(op)} open case(s), and the standing posture is unchanged: "
                "consult before acting at Ambiguity Events, and search with KEYWORDS "
                "rather than the sentence you were asked. Re-stating the settled "
                "readings below because they were lost with the compacted context, "
                "not because anything about them has changed.")
            const = [d for d in prec
                     if str(d["meta"].get("rule", "")).split("#")[0] == "constitution"]
            for d in sorted(const, key=lambda x: str(x["meta"]["rule"])):
                lines.append(f"  · [{d['meta']['rule']}] {d['fact']}")
            _emit(lines)
            return

        lines.append(
            f"Repository Memory (Common Law) is active — {n} atomic fact(s), "
            f"{len(op)} open case(s). Standing posture: question yourself before "
            "acting. At Ambiguity Events and at the start of design / "
            "investigation / verification, reflect on whether past experience "
            "applies and consult memory (skill: memory-consult) rather than "
            "proceeding from the moment. Search with KEYWORDS, never with the "
            "sentence you were asked — the scorer matches substrings, so a "
            "natural-language query scores the whole corpus and ranks it as "
            "noise. When you challenge-resolve or clarify a rule, consider "
            "capturing a fact (skill: memory-capture). Recall/CRUD only via "
            "scripts/memory.py.")

        # Precedent is PUSHED, never pulled. By the time you would think to
        # search for an interpretation of a rule you have already read the rule
        # and formed your own reading, so the settled reading has to arrive
        # first or it does not arrive at all. Only Constitution-scoped precedent
        # is emitted here: the Constitution is loaded every session, so its
        # readings are always in play. Legislation precedent is delivered by
        # MEMORY.md, which is read when the unit is.
        const = [d for d in prec
                 if str(d["meta"].get("rule", "")).split("#")[0] == "constitution"]
        if const:
            lines.append("")
            lines.append("Settled readings of the supreme laws — apply these "
                         "rather than re-deriving them:")
            for d in sorted(const, key=lambda x: str(x["meta"]["rule"])):
                lines.append(f"  · [{d['meta']['rule']}] {d['fact']}")
        # Report what the cycle did while you were away — dreams that ran,
        # promotion candidates that appeared. Deliberately NOT in the `compact`
        # branch above: a compaction happens mid-session, by which point this
        # already reported once, and saying it twice is how a useful notice
        # becomes one that gets skimmed.
        try:
            import memory as mem
            rep = mem.cycle("session-start")
            if rep:
                lines += ["", rep]
        except Exception:
            pass
        _emit(lines)
        return

    if event != "UserPromptSubmit":
        return

    prompt = str(data.get("prompt", "")).strip()
    low = prompt.lower()
    if len(prompt) < 15 or low.strip(" .!") in _TRIVIAL:
        return   # nothing worth self-questioning here

    # Always raise the consult question — ambiguity can't be keyword-detected,
    # so the model must be the one to judge whether this moment needs memory.
    #
    # A nudge that fires on every turn risks being tuned out, and the answer is
    # not to fire less (there is no reliable ambiguity detector) but to keep it
    # short and make it carry something actionable: the query form to use. A
    # cheap, specific line survives repetition in a way a long exhortation does
    # not.
    lines = [
        "↳ Memory reflection: is this ambiguous, or the start of design / "
        "investigation / verification? If so, consult Repository Memory "
        "(skill: memory-consult) before answering — searching with KEYWORDS "
        "drawn from the problem, not with the sentence you were asked.",
    ]
    if any(k in low for k in _CHALLENGE):
        lines.append(
            "  · This may challenge a prior outcome — once you've resolved it, "
            "ask whether to capture the correction (skill: memory-capture, run "
            "ASYNC so the flow keeps moving).")
    if any(k in low for k in _CLARIFY):
        lines.append(
            "  · If this clarifies (does not change) a CLAUDE.md rule, ask "
            "whether to capture the interpretation (skill: memory-capture).")
    _emit(lines)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass   # never disrupt the prompt flow
