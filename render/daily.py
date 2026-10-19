"""Täglicher Ablauf, damit die Routine möglichst wenig selbst tun muss.

  python3 render/daily.py next            -> zeigt Story-Datei, Teil und Sprechtext (für die Stimme)
  python3 render/daily.py build VOICE.mp3 -> rendert, prüft, committet, pusht; gibt JSON für Metricool aus
  python3 render/daily.py build --piper   -> wie oben, aber mit der lokalen Piper-Stimme (Notfall)
"""
import datetime, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "render"))


def load():
    st = json.load(open("state.json"))
    story = json.load(open(st["story"]))
    part = next((p for p in story["parts"] if p["part"] == st["next_part"]), None)
    return st, story, part


def sh(*cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw).stdout


def cmd_next():
    st, story, part = load()
    if part is None:
        print(json.dumps({"status": "MISSING_PART", "story": st["story"], "next_part": st["next_part"],
                          "plan": story.get("plan"), "next_series_idea": story.get("next_series_idea")},
                         ensure_ascii=False, indent=1))
        return
    script = "\n\n".join(((s.get("tag", "") + " ") if s.get("tag") else "") + s.get("say", s["text"]) for s in part["shots"])
    print(json.dumps({"status": "OK", "story": st["story"], "part": part["part"], "voice_elevenlabs": part.get("voice", "NBqeXKdZHweef6y0B67V"),
                      "voice_vidiq": part.get("voice_vidiq", "JBFqnCBsd6RMkjVDRZzb"),
                      "voice_model": part.get("voice_model", "eleven_v4"),
                      "script_plain": "\n\n".join(s.get("say", s["text"]) for s in part["shots"]),
                      "chars": len(script), "script": script}, ensure_ascii=False, indent=1))


def cmd_build(voice):
    import make_short
    st, story, part = load()
    today = datetime.date.today().isoformat()
    slug = story["series"]
    out = f"videos/{today}-{slug}-{part['part']}.mp4"
    os.makedirs("videos", exist_ok=True)
    # Story-Datei temporär mit Stimme versehen
    if voice != "--piper":
        part["voice_file"] = os.path.abspath(voice)
    tmp_story = "/tmp/_story.json"
    json.dump(story, open(tmp_story, "w"), ensure_ascii=False)
    info = make_short.render(tmp_story, part["part"], out, st.get("used_photos", []))
    json.dump(info, open(out + ".json", "w"), indent=1, ensure_ascii=False)
    # Kontaktbogen zur Sichtprüfung
    sheet = f"/tmp/sheet-{today}.jpg"
    sh("ffmpeg", "-loglevel", "error", "-y", "-i", out, "-vf", "fps=1/3.5,scale=270:480,tile=6x3",
       "-frames:v", "1", sheet)
    size = os.path.getsize(out)
    if size > 95_000_000:
        sys.exit(f"Video zu groß: {size} Bytes")
    # Zustand fortschreiben
    st["used_photos"] = sorted(set(st.get("used_photos", [])) | set(info["used"]))
    last = max([h.get("publish", h["date"]) for h in st["history"]] or [today])
    publish = max(datetime.date.fromisoformat(today),
                  datetime.date.fromisoformat(last) + datetime.timedelta(days=2)).isoformat()
    st["history"].append({"date": today, "publish": publish, "story": st["story"], "part": part["part"], "file": out})
    st["next_part"] = part["part"] + 1
    json.dump(st, open("state.json", "w"), indent=1, ensure_ascii=False)
    # Alte Videos (älter als 14 Tage) aus dem Repo nehmen, damit es klein bleibt
    for f in sorted(os.listdir("videos")):
        if f.endswith(".mp4") and f[:10] < (datetime.date.today() - datetime.timedelta(days=14)).isoformat():
            sh("git", "rm", "-q", f"videos/{f}")
            if os.path.exists(f"videos/{f}.json"):
                sh("git", "rm", "-q", f"videos/{f}.json")
    sh("git", "add", "-A")
    sh("git", "-c", "user.name=Rabetv", "-c", "user.email=raschke.fab@gmail.com", "commit", "-qm",
       f"Short {today}: {slug} Teil {part['part']}")
    sh("git", "push", "-q", "origin", "HEAD:main")
    sha = sh("git", "rev-parse", "HEAD").strip()
    url = f"https://raw.githubusercontent.com/Rabetv/rubic-shorts/{sha}/{out}"
    print(json.dumps({"status": "OK", "url": url, "publish_at": f"{publish}T19:00:00+03:00", "sheet": sheet, "duration": round(info["duration"], 1),
                      "yt_title": part["yt_title"], "description": part["description"], "tags": part["tags"],
                      "last_part_of_series": part["part"] == max(p["part"] for p in story["parts"])},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "next":
        cmd_next()
    elif sys.argv[1] == "build":
        cmd_build(sys.argv[2])
