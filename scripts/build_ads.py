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

# --- Captions -------------------------------------------------------------
# Word timings come from ElevenLabs Scribe (scripts/captions/<ad>.json).
# Thmanyah Sans Black. Its license forbids redistributing the font file, so it is
# NOT in this repo: download it from https://font.thmanyah.com and put
# thmanyah-sans-Black.otf in fonts/ (git-ignored).
FONT_DIR = "fonts"
FONT = "thmanyah sans Black"
FIXES = {"كاميرة": "كاميرا", "bass": "بيس"}  # transcription slips -> script spelling
MAX_WORDS = 3          # words on screen at once
HIGHLIGHT = "&H0033D6FF&"  # current word: warm yellow (ASS is BGR)

# Everything sits in the top band, clear of Instagram Reels' UI:
# top bar (0-220px), caption/username (bottom 420px) and side buttons.
CAP_TOP = 300          # spoken captions, normally
CAP_UNDER_HOOK = 590   # spoken captions while the opening hook is on screen

# Opening hook: big label for the first seconds of the ad.
HOOK_END = 2.6
HOOKS = {
    "camera-1-unboxing": "أفضل هدية لطفلك؟",
    "camera-2-instant-print": "أفضل هدية لطفلك؟",
    "camera-3-gift-games": "أفضل هدية لطفلك؟",
}

ASS_HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,8,4,8,120,120,{CAP_TOP},-1
Style: Hook,{FONT},140,&H00241A2E,&H00FFFFFF,&H00C9A8FF,&H00C9A8FF,0,0,0,0,100,100,0,0,3,26,0,8,100,100,290,-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(t):
    t = max(t, 0)
    return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"


def captions(name, offset, total, out):
    words = [w for w in json.load(open(os.path.join("scripts", "captions", f"{name}.json")))["words"]
             if w.get("type", "word") == "word"]
    # Group into short chunks; a sentence end always closes a chunk.
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == MAX_WORDS or w["text"].rstrip()[-1:] in ".!؟?،,":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    # Don't leave a single word alone ("6 في" / "1"): fold it into the chunk before.
    ends = lambda ch: ch[-1]["text"].rstrip()[-1:] in ".!؟?،,"
    merged = []
    for ch in chunks:
        if len(ch) == 1 and merged and not ends(merged[-1]):
            merged[-1] = merged[-1] + ch
        else:
            merged.append(ch)
    chunks = merged
    clean = lambda s: FIXES.get(s.strip(".،,!؟?"), s.strip(".،,!؟?"))
    lines = []
    hook = HOOKS.get(name)
    if hook:
        lines.append(f"Dialogue: 1,{ts(0)},{ts(HOOK_END)},Hook,,0,0,0,,{{\\fad(120,200)}}{hook}\n")
    for ci, ch in enumerate(chunks):
        nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else total - offset
        end_chunk = min(nxt, ch[-1]["end"] + 0.6)
        for wi, w in enumerate(ch):
            start = ch[0]["start"] if wi == 0 else w["start"]
            end = ch[wi + 1]["start"] if wi + 1 < len(ch) else end_chunk
            txt = " ".join((f"{{\\c{HIGHLIGHT}}}{clean(x['text'])}{{\\c&H00FFFFFF&}}" if xi == wi
                            else clean(x["text"])) for xi, x in enumerate(ch))
            pop = "{\\fscx108\\fscy108\\t(0,120,\\fscx100\\fscy100)}" if wi == 0 else ""
            # Under the hook while it shows; a chunk that starts under it stays there.
            mv = CAP_UNDER_HOOK if hook and ch[0]["start"] + offset < HOOK_END else 0
            lines.append(f"Dialogue: 0,{ts(start+offset)},{ts(end+offset)},Cap,,0,0,{mv},,{pop}{txt}\n")
    with open(out, "w", encoding="utf-8") as f:
        f.write(ASS_HEAD + "".join(lines))


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
        ass = os.path.join(tmp, "captions.ass")
        captions(name, VO_DELAY, total, ass)
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", vo,
             "-filter_complex",
             f"[0:v]ass={ass}:fontsdir={FONT_DIR},"
             f"fade=t=in:st=0:d=0.3,fade=t=out:st={total-0.4:.2f}:d=0.4[v];"
             f"[1:a]adelay={ms}|{ms},apad,atrim=0:{total:.2f},afade=t=out:st={total-0.3:.2f}:d=0.3,"
             f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
             "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", "-t", f"{total:.2f}", out])
    print(f"{out}  {total:.1f}s")


if __name__ == "__main__":
    for n in sys.argv[1:] or ADS:
        build(n)
