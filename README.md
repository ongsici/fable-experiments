# Weight-space programming with Claude Fable 5.2

A replication of Experiment 5 from "Sparks of Weight Space Programming" with Claude Fable 5.2. The model is given a
game's source code and asked to write, from scratch, every weight of a 600-32-32-6 tanh policy network that plays
it, with no tools, no training data, no gradients and no feedback. The network is then scored on the real game.

The experiment covers the three MinAtar games from the original post, Breakout, Seaquest and Asterix, and compares
Fable 5.2 with GPT-6 Astra's published one-shot networks and with PPO baselines.

## Results
Mean score over 1,000 episodes (± standard error). Each Fable 5.2 value is one independent run, at effort `xhigh`.

| Game | PPO 100M | PPO 500M | Astra (post) | Astra (rescored here) | Fable 5.2 runs | Fable 5.2 mean |
|---|---|---|---|---|---|---|
| Breakout | 15.8 | 25.3 | 517.4 ± 7.4 | 502.9 ± 7.7 | 455.7 ± 5.6, 458.9 ± 5.2 | **457.3** (n = 2) |
| Seaquest | 5.6 | 88.9 | 53.1 | 54.3 ± 1.4 | 75.1 ± 1.4, 17.9 ± 0.6, 59.6 ± 1.4 | **50.9** (n = 3) |
| Asterix | 25.8 | 55.2 | 53.2 | 53.9 ± 1.0 | 59.4 ± 0.9, 72.1 ± 1.1 | **65.8** (n = 2) |

PPO and Astra (post) numbers come from the original post; for Breakout, PPO is the best of 10 seeds (100M steps) and
of 3 seeds (500M steps). "Astra (rescored here)" is Astra's published network scored with this repo's `evaluate.py`.

- **Breakout:** both runs reach about 90% of Astra's score and are far above PPO. Bricks refill, so the score is
  capped only by the 10,000-step episode limit.
- **Seaquest:** the runs differ the most. The 75.1 and 59.6 runs beat Astra and PPO 100M; the 17.9 run dies about
  three times sooner than the 75.1 run, because its sub hovers next to an enemy in the adjacent row and a sticky
  repeated move carries it into the enemy (250 of 300 replayed episodes end this way).
- **Asterix:** both runs beat Astra and PPO 500M.

| Run | Score | Best episode | Mean episode length | Claude Code calls | Output tokens | Model time | Statements read |
|---|---|---|---|---|---|---|---|
| `breakout_…_think64000_20261111-083622` | 455.7 ± 5.6 | 684 | 8,200 | 1 | 255,073 | 44 min | 94/94 |
| `breakout_…_20261112-095453` | 458.9 ± 5.2 | 644 | 8,343 | 2 | 381,373 | 64 min | 168/168 |
| `seaquest_…_20261112-235804` | 75.1 ± 1.4 | 173 | 1,680 | 2 | 245,755 | 44 min | 243/243 |
| `seaquest_…_20261113-082013` | 17.9 ± 0.6 | 113 | 558 | 2 | 217,250 | 39 min | 187/187 |
| `seaquest_…_20261114-215251` | 59.6 ± 1.4 | 177 | 1,316 | 2 | 398,977 | 100 min | 209/209 |
| `asterix_…_20261113-182414` | 59.4 ± 0.9 | 216 | 974 | 3 | 465,381 | 81 min | 207/207 |
| `asterix_…_20261114-112529` | 72.1 ± 1.1 | 220 | 1,039 | 1 | 134,995 | 23 min | 176/176 |

Model time excludes waiting for usage limits to reset. Every run is tool-free (`tool_free: true` in `run.json`).

**Not strictly one-shot.** Every run needed more than one 128k-token reply before the weights appeared: Claude Code
continues automatically after its output cap, and the runner resumes with "Continue." after a usage limit. Astra's
runs were single replies, so treat the comparison as approximate.

**Excluded attempts.** 11 earlier Breakout attempts made with the first runner scripts are kept locally in
`runs/failed/` (not in git). 10 produced no network: the usage limit was hit before or during the reply, or the reply
spent its whole output budget thinking. One answered in a single reply (100,642 output tokens, 63 statements) and
scored 55.6 ± 1.7; it used the earlier `run_claude_code.py`, so it is listed here rather than in the tables.

## How it works
1. **Prompt.** `prompts/prompt_<game>.txt` is the published prompt for that game, copied unchanged from
   github.com/RikiyaT/lm_understand-logs (`exp5_write_from_scratch`). It contains the game's MinAtar source, the
   network's input format and the `edits` language for writing weights.
