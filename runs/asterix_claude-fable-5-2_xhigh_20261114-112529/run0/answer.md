## Design

**Strategy.** The player never moves horizontally: it stays in column 5 (its start column) and only chooses stay / up / down. Every enemy and treasure must cross column 5, so each row reduces to one question: is something approaching column 5, and how far away is it? The trail cell gives the direction. A treasure row is always safe, because a row holds only one entity.

The rules, in priority order:
1. **Leave a threatened row.** The stay penalty grows as the enemy in my row approaches (distance 3–4, then 2, then ≤1).
2. **Don't enter a dangerous row.** Moving costs a small amount if the target row has an enemy 3–4 cells away, and a lot if it is within 2 cells. A row two steps away with an enemy within 2 cells also costs a lot, which guards against a sticky repeat of the move.
3. **Go for treasure.** Stay if treasure is approaching in my own row; otherwise move toward a row with approaching treasure, preferring down when there is treasure both ways.
4. **Avoid the edges.** Rows 1 and 8 block the outward move and get a small bonus for stepping back in; ties when escaping break toward the centre.

Logits are scaled by 15, so the choice is nearly deterministic; left, right and fire sit at −2000.

**Layer 1 (32 units), for each row r = 1..8:**
- `T_r` (units 0–7): threat relative to column 5. About −1 for none, departing or treasure; −0.17 for an enemy approaching at distance 3–4; +1 at distance ≤2.
- `G_r` (units 8–15): +1 if treasure is approaching or at column 5, else −1.
- `P_r` (units 16–23): +1 if the player is in row r, else −1.
- `O_r` (units 24–31): player in row r and an enemy approaching in that row, graded −1 / −0.5 / 0 / +1 by distance (none / 3–4 / 2 / ≤1).

**Layer 2 (30 units used):**
- `Dn_r` (0–6) and `Up_r` (7–13): threat in the row one step below/above the player, and, through a shifted threshold, a close threat in the row two steps away.
- Units 14–15: wall flags for rows 1 and 8.
- Units 16–18: three thresholds on the own-row threat level.
- Units 19–20: "treasure strictly below" and "treasure strictly above", each one unit using power-of-two row weights compared against the player's row.
- Units 21–28: treasure approaching in the player's own row.
- Unit 29: which half of the grid the player is in (centre tie-break).

Nothing was run, so the weights are checked by hand only.

```edits
# ================= LAYER 1 =================
# ---- row 1 (inputs 60..119): T=0, G=8, P=16, O=24
W1[61:120:6, 0] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[64:120:6, 0] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[62:120:6, 0] = -10
W1[62:120:6, 8] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[64:120:6, 8] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[60:120:6, 16] = 16
W1[61:120:6, 24] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1
[64:120:6, 24] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
```

The block above was cut off, so here is the complete, self-contained block (this is the one to read):

