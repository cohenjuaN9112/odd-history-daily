#!/usr/bin/env python3
"""Animated vertical Shorts for Odd History Daily, drawn with the "Historia Animada" template engine.

The template (maps whose countries pull faces, cartoon people who talk) is downloaded separately into
$HISTORIA_ANIMADA (default ~/historia-animada) and is NEVER committed to this repo: its license allows making and
monetizing videos with it, but not redistributing it. See animado/README.md for how to install it.

  python3 animado/hacer.py stories/<dir> voz      # English narration + word timings (edge-tts)
  python3 animado/hacer.py stories/<dir> mapas    # satellite maps with the territories the plan colours
  python3 animado/hacer.py stories/<dir> fotos    # quick half-size render + out/preview_sheet.jpg (look at it!)
  python3 animado/hacer.py stories/<dir> final    # full render + captions + mix -> out/short.mp4
  python3 animado/hacer.py stories/<dir> todo     # voz + mapas + fotos + final

story.json for an animated Short has the usual keys (lines, hook, comment, badge_line, youtube, sources,
translation_es) plus:
  "format": "animado",
  "mapas": [[preparar_mapa.py options...], ...]       e.g. ["--nombre", "ohd-lagos", "--zona", "-93", "50", "-77", "37.5",
                                                       "--grados-min", "4.5", "--regiones", "USA:Ohio=ohio,Michigan=michigan"]
  "partir": {"<mapa>": {"<capa>": {"<nueva>": {"lat_min": 45.85}, "<otra>": {"resto": true}}}}
            splits one territory into pieces by the latitude/longitude of each of its islands/parts
  "plan": {"musica": [...], "planos": [...]}          the template's plan format (GUIA-HISTORIA-PROPIA.md), plus
            "corte" / "corte_hasta" per plano: the x (0-1920) the vertical window looks at (see short/Short.tsx).
  "cap_y", "badge_y", "hook_y": caption / LIKE·SUBSCRIBE badge / hook positions on the 1080x1920 frame.
"""
import json, math, os, re, shutil, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
T = os.path.abspath(os.path.expanduser(os.environ.get("HISTORIA_ANIMADA", "~/historia-animada")))
FONTDIR = "/usr/share/fonts/truetype/google-fonts"
W, H, FPS = 1080, 1920, 30
K = 1920 / 1080  # the template stage (1920x1080) is scaled by this much inside the vertical frame


