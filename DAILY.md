# Odd History Daily — daily run

Instructions for the scheduled Claude run that makes and schedules one YouTube Short per day
for the channel **Odd History Daily** (@OddHistoryDaily-u4b), owned by Juan.
Juan does not speak English: every message to him is in **Spanish (rioplatense)**.
Everything in the video and on YouTube is in **English for a U.S. audience**.

## 0. Setup (every run starts in a fresh workspace)
1. This repo is attached with push access and cloned. Work inside it.
2. `pip install --break-system-packages -q edge-tts numpy pillow` and check `ffmpeg` exists.
3. Poppins Bold must exist at `/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf`.
   If not, download it from `https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf`
   into that folder (create it).
4. If HTTPS from Python fails with a certificate error, the proxy CA bundle is at `~/.ccr/ca-bundle.crt`
   (tts_lines.py already uses it when present).

## 1. Pick today's story
- Read `log.csv` and never repeat a story. Prefer an unused one from `backlog.md`; you may find a new one.
- A good story: true, surprising, little-known, ideally American, explainable in 25–30 seconds,
  with a twist or a number people will repeat. Avoid gore, graphic death detail, living private people,
  politics/religion controversies, medical or financial advice, and anything that relies on rumor.
- **Verify every fact in at least two independent reputable sources** (encyclopedias, museums, universities,
  major news, government archives). If a number varies between sources, use the conservative one or "about".
  Drop any fact you cannot verify. Never invent quotes.
- **Images:** find 6–9 images on Wikimedia Commons that are public domain / CC0 / "No restrictions"
  (pre-1929 works, U.S. federal government works, etc.). Use the Commons API (see `pipeline/fetch_images.py`),
  with a pause between requests: Commons rate-limits (HTTP 429). If a story has fewer than 5 usable images, pick another story.
  Never use photos of people under 18 as the main subject, and never use copyrighted photos.

## 2. Write the script
- 6–8 lines, **65–80 words total** (≈25–30 s). One line = one sentence; that is how scenes are timed.
- Line 1 is the hook: 5–9 words, the most surprising fact, said straight away.
- Last line ends mid-sentence so it flows back into line 1 when the Short loops
  (e.g. "...long after" → "Boston was hit by a tsunami of molasses.").
- U.S. units (feet, miles, mph, °F). Short, spoken sentences. No filler ("Did you know...?").
- Vary the format from day to day so the channel never looks templated: alternate the card types
  (`bars` comparison, `number` big stat), framed photos, pans across newspapers/maps.
