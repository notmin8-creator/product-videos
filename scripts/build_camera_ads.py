#!/usr/bin/env python3
"""Build the 4 kids-print-camera ads (round 2).

  v1-kids      kids angle, Nora voice
  v2-girls     girls angle, Jumana voice
  v3-unboxing  unboxing angle, Nora voice
  v4-asmr      the user's own 55s edit (IMG_8031): music removed, Jumana voice
               lines + ElevenLabs ASMR sound effects

Captions: Arabic (Thmanyah Sans Black, spoken word in yellow) with the English
sentence underneath, all in the top band that Instagram Reels leaves clear.

Run from the repo root:  python3 scripts/build_camera_ads.py [name ...]
Needs fonts/thmanyah-sans-Black.otf and fonts/thmanyah-sans-Bold.otf
(not in the repo, see README) and the source clips in source/.
"""
import json, os, re, subprocess, sys, tempfile

W, H, FPS = 1080, 1920, 30
VO_DELAY = 0.25
FONT_DIR = "fonts"
AR_FONT, EN_FONT = "thmanyah sans Black", "thmanyah sans"
HIGHLIGHT = "&H0000FFFF&"  # pure yellow #FFFF00 (ASS is BGR; renders ~#FFF000 after encoding)
MAX_WORDS = 3
CAP_TOP, EN_GAP = 300, 135          # Arabic line, English line = Arabic + gap
CAP_UNDER_HOOK = 590
HOOK_END = 2.6

# (source, start, duration). Times picked from the footage, see voiceover-scripts-v2.md.
ADS = {
    "v1-kids": dict(
        vo="audio/v123/v1-kids.mp3", hook="أفضل هدية لطفلك؟", hook_end=2.2,
        shots=[("IMG_5121.mp4", 0.5, 2.2),   # box held up
               ("IMG_7943.mp4", 15.0, 3.0),  # her hands framing the lake on the camera screen
               ("IMG_7948.mp4", 3.0, 2.0),   # holding the camera up to shoot
               ("IMG_7948.mp4", 15.0, 2.4),  # print comes out
               ("IMG_5136.mp4", 12.0, 2.2),  # print placed in the notebook
               ("IMG_5136.mp4", 56.0, 3.5),  # writing next to it
               ("IMG_7943.mp4", 49.0, 2.1),  # print held against the view
               ("IMG_7934.mp4", 0.5, 2.2)],  # boxed camera on the railing (no hands)
        en=["Every child loves to discover…",
            "and this camera helps them observe the world around them.",
            "A camera to capture whatever they love…",
            "and the photo prints right into their hand!",
            "They color it and stick it in their notebook…",
            "building an album of memories to look back on as they grow.",
            "The best gift you can give your child.",
            "Order now!"]),
    "v2-girls": dict(
        vo="audio/v123/v2-girls-full.mp3", hook="يا بنات… لازم تشوفون هالكاميرا",
        shots=[("IMG_7948.mp4", 3.0, 2.4),   # holding the camera at the lake
               ("IMG_5135.mp4", 3.0, 2.2),   # in the shop
               ("IMG_7948.mp4", 15.0, 2.4),  # print coming out
               ("IMG_7943.mp4", 49.0, 2.4),  # print against the view
               ("IMG_5136.mp4", 42.0, 2.9),  # writing in the notebook
               ("still_thumbs_sleeve.jpg", 0, 1.45), # camera + thumbs up ("live the moment")
               ("still_phone_sleeve.jpg", 0, 1.25),  # phone held in both hands, wrists covered ("away from my phone")
               ("IMG_5135.mp4", 30.0, 2.0),  # print in the shop
               ("IMG_5136.mp4", 98.0, 2.1),  # the finished page
               ("IMG_7934.mp4", 0.5, 2.8)],  # boxed camera ("worth it, order now")
        en=["Girls…",
            "I found a cute vintage camera, you have to see it.",
            "Snap a photo…",
            "and it prints right in your hand, black and white, old-school style.",
            "I stick it in my notebook and write about my day.",
            "That way I live the moment…",
            "away from my phone.",
            "Imagine flipping through all these memories a year from now!",
            "It's worth it…", "Order it now!"]),
    "v3-unboxing": dict(
        vo="audio/v123/v3-unboxing.mp3", hook="وش يجي داخل العلبة؟",
        shots=[("IMG_5125.mp4", 0.0, 3.2),   # the box
               ("IMG_5125.mp4", 4.0, 2.4),   # camera out of the box
               ("IMG_5125.mp4", 44.0, 2.0),  # everything laid out
               ("IMG_5122.mp4", 16.0, 2.2),  # screen on
               ("IMG_7948.mp4", 17.0, 2.5),  # print comes out
               ("IMG_7943.mp4", 49.0, 3.1),  # print against the view
               ("IMG_5135.mp4", 30.0, 1.6),  # print in the shop
               ("IMG_7934.mp4", 0.5, 2.0)],  # boxed camera on the railing (no hands)
        en=["Here's everything that comes with this cute camera!",
            "The camera, printing paper, a charging cable and coloring pens.",
            "It snaps and prints instantly, like the well-known instant cameras…",
            "but since it prints black & white vintage style, it costs way less!",
            "Order now."]),
    "v4-asmr": dict(
        mix=True, hook=None,
        # Re-cut of the user's IMG_8031: writing part shortened, palm part (wrist showing) dropped,
        # phone/camera flipped to match the line.
        shots=[("IMG_8031.mp4", 0.0, 7.1),    # pens + box sleeve
               ("IMG_8031.mp4", 7.1, 8.0),    # camera screen, printing in the shop
               ("IMG_8031.mp4", 15.1, 3.6),   # notebook
               ("IMG_8031.mp4", 18.7, 4.9),   # writing (shortened from 21s)
               ("IMG_8031.mp4", 39.4, 1.3),   # notebook closed
               ("still_thumbs_sleeve.jpg", 0, 1.6),   # camera + thumbs up ("live the moment")
               ("still_phone_sleeve.jpg", 0, 1.6),    # phone held in both hands, wrists covered ("away from my phone")
               ("IMG_5136.mp4", 98.0, 2.3),   # the finished page
               ("IMG_7943.mp4", 49.0, 2.4),   # print against the view
               ("IMG_8031.mp4", 52.0, 2.5)],  # boxed camera on the railing
        en=["I've started documenting my day differently…",
            "A vintage camera…", "so cute!",
            "Snap a photo…", "and it prints right in your hand, black and white!",
            "I stick it in my notebook…", "and write about my day next to it.",
            "Every page…", "a memory to come back to later.",
            "That way I live the moment…", "away from my phone.",
            "Imagine looking back a year from now…", "flipping through all these memories!"]),
}

