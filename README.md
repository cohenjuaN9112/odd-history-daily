# Odd History Daily

Pipeline that makes one vertical history Short per day for the YouTube channel Odd History Daily.
The daily procedure is in [DAILY.md](DAILY.md); ideas in [backlog.md](backlog.md); history in [log.csv](log.csv).

- `pipeline/fetch_images.py` — downloads public-domain images from Wikimedia Commons and records credits
- `pipeline/tts_lines.py` — narration (one TTS clip per sentence) with word timings
- `pipeline/make_short.py` — scenes (pans, framed photos, stat cards), captions, music bed, final mix
