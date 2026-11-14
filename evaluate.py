"""Score a 600-32-32-6 tanh policy on a MinAtar game (v1.0.15), as in the post:
mean score over N episodes, actions sampled from softmax(logits), sticky actions 0.1,
episodes cut at 10,000 steps.

    python evaluate.py net.npz [--game breakout|seaquest|asterix] [--episodes 1000] [--seed 0] [--workers 8]
"""
import argparse
import json
from multiprocessing import Pool

import numpy as np
from minatar import Environment

KEYS = ["actor/dense1/kernel", "actor/dense1/bias", "actor/dense2/kernel",
        "actor/dense2/bias", "actor/logits/kernel", "actor/logits/bias"]
# Unified 6-channel input: 0 player, 1 danger, 2 reward, 3 projectile, 4 trail, 5 gauge.
# Each unified channel is the OR of these native channels (by name, as in each game's self.channels).
# Copied from "How the 6 channels are built" in each prompt (prompts/prompt_<game>.txt).
GAME_MAPS = {
    "breakout": {0: ["paddle"], 1: [], 2: ["brick"], 3: ["ball"], 4: ["trail"], 5: []},
    "seaquest": {0: ["sub_front", "sub_back"],
                 1: ["enemy_fish", "enemy_sub", "enemy_bullet"],
                 2: ["enemy_fish", "enemy_sub", "diver"],
                 3: ["friendly_bullet"],
                 4: ["trail", "sub_back"],
                 5: ["oxygen_guage", "diver_guage"]},
    "asterix": {0: ["player"], 1: ["enemy"], 2: ["gold"], 3: [], 4: ["trail"], 5: []},
}
GAMES = list(GAME_MAPS)
MAX_STEPS = 10_000


def load(path):
    d = np.load(path)
    return [d[k].astype(np.float64) for k in KEYS]


def channel_map(env, game):
    """Unified channel -> list of native channel indices, resolved from the game's own channel names."""
    names = env.env.channels
    return {ch: [names[n] for n in src] for ch, src in GAME_MAPS[game].items()}


def obs(state, cmap):
    x = np.zeros((10, 10, 6), dtype=np.float64)
    for ch, src in cmap.items():
        if src:
            x[:, :, ch] = state[:, :, src].any(axis=2)
    return x.reshape(-1)  # index = (row*10 + col)*6 + ch


def policy_logits(p, x):
    W1, b1, W2, b2, W3, b3 = p
    h1 = np.tanh(x @ W1 + b1)
    h2 = np.tanh(h1 @ W2 + b2)
    return h2 @ W3 + b3


def run_episode(args):
    path, seed, game = args
    p = load(path)
    env = Environment(game, sticky_action_prob=0.1)
    cmap = channel_map(env, game)
    env.seed(seed)
    rng = np.random.RandomState(seed + 1_000_003)
    env.reset()
    total, steps, done = 0.0, 0, False
    while not done and steps < MAX_STEPS:
        z = policy_logits(p, obs(env.state(), cmap))
        z = z - z.max()
        pr = np.exp(z) / np.exp(z).sum()
        a = rng.choice(6, p=pr)
        r, done = env.act(a)
        total += r
        steps += 1
    return total, steps


def evaluate(path, episodes=1000, seed=0, workers=8, game="breakout"):
    if game not in GAME_MAPS:
        raise ValueError(f"unknown game {game!r}; choose from {GAMES}")
    jobs = [(path, seed * 100_000 + i, game) for i in range(episodes)]
    with Pool(workers) as pool:
        res = pool.map(run_episode, jobs, chunksize=4)
    scores = np.array([r[0] for r in res])
    lengths = np.array([r[1] for r in res])
    return {"game": game, "mean": float(scores.mean()), "se": float(scores.std(ddof=1) / np.sqrt(len(scores))),
            "episodes": episodes, "max": float(scores.max()), "mean_length": float(lengths.mean())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("net")
    ap.add_argument("--game", default="breakout", choices=GAMES)
    ap.add_argument("--episodes", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    print(json.dumps(evaluate(a.net, a.episodes, a.seed, a.workers, game=a.game), indent=1))