def sh(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def dur_of(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode())


def env_t():
    e = dict(os.environ)
    e["PATH"] = os.path.join(T, "node", "bin") + os.pathsep + e["PATH"]
    return e


class Animado:
    def __init__(self, d):
        self.d = os.path.abspath(d)
        self.s = json.load(open(f"{self.d}/story.json"))
        self.id = os.path.basename(self.d)
        self.out = f"{self.d}/out"
        os.makedirs(self.out, exist_ok=True)
        self.vid = f"{T}/public/videos/{self.id}"
        if not os.path.exists(f"{T}/src/historia/VideoTerra.tsx"):
            sys.exit(f"Historia Animada is not installed in {T} (see animado/README.md).")
        # our vertical composition lives next to the template's code (copied every time, never edited there)
        shutil.copytree(f"{HERE}/short", f"{T}/src/short", dirs_exist_ok=True)

    # ---------- voice ----------
    def voz(self):
        open(f"{self.out}/lines.txt", "w").write("\n".join(self.s["lines"]) + "\n")
        sh(["python3", f"{REPO}/pipeline/tts_lines.py", f"{self.out}/lines.txt", self.s.get("voice", "en-US-ChristopherNeural"),
            f"{self.out}/vo.wav", self.s.get("rate", "+8%"), str(self.s.get("gap", 0.2))])
        self.tiempos()

    def tiempos(self):
        words = json.load(open(f"{self.out}/vo.wav.words.json"))
        os.makedirs(self.vid, exist_ok=True)
        pal = []
        for a, b, w, _ in words:
            # edge-tts sometimes returns two words as one ("Lake Michigan", "In 1835"); the plan anchors on single
            # words, so split them and share the time by length
            partes = w.split()
            total = sum(len(x) for x in partes) or 1
            t = a
            for x in partes:
                d = (b - a) * len(x) / total
                pal.append({"p": x, "ini": round(t, 3), "fin": round(t + d, 3)})
                t += d
        json.dump({"duracion": round(dur_of(f"{self.out}/vo.wav"), 2), "palabras": pal}, open(f"{self.vid}/voz.tiempos.json", "w"), indent=1)
        sh(["ffmpeg", "-v", "error", "-y", "-i", f"{self.out}/vo.wav", "-b:a", "192k", f"{self.vid}/voz.mp3"])
        print("words:", " ".join(f"{i}:{p['p']}" for i, p in enumerate(pal)))

    # ---------- maps ----------
    def mapas(self, rehacer=False):
        for m in self.s.get("mapas", []):
            nombre = m[m.index("--nombre") + 1]
            dest = f"{T}/public/mapas/{nombre}"
            if os.path.exists(f"{dest}/mapa.json") and not rehacer:
                print(f"map {nombre}: already there")
            else:
                shutil.rmtree(dest, ignore_errors=True)
                r = subprocess.run([f"{T}/.venv/bin/python", f"{T}/herramientas/preparar_mapa.py", *m], cwd=T, env=env_t(), capture_output=True, text=True)
                if r.returncode != 0:
                    sys.exit(f"map {nombre} failed:\n{(r.stderr or r.stdout)[-1500:]}")
                print(f"map {nombre}: ready")
            self.partir(nombre)
            if self.s.get("sin_lagos"):
                self.sin_lagos(nombre)

    def sin_lagos(self, nombre):
        """U.S. states in Natural Earth reach into the Great Lakes, so Ohio paints Lake Erie red. Cut the lakes
        out of every territory of this map (story.json: "sin_lagos": true)."""
        from shapely.geometry import Polygon, MultiPolygon
        from shapely.ops import unary_union
        p = f"{T}/public/mapas/{nombre}/mapa.json"
        m = json.load(open(p))
        if not m.get("lagos") or m.get("_sin_lagos"):
            return

        def geom(d):
            polys = []
            for a in re.findall(r"M[^MZ]*Z?", d):
                pts = [tuple(map(float, q)) for q in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", a)]
                if len(pts) >= 3:
                    polys.append(Polygon(pts).buffer(0))
            return unary_union(polys)

        lagos = geom(m["lagos"]).buffer(0)
        for k, c in m["capas"].items():
            g = geom(c["d"]).difference(lagos)
            if g.is_empty:
                continue
            partes = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
            partes = [q for q in partes if q.area > 50]
            c["d"] = "".join("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in list(r.coords)[:-1]) + "Z" for q in partes for r in [q.exterior, *q.interiors])
            grande = max(partes, key=lambda q: q.area)
            ce = grande.centroid if grande.contains(grande.centroid) else grande.representative_point()
            c["centro"] = [round(ce.x, 1), round(ce.y, 1)]
        m["_sin_lagos"] = True
        json.dump(m, open(p, "w"))
        print(f"  lakes cut out of the territories of {nombre}")

    def partir(self, nombre):
        """Cut one territory in two along a line drawn through water/land, e.g. Michigan's Upper and Lower
        Peninsulas: {"michigan_up": {"norte_de": [[lon, lat], ...]}, "michigan_lp": {"resto": true}}.
        The line must run west to east and be wider than the territory. The engine clips colours to land, so the
        line can cross lakes and seas freely."""
        reglas = self.s.get("partir", {}).get(nombre)
        if not reglas:
            return
        from shapely.geometry import Polygon, MultiPolygon
        from shapely.ops import unary_union
        p = f"{T}/public/mapas/{nombre}/mapa.json"
        m = json.load(open(p))
        x0, y0, x1, y1 = m["merc"]
        R = 6378137.0

        def px(lon, lat):
            X = R * math.radians(lon); Y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
            return ((X - x0) / (x1 - x0) * m["ancho"], (y1 - Y) / (y1 - y0) * m["alto"])

        def a_path(g):
            partes = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
            out = []
            for q in partes:
                for ring in [q.exterior, *q.interiors]:
                    c = list(ring.coords)
                    out.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in c[:-1]) + "Z")
            return "".join(out), max(partes, key=lambda q: q.area)

        for capa, nuevas in reglas.items():
            src = m["capas"].get(capa)
            if not src:
                print(f"  partir: no territory «{capa}» in {nombre}"); continue
            anillos = re.findall(r"M[^MZ]*Z?", src["d"])
            polys = []
            for a in anillos:
                pts = [tuple(map(float, q)) for q in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", a)]
                if len(pts) >= 3:
                    polys.append(Polygon(pts).buffer(0))
            todo = unary_union(polys)
            usado = None
            resto = None
            for k, r in nuevas.items():
                if r.get("resto"):
                    resto = k; continue
                linea = [px(lon, lat) for lon, lat in (r.get("norte_de") or r.get("sur_de"))]
                lejos = -1e7 if "norte_de" in r else 1e7
                zona = Polygon(linea + [(linea[-1][0], lejos), (linea[0][0], lejos)]).buffer(0)
                g = todo.intersection(zona)
                usado = g if usado is None else usado.union(g)
                self._guardar(m, src, k, g, a_path)
            if resto:
                self._guardar(m, src, resto, todo.difference(usado) if usado is not None else todo, a_path)
        json.dump(m, open(p, "w"))

    @staticmethod
    def _guardar(m, src, k, g, a_path):
        if g.is_empty:
            print(f"  partir -> {k}: empty"); return
        d, grande = a_path(g)
        c = grande.centroid if grande.contains(grande.centroid) else grande.representative_point()
        m["capas"][k] = {**src, "d": d, "centro": [round(c.x, 1), round(c.y, 1)], "nombre": k}
        print(f"  partir -> {k}: ok")

    # ---------- plan ----------
    def plan(self):
        if not os.path.exists(f"{self.vid}/voz.tiempos.json"):
            self.tiempos()
        os.makedirs(self.vid, exist_ok=True)
        json.dump({**self.s["plan"], "id": self.id}, open(f"{self.vid}/plan.json", "w"), ensure_ascii=False, indent=1)
        codigo = ("import { readFileSync } from 'node:fs';"
                  "import { resolverTerra } from './src/historia/resolverTerra.mjs';"
                  f"const p = JSON.parse(readFileSync('public/videos/{self.id}/plan.json','utf8'));"
                  f"const t = JSON.parse(readFileSync('public/videos/{self.id}/voz.tiempos.json','utf8'));"
                  "const r = resolverTerra(p, t);"
                  "console.log(JSON.stringify({avisos: r.avisos, duracion: r.duracion, planos: r.planos.map(x => ({n: x.n, tipo: x.tipo, en: x.en, ini: x.ini, fin: x.fin}))}));")
        r = subprocess.run([f"{T}/node/bin/node", "--input-type=module", "-e", codigo], cwd=T, env=env_t(), capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("plan check failed:\n" + r.stderr[-2000:])
        res = json.loads(r.stdout[r.stdout.index("{"):])
        res["avisos"] += self.revisar_camaras()
        for a in res["avisos"]:
            print("  " + a)
        for p in res["planos"]:
            print(f"  plano {p['n'] + 1:2d} {p['tipo']:8s} {p['ini']:5.2f}-{p['fin']:5.2f}  «{p['en']}»")
        self.res = res
        return res

    def revisar_camaras(self):
        """The engine never shows the edge of the satellite image, and it reasons about the full 16:9 stage even though
        the Short only shows its middle third. If a camera's 16:9 view does not fit inside the map's --zona, the
        engine silently zooms in and slides the map, and the Short shows the wrong place. Catch that here."""
        avisos = []
        merc = lambda lat: math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))
        for n, p in enumerate(self.s["plan"]["planos"]):
            if p.get("tipo") != "mapa":
                continue
            f = f"{T}/public/mapas/{p['mapa']}/mapa.json"
            if not os.path.exists(f):
                avisos.append(f"AVISO plano {n + 1}: map {p['mapa']} not prepared"); continue
            w, nn, e, sur = json.load(open(f))["zona"]
            for nombre in ("cam", "hasta"):
                c = p.get(nombre)
                if not c:
                    continue
                hw, hh = c["grados"] / 2, c["grados"] * 1080 / 1920 / 2
                if c["lon"] - hw < w or c["lon"] + hw > e or merc(c["lat"]) - hh < merc(sur) or merc(c["lat"]) + hh > merc(nn):
                    avisos.append(f"AVISO plano {n + 1}: «{nombre}» needs lon {c['lon'] - hw:.1f}..{c['lon'] + hw:.1f} and a taller zone "
                                  f"than map {p['mapa']} has ({w}..{e}, {sur}..{nn}); make the --zona bigger")
        return avisos

    # ---------- render ----------
    def render(self, dest, escala=1.0):
        args = ["npx", "remotion", "render", "src/short/index.ts", "Short", dest, f"--props={json.dumps({'id': self.id})}",
                f"--concurrency={os.environ.get('HISTORIA_CONCURRENCIA', '100%')}", "--crf=16", "--jpeg-quality=95",
                "--timeout=180000", "--log=error"]
        if escala != 1.0:
            args.append(f"--scale={escala}")
        log = f"{self.out}/render.log"
        with open(log, "w") as f:
            r = subprocess.run(args, cwd=T, env=env_t(), stdout=f, stderr=subprocess.STDOUT)
        if r.returncode != 0:
            sys.exit("render failed:\n" + open(log).read()[-2500:])

    # ---------- captions ----------
    def ass(self):
        words = [(a, b, w) for a, b, w, _ in json.load(open(f"{self.out}/vo.wav.words.json"))]
        groups = [[(a, b, w) for a, b, w, li in json.load(open(f"{self.out}/vo.wav.words.json")) if li == i] for i in range(len(self.s["lines"]))]
        end = round(dur_of(f"{self.out}/vo.wav") + 0.12, 2)
        ts = lambda t: f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{max(t, 0) % 60:05.2f}"
        chunks, cur = [], []
        for k, (s, e, w) in enumerate(words):
            cur.append((s, e, w))
            nxt = words[k + 1][0] if k + 1 < len(words) else None
            if len(cur) == 3 or nxt is None or nxt - e > 0.18 or len(" ".join(x[2] for x in cur)) > 15:
                chunks.append(cur); cur = []
        ev = []
        for ci, ch in enumerate(chunks):
            cend = end if ci == len(chunks) - 1 else min(chunks[ci + 1][0][0], ch[-1][1] + 0.35)
            for wi, (s, e, w) in enumerate(ch):
                en = ch[wi + 1][0] if wi + 1 < len(ch) else cend
                txt = " ".join((r"{\c&H0000B4FF&}" + ww.upper() + r"{\c&H00FFFFFF&}") if wj == wi else ww.upper() for wj, (_, _, ww) in enumerate(ch))
                ev.append((s, en, txt))
        cap_y, badge_y, hook_y = self.s.get("cap_y", 560), self.s.get("badge_y", 430), self.s.get("hook_y", 330)
        head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,8,4,5,90,90,0,1
Style: Cta,Poppins,62,&H00FFFFFF,&H00FFFFFF,&H001C1CE6,&H001C1CE6,1,0,0,0,100,100,3,0,3,20,0,5,80,80,0,1
Style: Hook,Poppins,140,&H00FFFFFF,&H00FFFFFF,&H00000000,&HB4000000,1,0,0,0,100,100,0,0,1,11,6,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        hook = self.s.get("hook")
        hend = min(groups[0][-1][1] + 0.15, 3.2) if hook else 0
        # while the big hook title is on screen, the captions wait (the hook says the same thing)
        lines = [f"Dialogue: 1,{ts(max(s, hend))},{ts(e)},Cap,,0,0,0,,{{\\pos(540,{cap_y})}}{t}" for s, e, t in ev if e > hend]
        bl = self.s.get("badge_line", len(groups) // 2)
        if bl is not None and bl is not False:
            g = groups[bl]
            lines.append(f"Dialogue: 2,{ts(g[0][0] - 0.1)},{ts(g[-1][1] + 0.25)},Cta,,0,0,0,,{{\\pos(540,{badge_y})\\fad(120,120)}}LIKE  ·  SUBSCRIBE")
        if hook:
            for i, x in enumerate(hook):
                col = r"\c&H0000B4FF&" if x.startswith("*") else ""
                fx = r"\fscx118\fscy118\t(0,160,\fscx100\fscy100)\fad(0,140)"
                lines.append(f"Dialogue: 3,{ts(0)},{ts(hend)},Hook,,0,0,0,,{{\\pos(540,{hook_y + i * 160}){fx}{col}}}{x.lstrip('*').upper()}")
        open(f"{self.out}/captions.ass", "w").write(head + "\n".join(lines) + "\n")
        self.end = end

    # ---------- preview ----------
    def fotos(self):
        res = self.plan()
        self.render(f"{self.out}/anim_preview.mp4", 0.5)
        self.ass()
        frames = []
        cuando = [0.1] + [round((p["ini"] + p["fin"]) / 2, 2) for p in res["planos"]]
        for i, t in enumerate(cuando):
            f = f"{self.out}/pv_{i:02d}.jpg"
            sh(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", f"{self.out}/anim_preview.mp4", "-frames:v", "1", "-copyts",
                "-vf", f"ass={self.out}/captions.ass:fontsdir={FONTDIR}", "-q:v", "3", f])
            frames.append(f)
        shutil.copy(frames[0], f"{self.out}/first_frame.jpg")
        tw, th = 270, 480
        cols = min(len(frames), 5); rows = math.ceil(len(frames) / cols)
        sheet = Image.new("RGB", (cols * (tw + 8), rows * (th + 8)), "black")
        for k, p in enumerate(frames):
            sheet.paste(Image.open(p).resize((tw, th)), ((k % cols) * (tw + 8), (k // cols) * (th + 8)))
        sheet.save(f"{self.out}/preview_sheet.jpg", quality=85)
        print("preview:", f"{self.out}/preview_sheet.jpg", "(first frame + the middle of every plano)")

    # ---------- final ----------
    def final(self):
        self.plan()
        anim = f"{self.out}/anim.mp4"
        self.render(anim)
        self.ass()
        end = self.end
        tmp = f"{self.out}/short.tmp.mp4"
        # the template's own music and sound effects (already ducked under the voice) + our narration
        fc = (f"[0:v]ass={self.out}/captions.ass:fontsdir={FONTDIR}[v];"
              f"[0:a]aresample=48000,apad,atrim=0:{end}[fx];[1:a]aresample=48000,apad,atrim=0:{end}[vo];"
              f"[vo][fx]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        sh(["ffmpeg", "-v", "error", "-y", "-i", anim, "-i", f"{self.out}/vo.wav", "-filter_complex", fc,
            "-map", "[v]", "-map", "[a]", "-t", str(end), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", tmp])
        os.replace(tmp, f"{self.out}/short.mp4")
        print("final:", f"{self.out}/short.mp4", round(os.path.getsize(f"{self.out}/short.mp4") / 1e6, 1), "MB", end, "s")


if __name__ == "__main__":
    a = Animado(sys.argv[1])
    paso = sys.argv[2]
    if paso == "voz": a.voz()
    elif paso == "mapas": a.mapas("--rehacer" in sys.argv)
    elif paso == "plan": a.plan()
    elif paso == "fotos": a.fotos()
    elif paso == "final": a.final()
    elif paso == "todo": a.voz(); a.mapas(); a.fotos(); a.final()
    else: sys.exit(__doc__)
