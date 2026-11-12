"""Build one vertical Short from stories/<slug>/story.json.

Usage:
  python3 make_short.py stories/<slug> voice     # narration + word timings
  python3 make_short.py stories/<slug> preview   # scenes + preview sheet (look at it before final)
  python3 make_short.py stories/<slug> final     # captions + music + mix -> out/short.mp4
  python3 make_short.py stories/<slug> scenes 3,4  # re-render only some scenes
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SS = 1080, 1920, 30, 2
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONTDIR = os.path.dirname(FONT)
GRADE = ("hue=s=0,colorchannelmixer=rr=1.07:gg=0.96:bb=0.80,eq=contrast=1.08,"
         "noise=alls=4:allf=t,vignette=angle=PI/5")
INK, PAPER, AMBER = (27, 18, 11), (240, 236, 228), (255, 180, 0)
GRADE_MAP = "noise=alls=3:allf=t,vignette=angle=PI/6"

def sh(cmd): subprocess.run(cmd, check=True)
def dur_of(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).decode())

class Story:
    def __init__(self, d):
        self.d = os.path.abspath(d)
        self.s = json.load(open(f"{self.d}/story.json"))
        self.out = f"{self.d}/out"; os.makedirs(self.out, exist_ok=True)
        self.sc = f"{self.out}/scenes"; os.makedirs(self.sc, exist_ok=True)

    # ---------- narration ----------
    def voice(self):
        open(f"{self.out}/lines.txt", "w").write("\n".join(self.s["lines"]) + "\n")
        sh(["python3", f"{HERE}/tts_lines.py", f"{self.out}/lines.txt", self.s.get("voice", "en-US-ChristopherNeural"),
            f"{self.out}/vo.wav", self.s.get("rate", "+8%"), str(self.s.get("gap", 0.2))])

    def timing(self):
        raw = json.load(open(f"{self.out}/vo.wav.words.json"))
        self.groups = [[(a, b, w) for a, b, w, li in raw if li == i] for i in range(len(self.s["lines"]))]
        self.words = [(a, b, w) for a, b, w, _ in raw]
        self.end = round(dur_of(f"{self.out}/vo.wav") + 0.12, 2)
        return self.words, self.groups

    def shot_times(self):
        self.timing()
        times = []
        for i, sh_ in enumerate(self.s["shots"]):
            if i == 0: times.append(0.0); continue
            g = self.groups[min(sh_["line"], len(self.groups) - 1)]
            w = g[min(sh_.get("at_word", 0), len(g) - 1)]
            times.append(round(max(w[0] - 0.08, times[-1] + 0.5), 2))
        return times + [self.end]

    # ---------- visuals ----------
    def img_path(self, key):
        for f in os.listdir(f"{self.d}/img"):
            if os.path.splitext(f)[0] == key: return f"{self.d}/img/{f}"
        raise FileNotFoundError(key)

    def prescale(self, shot, name):
        im = Image.open(self.img_path(shot["image"])).convert("RGB")
        zoom = shot.get("zoom", 1.08)
        if shot["kind"] == "framed":
            cw, ch = round(W * SS * zoom), round(H * SS * zoom)
            w, h = im.size; s = max(cw / w, ch / h)
            bg = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
            bx, by = (bg.width - cw) // 2, (bg.height - ch) // 2
            bg = bg.crop((bx, by, bx + cw, by + ch)).filter(ImageFilter.GaussianBlur(40))
            bg = Image.eval(bg, lambda v: int(v * 0.45))
            fw = round(cw * 0.90); fh = round(h * fw / w)
            if fh > ch * 0.62: fh = round(ch * 0.62); fw = round(w * fh / h)
            ph = im.resize((fw, fh), Image.LANCZOS); b = 18 * SS
            fr = Image.new("RGB", (fw + 2 * b, fh + 2 * b), (236, 230, 216)); fr.paste(ph, (b, b))
            bg.paste(fr, ((cw - fr.width) // 2, round(ch * 0.40 - fr.height / 2)))
            im = bg
        else:
            w, h = im.size; s = max(W * SS / w, H * SS / h) * zoom
            im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
        p = f"{self.out}/pre_{name}.jpg"; im.save(p, quality=93)
        return p, im.size

    def card_frames(self, shot, dur, out):
        tmp = out[:-4] + ".tmp.mp4"
        proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                 "-vf", "noise=alls=4:allf=t,vignette=angle=PI/5,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                                 "-crf", "16", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        f_t = ImageFont.truetype(FONT, 40); f_l = ImageFont.truetype(FONT, 46); f_b = ImageFont.truetype(FONT, 64)
        f_num = ImageFont.truetype(FONT, 150); f_lab = ImageFont.truetype(FONT, 56)
        for f in range(round(dur * FPS)):
            t = f / FPS
            im = Image.new("RGB", (W, H), INK); d = ImageDraw.Draw(im)
            if shot["kind"] == "bars":
                d.text((W // 2, 520), shot.get("title", "").upper(), font=f_t, fill=(190, 170, 140), anchor="mm")
                vmax = max(r[1] for r in shot["rows"])
                for k, (lab, val, txt) in enumerate(shot["rows"]):
                    y = 680 + k * 260
                    p = min(max((t - 0.15 - k * 0.25) / 0.55, 0), 1); p = 1 - (1 - p) ** 3
                    d.text((130, y), lab.upper(), font=f_l, fill=PAPER, anchor="ls")
                    bw = max(int(820 * val / vmax * p), 6)
                    d.rounded_rectangle([130, y + 25, 130 + bw, y + 115], radius=14, fill=AMBER if k == 0 else PAPER)
                    if p > 0.3: d.text((130 + bw - 20, y + 70), txt, font=f_b if k == 0 else f_l, fill=INK, anchor="rm")
            elif shot["kind"] == "number":
                p = min(t / 0.45, 1); p = 1 - (1 - p) ** 3
                if shot.get("title"): d.text((W // 2, 640), shot["title"].upper(), font=f_t, fill=(190, 170, 140), anchor="mm")
                big = f_num.font_variant(size=int(150 * (0.8 + 0.2 * p)))
                d.text((W // 2, 820), shot["value"], font=big, fill=AMBER, anchor="mm")
                d.text((W // 2, 960), shot.get("label", "").upper(), font=f_lab, fill=PAPER, anchor="mm")
            proc.stdin.write(im.tobytes())
        proc.stdin.close(); proc.wait(); os.replace(tmp, out)


    def is_map(self, key): return key in self.s.get("maps", {})

    def render_kb(self, shot, dur, out):
        """kind kb: zoom/pan inside one image. kind xfade: same move, crossfading images[0] -> images[1].
        from/to = [cx, cy, zw]: centre (0-1 of image) and crop width as a fraction of the image width."""
        keys = shot["images"] if shot["kind"] == "xfade" else [shot["image"]]
        ims = [Image.open(self.img_path(k)).convert("RGB") for k in keys]
        iw, ih = ims[0].size
        ims = [im if im.size == (iw, ih) else im.resize((iw, ih), Image.LANCZOS) for im in ims]
        a, b = shot.get("from", [0.5, 0.5, 1.0]), shot.get("to", [0.5, 0.5, 0.8])
        grade = GRADE_MAP if self.is_map(keys[0]) else GRADE
        tmp = out[:-4] + ".tmp.mp4"
        proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                 "-vf", f"{grade},format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                                 "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        n = round(dur * FPS); at = shot.get("at", 0.5); fade = 0.35
        for f in range(n):
            t = f / FPS; e = 0.5 - 0.5 * math.cos(math.pi * min(t / dur, 1))
            cx, cy, zw = [a[i] + (b[i] - a[i]) * e for i in range(3)]
            cw = zw * iw; ch = cw * H / W
            if ch > ih: ch = ih; cw = ch * W / H
            x0 = min(max(cx * iw - cw / 2, 0), iw - cw); y0 = min(max(cy * ih - ch / 2, 0), ih - ch)
            box = (x0, y0, x0 + cw, y0 + ch)
            fr = ims[0].resize((W, H), Image.BILINEAR, box=box)
            if len(ims) > 1:
                m = min(max((t - at * dur) / fade + 0.5, 0), 1)
                if m > 0: fr = Image.blend(fr, ims[1].resize((W, H), Image.BILINEAR, box=box), m)
            proc.stdin.write(fr.tobytes())
        proc.stdin.close(); proc.wait(); os.replace(tmp, out)

    def scenes(self, only=None):
        times = self.shot_times(); files = []
        for i, (shot, a, b) in enumerate(zip(self.s["shots"], times[:-1], times[1:])):
            out = f"{self.sc}/s{i:02d}.mp4"; files.append(out)
            if only is not None and i not in only: continue
            dur = round(b - a, 3)
            if shot["kind"] in ("bars", "number"):
                self.card_frames(shot, dur, out); print("scene", i, shot["kind"], dur); continue
            if shot["kind"] in ("kb", "xfade"):
                self.render_kb(shot, dur, out); print("scene", i, shot["kind"], shot.get("image") or shot.get("images"), dur); continue
            p, (pw, ph) = self.prescale(shot, f"s{i:02d}")
            X, Y = pw - W * SS, ph - H * SS
            x0, x1 = shot.get("x", [0.3, 0.6]); y0, y1 = shot.get("y", [0.5, 0.5])
            e = f"(0.5-0.5*cos(PI*t/{dur}))"
            vf = (f"crop={W*SS}:{H*SS}:x='{X}*({x0}+({x1}-{x0})*{e})':y='{Y}*({y0}+({y1}-{y0})*{e})',"
                  f"scale={W}:{H}:flags=lanczos,{GRADE},format=yuv420p")
            tmp = out[:-4] + ".tmp.mp4"
            sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", p, "-t", str(dur), "-vf", vf,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp])
            os.replace(tmp, out); print("scene", i, shot["image"], dur)
        open(f"{self.sc}/list.txt", "w").write("".join(f"file '{p}'\n" for p in files))
        sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{self.sc}/list.txt", "-c", "copy", f"{self.out}/video_noaudio.mp4"])
        self.times = times

    # ---------- captions ----------
    def ass(self):
        times = self.shot_times()
        card_spans = [(a, b) for sh_, a, b in zip(self.s["shots"], times[:-1], times[1:]) if sh_["kind"] in ("bars", "number")]
        ts = lambda t: f"{int(t//3600)}:{int(t%3600//60):02d}:{max(t,0)%60:05.2f}"
        chunks, cur = [], []
        for k, (s, e, w) in enumerate(self.words):
            cur.append((s, e, w))
            nxt = self.words[k + 1][0] if k + 1 < len(self.words) else None
            if len(cur) == 3 or nxt is None or nxt - e > 0.18 or len(" ".join(x[2] for x in cur)) > 15:
                chunks.append(cur); cur = []
        ev = []
        for ci, ch in enumerate(chunks):
            last = ci == len(chunks) - 1
            cend = self.end if last else min(chunks[ci + 1][0][0], ch[-1][1] + 0.35)
            for wi, (s, e, w) in enumerate(ch):
                en = ch[wi + 1][0] if wi + 1 < len(ch) else cend
                txt = " ".join((r"{\c&H0000B4FF&}" + ww.upper() + r"{\c&H00FFFFFF&}") if wj == wi else ww.upper() for wj, (_, _, ww) in enumerate(ch))
                if not any(a <= s < b for a, b in card_spans): ev.append((s, en, txt))
        head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins,94,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,7,4,5,90,90,0,1
Style: Tag,Poppins,60,&H00E8F0F5,&H00FFFFFF,&H64000000,&H64000000,1,0,0,0,100,100,4,0,3,16,0,8,80,80,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = [f"Dialogue: 1,{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\pos(540,1330)}}{t}" for s, e, t in ev]
        if self.s.get("tag"):
            lines.append(f"Dialogue: 0,{ts(0)},{ts(3.0)},Tag,,0,0,0,,{{\\fad(0,250)}}{self.s['tag']}")
        open(f"{self.out}/captions.ass", "w").write(head + "\n".join(lines) + "\n")

    # ---------- music ----------
    def music(self):
        sr = 48000; n = int(self.end * sr); t = np.arange(n) / sr
        root = self.s.get("music_root", 73.42)
        pad = np.zeros(n)
        for mul, a in [(1, 0.5), (1.5, 0.35), (2, 0.25), (2.378, 0.18)]:
            for hm, ha in [(1, 1), (2, 0.35), (3, 0.15)]:
                pad += a * ha * np.sin(2 * np.pi * root * mul * hm * t + hm)
        pad *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t) ** 2
        rng = np.random.default_rng(1)
        noise = np.convolve(rng.standard_normal(n), np.ones(400) / 400, mode="same") * 0.6
        cl = int(0.03 * sr); click = np.exp(-np.arange(cl) / (0.004 * sr)) * np.sin(2 * np.pi * 2200 * np.arange(cl) / sr)
        tick = np.zeros(n)
        for k in range(int(self.end / 0.5)):
            s0 = int(k * 0.5 * sr); m = max(0, min(cl, n - s0)); tick[s0:s0 + m] += (0.5 if k % 2 == 0 else 0.3) * click[:m]
        bl = int(1.6 * sr); bt = np.arange(bl) / sr; bshape = np.sin(2 * np.pi * (55 - 20 * bt) * bt) * np.exp(-bt * 2.5)
        boom = np.zeros(n)
        hits = [0.0, self.groups[0][-1][0]] + [self.groups[l][0][0] for l in self.s.get("boom_lines", [])]
        for at in hits:
            s0 = int(at * sr); m = min(bl, n - s0); boom[s0:s0 + m] += 1.6 * bshape[:m]
        mix = 0.22 * pad / np.max(np.abs(pad)) + 0.05 * noise + 0.10 * tick + 0.5 * boom
        mix *= np.clip(t / 0.05, 0, 1) * np.clip((self.end - t) / 0.4, 0, 1)
        with wave.open(f"{self.out}/music.wav", "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes((np.clip(mix, -1, 1) * 32767 * 0.8).astype(np.int16).tobytes())

    # ---------- output ----------
    def preview(self):
        self.scenes(); self.ass()
        times = self.times; frames = []
        for i, (a, b) in enumerate(zip(times[:-1], times[1:])):
            t = round((a + b) / 2, 2); p = f"{self.out}/pv_{i:02d}.png"
            sh(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", f"{self.out}/video_noaudio.mp4", "-frames:v", "1", "-copyts",
                "-vf", f"ass={self.out}/captions.ass:fontsdir={FONTDIR}", p]); frames.append(p)
        tw, th = 270, 480; cols = min(len(frames), 6); rows = math.ceil(len(frames) / cols)
        sheet = Image.new("RGB", (cols * (tw + 8), rows * (th + 8)), "black")
        for k, p in enumerate(frames): sheet.paste(Image.open(p).resize((tw, th)), ((k % cols) * (tw + 8), (k // cols) * (th + 8)))
        sheet.save(f"{self.out}/preview_sheet.jpg", quality=85)
        print("preview:", f"{self.out}/preview_sheet.jpg", "shot times:", times)

    def final(self):
        self.timing(); self.ass(); self.music()
        end = self.end; tmp = f"{self.out}/short.tmp.mp4"
        fc = (f"[0:v]ass={self.out}/captions.ass:fontsdir={FONTDIR}[v];"
              f"[1:a]aresample=48000,apad,atrim=0:{end}[vo];[2:a]aresample=48000,atrim=0:{end},volume=0.27[mu];"
              f"[vo][mu]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        sh(["ffmpeg", "-v", "error", "-y", "-i", f"{self.out}/video_noaudio.mp4", "-i", f"{self.out}/vo.wav", "-i", f"{self.out}/music.wav",
            "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", str(end),
            "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", tmp])
        os.replace(tmp, f"{self.out}/short.mp4")
        print("final:", f"{self.out}/short.mp4", round(os.path.getsize(f"{self.out}/short.mp4") / 1e6, 1), "MB", end, "s")

if __name__ == "__main__":
    st = Story(sys.argv[1]); step = sys.argv[2]
    if step == "voice": st.voice()
    elif step == "preview": st.preview()
    elif step == "scenes": st.scenes([int(x) for x in sys.argv[3].split(",")]); st.ass()
    elif step == "final": st.final()
