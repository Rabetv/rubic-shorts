# Rubic Shorts – tägliche Routine

Jeden Tag entsteht **ein** deutscher YouTube Short (Teil einer mehrteiligen Story) und wird über
Metricool auf dem Kanal **Rubic (@rubic.shorts)** eingeplant.

## Regeln für den Inhalt
- Spannende, **wahre** Geschichten (Natur, Geschichte, Kosmos, Elemente Feuer/Wasser/Erde/Wind), Serien mit 4–6 Teilen.
- **Keine Werbung** in den Videos: kein Shop, kein Logo, kein „Euer Nikki“, keine Produkte. Der Link zu nikki-stones.com steht nur in der Kanal-Bio.
- Jede Tatsache vor dem Schreiben mit einer Websuche prüfen; Quellen in `sources` der Story-Datei eintragen. Lieber vage formulieren als falsch.
- Pro Bild **ein Gedanke**, 12–16 Shots, 40–55 s. Schlüsselwort pro Shot in `key` (wird gold).
- Erster Shot und letzter Shot nutzen dasselbe Milchstraßen-Foto (`"same_as": 0`, letzter Shot `"motion": "pull"`, `"text_out": 0.5`) → Loop.
- Letzter Text immer: „Bis dann.“ Vorletzter Shot macht neugierig auf den nächsten Teil (oder auf die nächste Serie, wenn es der letzte Teil war).
- Zahlen im Feld `say` ausschreiben (z. B. „neunzehnhundertdreiundsechzig“), damit der Sprecher sie richtig liest.
- Fotos nur von Unsplash (`{"unsplash": "englische Suchbegriffe"}`) oder NASA (`{"nasa": "..."}`); Suchbegriffe so wählen, dass keine Menschen, Städte oder Boote im Bild sind, wenn sie nicht passen. `{"sketch": "volcano"}` erzeugt eine blaue Linienskizze.
- Bewegungen: `push`, `pull`, `pan_l`, `pan_r`, `pan_u`, `pan_d`, `rot` mit `amount` 0.03–0.08. `"xfade": true` nur an ruhigen Stellen.

## Ablauf (für die geplante Sitzung)
1. Repo `Rabetv/rubic-shorts` anhängen und klonen. `state.json` lesen: aktuelle Serie und nächster Teil.
2. Falls der nächste Teil in der Story-Datei noch fehlt: Fakten recherchieren, Teil schreiben (Format wie Teil 1 in `stories/01-surtsey.json`).
   Ist die Serie fertig, eine neue Serie `stories/NN-<slug>.json` mit Plan anlegen und mit Teil 1 beginnen.
3. Setup: `pip install --break-system-packages -q piper-tts`; Stimme laden nach `~/rubic-cache/voice/`:
   `https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx` (+ `.onnx.json`). Lizenz: CC0.
   Unsplash-Schlüssel steht im Prompt der Routine → `export UNSPLASH_KEY=...`.
4. Rendern (dauert ~8–10 min, im Hintergrund starten):
   `python3 render/make_short.py stories/<datei>.json <teil> videos/<YYYY-MM-DD>-<slug>-<teil>.mp4 --used state.json`
5. Prüfen: Kontaktbogen (`ffmpeg -vf "fps=1/2.5,scale=270:480,tile=6x3"`) ansehen. Unpassende Fotos (Menschen, Städte, Boote, Text) → Suchbegriff ändern, neu rendern.
6. `state.json` aktualisieren (`used_photos` ← `used` aus der `.mp4.json`, nächster Teil), Video + JSON committen und pushen.
7. Öffentliche URL: `https://raw.githubusercontent.com/Rabetv/rubic-shorts/main/videos/<datei>.mp4`
8. Metricool (`blogId` 7525052, Zeitzone Asia/Nicosia): `createScheduledPost` für heute 19:00 Asia/Nicosia (= 18:00 deutsche Zeit, ganzjährig 1 h Unterschied),
   providers `[{"network":"youtube"}]`, `youtubeData`: `{"title": yt_title, "type": "short", "privacy": "public", "madeForKids": false, "tags": tags, "category": "EDUCATION"}`,
   `text` = description, `media` = [URL], `autoPublish`: true.
9. Kurze Nachricht an den Nutzer: Titel, geplante Zeit, Link zum Video.