2. **Model call.** `run_claude_code_continue.py` sends the prompt through Claude Code (`claude -p`) on a Claude
   subscription, with no tools (`--tools ""`), no MCP servers, no settings files, no skills, and the system prompt
   replaced by the same one line the original used. Claude Code runs in an empty temporary folder outside the repo,
   so no `CLAUDE.md`, `AGENTS.md` or project memory can reach the model.
3. **Usage limits.** A run uses about 135k–470k output tokens, often more than one 5-hour usage window. When the
   limit is hit, the runner waits until it resets and resumes the same conversation with "Continue.". If a reply ends
   without weights, it also continues, up to `--max-turns` (default 3).
4. **Reading the weights.** `parse_edits.py` reads the last `edits` block of the reply into the network. A block cut
   off mid-reply is marked `cut_off` and the run is not scored.
5. **Scoring.** `evaluate.py` plays 1,000 episodes of MinAtar 1.0.15 with actions sampled from the network's softmax,
   sticky actions with probability 0.1, and a 10,000-step cap. It builds the 6 input channels the way each game's
   prompt describes.

Each run writes `runs/<game>_<model>_<effort>_<time>/run0/`: `answer.md` (the reply), `net.npz` (the weights),
`score.json`, `run.json` (status, turns, tokens, tool audit, parse report), `state.json` (the conversation state,
for resuming), and the raw Claude Code event logs.

## Validation
Astra's published replies and networks are in `reference/`. Reading each reply with `parse_edits.py` reproduces the
published network exactly (92/92, 122/122 and 55/55 statements for Breakout, Seaquest and Asterix). Scoring those
networks with `evaluate.py` gives 502.9 ± 7.7, 54.3 ± 1.4 and 53.9 ± 1.0, against 517.4, 53.1 and 53.2 in the post,
which agree within random-seed noise.

## Running it
```bash
pip install "minatar==1.0.15" numpy
claude                 # log in once with your Claude subscription, then exit

python run_claude_code_continue.py --game breakout --runs 1      # games: breakout, seaquest, asterix
python run_claude_code_continue.py --game seaquest --model claude-opus-5-5 --effort high
python run_claude_code_continue.py --resume-dir runs/<folder>/run0   # finish an interrupted run
python evaluate.py runs/<folder>/run0/net.npz --game seaquest        # rescore a network
```
The defaults are `claude-fable-5-2` at effort `xhigh`. Use `caffeinate -dims` on macOS to keep the machine awake
through a long run, and `--no-wait` to stop at a usage limit instead of waiting. If you have a personal
`~/.claude/CLAUDE.md`, move it aside while running so it can't reach the model.

Scoring 1,000 episodes takes about 3 minutes on 2 cores for a strong policy (long episodes) and seconds for a weak one.

To try a game by hand, paste its prompt into claude.ai, save the reply as `reply.md`, then run
`python parse_edits.py reply.md net.npz && python evaluate.py net.npz --game <game>`.

`visualise.py` builds a standalone HTML page with a replayed Breakout game and a score histogram, for example
`python visualise.py reference/astra_breakout.npz --label "GPT-6 Astra" -o visualisation/astra.html`.

## Repository layout
| Path | What it is |
|---|---|
| `prompts/` | The published prompt for each game, unchanged |
| `run_claude_code_continue.py` | Runner: sends the prompt, handles usage limits and resuming, reads and scores the weights |
| `parse_edits.py` | Reader for the `edits` language (written for this repo; the original reader wasn't published) |
| `evaluate.py` | Scorer for all three games |
| `visualise.py`, `visualisation/` | Breakout replay pages for Astra's and Fable's networks |
| `reference/` | GPT-6 Astra's published replies and networks, used to check the reader and the scorer |
| `runs/` | Output of every successful run |
| `run_claude_code.py`, `run_claude_code_updated.py`, `run_claude_code_updated_2.py` | Earlier single-call Breakout runners, kept for the record; they don't handle usage limits |

## Fairness notes
- Report the mean and spread over several runs. The original post reports a single run per game.
- `tool_free` in `run.json` is true only if Claude Code offered no tools or MCP servers and the model made no tool
  calls.
- Report runs that fail (no weights, or weights cut off) instead of rerunning silently.
- The prompts contain MinAtar source code (GPL-3.0, see `LICENSE-MinAtar`).
