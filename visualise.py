"""Build a standalone HTML page: replay of one Breakout game plus a score histogram.

    python visualise.py reference/astra_breakout.npz --label "GPT-6 Astra" -o visualisation/astra.html
    python visualise.py runs/<run>/run0/net.npz --label "Fable 5.2 run 0" -o visualisation/fable_run0.html
"""
import argparse
import json

import numpy as np
from minatar import Environment

import evaluate as ev


def play(params, seed, max_steps, record):
    env = Environment("breakout", sticky_action_prob=0.1)
    env.seed(seed)
    rng = np.random.RandomState(seed + 1_000_003)
    env.reset()
    frames, total, done, t = [], 0, False, 0
    while not done and t < max_steps:
        g = env.env
        z = ev.policy_logits(params, ev.obs(env.state()))
        z = z - z.max()
        a = int(rng.choice(6, p=np.exp(z) / np.exp(z).sum()))
        if record:
            bricks = int("".join(str(int(v)) for v in g.brick_map[1:4].reshape(-1)), 2)
            frames.append([int(g.pos), int(g.ball_x), int(g.ball_y), int(g.last_x), int(g.last_y),
                           bricks, int(total), a])
        r, done = env.act(a)
        total += r
        t += 1
    return total, t, frames


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>__LABEL__ - MinAtar Breakout</title>
<style>
:root{--bg:#fff;--card:#f5f4ef;--text:#1f1e1d;--muted:#6b6a65;--border:#e3e1da}
@media (prefers-color-scheme:dark){:root{--bg:#1f1e1d;--card:#2b2a27;--text:#f5f4ef;--muted:#a8a69e;--border:#3d3c38}}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);max-width:760px;margin:2rem auto;padding:0 1rem}
h1{font-size:20px;font-weight:500;margin:0 0 1rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:1.5rem}
.stat{background:var(--card);border-radius:8px;padding:1rem}.stat .l{font-size:13px;color:var(--muted)}.stat .v{font-size:24px;font-weight:500}
.main{display:grid;grid-template-columns:260px 1fr;gap:24px;align-items:start}
canvas{border:1px solid var(--border);border-radius:8px}
button{background:transparent;color:var(--text);border:1px solid var(--border);border-radius:8px;padding:6px 12px;cursor:pointer}
.small{font-size:13px;color:var(--muted)}
#hist{display:flex;align-items:flex-end;gap:4px;height:180px;border-bottom:1px solid var(--border)}
#hist>div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:100%}
#hl{display:flex;gap:4px;font-size:11px;color:var(--muted);margin-top:4px}#hl>div{flex:1;text-align:center}
.key{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
</style></head><body>
<h1>__LABEL__ playing MinAtar Breakout</h1>
<div class="stats">
<div class="stat"><div class="l">Mean score (__N__ games)</div><div class="v">__MEAN__</div></div>
<div class="stat"><div class="l">PPO, 500M steps</div><div class="v">25.3</div></div>
<div class="stat"><div class="l">Weights set</div><div class="v">__NZ__ <span class="small">of 20,486</span></div></div>
<div class="stat"><div class="l">Games lost before cap</div><div class="v">__LOST__%</div></div>
</div>
<div class="main">
<div>
<canvas id="cv" width="260" height="260"></canvas>
<div style="display:flex;gap:8px;align-items:center;margin-top:10px">
<button id="pp">Pause</button><button id="rs">Restart</button>
<input type="range" id="sp" min="1" max="30" value="8" style="flex:1" aria-label="Speed">
</div>
<div class="small" style="margin-top:8px">Step <span id="st"></span> of __NF__ &middot; score <span id="sc"></span> &middot; action <span id="ac"></span></div>
</div>
<div>
<div class="small" style="margin-bottom:8px">Score per game (bins of __BW__)</div>
<div id="hist"></div><div id="hl"></div>
<div class="small" style="margin-top:12px">
<span><span class="key" style="background:#D85A30"></span>ball missed</span>&nbsp;&nbsp;
<span><span class="key" style="background:#1D9E75"></span>survived to 10,000-step cap</span>
</div>
</div>
</div>
<script>
const F=__FRAMES__;
const B=__BINS__;
const BW=__BW__;
const hist=document.getElementById('hist'),hl=document.getElementById('hl');
const mx=Math.max(1,...B.map(b=>b[0]+b[1]));
B.forEach((b,i)=>{const col=document.createElement('div');col.title=(i*BW)+'-'+((i+1)*BW-1)+': '+(b[0]+b[1])+' games';
 const s=document.createElement('div');s.style.cssText='background:#1D9E75;height:'+(b[1]/mx*100)+'%;border-radius:2px 2px 0 0';
 const d=document.createElement('div');d.style.cssText='background:#D85A30;height:'+(b[0]/mx*100)+'%';
 col.append(s,d);hist.append(col);const l=document.createElement('div');l.textContent=i*BW;hl.append(l);});
const cv=document.getElementById('cv'),cx=cv.getContext('2d'),C=26;
const names=['no-op','left','up','right','down','fire'];
const dark=matchMedia('(prefers-color-scheme: dark)').matches;
let t=0,run=true,last=0;
function draw(){const [p,bx,by,lx,ly,bm,s,a]=F[t];
 cx.fillStyle=dark?'#2b2a27':'#f5f4ef';cx.fillRect(0,0,260,260);
 for(let r=0;r<3;r++)for(let c=0;c<10;c++){const bit=29-(r*10+c);
  if(Math.floor(bm/Math.pow(2,bit))%2){cx.fillStyle=['#7F77DD','#AFA9EC','#CECBF6'][r];cx.fillRect(c*C+1,(r+1)*C+1,C-2,C-2);}}
 cx.fillStyle='rgba(216,90,48,0.35)';cx.fillRect(lx*C+4,ly*C+4,C-8,C-8);
 cx.fillStyle='#D85A30';cx.beginPath();cx.arc(bx*C+C/2,by*C+C/2,C/2-4,0,7);cx.fill();
 cx.fillStyle='#1D9E75';cx.fillRect(p*C+1,9*C+8,C-2,C-10);
 st.textContent=t+1;sc.textContent=s;ac.textContent=names[a];}
function loop(ts){if(run&&ts-last>1000/+sp.value){last=ts;t=(t+1)%F.length;draw();}requestAnimationFrame(loop);}
pp.onclick=()=>{run=!run;pp.textContent=run?'Pause':'Play';};
rs.onclick=()=>{t=0;draw();};
draw();requestAnimationFrame(loop);
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("net")
    ap.add_argument("-o", "--out", default="visualisation/breakout_replay.html")
    ap.add_argument("--label", default="Network")
    ap.add_argument("--games", type=int, default=150, help="games for the histogram")
    ap.add_argument("--replay-seed", type=int, default=3)
    ap.add_argument("--replay-steps", type=int, default=400)
    ap.add_argument("--bin", type=int, default=100)
    a = ap.parse_args()

    params = ev.load(a.net)
    nz = int(sum(np.count_nonzero(p) for p in params))
    results = [play(params, s, ev.MAX_STEPS, False)[:2] for s in range(a.games)]
    scores = np.array([r[0] for r in results])
    lost = np.array([r[1] < ev.MAX_STEPS for r in results])
    nbins = int(scores.max() // a.bin) + 1
    bins = [[int(((scores // a.bin == i) & lost).sum()), int(((scores // a.bin == i) & ~lost).sum())]
            for i in range(nbins)]
    _, _, frames = play(params, a.replay_seed, a.replay_steps, True)

    html = (TEMPLATE.replace("__LABEL__", a.label).replace("__N__", str(a.games))
            .replace("__MEAN__", f"{scores.mean():.1f}").replace("__NZ__", f"{nz:,}")
            .replace("__LOST__", f"{100 * lost.mean():.0f}").replace("__NF__", str(len(frames)))
            .replace("__BW__", str(a.bin)).replace("__BINS__", json.dumps(bins))
            .replace("__FRAMES__", json.dumps(frames, separators=(",", ":"))))
    open(a.out, "w", encoding="utf-8").write(html)
    print(f"wrote {a.out}: mean {scores.mean():.1f} over {a.games} games, {100 * lost.mean():.0f}% lost")


if __name__ == "__main__":
    main()