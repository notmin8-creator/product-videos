#!/usr/bin/env python3
"""Paint a black "sleeve" over bare wrists in a short clip.

For each frame: find the black sleeve (dark pixels), then turn the skin that sits
directly above the sleeve's top edge (the wrist, up to EXTEND px) black too, so the
sleeve looks like it reaches the hand. Fingers and the hand stay as they are.

Usage: python3 scripts/cover_wrist.py SRC START DURATION OUT [EXTEND]
Output is 1080x1920, 30 fps, no audio.
"""
import subprocess, sys
import numpy as np
import cv2

src, start, dur, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
EXTEND = int(sys.argv[5]) if len(sys.argv) > 5 else 170
W, H, FPS = 1080, 1920, 30
FILL = ("scale=trunc(iw*sar/2)*2:ih,setsar=1,"
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}")

dec = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(start), "-i", src, "-t", str(dur),
                        "-vf", FILL, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)

kernel_up = np.zeros((2 * EXTEND + 1, 1), np.uint8); kernel_up[EXTEND:, 0] = 1   # grows a mask upward
n = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    ycc = cv2.cvtColor(f, cv2.COLOR_BGR2YCrCb)
    # sleeve: very dark, low saturation, in the lower part of the frame
    sleeve = ((hsv[..., 2] < 60) & (hsv[..., 1] < 120)).astype(np.uint8)
    sleeve[: H // 3] = 0
    sleeve = cv2.morphologyEx(sleeve, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    sleeve = cv2.morphologyEx(sleeve, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    # keep only big blobs (the arms), not phone screens or shadows
    cnt, lab, stats, _ = cv2.connectedComponentsWithStats(sleeve)
    big = np.zeros_like(sleeve)
    for i in range(1, cnt):
        if stats[i, cv2.CC_STAT_AREA] > 40000 and stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] > H * 0.8:
            big[lab == i] = 1
    # fill holes in the sleeve mask (highlights on the fabric) so they aren't repainted
    inv = (1 - big).copy(); ff = np.zeros((H + 2, W + 2), np.uint8)
    cv2.floodFill(inv, ff, (0, 0), 0)
    big = big | inv
    # extend each arm's sleeve along the arm direction, like a longer cuff
    cover = big.copy()
    for i in range(1, cnt):
        if stats[i, cv2.CC_STAT_AREA] <= 40000 or stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] <= H * 0.8:
            continue
        ys, xs = np.nonzero(lab == i)
        top = ys.min()
        sel = ys < top + 260                       # the cuff end of the sleeve
        tx, ty = xs[sel], ys[sel]
        # arm direction from the whole blob: from its bottom centre to its top centre
        bx, by = xs[ys > ys.max() - 200].mean(), ys.max()
        cx, cy = tx.mean(), ty.mean()
        v = np.array([cx - bx, cy - by], float); v /= (np.linalg.norm(v) + 1e-6)
        cuff = np.zeros_like(big); cuff[ty, tx] = 1
        cuff = cv2.morphologyEx(cuff, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        for d in range(6, EXTEND, 6):
            M = np.float32([[1, 0, v[0] * d], [0, 1, v[1] * d]])
            shifted = cv2.warpAffine(cuff, M, (W, H), flags=cv2.INTER_NEAREST)
            # taper: the cuff narrows slightly towards the hand
            k = max(1, int(d * 0.12)) | 1
            cover |= cv2.erode(shifted, np.ones((k, k), np.uint8))
    cover = cv2.morphologyEx(cover, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    cover = cv2.morphologyEx(cover, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    # paint only the new cuff; keep the real sleeve (and its fabric texture) untouched
    ext = (cover & (1 - cv2.erode(big, np.ones((9, 9), np.uint8)))).astype(np.float32)
    ext = cv2.GaussianBlur(ext, (0, 0), 5)[..., None]
    # fabric: sample the real sleeve's colour and add faint grain so it doesn't look flat
    if big.any():
        base = np.percentile(f[big.astype(bool)], 25, axis=0).astype(np.float32)
    else:
        base = np.array([18, 18, 20], np.float32)
    grain = np.random.default_rng(n).normal(0, 3, (H, W, 1)).astype(np.float32)
    fabric = np.clip(base + grain, 0, 255)
    f = (f * (1 - ext) + fabric * ext).astype(np.uint8)
    enc.stdin.write(f.tobytes())
    n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print(f"{out}: {n} frames")
