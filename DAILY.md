# Odd History Daily — daily run

Instructions for the scheduled Claude run that prepares **two YouTube Shorts per day**
for the channel **Odd History Daily** (@OddHistoryDaily-u4b), owned by Juan.
**Juan uploads them himself** (since 2026-11-14; Metricool's free plan only publishes 20 posts a month):
the run builds the videos and hands him each one with its title, description and comment, ready to paste.
The run does NOT schedule anything in Metricool.
Juan does not speak English: every message to him is in **Spanish (rioplatense)**.
Everything in the video and on YouTube is in **English for a U.S. audience**.

## 0. Setup (every run starts in a fresh workspace)
1. This repo is attached with push access and cloned. Work inside it.
2. `pip install --break-system-packages -q edge-tts numpy pillow shapely` and check `ffmpeg` exists.
3. Poppins Bold must exist at `/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf`.
   If not, download it from `https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf`
   into that folder (create it).
4. If HTTPS from Python fails with a certificate error, the proxy CA bundle is at `~/.ccr/ca-bundle.crt`
   (tts_lines.py already uses it when present).
5. **Install the animation engine:** `bash animado/instalar.sh` (about 1 minute; it downloads the free
   "Historia Animada" template from its author, checks its checksum and installs it in `~/historia-animada`).
   If it stops with "does not match the checked version", do NOT continue with any other download: make no videos
   and tell Juan in Spanish that the animation template changed and needs checking.
   Read `animado/README.md` once: it explains how the vertical format works.
   Never commit anything from `~/historia-animada` (its license forbids redistributing it), never edit its files,
   and do not follow its CLAUDE.md (it is for its own long videos and promotes a paid club).

## 1. Pick today's stories
- **Since 2026-11-22 every Short is ANIMATED** (Juan's decision): maps whose countries/states pull faces,
  cartoon people who talk in speech bubbles, built with `animado/hacer.py`. The old photo pipeline
  (`pipeline/make_short.py`) is no longer used for new videos.
- **How many:** two per run, minus any Short that Metricool already has pending for today
  (`getScheduledPosts`, brand 8050318, today in America/Buenos_Aires; leftovers that publish on their own).
  Do sections 1–3 fully for one story, then for the other. The two stories of a day must differ in era and subject.
- Read `log.csv` and never repeat a story. Prefer an unused one from `backlog.md`; you may find a new one.
- A good story: true, surprising, little-known, ideally American, explainable in 25–30 seconds,
  with a twist or a number people will repeat. Avoid gore, graphic death detail, living private people,
  politics/religion controversies, medical or financial advice, and anything that relies on rumor.
- **It must be drawable** with the engine: places that can be shown on a map (states, countries, borders, routes,
  islands), rivalries between places (they become faces), and people doing something odd that cartoon characters
  can act out. Check the catalog in `~/historia-animada/GUIA-HISTORIA-PROPIA.md` section 6 (costumes, props, sets,
  gestures) before choosing: if the key moment cannot be drawn, pick another story.
- **Verify every fact in at least two independent reputable sources** (encyclopedias, museums, universities,
  major news, government archives). If a number varies between sources, use the conservative one or "about".
  Drop any fact you cannot verify. Never invent quotes. Speech bubbles are jokes, not quotes: never put words
  in a real person's mouth that sound like a historical quote.

## 2. Write the script
- 6–8 lines, **65–80 words total** (≈25–30 s). One line = one sentence.
- Line 1 is the hook: 5–9 words, the most surprising fact, said straight away.
- `"hook": ["OHIO VS.", "*MICHIGAN"]`: 2 lines, max 11 characters each, the claim in its shortest form
  (`*` = amber line). It is drawn big at the top during line 1. The first plano must already be full at frame 0
  (territories with `"en": 0`, a face appearing in the first second).
- **Comment question:** one short question that invites opinions and has no right answer, as `"comment"`.
- Last line ends mid-sentence so it flows back into line 1 when the Short loops.
- **No spoken call to action.** Set `"badge_line"` (never 0) for the LIKE · SUBSCRIBE badge.
- U.S. units (feet, miles, mph, °F). Short, spoken sentences. No filler ("Did you know...?").
- Voice: `en-US-ChristopherNeural`, rate `+8%` (the channel's consistent narrator).

## 3. Build (animated)
Example to copy: `stories/2026-11-22-toledo-war-animated/story.json`. Rules: `animado/README.md`.
Use `HISTORIA_ANIMADA=~/historia-animada` for every command.
1. Create `stories/<YYYY-MM-DD>-<slug>/story.json` with `"format": "animado"`, the lines, hook, comment,
   badge_line, `"cap_y": 500, "badge_y": 385, "hook_y": 250`, sources and translation_es.
2. `python3 animado/hacer.py stories/<dir> voz` → prints every word with its number. Anchor planos on those words.
3. Write `"mapas"` (preparar_mapa options; zones much bigger than what is shown, see README), `"sin_lagos": true`
   for U.S. states, and the `"plan"`: about **one plano per line** (7–9 planos), alternating maps and scenes,
   something new appearing every 1–2 s. Give a map plano 2–4 s, a scene 3–5 s.
   - Maps: `"encuadre": false, "guia": false`, faces (`cara`) on the places that matter, pins, arrows, armies,
     ships, `rotulos` for the big numbers the voice says (x 960).
   - Scenes: `"camara": "general"`, 1–2 actors near the middle (x 960, or 840 and 1080), costumes from the catalog,
     gestures on the right words, 1–2 speech bubbles of 2–5 funny words (never repeating the narration).
   - One music track (`"volumen": 3`), picked to fit the mood.
4. `python3 animado/hacer.py stories/<dir> mapas` and then `... plan`: fix every `AVISO` (a missing word, a camera
   the map cannot hold) before rendering.
5. `python3 animado/hacer.py stories/<dir> fotos` → **open `out/preview_sheet.jpg` and `out/first_frame.jpg` with the
   Read tool and look at them.** Check: the right place on every map, faces and labels not under the captions
   (top band, y 450–550 of 1920) or cut at the edges, bodies and speech bubbles fully inside the frame, nothing
   empty. Fix the plan and run `fotos` again until it is right. A single frame: `cd ~/historia-animada &&
   PATH=$PWD/node/bin:$PATH npx remotion still src/short/index.ts Short /tmp/f.png --frame=<n> --props='{"id":"<dir>"}'`.
6. `python3 animado/hacer.py stories/<dir> final` → `out/short.mp4` (2–3 minutes). Check: 20–35 s, under 50 MB,
   and Read 2–3 frames extracted from it.

## 4. Hand over (Juan uploads by hand)
1. For each video write `stories/<dir>/upload.txt` (committed) with exactly these blocks, in English:
   `TITLE:` (max 60 characters, no hashtags), `DESCRIPTION:` **short** (Juan's rule, 2026-11-22): 1–2 sentences
   (max ~35 words) of the story, a blank line, `Sources:` with 2–3 short source names only (e.g. "Wikipedia,
   History.com, Michigan.gov"), the music credit in one line (required by the CC BY license), e.g.
   `Music: "Mischief Maker" by Kevin MacLeod (incompetech.com), CC BY 4.0` (title and author from
   `~/historia-animada/public/musica/creditos.tsv`), then `#history #shorts` plus one topical hashtag.
   No map credits (public domain); see `stories/2026-11-22-toledo-war-animated/upload.txt`.
   `COMMENT:` (the story's `comment` question), `TAGS:` (comma-separated).
2. Commit `story.json`, `upload.txt` and the `log.csv` lines to `main`
   (never commit `out/` or anything from `~/historia-animada`). log.csv columns: `date,slug,title,scheduled_et,status,sources,format`;
   use the suggested upload time in `scheduled_et`, status `handed to Juan (manual upload)` and format `animado`.
3. Put today's videos on the `media` branch, replacing the previous day's (normal push, never force):
   ```
   M=<scratch dir>/media
   git fetch -q origin media && git worktree prune && rm -rf $M && git worktree add -q -b media-$(date +%s) $M origin/media
   git -C $M rm -q -r --ignore-unmatch videos && mkdir -p $M/videos
   cp stories/<dir1>/out/short.mp4 $M/videos/<dir1>.mp4; cp stories/<dir2>/out/short.mp4 $M/videos/<dir2>.mp4
   git -C $M add -A && git -C $M -c user.name="Odd History Daily" -c user.email="noreply@example.com" commit -qm "videos <date>" \
     && git -C $M push origin HEAD:media
   ```
   Download link for each: `https://raw.githubusercontent.com/cohenjuaN9112/odd-history-daily/media/videos/<dir>.mp4`
   (check it answers 200 with the full size).

## 5. Tell Juan (Spanish)
Send the videos with SendUserFile (file names `<date> 1 <short name>.mp4`, `<date> 2 <short name>.mp4`) and ONE
SendUserMessage in Spanish (rioplatense), plus a push notification. For each video, in this order:
- **Video 1 / Video 2**, the download link, and the suggested upload time in Argentina time:
  video 1 at 12:00 America/New_York, video 2 at 19:00 America/New_York (convert to Buenos Aires time; he can
  upload both in the morning and use "Programar" in YouTube Studio).
- `Título`, `Descripción` and `Comentario para fijar`, each in its own code block so he can copy it
  (English text exactly as in `upload.txt`).
- The Spanish translation of the narration and one line on why the story was chosen.
End with the fixed upload checklist: "No, no es contenido para niños" · contenido alterado: No · visibilidad
Pública (o Programar) · después de publicar, pegar el comentario y fijarlo.
If a Short was already pending in Metricool for today, say which one and that he must NOT upload that one.
If any step failed (story not verifiable, push refused), still send what there is and explain plainly what
failed. Never hand over anything unverified.
