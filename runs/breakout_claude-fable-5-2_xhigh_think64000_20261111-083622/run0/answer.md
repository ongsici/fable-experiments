## Design

**Strategy: go to where the ball will land, early, and wait there.** The ball's horizontal motion is fully predictable, because it moves one column per step and only side walls reverse it. A catch needs the paddle on one of two cells: the ball's column at row 8, or its next column. I treat that pair as a landing zone with centre C, a half-integer:

- paddle left of the zone (C − p ≥ 1) → right;
- paddle right of the zone (C − p ≤ −1) → left;
- otherwise no-op.

The zone is always computed for the earliest possible landing, so if the ball goes higher than assumed the zone only moves later and stays reachable. Arriving early means a sticky repeat usually costs nothing, and one column of overshoot still lies inside the zone. None of this was run; it is hand-traced on the opening rally and a few wall cases only.

**Hidden layer 1 (8 units used):**

- **Units 0–3: linear lookups of 0.01·(C − paddle column)**, one table per ball cell, small enough that tanh stays linear.
  - Units 0 and 1: ball descending right / left, with wall reflections folded in.
  - Units 2 and 3: ball ascending right / left, assuming the earliest turn-around (a row-3 brick, the next brick row up, or the ceiling).
- **Unit 4: 0.01·(ball col + trail col − 2·paddle col)**, used only on the step right after a paddle hit. There the trail alone cannot tell which way the ball bounced, but this sign always moves the paddle with the ball.
- **Unit 5: horizontal direction**, the sign of ball col − trail col, with a wall correction for when both are in column 0 or 9.
- **Unit 6: descending flag**, on when ball row − trail row ≥ 0, except on the just-hit step at row 8.
- **Unit 7: just-hit flag**, on when ball and trail are both in row 8.

**Hidden layer 2 (10 units used):** one "go right" and one "go left" unit for each of five modes (descending right, descending left, ascending right, ascending left, just hit). Each thresholds its mode's lookup at ±1 (±0.5 for just-hit) and is switched off by a large negative gate unless units 5–7 select that mode.

**Output:** right logit = 15·(sum of right units) + 60 and likewise for left, so the chosen move gets +15 and the other −15; no-op stays at 0; up/down/fire sit at −30.

