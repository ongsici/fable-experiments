"""Run Experiment 5 (Breakout) through Claude Code on a Claude subscription (no API key).

Each run is one fresh `claude -p` call: no tools, no MCP servers, no skills, no settings
files, a neutral one-line system prompt, prompt sent on stdin. The reply's edits block
is read into a network and scored.

    claude            # log in once with your subscription (/login), then exit
    python run_claude_code.py --runs 5
    python run_claude_code.py --model claude-opus-5-5 --runs 3 --effort high
"""
import argparse
import json
import os
import pathlib
import subprocess
import tempfile
import time

import parse_edits
import evaluate

SYSTEM = "Answer the user's request."


def claude_cmd(model, effort):
    return [
        "claude", "-p",
        "--model", model,
        "--effort", effort,
        "--tools", "",                      # no built-in tools at all
        "--strict-mcp-config",              # no MCP servers
        "--setting-sources", "",            # ignore user/project/local settings
        "--disable-slash-commands",         # no skills listed in context
        "--system-prompt", SYSTEM,          # replaces Claude Code's system prompt
        "--no-session-persistence",
        "--output-format", "stream-json", "--verbose",
    ]


def one_run(model, effort, prompt, out_dir, timeout_s):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)                    # force subscription auth
    env.setdefault("CLAUDE_CODE_MAX_OUTPUT_TOKENS", "64000")
    with tempfile.TemporaryDirectory() as clean_cwd:      # empty dir: no project CLAUDE.md
        t0 = time.time()
        proc = subprocess.run(claude_cmd(model, effort), input=prompt, text=True,
                              capture_output=True, cwd=clean_cwd, env=env, timeout=timeout_s)
        wall = time.time() - t0
    (out_dir / "events.jsonl").write_text(proc.stdout, encoding="utf-8")
    (out_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")

    texts, thinking, tool_uses, init, result = [], [], [], {}, {}
    for line in proc.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            init = ev
        elif ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "text":
                    texts.append(b["text"])
                elif b.get("type") == "thinking":
                    thinking.append(b.get("thinking", ""))
                elif b.get("type") in ("tool_use", "server_tool_use"):
                    tool_uses.append(b.get("name"))
        elif ev.get("type") == "result" and ("usage" in ev or "result" in ev):
            result = ev
    answer = "\n".join(texts) or result.get("result", "")
    (out_dir / "answer.md").write_text(answer, encoding="utf-8")
    (out_dir / "thinking.md").write_text("\n\n".join(thinking), encoding="utf-8")

    tensors, report = parse_edits.build(answer)
    parse_edits.save_npz(tensors, out_dir / "net.npz")
    record = {
        "model": init.get("model", model), "effort": effort, "exit_code": proc.returncode,
        "wall_s": round(wall, 1),
        "tool_free": not tool_uses and init.get("tools") == [] and init.get("mcp_servers") == [],
        "tools_offered": init.get("tools"), "mcp_servers": init.get("mcp_servers"),
        "tool_uses": tool_uses, "usage": result.get("usage"), "is_error": result.get("is_error"),
        "edit_report": report,
    }
    (out_dir / "run.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-fable-5-2")
    ap.add_argument("--effort", default="xhigh", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--prompt", default="prompt_breakout.txt")
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--timeout", type=int, default=3600, help="seconds per Claude call")
    ap.add_argument("--out", default="runs")
    a = ap.parse_args()

    prompt = pathlib.Path(a.prompt).read_text(encoding="utf-8")
    root = pathlib.Path(a.out) / f"{a.model}_{a.effort}_{time.strftime('%Y%m%d-%H%M%S')}"
    summary = []
    for i in range(a.runs):
        d = root / f"run{i}"
        print(f"[{i + 1}/{a.runs}] {a.model} (effort {a.effort}) ...", flush=True)
        rec = one_run(a.model, a.effort, prompt, d, a.timeout)
        rep = rec["edit_report"]
        print(f"  exit={rec['exit_code']} tool_free={rec['tool_free']} "
              f"read={rep['applied']}/{rep['statements']} cut_off={rep['cut_off']} "
              f"nonzero={rep.get('nonzero_total', 0)}", flush=True)
        if rec["exit_code"] != 0 or not rep["block"]:
            print(f"  no usable edits block -- see {d}/stderr.log and answer.md", flush=True)
        score = evaluate.evaluate(str(d / "net.npz"), a.episodes, seed=0, workers=a.workers)
        (d / "score.json").write_text(json.dumps(score, indent=1))
        print(f"  score = {score['mean']:.1f} +/- {score['se']:.1f}", flush=True)
        summary.append({"run": i, **score, "tool_free": rec["tool_free"], "cut_off": rep["cut_off"],
                        "read": f"{rep['applied']}/{rep['statements']}"})
    (root / "summary.json").write_text(json.dumps(summary, indent=1))
    means = [s["mean"] for s in summary]
    print(json.dumps(summary, indent=1))
    print(f"mean over {len(means)} runs: {sum(means) / len(means):.1f}  (Astra one-shot: 517.4)")


if __name__ == "__main__":
    main()
