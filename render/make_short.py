"""Rendert einen YouTube Short (1080x1920, 30 fps) aus einer Story-Teil-Definition.

Aufruf:  python3 make_short.py stories/<serie>.json <teil> out.mp4 [--used state.json]
"""
import json, math, os, re, subprocess, sys, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import fetch

W, H, FPS = 1080, 1920, 30
SC = 1.5                                   # Supersampling der Basisbilder
BW, BH = int(W * SC), int(H * SC)
GOLD = (236, 203, 128)
WHITE = (255, 255, 255)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "assets", "Gelasio.ttf")   # metrisch kompatibel zu Georgia
VOICE = os.path.expanduser(os.environ.get("PIPER_VOICE", "~/rubic-cache/voice/de_DE-thorsten-high.onnx"))

# Safe Zone: kein Text in unteren 20 % und rechten 12 %; Textblöcke zwischen y=250 und 1400
TX0, TXMAX_W = 90, 860
TY_MIN, TY_MAX = 250, 1400
assert TX0 + TXMAX_W <= int(W * 0.88) + 1


def font(size):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name("Regular")
    except Exception:
        pass
    return f


# ---------------------------------------------------------------- Grading
def grade(img):
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    a = lum[..., None] + 0.9 * (a - lum[..., None])            # Sättigung 0,9
    a = np.clip(a, 0, 1)
    s = a * a * (3 - 2 * a)
    a = a + 0.22 * (s - a)                                       # leichte S-Kurve
    a[..., 0] *= 1.03                                            # warm
    a[..., 2] *= 0.95
    m = float((a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)).mean())
    if m > 0.28:                                                 # helle Bilder abdunkeln 0,8 … 0,55
        f = float(np.interp(m, [0.28, 0.6], [0.8, 0.55]))
        a *= f
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def cover(img, fx=0.5, fy=0.5):
    iw, ih = img.size
    s = max(BW / iw, BH / ih)
    nw, nh = math.ceil(iw * s), math.ceil(ih * s)
    img = img.resize((nw, nh), Image.LANCZOS)
    x = int((nw - BW) * fx)
    y = int((nh - BH) * fy)
    return img.crop((x, y, x + BW, y + BH))


def vignette():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    v = 1 - 0.40 * np.clip((r - 0.25) / 0.75, 0, 1) ** 1.6     # ~40 % in den Ecken
    return v[..., None]