```edits
# ---------- Layer 1 ----------
# unit 0: descending-right zone centre (x0.01) minus paddle col
W1[3:60:6, 0]    = [0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015]
W1[63:120:6, 0]  = [0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025]
W1[123:180:6, 0] = [0.065, 0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035]
W1[183:240:6, 0] = [0.055, 0.065, 0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045]
W1[243:300:6, 0] = [0.045, 0.055, 0.065, 0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055]
W1[303:360:6, 0] = [0.035, 0.045, 0.055, 0.065, 0.075, 0.085, 0.095, 0.085, 0.075, 0.065]
W1[363:420:6, 0] = [0.025, 0.035, 0.045, 0.055, 0.065, 0.075, 0.085, 0.095, 0.085, 0.075]
W1[423:480:6, 0] = [0.015, 0.025, 0.035, 0.045, 0.055, 0.065, 0.075, 0.085, 0.095, 0.085]
W1[483:540:6, 0] = [0.005, 0.015, 0.025, 0.035, 0.045, 0.055, 0.065, 0.075, 0.085, 0.095]
W1[540:600:6, 0] = [0, -0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09]

# unit 1: descending-left zone centre
W1[3:60:6, 1]    = [0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005]
W1[63:120:6, 1]  = [0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015]
W1[123:180:6, 1] = [0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015, 0.025]
W1[183:240:6, 1] = [0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015, 0.025, 0.035]
W1[243:300:6, 1] = [0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015, 0.025, 0.035, 0.045]
W1[303:360:6, 1] = [0.025, 0.015, 0.005, -0.005, 0.005, 0.015, 0.025, 0.035, 0.045, 0.055]
W1[363:420:6, 1] = [0.015, 0.005, -0.005, 0.005, 0.015, 0.025, 0.035, 0.045, 0.055, 0.065]
W1[423:480:6, 1] = [0.005, -0.005, 0.005, 0.015, 0.025, 0.035, 0.045, 0.055, 0.065, 0.075]
W1[483:540:6, 1] = [-0.005, 0.005, 0.015, 0.025, 0.035, 0.045, 0.055, 0.065, 0.075, 0.085]
W1[540:600:6, 1] = [0, -0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09]

# unit 2: ascending-right predicted zone centre (earliest possible landing)
W1[3:60:6, 2]    = [0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005]
W1[63:120:6, 2]  = [0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005]
W1[123:180:6, 2] = [0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025]
W1[183:240:6, 2] = [0.065, 0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035]
W1[243:300:6, 2] = [0.055, 0.065, 0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045]
W1[303:360:6, 2] = [0.065, 0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035]
W1[363:420:6, 2] = [0.075, 0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025]
W1[423:480:6, 2] = [0.085, 0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015]
W1[483:540:6, 2] = [0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005]
W1[540:600:6, 2] = [0, -0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09]

# unit 3: ascending-left predicted zone centre
W1[3:60:6, 3]    = [0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005]
W1[63:120:6, 3]  = [0.095, 0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005]
W1[123:180:6, 3] = [0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015]
W1[183:240:6, 3] = [0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015, 0.025]
W1[243:300:6, 3] = [0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015, 0.025, 0.035]
W1[303:360:6, 3] = [0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015, 0.025]
W1[363:420:6, 3] = [0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005, 0.015]
W1[423:480:6, 3] = [0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005, 0.005]
W1[483:540:6, 3] = [0.085, 0.075, 0.065, 0.055, 0.045, 0.035, 0.025, 0.015, 0.005, -0.005]
W1[540:600:6, 3] = [0, -0.01, -0.02, -0.03, -0.04, -0.05, -0.06, -0.07, -0.08, -0.09]

# unit 4: just-hit state: 0.01*(f(ball col) + f(trail col) - 2*paddle col), f clamps cols 0->1, 9->8
W1[483:540:6, 4] = [0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.08]
W1[484:540:6, 4] = [0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.08]
W1[540:600:6, 4] = [0, -0.02, -0.04, -0.06, -0.08, -0.10, -0.12, -0.14, -0.16, -0.18]

# unit 5: horizontal direction sign = 12*(ball col - trail col + wall correction)
W1[3:600:60, 5] = 6
W1[9:600:60, 5] = 12
W1[15:600:60, 5] = 24
W1[21:600:60, 5] = 36
W1[27:600:60, 5] = 48
W1[33:600:60, 5] = 60
W1[39:600:60, 5] = 72
W1[45:600:60, 5] = 84
W1[51:600:60, 5] = 96
W1[57:600:60, 5] = 102
W1[10:600:60, 5] = -12
W1[16:600:60, 5] = -24
W1[22:600:60, 5] = -36
W1[28:600:60, 5] = -48
W1[34:600:60, 5] = -60
W1[40:600:60, 5] = -72
W1[46:600:60, 5] = -84
W1[52:600:60, 5] = -96
W1[58:600:60, 5] = -108

# unit 6: descending flag = 12*(ball row - trail row + 0.5 - [ball row 8])
W1[63:120:6, 6] = 12
W1[123:180:6, 6] = 24
W1[183:240:6, 6] = 36
W1[243:300:6, 6] = 48
W1[303:360:6, 6] = 60
W1[363:420:6, 6] = 72
W1[423:480:6, 6] = 84
W1[483:540:6, 6] = 84
W1[64:120:6, 6] = -12
W1[124:180:6, 6] = -24
W1[184:240:6, 6] = -36
W1[244:300:6, 6] = -48
W1[304:360:6, 6] = -60
W1[364:420:6, 6] = -72
W1[424:480:6, 6] = -84
W1[484:540:6, 6] = -96
b1[6] = 6

# unit 7: just-hit flag (ball in row 8 AND trail in row 8)
W1[483:540:6, 7] = 12
W1[484:540:6, 7] = 12
b1[7] = -18

# ---------- Layer 2 ----------
# units: 0 DR_right, 1 DR_left, 2 DL_right, 3 DL_left, 4 AR_right, 5 AR_left, 6 AL_right, 7 AL_left, 8 Q_right, 9 Q_left
W2[0, 0:2] = [1000, -1000]
W2[1, 2:4] = [1000, -1000]
W2[2, 4:6] = [1000, -1000]
W2[3, 6:8] = [1000, -1000]
W2[4, 8:10] = [1000, -1000]
W2[5, 0:8] = [200, 200, -200, -200, 200, 200, -200, -200]
W2[6, 0:8] = [200, 200, 200, 200, -200, -200, -200, -200]
W2[7, 4:10] = [-200, -200, -200, -200, 200, 200]
b2[0:10] = [-410, -410, -410, -410, -610, -610, -610, -610, -205, -205]

# ---------- Output ----------
W3[0:10:2, 3] = 15
W3[1:10:2, 1] = 15
b3[0:6] = [0, 60, -30, 60, -30, -30]
```