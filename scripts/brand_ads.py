#!/usr/bin/env python3
"""Add Baskio branding to finished ads: a small logo in the top-left corner the
whole time, plus a 2-second end card (logo, store name, website).

Usage (repo root): python3 scripts/brand_ads.py ads/camera/v1-kids.mp4 [...]
Writes ads/final/<name>.mp4. Logo: brand/baskio-logo.png (from baskiostore.com).
"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
GREEN = (36, 70, 56)
LIME = (129, 182, 82)
SITE = "baskiostore.com"
END = 2.0
FONT = "fonts/thmanyah-sans-Black.otf"
LOGO = "brand/baskio-logo.png"


def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], r, fill=255)
    out = img.convert("RGBA"); out.putalpha(m); return out


def make_assets(tmp):
    logo = Image.open(LOGO).convert("RGB")
    # corner logo: 96px rounded square, clear of Instagram's top bar (0-220px)
    small = rounded(logo.resize((96, 96), Image.LANCZOS), 22)
    small.save(os.path.join(tmp, "corner.png"))
    # end card
    card = Image.new("RGB", (W, H), GREEN)
    big = logo.resize((520, 520), Image.LANCZOS)
    card.paste(big, ((W - 520) // 2, 560))
    d = ImageDraw.Draw(card)
    f1 = ImageFont.truetype(FONT, 110)
    f2 = ImageFont.truetype(FONT, 64)
    for text, font, y, col in [("baskio", f1, 1120, (255, 255, 255)), (SITE, f2, 1270, LIME)]:
        w = d.textlength(text, font=font)
        d.text(((W - w) / 2, y), text, font=font, fill=col)
    card.save(os.path.join(tmp, "card.png"))


def run(cmd):
    subprocess.run(cmd, check=True)


def brand(src):
    name = os.path.splitext(os.path.basename(src))[0]
    os.makedirs("ads/final", exist_ok=True)
    out = f"ads/final/{name}.mp4"
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", src]).decode())
    with tempfile.TemporaryDirectory() as tmp:
        make_assets(tmp)
        fc = (f"[0:v][1:v]overlay=40:236:format=auto,fps={FPS},format=yuv420p,setsar=1[main];"
              f"[2:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1,fade=t=in:st=0:d=0.3[card];"
              f"[main][card]concat=n=2:v=1:a=0[v];"
              f"[0:a]apad=pad_dur={END},atrim=0:{dur + END:.3f},afade=t=out:st={dur + END - 0.6:.3f}:d=0.6[a]")
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src,
             "-i", os.path.join(tmp, "corner.png"),
             "-loop", "1", "-t", str(END), "-i", os.path.join(tmp, "card.png"),
             "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
    print(f"{out}  {dur + END:.1f}s")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        brand(s)