# Video 4 sound design: (file in audio/ad-8031, start s, volume, loop-to-seconds or None)
V4_LINES = [0.3, 4.2, 7.3, 15.4, 19.6, 24.9, 28.3]   # where each voice line starts (re-cut timeline)
V4_SFX = [("sfx_pens.mp3", 0.0, 0.45, None), ("sfx_box.mp3", 4.0, 0.45, None),
          ("sfx_shutter.mp3", 8.6, 0.5, None), ("sfx_printer.mp3", 10.0, 2.2, None),
          ("sfx_tear.mp3", 13.4, 1.8, None), ("sfx_cap.mp3", 15.3, 0.45, None),
          ("sfx_writing.mp3", 19.0, 0.08, 4.6), ("sfx_close.mp3", 24.0, 0.4, None),
          ("sfx_outdoor.mp3", 24.9, 0.2, 10.4)]   # sounds sit under the (levelled) voice

ENDS = ".!؟?…"


def run(cmd):
    subprocess.run(cmd, check=True)


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode())


def ts(t):
    t = max(t, 0)
    return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"


def ass_header():
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Ar,{AR_FONT},96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,8,4,8,120,120,{CAP_TOP},-1
Style: En,{EN_FONT},56,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1.5,0,1,5,3,8,110,110,{CAP_TOP+EN_GAP},1
Style: Hook,{AR_FONT},140,&H00241A2E,&H00FFFFFF,&H00C9A8FF,&H00C9A8FF,0,0,0,0,100,100,0,0,3,26,0,8,100,100,290,-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def captions(name, cfg, offset, total, out):
    global HOOK_END
    HOOK_END = cfg.get("hook_end", 2.6)
    words = [w for w in json.load(open(f"scripts/captions/{name}.json"))["words"]
             if not w["text"].startswith("[")]
    # Sentences (for the English line): split on . ! ؟ …
    sents, cur = [], []
    for w in words:
        cur.append(w)
        if w["text"][-1:] in ENDS:
            sents.append(cur); cur = []
    if cur:
        sents.append(cur)
    assert len(sents) == len(cfg["en"]), f"{name}: {len(sents)} Arabic parts vs {len(cfg['en'])} English"
    hook = cfg.get("hook")
    clean = lambda s: s.strip(".،,!؟?…")
    lines = []

    def emit(style, st, en, txt, mv_under):
        if hook and st < HOOK_END < en:
            lines.append(f"Dialogue: 0,{ts(st)},{ts(HOOK_END)},{style},,0,0,{mv_under},,{txt}\n")
            lines.append(f"Dialogue: 0,{ts(HOOK_END)},{ts(en)},{style},,0,0,0,,{txt.split('}',1)[-1] if txt.startswith('{\\fscx') else txt}\n")
        else:
            lines.append(f"Dialogue: 0,{ts(st)},{ts(en)},{style},,0,0,{mv_under if hook and st < HOOK_END else 0},,{txt}\n")
    if hook:
        lines.append(f"Dialogue: 1,{ts(0)},{ts(HOOK_END)},Hook,,0,0,0,,{{\\fad(120,200)}}{hook}\n")
    for si, s in enumerate(sents):
        nxt = sents[si + 1][0]["start"] if si + 1 < len(sents) else total - offset
        s_end = min(nxt, s[-1]["end"] + 0.6)
        emit("En", s[0]["start"] + offset, s_end + offset, cfg["en"][si], CAP_UNDER_HOOK + EN_GAP)
        # Arabic: up to 3 words at a time, breaking at commas too.
        chunks, c = [], []
        for w in s:
            c.append(w)
            if len(c) == MAX_WORDS or w["text"][-1:] in "،,":
                chunks.append(c); c = []
        if c:
            if len(c) == 1 and chunks and chunks[-1][-1]["text"][-1:] not in "،,":
                chunks[-1] += c
            else:
                chunks.append(c)
        for ci, ch in enumerate(chunks):
            c_end = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else s_end
            for wi, w in enumerate(ch):
                st = ch[0]["start"] if wi == 0 else w["start"]
                en = ch[wi + 1]["start"] if wi + 1 < len(ch) else c_end
                txt = " ".join((f"{{\\c{HIGHLIGHT}}}{clean(x['text'])}{{\\c&H00FFFFFF&}}" if xi == wi
                                else clean(x["text"])) for xi, x in enumerate(ch))
                pop = "{\\fscx108\\fscy108\\t(0,120,\\fscx100\\fscy100)}" if wi == 0 else ""
                emit("Ar", st + offset, en + offset, pop + txt, CAP_UNDER_HOOK)
    with open(out, "w", encoding="utf-8") as f:
        f.write(ass_header() + "".join(lines))


