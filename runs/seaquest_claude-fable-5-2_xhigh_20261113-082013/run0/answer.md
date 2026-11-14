You've hit your session limit · resets 9:20am (Asia/Singapore)
## Design

**Strategy.** The sub stays in columns 5–6, where one left/right press flips its facing without changing the cells it occupies. It hunts in rows 2–8:

- **Navigate:** go to a row holding a target (an enemy or a diver), but never step into a row with danger in columns 3–7.
- **Fight:** in a target's row, face it and fire; a diver is simply waited for until it swims into the sub.
- **Dodge:** if danger enters columns 3–7 of the sub's own row, leave the row.
- **Surface:** when oxygen is below 60 and at least one diver is on board, go up; then dive again, waiting at the surface while rows 1–2 are unsafe.
- **Idle:** drift to row 5 and fire.

**Layer 1 (32 units).** A row-gated unit sits at −1 unless the sub is in that row, so the sum over rows reads out the value for the sub's own row.

| Units | What they compute |
|---|---|
| 0–6 | Rows 2–8, gated: side of the target in my row (+ left, − right, 0 none) |
| 7–13 | Rows 2–8, gated: danger in columns 3–7 of my row |
| 14–21 | Rows 1–8, gated: danger zone in the row below minus the row above |
| 22, 23 | Target strictly below / above me (row weights in powers of 6 against a threshold set by my row) |
| 24 | Facing (trail channel at column 6 minus column 5) |
| 25 | Surface now (diver bar present and oxygen cell 2 off) |
| 26 | Sub in row 0 or 1 |
| 27 | At row 0 with rows 1–2 unsafe |
| 28, 29 | Sub off-centre to the left / right |
| 30 | Above or below row 5 |
| 31 | Sub in row 8 |

**Layer 2 (18 units used).** Each unit is one rule, and the output weights double per priority level so a higher rule always wins:

1. dodge (down, or up if below is blocked or at row 8)
2. recentre
3. surface
4. leave rows 0–1 downward
5. flip to face the target
6. stay and fire
7. navigate down, else up
8. drift to row 5

Three veto units put −5000 on "up" or "down" when the destination row is unsafe.

