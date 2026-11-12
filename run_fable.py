"""Run Experiment 5 (Breakout) on a Claude model: one fresh conversation per run,
one reply, no tools, no feedback. Then read the edits block and score the network.

    export ANTHROPIC_API_KEY=...
    python run_fable.py --runs 5                      # Fable 5.2, 5 independent attempts
    python run_fable.py --model claude-opus-5-5 --runs 3
"""
import argparse
import json
import pathlib
import time

import anthropic

import parse_edits
import evaluate

SYSTEM = "Answer the user's request."  # same neutral one-liner the original harness used


def one_run(client, model, prompt, max_tokens, thinking_budget, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    kwargs = dict(model=model, max_tokens=max_tokens, system=SYSTEM,
                  messages=[{"role": "user", "content": prompt}])  # no `tools` => tool-free
    if thinking_budget:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    t0 = time.time()
    with client.messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()
    wall = time.time() - t0

    answer = "".join(b.text for b in msg.content if b.type == "text")
    thinking = "".join(getattr(b, "thinking", "") or "" for b in msg.content if b.type == "thinking")
    (out_dir / "answer.md").write_text(answer, encoding="utf-8")
    (out_dir / "thinking.md").write_text(thinking, encoding="utf-8")
    (out_dir / "raw_response.json").write_text(msg.model_dump_json(indent=1), encoding="utf-8")

    tensors, report = parse_edits.build(answer)
    parse_edits.save_npz(tensors, out_dir / "net.npz")
    record = {
        "model": model, "stop_reason": msg.stop_reason, "wall_s": round(wall, 1),
        "usage": msg.usage.model_dump(),
        "tool_free": all(b.type in ("text", "thinking", "redacted_thinking") for b in msg.content),
        "edit_report": report,
    }
    (out_dir / "run.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-fable-5-2")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--prompt", default="prompt_breakout.txt")
    ap.add_argument("--max-tokens", type=int, default=64000)
    ap.add_argument("--thinking-budget", type=int, default=48000,
                    help="extended thinking budget; 0 disables thinking")
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default="runs")
    a = ap.parse_args()

    client = anthropic.Anthropic()
    prompt = pathlib.Path(a.prompt).read_text(encoding="utf-8")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    summary = []
    for i in range(a.runs):
        d = pathlib.Path(a.out) / f"{a.model}_{stamp}" / f"run{i}"
        print(f"[{i + 1}/{a.runs}] querying {a.model} ...", flush=True)
        rec = one_run(client, a.model, prompt, a.max_tokens, a.thinking_budget, d)
        rep = rec["edit_report"]
        print(f"  stop={rec['stop_reason']} applied={rep['applied']}/{rep['statements']} "
              f"nonzero={rep.get('nonzero_total', 0)} errors={len(rep['errors'])}", flush=True)
        score = evaluate.evaluate(str(d / "net.npz"), a.episodes, seed=0, workers=a.workers)
        (d / "score.json").write_text(json.dumps(score, indent=1))
        print(f"  score = {score['mean']:.1f} +/- {score['se']:.1f}", flush=True)
        summary.append({"run": i, **score, "stop_reason": rec["stop_reason"],
                        "applied": rep["applied"], "statements": rep["statements"]})
    (pathlib.Path(a.out) / f"{a.model}_{stamp}" / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