# Squeezed (anamorphic) phone exports are un-squeezed first, then cropped to fill 9:16.
FILL = (f"scale=trunc(iw*sar/2)*2:ih,setsar=1,"
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1")


def shot(src, start, d, out):
    if src.lower().endswith(".jpg"):
        n = round(d * FPS)
        vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='min(zoom+0.0015,1.08)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:s={W}x{H}:fps={FPS},setsar=1")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-loop", "1", "-i", f"source/{src}", "-vf", vf,
             "-frames:v", str(n), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out])
        return
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(start), "-i", f"source/{src}", "-t", str(d),
         "-vf", f"{FILL},fps={FPS}", "-frames:v", str(round(d * FPS)), "-an",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out])


def v4_audio(total, out):
    base = "audio/ad-8031"
    ins, parts = ["-i", f"{base}/vo_track.mp3"], ["[0]volume=1.0[v]"]
    for i, (f, st, vol, loop) in enumerate(V4_SFX, 1):
        ins += ["-i", f"{base}/{f}"]
        chain = f"[{i}]"
        if loop:
            chain += f"aloop=loop=-1:size=2147483647,atrim=0:{loop},afade=t=in:d=0.6,afade=t=out:st={loop-0.8}:d=0.8,"
        ms = int(st * 1000)
        parts.append(f"{chain}volume={vol},adelay={ms}|{ms}[s{i}]")
    mix = "[v]" + "".join(f"[s{i}]" for i in range(1, len(V4_SFX) + 1))
    graph = ";".join(parts) + f";{mix}amix=inputs={len(V4_SFX)+1}:normalize=0,apad,atrim=0:{total}," \
            f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", *ins, "-filter_complex", graph, "-map", "[a]",
         "-c:a", "aac", "-b:a", "160k", out])


