# Experiment 5 (Breakout) for Claude Fable 5.2

Replication kit for "Sparks of Weight Space Programming", Experiment 5: the model writes every weight of a
600-32-32-6 tanh policy for MinAtar Breakout, in one reply, with no tools, no training, and no feedback.

## Files
| File | What it is |
|---|---|
| `prompt_breakout.txt` | The exact prompt from the original run, copied unchanged from the published logs |
| `run_claude_code.py` | Same, through Claude Code on a subscription (no API key) |
| `run_fable.py` | API version: sends the prompt (no tools, neutral system line), saves the reply, reads the weights, scores them |
| `parse_edits.py` | Reader for the `edits` language (written for this kit; the original reader wasn't published) |
| `evaluate.py` | Scorer: MinAtar 1.0.15, 1,000 episodes, softmax sampling, sticky actions 0.1, 10k-step cap |
| `reference/` | GPT-6 Astra's reply and network, used to check the reader and the scorer |

## Validation (already done)
- `parse_edits.py` on Astra's reply gives 92/92 statements read and weights identical to their `hand.npz` (max diff 0.0).
- `evaluate.py` on Astra's network gives **502.9 ± 7.7**. The post reports **517.4 ± 7.4**, so the two agree within
  random-seed noise (about 1.3 standard errors).

## Run with Claude Code (subscription, no API key)
```bash
pip install "minatar==1.0.15" numpy
claude                 # log in once with your Claude subscription, then exit
python run_claude_code.py --runs 5                           # Fable 5.2, effort xhigh (same as original)
python run_claude_code.py --model claude-opus-5-5 --runs 5   # comparison
python run_claude_code.py --effort high --runs 5             # effort ablation
```
Each call is `claude -p` with `--tools "" --strict-mcp-config --setting-sources "" --disable-slash-commands`
and the system prompt replaced by the same one line the original used. It runs in an empty temporary folder.
`run.json` records the tools and MCP servers Claude Code offered (both must be `[]`) and any tool calls, and
`tool_free` is true only if all three are empty.
If you have a personal `~/.claude/CLAUDE.md`, move it aside while running so it can't reach the model.
A run uses about 20–60k output tokens, so 5 runs fit comfortably in normal subscription limits.

## Seaquest and Asterix
`run_claude_code_continue.py --game {breakout,seaquest,asterix}` (default `breakout`) sends `prompt_<game>.txt`, the
published prompt for that game copied unchanged from github.com/RikiyaT/lm_understand-logs (`exp5_write_from_scratch`),
and scores with `evaluate.py --game <game>`, which builds the 6 input channels the way that prompt describes.
Run folders are named `runs/<game>_<model>_<effort>_<time>/`.
```bash
python run_claude_code_continue.py --game seaquest --runs 1
python run_claude_code_continue.py --game asterix --runs 1
python evaluate.py runs/<folder>/run0/net.npz --game seaquest
```
Check (Astra's published networks in `reference/`): the replies read 122/122 (Seaquest) and 55/55 (Asterix) with weights
identical to `hand.npz`; the scorer gives Seaquest 54.3 ± 1.4 (post: 53.1) and Asterix 53.9 ± 1.0 (post: 53.2).

| Game | PPO 100M | PPO 500M | Astra one-shot |
|---|---|---|---|
| Seaquest | 5.6 | 88.9 | 53.1 |
| Asterix | 25.8 | 55.2 | 53.2 |

## Run with the API (needs an API key)
```bash
pip install "minatar==1.0.15" anthropic numpy
export ANTHROPIC_API_KEY=sk-...
python run_fable.py --runs 5 --workers 8          # claude-fable-5-2 by default
python run_fable.py --model claude-opus-5-5 --runs 5
python run_fable.py --thinking-budget 0 --runs 5  # ablation: no extended thinking
```
Each run writes `runs/<model>_<time>/runN/`: `answer.md`, `thinking.md`, `net.npz`, `run.json`
(tokens, stop reason, tool audit, parse report), and `score.json`.
1,000 episodes take about 3 min on 2 cores for a strong policy (long episodes) and seconds for a weak one.

If your API rejects the `thinking` parameter for this model, change `kwargs["thinking"]` in `run_fable.py`
(for example, to whatever effort setting the model supports).

Manual route: paste `prompt_breakout.txt` into claude.ai with Fable 5.2 selected, save the reply as `reply.md`, then
`python parse_edits.py reply.md net.npz && python evaluate.py net.npz`.

## Reference scores (Breakout)
| Method | Score |
|---|---|
| PPO, 100M steps (best of 10 seeds) | 15.8 |
| PPO, 500M steps (best of 3 seeds) | 25.3 |
| GPT-6 Astra, one shot, xhigh effort | 517.4 |
| Perfect play ceiling | 3 rows x 10 bricks, repeated; capped by the 10k-step limit (Astra's max episode: 800) |

## Fairness notes
- Report the mean and spread over several runs. The original post reports a single run per game.
- `tool_free` in `run.json` is true only if the reply contains nothing but text and thinking blocks.
- A reply that hits `max_tokens` can cut off the edits block. The reader still applies the statements it got and
  sets `cut_off: true`. Treat such runs as failures or rerun them, and report which you chose.
- The prompt contains MinAtar source code (GPL-3.0, see `LICENSE-MinAtar`).
