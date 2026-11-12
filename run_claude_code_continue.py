"""Run Experiment 5 (MinAtar Breakout, Seaquest or Asterix) through Claude Code on a Claude subscription
(no API key), then read the weights and score the network.

Each run is one fresh Claude Code conversation: no tools, no MCP servers, no skills, no
settings files, a neutral one-line system prompt, prompt_<game>.txt on stdin
(the published prompt for that game, unchanged).

Resuming. The conversation is saved (in runs/.../runN/cwd), so a run is not lost when it
stops early:
  * usage limit hit  -> the script waits until the limit resets, then resumes the SAME
                        conversation with "Continue." (or stops, with --no-wait).
  * reply ended with no edits block (output limit reached while thinking)
                     -> resumes the same conversation with "Continue."
Each extra turn is recorded in run.json ("turns"), since Astra's run was a single turn.

    python run_claude_code_continue.py --runs 1                       # breakout (default)
    python run_claude_code_continue.py --game seaquest --runs 1
    python run_claude_code_continue.py --game asterix --runs 1 --effort high
    python run_claude_code_continue.py --resume-dir runs/<folder>/run0     # finish an interrupted run
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import time

import parse_edits
import evaluate

# Reference scores from the post (mean over 1,000 episodes): (Astra one-shot, best PPO 100M, best PPO 500M)
REFERENCE = {"breakout": (517.4, 15.8, 25.3), "seaquest": (53.1, 5.6, 88.9), "asterix": (53.2, 25.8, 55.2)}

SYSTEM = "Answer the user's request."
CONTINUE_MSG = "Continue."
LIMIT_PATTERNS = ("session limit", "usage limit", "usage_limit", "limit reached", "rate limit", "quota",
                  "limit will reset", "out of extra usage")


def base_cmd(model, effort):
    return [
        "claude", "-p",
        "--model", model,
        "--effort", effort,
        "--tools", "",                      # no built-in tools at all
        "--strict-mcp-config",              # no MCP servers
        "--setting-sources", "",            # ignore user/project/local settings
        "--disable-slash-commands",         # no skills listed in context
        "--settings", json.dumps({"showThinkingSummaries": True}),  # keep thinking summaries
        "--system-prompt", SYSTEM,          # replaces Claude Code's system prompt
        "--output-format", "stream-json", "--verbose",
    ]


def call_claude(cmd, stdin_text, cwd, timeout_s, max_output):
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)                    # force subscription auth
    if max_output:
        env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(max_output)
    try:
        p = subprocess.run(cmd, input=stdin_text, text=True, capture_output=True,
                           cwd=cwd, env=env, timeout=timeout_s)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        return -9, (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"


def parse_stream(stdout):
    out = {"texts": [], "thinking": [], "tool_uses": [], "init": {}, "result": {}}
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            out["init"] = ev
        elif t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "text":
                    out["texts"].append(b["text"])
                elif b.get("type") == "thinking":
                    out["thinking"].append(b.get("thinking", ""))
                elif b.get("type") in ("tool_use", "server_tool_use"):
                    out["tool_uses"].append(b.get("name"))
        elif t == "result" and ("usage" in ev or "result" in ev):
            out["result"] = ev
    return out


def rejected_limit_events(stdout):
    """rate_limit_event lines with status "rejected" (every stream also has "allowed" ones)."""
    out = []
    for line in stdout.splitlines():
        if '"rate_limit_event"' not in line:
            continue
        try:
            info = json.loads(line).get("rate_limit_info") or {}
        except json.JSONDecodeError:
            continue
        if info.get("status") == "rejected":
            out.append(info)
    return out


def is_usage_limit(stdout, stderr, result):
    if result.get("api_error") == "usage_limit_reached" or rejected_limit_events(stdout):
        return True
    # fallback: the limit message itself (stderr and the result text only, not the event stream)
    blob = (stderr + " " + str(result.get("result", ""))).lower()
    return any(k in blob for k in LIMIT_PATTERNS)


def reset_time(stdout, stderr, result):
    """Unix time the limit resets: resetsAt of the rejected window(s), else a '|<timestamp>' in the message."""
    ts = []
    for info in rejected_limit_events(stdout):
        windows = [w for w in (info.get("unifiedWindows") or {}).values() if w.get("status") == "rejected"]
        ts += [w["resetsAt"] for w in windows if w.get("resetsAt")] or [info.get("resetsAt")]
    ts = [int(t) for t in ts if t]
    if ts:
        return max(ts)                                  # wait for every rejected window to reset
    m = re.search(r"\|(\d{10})\b", stderr + " " + json.dumps(result))  # e.g. "usage limit reached|1731400000"
    return int(m.group(1)) if m else None


def wait_for_reset(ts, poll_min):
    if ts and ts > time.time():
        secs = ts - time.time() + 60
        print(f"  usage limit: waiting until {time.strftime('%H:%M', time.localtime(ts))} "
              f"({secs / 60:.0f} min)", flush=True)
        time.sleep(secs)
    else:
        print(f"  usage limit: no reset time found, retrying in {poll_min} min", flush=True)
        time.sleep(poll_min * 60)


def run_conversation(a, prompt, d, state):
    """Drive one conversation to an edits block (or give up). `state` is saved in state.json."""
    cwd = d / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)               # fixed folder so --resume finds the session
    waited = 0
    while True:
        turn = len(state["turns"])
        if turn == 0:
            cmd, stdin_text = base_cmd(a.model, a.effort), prompt
        else:
            if not state.get("session_id"):
                state["stop"] = "no_session_id_to_resume"
                return
            cmd = base_cmd(a.model, a.effort) + ["--resume", state["session_id"]]
            stdin_text = CONTINUE_MSG
        print(f"  turn {turn + 1}: {'prompt' if turn == 0 else 'resume + ' + repr(CONTINUE_MSG)}", flush=True)
        t0 = time.time()
        code, stdout, stderr = call_claude(cmd, stdin_text, str(cwd), a.timeout, a.max_output_tokens)
        (d / f"events_turn{turn + 1}.jsonl").write_text(stdout, encoding="utf-8")
        (d / f"stderr_turn{turn + 1}.log").write_text(stderr, encoding="utf-8")
        ps = parse_stream(stdout)
        sid = ps["init"].get("session_id") or ps["result"].get("session_id")
        if sid:
            state["session_id"] = sid
        state["turns"].append({
            "exit_code": code, "wall_s": round(time.time() - t0, 1),
            "model": ps["init"].get("model"), "tools_offered": ps["init"].get("tools"),
            "mcp_servers": ps["init"].get("mcp_servers"), "tool_uses": ps["tool_uses"],
            "usage": ps["result"].get("usage"), "is_error": ps["result"].get("is_error"),
            "subtype": ps["result"].get("subtype"),
        })
        state["texts"] += ps["texts"]
        state["thinking"] += ps["thinking"]
        (d / "state.json").write_text(json.dumps(state, indent=1), encoding="utf-8")

        block, cut = parse_edits.last_edits_block("\n".join(state["texts"]))
        has_block = block is not None
        if has_block and not cut:
            state["stop"] = "answered"
            return
        if is_usage_limit(stdout, stderr, ps["result"]):
            if a.no_wait or waited >= a.max_wait_hours * 3600:
                state["stop"] = "usage_limit"
                return
            t1 = time.time()
            wait_for_reset(reset_time(stdout, stderr, ps["result"]), a.poll_minutes)
            waited += time.time() - t1
            state["turns"][-1]["usage_limited"] = True
            if not state["session_id"]:                  # limit hit before the conversation started
                state["turns"], state["texts"], state["thinking"] = [], [], []
            continue
        if sum(1 for t in state["turns"] if not t.get("usage_limited")) >= a.max_turns:
            state["stop"] = "no_answer_after_max_turns" if not has_block else "cut_off"
            return
        # no edits block yet (e.g. output limit reached while thinking): ask it to continue


def finish(a, d, state):
    answer = "\n".join(state["texts"])
    (d / "answer.md").write_text(answer, encoding="utf-8")
    (d / "thinking.md").write_text("\n\n".join(state["thinking"]), encoding="utf-8")
    tensors, report = parse_edits.build(answer)
    parse_edits.save_npz(tensors, d / "net.npz")
    turns = state["turns"]
    tool_free = all(t["tools_offered"] in ([], None) and t["mcp_servers"] in ([], None) and not t["tool_uses"]
                    for t in turns) and bool(turns)
    out_tok = sum((t.get("usage") or {}).get("output_tokens", 0) for t in turns)
    status = "ok" if state.get("stop") == "answered" and not report["cut_off"] else (state.get("stop") or "error")
    record = {"game": a.game, "model": next((t["model"] for t in turns if t["model"]), a.model),
              "effort": a.effort, "status": status, "turns": len(turns),
              "extra_continue_turns": max(0, len(turns) - 1), "output_tokens_total": out_tok,
              "tool_free": tool_free, "session_id": state.get("session_id"), "edit_report": report,
              "turn_log": turns}
    (d / "run.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"  status={status} turns={len(turns)} output_tokens={out_tok} tool_free={tool_free} "
          f"read={report['applied']}/{report['statements']} nonzero={report.get('nonzero_total', 0)}", flush=True)
    row = {"run": d.name, "game": a.game, "status": status, "turns": len(turns), "output_tokens": out_tok,
           "tool_free": tool_free}
    if status == "ok":
        score = evaluate.evaluate(str(d / "net.npz"), a.episodes, seed=0, workers=a.workers, game=a.game)
        (d / "score.json").write_text(json.dumps(score, indent=1))
        print(f"  score = {score['mean']:.1f} +/- {score['se']:.1f}", flush=True)
        row.update(score)
    else:
        print(f"  not scored ({status}); see {d}", flush=True)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-fable-5-2")
    ap.add_argument("--effort", default="xhigh", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--game", default="breakout", choices=evaluate.GAMES,
                    help="MinAtar game; picks prompt_<game>.txt and the scorer's channel map")
    ap.add_argument("--prompt", default=None, help="override the prompt file (default: prompt_<game>.txt)")
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--timeout", type=int, default=3 * 3600, help="seconds per Claude call")
    ap.add_argument("--max-output-tokens", type=int, default=None,
                    help="sets CLAUDE_CODE_MAX_OUTPUT_TOKENS (default: Claude Code's own limit)")
    ap.add_argument("--max-turns", type=int, default=3, help="prompt + up to N-1 'Continue.' turns")
    ap.add_argument("--no-wait", action="store_true", help="stop at the usage limit instead of waiting")
    ap.add_argument("--max-wait-hours", type=float, default=12)
    ap.add_argument("--poll-minutes", type=int, default=30)
    ap.add_argument("--resume-dir", default=None, help="finish an interrupted run folder (runs/.../runN)")
    ap.add_argument("--out", default="runs")
    a = ap.parse_args()

    if a.resume_dir:
        d = pathlib.Path(a.resume_dir)
        state = json.loads((d / "state.json").read_text())
        a.model, a.effort = state["model"], state["effort"]
        a.game = state.get("game", "breakout")             # runs made before --game existed are breakout
        prompt = (d / "prompt.txt").read_text(encoding="utf-8")
        print(f"resuming {d} [{a.game}] ({len(state['turns'])} turns so far)", flush=True)
        state.pop("stop", None)
        run_conversation(a, prompt, d, state)
        print(json.dumps(finish(a, d, state), indent=1))
        return

    prompt = pathlib.Path(a.prompt or f"prompt_{a.game}.txt").read_text(encoding="utf-8")
    root = pathlib.Path(a.out) / f"{a.game}_{a.model}_{a.effort}_{time.strftime('%Y%m%d-%H%M%S')}"
    summary = []
    for i in range(a.runs):
        d = root / f"run{i}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "prompt.txt").write_text(prompt, encoding="utf-8")
        print(f"[{i + 1}/{a.runs}] {a.game}: {a.model} (effort {a.effort})", flush=True)
        state = {"game": a.game, "model": a.model, "effort": a.effort, "session_id": None,
                 "turns": [], "texts": [], "thinking": []}
        run_conversation(a, prompt, d, state)
        summary.append(finish(a, d, state))
        (root / "summary.json").write_text(json.dumps(summary, indent=1))
        if state.get("stop") == "usage_limit":
            print(f"  stopped at usage limit. Later: python run_claude_code_continue.py --resume-dir {d}")
            break
    ok = [s["mean"] for s in summary if s["status"] == "ok"]
    print(f"{len(ok)}/{len(summary)} runs produced a network"
          + (f"; mean score {sum(ok) / len(ok):.1f}" if ok else "")
          + "  ({}: Astra one-shot {}, PPO 100M {}, PPO 500M {})".format(a.game, *REFERENCE[a.game]))


if __name__ == "__main__":
    main()