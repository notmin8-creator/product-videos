#!/usr/bin/env python3
"""Add Baskio branding to finished ads: a small 'baskio' wordmark in the top-left corner the
whole time, plus a green rounded 'www.baskiostore.com' badge over the last shot.

Usage (repo root): python3 scripts/brand_ads.py ads/camera/v1-kids.mp4 [...]
Writes ads/final/<name>.mp4. Logo: brand/wordmark-ar.png and brand/wordmark-en.png (Baskio wordmarks).
"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
GREEN = (36, 70, 56)
LIME = (36, 70, 56)   # website text in brand green on the white card
SITE = "www.baskiostore.com"
BADGE = 2.5   # seconds the website badge shows at the end
BADGE_Y = {"v4-asmr": 470}   # per-ad badge height where the last shot needs it
FONT = "fonts/thmanyah-sans-Black.otf"



def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    out = img.convert("RGBA"); out.putalpha(m); return out


def fit(path, w):
    im = Image.open(path).convert("RGBA")
    return im.resize((w, round(im.size[1] * w / im.size[0])), Image.LANCZOS)


def make_assets(tmp):
    # corner: green "baskio" wordmark on a white rounded pill, clear of Instagram's top bar
    en = fit("brand/wordmark-en.png", 170)
    pw, ph = en.size[0] + 44, en.size[1] + 30
    pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([0, 0, pw - 1, ph - 1], ph // 2, fill=(255, 255, 255, 235))
    pill.alpha_composite(en, ((pw - en.size[0]) // 2, (ph - en.size[1]) // 2))
    pill.save(os.path.join(tmp, "corner.png"))
    # website badge for the last shot: white text on a brand-green rounded rectangle
    f = ImageFont.truetype(FONT, 58)
    tw = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(SITE, font=f)
    bw, bh = int(tw) + 96, 118
    badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(badge)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], 30, fill=GREEN + (255,))
    d.text(((bw - tw) / 2, 22), SITE, font=f, fill=(255, 255, 255))
    badge.save(os.path.join(tmp, "badge.png"))


def run(cmd):
    subprocess.run(cmd, check=True)


def brand(src):
    name = os.path.splitext(os.path.basename(src))[0]
    os.makedirs("ads/final", exist_ok=True)
    out = f"ads/final/{name}.mp4"
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", src]).decode())
    st = max(dur - BADGE, 0)
    with tempfile.TemporaryDirectory() as tmp:
        make_assets(tmp)
        # badge sits in the open area under the captions, clear of the product and Instagram's UI
        fc = (f"[0:v][1:v]overlay=40:236:format=auto[c];"
              f"[2:v]format=rgba,fade=t=in:st={st:.2f}:d=0.3:alpha=1[b];"
              f"[c][b]overlay=(W-w)/2:{BADGE_Y.get(name, 820)}:enable='gte(t,{st:.2f})':format=auto,format=yuv420p[v]")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src,
             "-i", os.path.join(tmp, "corner.png"),
             "-loop", "1", "-t", f"{dur:.3f}", "-i", os.path.join(tmp, "badge.png"),
             "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
             "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
             "-c:a", "copy", "-movflags", "+faststart", "-t", f"{dur:.3f}", out])
    print(f"{out}  {dur:.1f}s")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        brand(s)