def grains(n=10, seed=7):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        g = rng.normal(0, 0.03 * 255, (H // 2, W // 2)).astype(np.float32)
        g = np.repeat(np.repeat(g, 2, 0), 2, 1)                  # 2-px-Körnung
        out.append(g[..., None])
    return out


# ---------------------------------------------------------------- Skizze (blaue Linien)
def sketch_volcano():
    rng = np.random.default_rng(3)
    bg = np.zeros((BH, BW, 3), np.float32)
    bg[...] = (14, 20, 34)
    bg += rng.normal(0, 4, (BH, BW, 1))
    img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    blue = (110, 168, 255)

    def wob(pts, amp=3):
        return [(x + rng.normal(0, amp), y + rng.normal(0, amp)) for x, y in pts]

    sea_y, bed_y = int(BH * 0.52), int(BH * 0.80)
    for k in range(3):                                            # Meeresoberfläche
        pts = [(x, sea_y + 10 * math.sin(x / 70 + k) + k * 22) for x in range(0, BW + 20, 20)]
        d.line(wob(pts, 1.5), fill=blue if k == 0 else (70, 110, 180), width=5 if k == 0 else 3)
    pts = [(x, bed_y + 25 * math.sin(x / 210)) for x in range(0, BW + 20, 20)]
    d.line(wob(pts), fill=blue, width=5)                          # Meeresboden
    cx = BW * 0.50                                                # Vulkankegel
    cone = [(cx - 520, bed_y + 10), (cx - 110, bed_y - 300), (cx + 110, bed_y - 300), (cx + 520, bed_y + 10)]
    d.line(wob(cone, 2), fill=blue, width=5)
    for i in range(7):                                            # aufsteigende Dampffahne
        x0 = cx - 60 + i * 20
        pts = [(x0 + 40 * math.sin(t / 60 + i), bed_y - 300 - t) for t in range(0, 1300, 25)]
        d.line(wob(pts, 2), fill=(90, 140, 230), width=3)
    ax = BW * 0.80                                                # Maßpfeil 130 m
    d.line([(ax, sea_y), (ax, bed_y - 20)], fill=blue, width=4)
    for yy, dirn in ((sea_y, 1), (bed_y - 20, -1)):
        d.line([(ax - 22, yy + 30 * dirn), (ax, yy), (ax + 22, yy + 30 * dirn)], fill=blue, width=4)
    f = font(84)
    d.text((ax - 160, (sea_y + bed_y) / 2 - 40), "130 m", font=f, fill=blue)
    return img.filter(ImageFilter.GaussianBlur(0.6))


# ---------------------------------------------------------------- Text
def norm(w):
    return re.sub(r"[^\wäöüÄÖÜß]", "", w).lower()


def wrap(words, f, maxw):
    lines, cur = [], []
    for w in words:
        t = " ".join(cur + [w])
        if cur and f.getlength(t) > maxw:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def text_layers(text, key, sub, size):
    """Gibt (Hauptlayer, Nebenlayer) als RGBA zurück, inkl. weichem Schatten."""
    keyset = {norm(k) for k in (key or "").split()}
    words = text.split()
    size = max(96, min(160, size))
    while True:
        f = font(size)
        lines = wrap(words, f, TXMAX_W)
        widest = max(f.getlength(" ".join(l)) for l in lines)
        if (widest <= TXMAX_W and len(lines) <= 4) or size <= 60:
            break
        size -= 4                                                 # zu breit → automatisch kleiner
    lh = int(size * 1.18)
    sub_size = 52
    fs = font(sub_size)
    sub_lines = wrap(sub.split(), fs, TXMAX_W) if sub else []
    sub_h = (len(sub_lines) * int(sub_size * 1.3) + 34) if sub_lines else 0
    block_h = len(lines) * lh + sub_h
    top = int(860 - block_h / 2)
    top = max(TY_MIN, min(top, TY_MAX - block_h))

    def layer(draw_fn):
        mask = Image.new("L", (W, H), 0)
        col = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(mask), ImageDraw.Draw(col))
        sh = mask.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.8))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow.putalpha(sh)
        shadow = shadow.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -5))
        return Image.alpha_composite(shadow, col)

    def main(dm, dc):
        y = top
        for l in lines:
            x = TX0
            for i, w in enumerate(l):
                token = w + (" " if i < len(l) - 1 else "")
                c = GOLD if norm(w) in keyset and norm(w) else WHITE
                dm.text((x, y), w, font=f, fill=255)
                dc.text((x, y), w, font=f, fill=c + (255,))
                x += f.getlength(token)
            y += lh

    def subl(dm, dc):
        y = top + len(lines) * lh + 34
        for l in sub_lines:
            t = " ".join(l)
            dm.text((TX0, y), t, font=fs, fill=230)
            dc.text((TX0, y), t, font=fs, fill=(255, 255, 255, 225))
            y += int(sub_size * 1.3)

    return layer(main), (layer(subl) if sub_lines else None)


def ease_out(t):
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------- Audio
def synth_voice(text, out):
    subprocess.run(["piper", "-m", VOICE, "--length-scale", "1.07", "--output_file", out],
                   input=text.encode(), check=True, capture_output=True)
    with wave.open(out) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    thr = 0.02 * np.abs(a).max()
    nz = np.nonzero(np.abs(a) > thr)[0]
    a = a[max(0, nz[0] - int(0.01 * sr)): nz[-1] + int(0.06 * sr)]      # Stille abschneiden
    return a, sr


