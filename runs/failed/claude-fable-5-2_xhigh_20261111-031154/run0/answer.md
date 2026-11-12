**Design.** The paddle tracks the ball's *next* column, so it stays directly under the ball and catches it with no lookahead. None of this was run or tested; the weights are hand-derived from the game source.

- **Strategy.** Because exactly one ball, one trail and one paddle cell are lit, the signed distance to the target is linear in the inputs: `d = wb[ball col] + wt[trail col] − paddle col`. With `wb = [1,2,4,6,8,10,12,14,16,17]` and `wt = −[0..9]`, this equals (next ball column − paddle column), with the wall bounces handled by the edge values. Move right if `d ≥ 1`, left if `d ≤ −1`, otherwise no-op.
- **The one nonlinear case.** Right after a paddle bounce, ball and trail are both in row 8, and if the paddle sits under the ball the ball has reversed, so the trail points the wrong way. There the correct signed distance is `dP = fb[ball col] + trail col − 2·paddle col`, with `fb = [1,1,2,3,4,5,6,7,8,8]`.
- **Hidden layer 1 (4 units used).**
  - h1[0] = tanh(6(d − 0.5)): "go right" from the general rule.
  - h1[1] = tanh(6(−d − 0.5)): "go left" from the general rule.
  - h1[2] and h1[3]: the same two tests for `dP`, AND-gated by +200 on each row-8 ball and trail cell and a −403 bias, so they sit at exactly −1 unless both ball and trail are in row 8.
- **Hidden layer 2 (2 units used).**
  - h2[0] = tanh(3·h1[0] + 12·(h1[2] − h1[3])): final "right".
  - h2[1] = tanh(3·h1[1] + 12·(h1[3] − h1[2])): final "left".
  - The post-bounce units override the general rule when active and cancel exactly otherwise.
- **Output.** Right logit = 20·h2[0], left logit = 20·h2[1], no-op = 0, and up/down/fire get −30. The sampled action is therefore deterministic to about 1e-8.

Sticky actions can only cause a slip when the desired action changes (at a wall or after a paddle bounce), and the ball's next wall bounce brings it back to the paddle. By hand-tracing shortest trips, one or two consecutive slips after a paddle bounce are still recovered.

```edits
# ---- unit 0: general "right"  tanh(6*(d-0.5)),  d = wb[ball] + wt[trail] - paddle
W1[3:600:60, 0] = 6
W1[9:600:60, 0] = 12
W1[15:600:60, 0] = 24
W1[21:600:60, 0] = 36
W1[27:600:60, 0] = 48
W1[33:600:60, 0] = 60
W1[39:600:60, 0] = 72
W1[45:600:60, 0] = 84
W1[51:600:60, 0] = 96
W1[57:600:60, 0] = 102
W1[4:600:60, 0] = 0
W1[10:600:60, 0] = -6
W1[16:600:60, 0] = -12
W1[22:600:60, 0] = -18
W1[28:600:60, 0] = -24
W1[34:600:60, 0] = -30
W1[40:600:60, 0] = -36
W1[46:600:60, 0] = -42
W1[52:600:60, 0] = -48
W1[58:600:60, 0] = -54
W1[540:600:6, 0] = [0, -6, -12, -18, -24, -30, -36, -42, -48, -54]
b1[0] = -3

# ---- unit 1: general "left"  tanh(6*(-d-0.5))
W1[3:600:60, 1] = -6
W1[9:600:60, 1] = -12
W1[15:600:60, 1] = -24
W1[21:600:60, 1] = -36
W1[27:600:60, 1] = -48
W1[33:600:60, 1] = -60
W1[39:600:60, 1] = -72
W1[45:600:60, 1] = -84
W1[51:600:60, 1] = -96
W1[57:600:60, 1] = -102
W1[4:600:60, 1] = 0
W1[10:600:60, 1] = 6
W1[16:600:60, 1] = 12
W1[22:600:60, 1] = 18
W1[28:600:60, 1] = 24
W1[34:600:60, 1] = 30
W1[40:600:60, 1] = 36
W1[46:600:60, 1] = 42
W1[52:600:60, 1] = 48
W1[58:600:60, 1] = 54
W1[540:600:6, 1] = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54]
b1[1] = -3

# ---- unit 2: post-bounce "right" (active only if ball AND trail in row 8)
# tanh(6*(dP-0.5)),  dP = fb[ball] + trail - 2*paddle
W1[483:540:6, 2] = [206, 206, 212, 218, 224, 230, 236, 242, 248, 248]
W1[484:540:6, 2] = [200, 206, 212, 218, 224, 230, 236, 242, 248, 254]
W1[540:600:6, 2] = [0, -12, -24, -36, -48, -60, -72, -84, -96, -108]
b1[2] = -403

# ---- unit 3: post-bounce "left"
W1[483:540:6, 3] = [194, 194, 188, 182, 176, 170, 164, 158, 152, 152]
W1[484:540:6, 3] = [200, 194, 188, 182, 176, 170, 164, 158, 152, 146]
W1[540:600:6, 3] = [0, 12, 24, 36, 48, 60, 72, 84, 96, 108]
b1[3] = -403

# ---- layer 2: final right / left, post-bounce units override
W2[0, 0] = 3
W2[2, 0] = 12
W2[3, 0] = -12
W2[1, 1] = 3
W2[3, 1] = 12
W2[2, 1] = -12

# ---- output: 0 no-op, 1 left, 3 right
W3[0, 3] = 20
W3[1, 1] = 20
b3[2] = -30
b3[4] = -30
b3[5] = -30
```