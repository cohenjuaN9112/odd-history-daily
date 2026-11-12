# One TTS clip per line, trimmed and joined with a fixed gap; writes out.wav and out.wav.words.json
import sys, ssl, asyncio, json, subprocess, os
import edge_tts, edge_tts.communicate as c
import os as _os
_ca = _os.environ.get("SSL_CERT_FILE") or ("/root/.ccr/ca-bundle.crt" if _os.path.exists("/root/.ccr/ca-bundle.crt") else None)
if _ca: c._SSL_CTX = ssl.create_default_context(cafile=_ca)
lines = [l.strip() for l in open(sys.argv[1]) if l.strip()]
voice, out, rate = sys.argv[2], sys.argv[3], sys.argv[4]
gap = float(sys.argv[5]) if len(sys.argv) > 5 else 0.22
tmp = os.path.abspath(out) + "_parts"; os.makedirs(tmp, exist_ok=True)
async def one(i, text):
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    marks = []
    with open(f"{tmp}/{i}.mp3", "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary": marks.append((ch["offset"]/1e7, (ch["offset"]+ch["duration"])/1e7, ch["text"]))
    return marks
words, t, parts = [], 0.0, []
for i, l in enumerate(lines):
    m = asyncio.run(one(i, l))
    a = max(m[0][0] - 0.04, 0); b = m[-1][1] + 0.12
    subprocess.run(["ffmpeg","-v","error","-y","-i",f"{tmp}/{i}.mp3","-ss",f"{a:.3f}","-to",f"{b:.3f}","-ar","48000","-ac","1",f"{tmp}/{i}.wav"], check=True)
    d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f"{tmp}/{i}.wav"]).decode())
    for s, e, w in m: words.append((round(t + s - a, 3), round(t + e - a, 3), w, i))
    parts.append(f"{tmp}/{i}.wav"); t += d
    if i < len(lines) - 1:
        subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",f"anullsrc=r=48000:cl=mono","-t",str(gap),f"{tmp}/g{i}.wav"], check=True)
        parts.append(f"{tmp}/g{i}.wav"); t += gap
open(f"{tmp}/list.txt","w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",f"{tmp}/list.txt","-c","pcm_s16le",out], check=True)
json.dump(words, open(out + ".words.json","w"))
print("total", round(t, 2), "words", len(words))