def ambient(dur, sr=44100, seed=1):
    t = np.arange(int(dur * sr)) / sr
    rng = np.random.default_rng(seed)
    out = np.zeros_like(t)
    for f, amp in ((55.0, 0.30), (82.4, 0.22), (110.0, 0.18), (130.8, 0.10), (164.8, 0.08)):
        for det in (-0.25, 0.25):
            lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.05 + rng.random() * 0.05) * t + rng.random() * 6)
            out += amp * lfo * np.sin(2 * np.pi * (f + det) * t + rng.random() * 6)
    noise = rng.normal(0, 1, len(t))
    k = int(sr * 0.004)                                           # weiches Rauschen („Wind“)
    noise = np.convolve(noise, np.ones(k) / k, mode="same")
    wind = noise * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t))
    out = out / np.abs(out).max() * 0.6 + wind / (np.abs(wind).max() + 1e-9) * 0.25
    fade = int(0.6 * sr)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


# ---------------------------------------------------------------- Hauptprogramm
def render(story_path, part_no, out_mp4, used_ids=None):
    story = json.load(open(story_path))
    part = next(p for p in story["parts"] if p["part"] == part_no)
    shots = part["shots"]
    used = set(used_ids or [])
    tmp = tempfile.mkdtemp(prefix="short_")
    credits, bases = [], []

    # Bilder
    for i, s in enumerate(shots):
        img = s["img"]
        if "same_as" in img:
            bases.append(bases[img["same_as"]])
            continue
        if "sketch" in img:
            bases.append(grade(sketch_volcano()))
            continue
        path, meta = fetch.fetch(img, used)
        used.add(meta["id"])
        credits.append(meta)
        src = Image.open(path)
        bases.append(grade(cover(src, img.get("fx", 0.5), img.get("fy", 0.5))))
        print(f"[{i+1}/{len(shots)}] {meta['source']} {meta['id']}", flush=True)

    # Sprecher und Timing (Schnitt jeweils auf den ersten Wortanfang)
    sr_v, clips, starts, durs = None, [], [], []
    t = 0.0
    for i, s in enumerate(shots):
        a, sr_v = synth_voice(s.get("say", s["text"]), os.path.join(tmp, f"v{i}.wav"))
        lead = s.get("lead", 0.35 if i == 0 else 0.0)
        d = lead + len(a) / sr_v + s.get("pause", 0.45)
        d = max(d, s.get("min", 1.6))
        clips.append((t + lead, a))
        starts.append(t)
        durs.append(d)
        t += d
    total = t
    nframes = int(round(total * FPS))

    # Audio-Mix
    sr = 44100
    voice = np.zeros(int(total * sr) + sr)
    for st, a in clips:
        a = np.interp(np.arange(0, len(a), sr_v / sr), np.arange(len(a)), a) / 32768.0
        i0 = int(st * sr)
        voice[i0:i0 + len(a)] += a[: len(voice) - i0]
    bed = ambient(total, sr)
    mix = voice[: len(bed)] * 0.9 + bed * 0.09
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.9
    wav = os.path.join(tmp, "mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    wav_n = os.path.join(tmp, "mix_n.wav")                       # Lautheit fuer Shorts: -14 LUFS
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100", wav_n], check=True)
    wav = wav_n

    # Text-Layer vorbereiten
    layers = [text_layers(s["text"], s.get("key"), s.get("sub"), s.get("size", 120)) for s in shots]
    vig = vignette()
    gr = grains()

    def motion(s, u):
        m = s.get("motion", "push")
        a = s.get("amount", 0.05)
        z, ox, oy, rot = 1.0, 0.0, 0.0, 0.0
        if m == "push":
            z = 1.0 + a * u
        elif m == "pull":
            z = 1.0 + a * (1 - u)
        elif m in ("pan_l", "pan_r", "pan_u", "pan_d"):
            z = 1.0 + a + 0.01
            sgn = 1 if m in ("pan_r", "pan_d") else -1
            v = sgn * a * 0.45 * (u - 0.5) * 2
            ox, oy = (v, 0) if m in ("pan_l", "pan_r") else (0, v)
        elif m == "rot":
            z = 1.04 + a * u
            rot = s.get("deg", 0.8) * (u - 0.5)
        return z, ox, oy, rot

    def frame_img(i, tl):
        s = shots[i]
        u = min(max(tl / durs[i], 0), 1.1)
        z, ox, oy, rot = motion(s, u)
        k = SC / z
        c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        a_, b_ = k * c, -k * sn
        d_, e_ = k * sn, k * c
        cbx, cby = BW / 2 + ox * BW, BH / 2 + oy * BH
        data = (a_, b_, cbx - a_ * W / 2 - b_ * H / 2, d_, e_, cby - d_ * W / 2 - e_ * H / 2)
        return bases[i].transform((W, H), Image.AFFINE, data, resample=Image.BICUBIC)

    def text_on(img, i, tl):
        main, sub = layers[i]
        s = shots[i]
        fade_out = 1.0
        if s.get("text_out"):                                    # Text vor Ende ausblenden (letzter Shot)
            te = durs[i] - s["text_out"]
            fade_out = 1 - min(max((tl - te + 0.4) / 0.4, 0), 1)
        t0 = s.get("text_in", 0.0 if i else 0.25)
        for lay, delay in ((main, 0.0), (sub, 0.15)):
            if lay is None:
                continue
            p = min(max((tl - t0 - delay) / 0.2, 0), 1)          # 0,2 s Einblenden
            al = ease_out(p) * fade_out
            if al <= 0:
                continue
            dy = int(round(14 * (1 - ease_out(p))))               # 14 px Aufwärtsbewegung
            l = lay if dy == 0 else lay.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -dy))
            if al < 1:
                l = l.copy()
                l.putalpha(l.getchannel("A").point(lambda v: int(v * al)))
            img = Image.alpha_composite(img, l)
        return img

    XF = 7                                                        # Crossfade 7 Frames (nur ruhige Stellen)
    ff = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
         "-c:v", "libx264", "-preset", "medium", "-b:v", "6M", "-maxrate", "8M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-t", f"{nframes / FPS:.4f}", "-movflags", "+faststart", out_mp4],
        stdin=subprocess.PIPE)
    shot_frames = [int(round(st * FPS)) for st in starts] + [nframes]
    for fi in range(nframes):
        tt = fi / FPS
        i = max(j for j in range(len(shots)) if shot_frames[j] <= fi)
        tl = tt - starts[i]
        img = frame_img(i, tl).convert("RGBA")
        if fi == nframes - 1 and shots[-1]["img"].get("same_as") == 0:
            img = frame_img(0, 0).convert("RGBA")                 # letzter Frame = erster Frame
        fl = fi - shot_frames[i]
        if i > 0 and shots[i].get("xfade") and fl < XF:
            prev = frame_img(i - 1, tt - starts[i - 1]).convert("RGBA")
            prev = text_on(prev, i - 1, tt - starts[i - 1])
            img = Image.blend(prev, img, (fl + 1) / (XF + 1))
        arr = np.asarray(img.convert("RGB"), np.float32) * vig
        arr = np.asarray(text_on(Image.fromarray(arr.astype(np.uint8)).convert("RGBA"), i, tl).convert("RGB"),
                         np.float32)
        g = gr[0] if fi in (0, nframes - 1) else gr[fi % len(gr)]   # 10 wechselnde Kornmuster
        arr = np.clip(arr + g, 0, 255).astype(np.uint8)
        ff.stdin.write(arr.tobytes())
        if fi % 150 == 0:
            print(f"frame {fi}/{nframes}", flush=True)
    ff.stdin.close()
    ff.wait()
    return {"duration": total, "credits": credits, "used": sorted(used)}


if __name__ == "__main__":
    story, part, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    used = []
    if "--used" in sys.argv:
        p = sys.argv[sys.argv.index("--used") + 1]
        if os.path.exists(p):
            used = json.load(open(p)).get("used_photos", [])
    info = render(story, part, out, used)
    json.dump(info, open(out + ".json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"duration": info["duration"], "n_credits": len(info["credits"])}))