- Voice: `en-US-ChristopherNeural`, rate `+8%` (the channel's consistent narrator).
- **Format rotation:** every 3rd Short is a **maps & numbers** story (see the `format` column in `log.csv`:
  if neither of the last two is `maps`, today is `maps`). It is still a true history story, but told mainly with
  generated maps (`region`), same-scale shape comparisons (`compare`), dates/time zones/borders, and number cards,
  plus 2–3 archival photos. Good fits: territory deals, borders, "bigger than" comparisons, distances, time zones,
  what a place used to be. Example: `stories/2026-11-13-alaska-purchase/`. Other days use format `photos`.

## 3. Build
1. Create `stories/<YYYY-MM-DD>-<slug>/story.json` (copy the structure of the newest story in `stories/`).
   `shots[i].line` = the line where the shot starts, optional `at_word` = word index in that line.
   Pan values `x`/`y` are 0–1 positions inside the free area of the image; `zoom` ≥ 1.0.
2. `python3 pipeline/fetch_images.py stories/<dir>` and, for maps stories, `python3 pipeline/maps.py stories/<dir>`
   (map specs are documented at the top of `pipeline/maps.py`; open the PNGs with Read before using them).
   Shot kinds: `pan` and `framed` (photos), `kb` (zoom/pan: `from`/`to` = [cx, cy, crop width as fraction of image
   width]; use it for maps and to zoom into faces), `xfade` (same move, crossfade `images[0]`→`images[1]` at `at`),
   `bars` and `number` (stat cards). Keep labels and key details out of the caption band (65–75% of the height).
3. `python3 pipeline/make_short.py stories/<dir> voice`
4. `python3 pipeline/make_short.py stories/<dir> preview` → **open `out/preview_sheet.jpg` with the Read tool and look at it.**
   Fix crops where faces/subjects are cut or the caption covers the key detail, re-render only those scenes
   (`... scenes 3,5`), and look again.
5. `python3 pipeline/make_short.py stories/<dir> final` → `out/short.mp4`. Check: 20–35 s, under 50 MB,
   and Read 2–3 frames extracted from it.

## 4. Publish (Metricool → YouTube)
1. Commit `story.json`, `img/credits.json` and the `log.csv` line to `main` (never commit `img/*.jpg` or `out/`).
2. Put the video on the `media` branch, replacing whatever is there (keeps the repo small):
   ```
   D=<dir>   # e.g. 2026-11-13-some-story
   rm -rf /tmp/media && git worktree add -q --orphan -b media-$D /tmp/media
   mkdir -p /tmp/media/videos && cp stories/$D/out/short.mp4 /tmp/media/videos/$D.mp4
   cd /tmp/media && git add -A && git -c user.name="Odd History Daily" -c user.email="noreply@example.com" commit -qm "video $D" \
     && git push -f origin HEAD:media && cd -
   curl -sS -o /dev/null -w "%{http_code} %{size_download}\n" https://raw.githubusercontent.com/cohenjuaN9112/odd-history-daily/media/videos/$D.mp4
   ```
   Public URL: `https://raw.githubusercontent.com/cohenjuaN9112/odd-history-daily/media/videos/<dir>.mp4`
   (must answer 200 with the full size before you use it; wait a minute and retry if not).
3. Metricool: `getBrandSettings` → blogId (8050318) and timezone. **`networksData.youtubeData` must be
   `UCoZ3HTblBSzBHW9Co4JBufg` (Odd History Daily).** If it is anything else (e.g. Juan's personal channel
   `UC56op-wo9H5-OvSvAeu1yVw`) do NOT publish: tell Juan to reconnect the right channel in Metricool.
   Then `createScheduledPost` with:
   - date / publicationDate: **today at 19:00 America/New_York** (21:00 Buenos Aires in the U.S. winter,
     20:00 in the U.S. summer). If today's slot is already taken, use the next free *posting day*.
   - **Posting days (Metricool free plan = max 20 published posts per calendar month):** only days of the month
     that are NOT a multiple of 3 and never the 31st (1,2,4,5,7,8,10,11,13,14,16,17,19,20,22,23,25,26,28,29).
     Never two Shorts on the same day.
   - **Monthly cap check before scheduling:** count this calendar month's posts in Metricool
     (`getScheduledPosts` for the whole month with `extendedRange`, published + pending) and in `log.csv`.
     If there are already 20, do NOT make or schedule a video; tell Juan the monthly limit is reached.
   - providers `[{"network":"youtube"}]`, media `[<raw URL>]`, text = description
   - youtubeData: `{"title": <title>, "type": "short", "privacy": "public", "madeForKids": false,
     "isAiGeneratedContent": false, "category": "EDUCATION", "tags": [...]}`
   (real archival photos + a narrator voice are not "realistic altered content"; set it to true only if a
   video ever shows generated realistic people, events or places.)
4. Append a line to `log.csv`: `date,slug,title,scheduled_et,status,sources,format` and push `main`.

## 5. Tell Juan (Spanish)
Send him, with SendUserMessage + SendUserFile (the video) and a push notification:
- the English title and when it goes out (Argentina time and U.S. East time),
- the Spanish translation of the narration,
- one line on why the story was chosen,
- that he can stop or edit it in Metricool's planner before it goes out.
If any step failed (Metricool not connected, push refused, story not verifiable), still send the video if
there is one and explain plainly what failed and what he needs to do. Never publish anything unverified.