```edits
# ---- a_r: target side in my row (units 0..6 = rows 2..8)
W1[120:180:6, 0] = 12
W1[121:146:6, 0] = 3
W1[122:147:6, 0] = 3
W1[163:176:6, 0] = -3
W1[164:177:6, 0] = -3
W1[180:240:6, 1] = 12
W1[181:206:6, 1] = 3
W1[182:207:6, 1] = 3
W1[223:236:6, 1] = -3
W1[224:237:6, 1] = -3
W1[240:300:6, 2] = 12
W1[241:266:6, 2] = 3
W1[242:267:6, 2] = 3
W1[283:296:6, 2] = -3
W1[284:297:6, 2] = -3
W1[300:360:6, 3] = 12
W1[301:326:6, 3] = 3
W1[302:327:6, 3] = 3
W1[343:356:6, 3] = -3
W1[344:357:6, 3] = -3
W1[360:420:6, 4] = 12
W1[361:386:6, 4] = 3
W1[362:387:6, 4] = 3
W1[403:416:6, 4] = -3
W1[404:417:6, 4] = -3
W1[420:480:6, 5] = 12
W1[421:446:6, 5] = 3
W1[422:447:6, 5] = 3
W1[463:476:6, 5] = -3
W1[464:477:6, 5] = -3
W1[480:540:6, 6] = 12
W1[481:506:6, 6] = 3
W1[482:507:6, 6] = 3
W1[523:536:6, 6] = -3
W1[524:537:6, 6] = -3
b1[0:7] = -24
# ---- n_r: danger in cols 3..7 of my row (units 7..13 = rows 2..8)
W1[120:180:6, 7] = 12
W1[139:164:6, 7] = 6
W1[180:240:6, 8] = 12
W1[199:224:6, 8] = 6
W1[240:300:6, 9] = 12
W1[259:284:6, 9] = 6
W1[300:360:6, 10] = 12
W1[319:344:6, 10] = 6
W1[360:420:6, 11] = 12
W1[379:404:6, 11] = 6
W1[420:480:6, 12] = 12
W1[439:464:6, 12] = 6
W1[480:540:6, 13] = 12
W1[499:524:6, 13] = 6
b1[7:14] = -27
# ---- s_r: zone below minus zone above (units 14..21 = rows 1..8)
W1[60:120:6, 14] = 10
W1[139:164:6, 14] = 3
W1[120:180:6, 15] = 10
W1[199:224:6, 15] = 3
W1[79:104:6, 15] = -3
W1[180:240:6, 16] = 10
W1[259:284:6, 16] = 3
W1[139:164:6, 16] = -3
W1[240:300:6, 17] = 10
W1[319:344:6, 17] = 3
W1[199:224:6, 17] = -3
W1[300:360:6, 18] = 10
W1[379:404:6, 18] = 3
W1[259:284:6, 18] = -3
W1[360:420:6, 19] = 10
W1[439:464:6, 19] = 3
W1[319:344:6, 19] = -3
W1[420:480:6, 20] = 10
W1[499:524:6, 20] = 3
W1[379:404:6, 20] = -3
W1[480:540:6, 21] = 10
W1[439:464:6, 21] = -3
b1[14:22] = -20
# ---- D: target strictly below (unit 22)
W1[182:240:6, 22] = 18
W1[242:300:6, 22] = 108
W1[302:360:6, 22] = 648
W1[362:420:6, 22] = 3888
W1[422:480:6, 22] = 23328
W1[482:540:6, 22] = 139968
W1[120:180:6, 22] = -4.5
W1[180:240:6, 22] = -27
W1[240:300:6, 22] = -162
W1[300:360:6, 22] = -972
W1[360:420:6, 22] = -5832
W1[420:480:6, 22] = -34992
W1[480:540:6, 22] = -209952
b1[22] = -3
# ---- U: target strictly above, rows 2..7 (unit 23)
W1[122:180:6, 23] = 139968
W1[182:240:6, 23] = 23328
W1[242:300:6, 23] = 3888
W1[302:360:6, 23] = 648
W1[362:420:6, 23] = 108
W1[422:480:6, 23] = 18
W1[120:180:6, 23] = -209952
W1[180:240:6, 23] = -34992
W1[240:300:6, 23] = -5832
W1[300:360:6, 23] = -972
W1[360:420:6, 23] = -162
W1[420:480:6, 23] = -27
W1[480:540:6, 23] = -4.5
b1[23] = -3
# ---- O: facing (+ = left) (unit 24)
W1[40:600:60, 24] = 3
W1[34:600:60, 24] = -3
# ---- Surf: diver>=1 and oxygen<60 (unit 25)
W1[593, 25] = 6
W1[557, 25] = -6
b1[25] = -3
# ---- T: sub in row 0 or 1 (unit 26)
W1[0:120:6, 26] = 3
b1[26] = -3
# ---- W0: at row 0 and rows 1/2 unsafe (unit 27)
W1[0:60:6, 27] = 15
W1[79:104:6, 27] = 6
W1[139:164:6, 27] = 6
b1[27] = -33
# ---- CL / CR: off-centre (units 28, 29)
W1[0:600:60, 28] = 6
W1[6:600:60, 28] = 6
W1[12:600:60, 28] = 6
W1[18:600:60, 28] = 6
W1[24:600:60, 28] = 6
b1[28] = -3
W1[42:600:60, 29] = 6
W1[48:600:60, 29] = 6
W1[54:600:60, 29] = 6
b1[29] = -3
# ---- Mid: + above row 5, - below (unit 30)
W1[120:300:6, 30] = 1.5
W1[360:540:6, 30] = -1.5
# ---- B8: sub in row 8 (unit 31)
W1[480:540:6, 31] = 3
b1[31] = -3

# ================= layer 2 =================
# 0: dodge down = threat & not below-blocked & not row 8
W2[7:14, 0] = 32
W2[14:22, 0] = -16
W2[31, 0] = -32
b2[0] = 24
# 1: dodge up = threat & below-blocked
W2[7:14, 1] = 32
W2[14:22, 1] = 16
b2[1] = 264
# 2,3: recentre
W2[28, 2] = 8
W2[29, 3] = 8
# 4: surface
W2[25, 4] = 8
# 5: in rows 0/1 -> down
W2[26, 5] = 8
# 6: flip left = target left & facing right
W2[0:7, 6] = 16
W2[24, 6] = -16
b2[6] = 72.08
# 7: flip right = target right & facing left
W2[0:7, 7] = -16
W2[24, 7] = 16
b2[7] = -119.92
# 8,9: target left / right in my row -> stay and fire
W2[0:7, 8] = 16
b2[8] = 88
W2[0:7, 9] = -16
b2[9] = -104
# 10: nav down = D & not Surf
W2[22, 10] = 8
W2[25, 10] = -8
b2[10] = -8
# 11: nav up = U & not D & not Surf
W2[23, 11] = 8
W2[22, 11] = -8
W2[25, 11] = -8
b2[11] = -16
# 12: drift down (above mid, not Surf); 13: drift up
W2[30, 12] = 16
W2[25, 12] = -8
b2[12] = -16
W2[30, 13] = -16
b2[13] = -8
# 14: veto up (above blocked); 15: veto down (below blocked); 16: veto down (wait at surface)
W2[14:22, 14] = -16
b2[14] = -120
W2[14:22, 15] = 16
b2[15] = 104
W2[27, 16] = 8
# 17: dodge up at row 8
W2[7:14, 17] = 8
W2[31, 17] = 8
b2[17] = 40

# ================= output =================
W3[0, 4] = 1280
W3[1, 2] = 1280
W3[17, 2] = 1280
W3[2, 3] = 640
W3[3, 1] = 640
W3[4, 2] = 320
W3[5, 4] = 160
W3[6, 1] = 80
W3[7, 3] = 80
W3[8, 5] = 40
W3[9, 5] = 40
W3[10, 4] = 20
W3[11, 2] = 20
W3[12, 4] = 10
W3[13, 2] = 10
W3[14, 2] = -2500
W3[15, 4] = -2500
W3[16, 4] = -2500
b3[0:6] = [0, 720, 410, 720, -3530, 90]
```