```edits
# ================= LAYER 1 =================
# per row r (base 60r): T_r = unit r-1, G_r = unit 7+r, P_r = unit 15+r, O_r = unit 23+r
# ---- row 1
W1[61:120:6, 0] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[64:120:6, 0] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[62:120:6, 0] = -10
W1[62:120:6, 8] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[64:120:6, 8] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[60:120:6, 16] = 16
W1[61:120:6, 24] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[64:120:6, 24] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[62:120:6, 24] = -10
W1[60:120:6, 24] = 20
# ---- row 2
W1[121:180:6, 1] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[124:180:6, 1] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[122:180:6, 1] = -10
W1[122:180:6, 9] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[124:180:6, 9] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[120:180:6, 17] = 16
W1[121:180:6, 25] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[124:180:6, 25] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[122:180:6, 25] = -10
W1[120:180:6, 25] = 20
# ---- row 3
W1[181:240:6, 2] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[184:240:6, 2] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[182:240:6, 2] = -10
W1[182:240:6, 10] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[184:240:6, 10] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[180:240:6, 18] = 16
W1[181:240:6, 26] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[184:240:6, 26] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[182:240:6, 26] = -10
W1[180:240:6, 26] = 20
# ---- row 4
W1[241:300:6, 3] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[244:300:6, 3] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[242:300:6, 3] = -10
W1[242:300:6, 11] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[244:300:6, 11] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[240:300:6, 19] = 16
W1[241:300:6, 27] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[244:300:6, 27] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[242:300:6, 27] = -10
W1[240:300:6, 27] = 20
# ---- row 5
W1[301:360:6, 4] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[304:360:6, 4] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[302:360:6, 4] = -10
W1[302:360:6, 12] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[304:360:6, 12] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[300:360:6, 20] = 16
W1[301:360:6, 28] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[304:360:6, 28] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[302:360:6, 28] = -10
W1[300:360:6, 28] = 20
# ---- row 6
W1[361:420:6, 5] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[364:420:6, 5] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[362:420:6, 5] = -10
W1[362:420:6, 13] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[364:420:6, 13] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[360:420:6, 21] = 16
W1[361:420:6, 29] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[364:420:6, 29] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[362:420:6, 29] = -10
W1[360:420:6, 29] = 20
# ---- row 7
W1[421:480:6, 6] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[424:480:6, 6] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[422:480:6, 6] = -10
W1[422:480:6, 14] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[424:480:6, 14] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[420:480:6, 22] = 16
W1[421:480:6, 30] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[424:480:6, 30] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[422:480:6, 30] = -10
W1[420:480:6, 30] = 20
# ---- row 8
W1[481:540:6, 7] = [-5, -0.175, 4.825, 15, 20, 25, 20, 15, 4.825, 4.825]
W1[484:540:6, 7] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[482:540:6, 7] = -10
W1[482:540:6, 15] = [16, 24, 32, 40, 48, 56, 48, 40, 32, 16]
W1[484:540:6, 15] = [-8, -16, -24, -32, -40, -48, -40, -32, -24, -16]
W1[480:540:6, 23] = 16
W1[481:540:6, 31] = [-5, -0.55, 4.45, 10, 20, 25, 20, 10, 4.45, 4.45]
W1[484:540:6, 31] = [5, 0, -5, -10, -15, -20, -15, -10, -5, 0]
W1[482:540:6, 31] = -10
W1[480:540:6, 31] = 20
# ---- layer-1 biases
b1[0:8] = -5
b1[8:16] = -8
b1[16:24] = -8
b1[24:32] = -25

# ================= LAYER 2 =================
# Dn_r (r=2..8) -> units 0..6 : threat in row below (and 2 below)
W2[1, 0] = 5
W2[16, 0] = 7.5
b2[0] = -7.5
W2[2, 1] = 5
W2[17, 1] = 7.5
W2[16, 1] = 5.175
W2[3, 2] = 5
W2[18, 2] = 7.5
W2[17, 2] = 5.175
W2[4, 3] = 5
W2[19, 3] = 7.5
W2[18, 3] = 5.175
W2[5, 4] = 5
W2[20, 4] = 7.5
W2[19, 4] = 5.175
W2[6, 5] = 5
W2[21, 5] = 7.5
W2[20, 5] = 5.175
W2[7, 6] = 5
W2[22, 6] = 7.5
W2[21, 6] = 5.175
b2[1:7] = -2.325
# Up_r (r=1..7) -> units 7..13 : threat in row above (and 2 above)
W2[0, 7] = 5
W2[17, 7] = 7.5
W2[18, 7] = 5.175
W2[1, 8] = 5
W2[18, 8] = 7.5
W2[19, 8] = 5.175
W2[2, 9] = 5
W2[19, 9] = 7.5
W2[20, 9] = 5.175
W2[3, 10] = 5
W2[20, 10] = 7.5
W2[21, 10] = 5.175
W2[4, 11] = 5
W2[21, 11] = 7.5
W2[22, 11] = 5.175
W2[5, 12] = 5
W2[22, 12] = 7.5
W2[23, 12] = 5.175
W2[6, 13] = 5
W2[23, 13] = 7.5
b2[7:13] = -2.325
b2[13] = -7.5
# wall flags: unit 14 = player in row 1, unit 15 = player in row 8
W2[16, 14] = 8
W2[23, 15] = 8
# own-row threat thresholds: units 16,17,18
W2[24:32, 16] = 20
b2[16] = 155
W2[24:32, 17] = 20
b2[17] = 145
W2[24:32, 18] = 20
b2[18] = 130
# unit 19: treasure strictly below
W2[8:16, 19] = [4, 8, 16, 32, 64, 128, 256, 512]
W2[16:24, 19] = [-8, -16, -32, -64, -128, -256, -512, -1024]
b2[19] = -1016
# unit 20: treasure strictly above
W2[8:16, 20] = [512, 256, 128, 64, 32, 16, 8, 4]
W2[16:24, 20] = [-1024, -512, -256, -128, -64, -32, -16, -8]
b2[20] = -1016
# units 21..28: treasure approaching in the player's own row
W2[8, 21] = 6
W2[16, 21] = 6
W2[9, 22] = 6
W2[17, 22] = 6
W2[10, 23] = 6
W2[18, 23] = 6
W2[11, 24] = 6
W2[19, 24] = 6
W2[12, 25] = 6
W2[20, 25] = 6
W2[13, 26] = 6
W2[21, 26] = 6
W2[14, 27] = 6
W2[22, 27] = 6
W2[15, 28] = 6
W2[23, 28] = 6
b2[21:29] = -6
# unit 29: +1 if player in rows 5..8, -1 if rows 1..4
W2[16:20, 29] = -4
W2[20:24, 29] = 4

# ================= OUTPUT =================
# stay (action 0)
W3[16, 0] = -15
W3[17, 0] = -30
W3[18, 0] = -180
W3[21:29, 0] = 52.5
# up (action 2)
W3[7:14, 2] = -90
W3[20, 2] = 30
W3[14, 2] = -225
W3[15, 2] = 11.25
W3[29, 2] = 3
# down (action 4)
W3[0:7, 4] = -90
W3[19, 4] = 37.5
W3[15, 4] = -225
W3[14, 4] = 11.25
W3[29, 4] = -3
# biases: left, right, fire are never chosen
b3[0:6] = [195, -2000, -828.75, -2000, -821.25, -2000]
```