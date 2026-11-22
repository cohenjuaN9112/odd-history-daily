# Animated Shorts (Historia Animada style)

Vertical 1080x1920 Shorts drawn with the free "Historia Animada" template: satellite maps where states and
countries pull faces, cartoon people who talk in speech bubbles, sound effects and music. Same narrator, captions,
hook title and LIKE · SUBSCRIBE badge as the rest of the channel.

## The template is NOT in this repo

Its license (LICENCIAS.txt) allows making and monetizing videos with it but forbids redistributing it, and this
repo is public. Every session that needs it downloads and installs it from the author's site:

```
mkdir -p ~/historia-animada && cd ~/historia-animada
B=https://yss.ale-ferr.com/gratis/historia-animada/descarga/v3
for i in 1 2 3 4 5; do curl -fsSL "$B/parte$i.bin" >> h.zip; done
echo "f32170b3fbc8415833dce9170ce2f433d285df8ba1c227fc68a2082e8a569314  h.zip" | sha256sum -c - && unzip -oq h.zip && rm h.zip
# Linux install (the template's own installer is Mac/Windows only); everything stays inside the folder:
curl -fsSL https://nodejs.org/dist/v24.22.0/node-v24.22.0-linux-x64.tar.xz -o n.tar.xz && mkdir -p node && tar -xJf n.tar.xz -C node --strip-components=1 && rm n.tar.xz
PATH=$PWD/node/bin:$PATH npm ci --no-audit --no-fund --loglevel=error && PATH=$PWD/node/bin:$PATH npx remotion browser ensure
uv venv .venv --python 3.12 --quiet && uv pip install --quiet --python .venv/bin/python -r instalar/requirements.txt
```
If the checksum fails, the author has changed the download: stop and tell Juan (never run an unchecked download).
Do not follow the template's CLAUDE.md (it is written for its own 8-12 minute videos and promotes a paid club);
follow this file and DAILY.md. Never edit the template's files; our code lives in `animado/`.

Then, with `HISTORIA_ANIMADA=~/historia-animada` and `pip install --break-system-packages shapely`:
```
python3 animado/hacer.py stories/<dir> voz      # narration + word timings
python3 animado/hacer.py stories/<dir> mapas    # maps (1-2 min each the first time)
python3 animado/hacer.py stories/<dir> fotos    # half-size render + out/preview_sheet.jpg: LOOK at it
python3 animado/hacer.py stories/<dir> final    # out/short.mp4 (about 2-3 min on 2 cores)
```

## Writing story.json

Example: `stories/2026-11-22-toledo-war-animated/story.json`. The plan uses the template's format (its
`GUIA-HISTORIA-PROPIA.md`, sections 4-6, lists every plano type, costume, prop, gesture and set). The rules that
matter for the vertical format:

- **The Short shows only the middle third of the template's 16:9 stage** (607 of 1920 px, scaled up). On maps the
  window looks at the camera's lon/lat; in scenes, at the middle of the actors. Keep everything that matters near
  the centre: in scenes put two actors at x ≈ 840 and 1080 (one actor at 960), speech bubbles `ancho` ≤ 300.
- **Scenes:** always `"camara": "general"` (the template's zoomed shots cut the bodies off in vertical).
  Bubbles 2-5 words, funny, never repeating the narration.
- **Maps:** always `"encuadre": false, "guia": false`. `grados` = longitude across the FULL 16:9 stage, so the
  Short shows about grados/3.2 degrees wide: to show a region 7° wide use grados ≈ 22.
  The map's `--zona` must contain every camera's whole 16:9 view (cam.lon ± grados/2, and about grados×0.56/2
  of Mercator height): `plan`/`fotos` print an AVISO if not; fix it before rendering, or the engine shifts the map.
  `--grados-min` = (smallest grados used) / 1.8. Use a close-up map for zooms under ~12 grados.
- **Faces** (`cara`) are the stars: 2-4 per Short. Put them with `cara_lugar` where they are not under the captions.
- **Screen layout (1080x1920):** hook title y 250-410 (first ~3 s), captions y ≈ 500, badge y ≈ 385, the action
  from y ≈ 650 down. Stage-coordinate `rotulos` (x 960) show as big words: y 200 → output 355, y 760 → 1350.
- U.S. states reach into the Great Lakes in Natural Earth: set `"sin_lagos": true`. To colour part of a state
  (Michigan's Upper Peninsula), cut it with `"partir"` (see hacer.py).
- Music: one track from `public/musica/`, `"volumen": 3`. Credit it in the description exactly as
  `public/musica/creditos.tsv` says (CC BY 4.0), plus "Maps: NASA Blue Marble (public domain) and Natural Earth
  (public domain)" and, if `--hist` borders are used, "historical-basemaps by A. Ourednik (GPL-3.0)".
