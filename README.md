# product-videos

Baskio product ads with Saudi Arabic voiceovers from ElevenLabs.

- `source/` — the original product videos. Their own sound is ignored.
- `scripts/` — the ad scripts, timed to what each video shows.
- `voiceovers/` — the ElevenLabs voice files.
- `ads/` — the finished ads (video + voiceover).

The original footage in `source/` is not committed (about 425 MB). To rebuild,
put the files in `source/` and run `python3 scripts/build_ads.py`.