def build(name):
    cfg = ADS[name]
    os.makedirs("ads/camera", exist_ok=True)
    out = f"ads/camera/{name}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        ass = os.path.join(tmp, "c.ass")
        if cfg.get("mix"):
            # Voice lines placed on the re-cut timeline; caption timings follow them.
            words = []
            for i, off in enumerate(V4_LINES, 1):
                words += [{**w, "start": w["start"] + off, "end": w["end"] + off}
                          for w in json.load(open(f"scripts/captions/v4/l{i}.json"))["words"]]
            json.dump({"words": words}, open(f"scripts/captions/{name}.json", "w"), ensure_ascii=False)
            ins, fl = [], []
            for i, off in enumerate(V4_LINES):
                ins += ["-i", f"audio/ad-8031/vo{i+1}.mp3"]
                ms = int(off * 1000)
                fl.append(f"[{i}]loudnorm=I=-16:TP=-1.5:LRA=7,aresample=44100,adelay={ms}|{ms}[a{i}]")
            total = sum(d for *_, d in cfg["shots"])
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", *ins, "-filter_complex",
                 ";".join(fl) + ";" + "".join(f"[a{i}]" for i in range(len(V4_LINES))) +
                 f"amix=inputs={len(V4_LINES)}:normalize=0,apad,atrim=0:{total}",
                 "-c:a", "libmp3lame", "-b:a", "128k", "audio/ad-8031/vo_track.mp3"])
            parts = []
            for i, (src, st, d) in enumerate(cfg["shots"]):
                p = os.path.join(tmp, f"{i:02d}.mp4"); shot(src, st, d, p); parts.append(p)
            lst = os.path.join(tmp, "l.txt")
            open(lst, "w").writelines(f"file '{p}'\n" for p in parts)
            aud = os.path.join(tmp, "a.m4a")
            v4_audio(total, aud)
            captions(name, cfg, 0.0, total, ass)
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", aud,
                 "-vf", f"ass={ass}:fontsdir={FONT_DIR},fade=t=out:st={total-0.4:.2f}:d=0.4",
                 "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                 "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total:.2f}", out])
        else:
            total = sum(d for *_, d in cfg["shots"])
            parts = []
            for i, (src, st, d) in enumerate(cfg["shots"]):
                p = os.path.join(tmp, f"{i:02d}.mp4"); shot(src, st, d, p); parts.append(p)
            lst = os.path.join(tmp, "l.txt")
            open(lst, "w").writelines(f"file '{p}'\n" for p in parts)
            captions(name, cfg, VO_DELAY, total, ass)
            ms = int(VO_DELAY * 1000)
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", cfg["vo"],
                 "-filter_complex",
                 f"[0:v]ass={ass}:fontsdir={FONT_DIR},fade=t=in:st=0:d=0.3,fade=t=out:st={total-0.4:.2f}:d=0.4[v];"
                 f"[1:a]adelay={ms}|{ms},apad,atrim=0:{total:.2f},afade=t=out:st={total-0.3:.2f}:d=0.3,"
                 f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
                 "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                 "-t", f"{total:.2f}", out])
    print(f"{out}  {total:.1f}s")


if __name__ == "__main__":
    for n in sys.argv[1:] or ADS:
        build(n)
