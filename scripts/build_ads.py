#!/usr/bin/env python3
"""Build the vertical ads: cut source clips/photos to each voiceover, drop the
original sound, and lay the ElevenLabs voiceover on top.

Usage: python3 scripts/build_ads.py [ad-name ...]
Run from the repo root. Sources are read from source/ (IMG_xxxx.MOV / .jpg).
"""
import json, os, subprocess, sys, tempfile

W, H, FPS = 1080, 1920, 30
VO_DELAY = 0.25  # seconds of picture before the voice starts

# Each shot: (source file, start seconds, duration seconds). Photos ignore start.
ADS = {
    "camera-1-unboxing": [
        ("IMG_5123.MOV", 0.0, 2.0),   # box on the table
        ("IMG_7941.MOV", 4.0, 2.2),   # box held up at the lake
        ("IMG_5062.MOV", 3.5, 2.6),   # print coming out of the camera
        ("IMG_5124.MOV", 3.0, 2.6),   # box open: camera + pens
        ("IMG_7950.MOV", 1.5, 2.4),   # printed photo next to the camera
        ("IMG_5126.MOV", 1.0, 2.0),   # games on the screen
        ("IMG_7932.jpg", 0, 1.8),     # packshot for the call to action
    ],
    "camera-2-instant-print": [
        ("IMG_5055.MOV", 0.0, 2.4),   # shooting the palm trees
        ("IMG_5062.MOV", 3.5, 2.6),   # print comes out in hand
        ("IMG_7941.MOV", 5.0, 2.0),   # the box
        ("IMG_5056.MOV", 2.0, 2.0),   # shooting the palms
        ("IMG_7951.MOV", 3.0, 2.6),   # print held beside the camera
        ("IMG_7937.MOV", 0.5, 2.0),   # coloring pens in the box
        ("IMG_7950.MOV", 4.0, 1.8),   # holding the print
        ("IMG_7936.jpg", 0, 1.5),     # packshot
    ],
    "camera-3-gift-games": [
        ("IMG_7940.MOV", 0.0, 2.4),   # holding the camera at the lake
        ("IMG_5058.MOV", 0.5, 1.8),   # screen
        ("IMG_5126.MOV", 0.0, 2.6),   # games
        ("IMG_5127.MOV", 3.0, 2.2),   # games
        ("IMG_5128.jpg", 0, 1.6),     # in hand at the shop
        ("IMG_5053.MOV", 0.0, 1.8),   # small, in one hand
        ("IMG_7950.MOV", 0.0, 1.6),   # print + camera
        ("IMG_7929.jpg", 0, 1.1),     # boxed, at the lake
    ],
    "earbuds-1-features": [
        ("IMG_5069.MOV", 0.0, 2.2),   # box + case
        ("IMG_5067.jpg", 0, 1.6),     # box close-up
        ("IMG_5075.jpg", 0, 1.7),     # earbuds out of the case
        ("IMG_5076.jpg", 0, 1.6),
        ("IMG_5074.jpg", 0, 1.6),     # case open
        ("IMG_5078.jpg", 0, 1.8),     # all the pieces
        ("IMG_5079.jpg", 0, 1.6),
        ("IMG_5070.MOV", 0.0, 1.6),   # box + case
    ],
    "earbuds-2-no-wires": [
        ("IMG_5071.jpg", 0, 1.6),     # case closed
        ("IMG_5072.jpg", 0, 1.4),
        ("IMG_5077.jpg", 0, 1.8),     # earbuds out
        ("IMG_5079.jpg", 0, 1.8),
        ("IMG_5063.jpg", 0, 1.6),     # box + case
        ("IMG_5069.MOV", 2.5, 2.2),
        ("IMG_5066.jpg", 0, 1.2),
        ("IMG_5070.MOV", 0.5, 1.4),
    ],
}

COVER = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"


def run(cmd):
    subprocess.run(cmd, check=True)


def shot(src, start, dur, out, i):
    path = os.path.join("source", src)
    frames = round(dur * FPS)
    if src.lower().endswith(".jpg"):
        # Slow push-in on still photos, alternating zoom direction.
        z = "min(zoom+0.0012,1.12)" if i % 2 == 0 else "if(eq(on,0),1.12,max(zoom-0.0012,1))"
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s={W}x{H}:fps={FPS},setsar=1")
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", path, "-vf", vf,
             "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-pix_fmt", "yuv420p", out])
    else:
        vf = f"{COVER},fps={FPS}"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-i", path, "-t", str(dur),
             "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-pix_fmt", "yuv420p", out])


def build(name):
    shots = ADS[name]
    vo = os.path.join("voiceovers", f"{name}.mp3")
    total = sum(d for _, _, d in shots)
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, (src, start, dur) in enumerate(shots):
            p = os.path.join(tmp, f"{i:02d}.mp4")
            shot(src, start, dur, p, i)
            parts.append(p)
        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w") as f:
            f.writelines(f"file '{p}'\n" for p in parts)
        os.makedirs("ads", exist_ok=True)
        out = os.path.join("ads", f"{name}.mp4")
        ms = int(VO_DELAY * 1000)
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", vo,
             "-filter_complex",
             f"[0:v]fade=t=in:st=0:d=0.3,fade=t=out:st={total-0.4:.2f}:d=0.4[v];"
             f"[1:a]adelay={ms}|{ms},apad,atrim=0:{total:.2f},afade=t=out:st={total-0.3:.2f}:d=0.3,"
             f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
             "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", "-t", f"{total:.2f}", out])
    print(f"{out}  {total:.1f}s")


if __name__ == "__main__":
    for n in sys.argv[1:] or ADS:
        build(n)
