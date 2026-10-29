# Rubic Shorts – Routine alle 2 Tage (sparsam!)

Kanal: **Rubic (@rubic.shorts)**, Thema **Steine und die vier Elemente** (Feuer, Wasser, Erde, Wind).
Jeden zweiten Tag ein deutscher Short (Teil einer Serie), eingeplant über Metricool für 18:00 deutsche Zeit.
Keine Werbung im Video (kein Shop, kein Logo, kein Produkt). Der Shop-Link steht nur in der Kanal-Bio.

## Ablauf – wenige Schritte, kurze Ausgaben
1. Repo `Rabetv/rubic-shorts` anhängen (add_repo, push) und klonen. Setup in EINEM Bash-Aufruf:
   `pip install --break-system-packages -q piper-tts faster-whisper; mkdir -p ~/rubic-cache/voice && cd ~/rubic-cache/voice && for e in onnx onnx.json; do [ -f de_DE-thorsten-high.$e ] || curl -sSL -o de_DE-thorsten-high.$e https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/high/de_DE-thorsten-high.$e; done`
1b. **Analytics (jeder Lauf):** `vidiq_user_videos` (channelId `UC3OXnEqXsoapzesJ3LQCwxA`, limit 10, privacyStatus [public], videoType [short]; 5 Credits). Zahlen der Rubic-Shorts (ab Okt. 2026, alte englische Videos ignorieren) als Zeile in `ANALYTICS.md` unter „Verlauf“ ergänzen (Datum, Teil, Aufrufe, Likes, Kommentare, Länge). Nur Videos ≥ 2 Tage alt bewerten. Wenn sich ein klares Muster zeigt, die „Erkenntnisse“ in `ANALYTICS.md` kurz anpassen. Beim Schreiben neuer Teile die Erkenntnisse aus `ANALYTICS.md` anwenden (Titel-Stil, Länge, Hook, Kommentar-Frage). Mit dem nächsten Commit pushen.
2. `python3 render/daily.py next`
   - `MISSING_PART`: nur dann den nächsten Teil schreiben (siehe „Neue Teile“), committen, dann erneut `next`.
3. Stimme (in dieser Reihenfolge, Text = `script`):
   a) ElevenLabs-Connector: `creative_generate_speech` mit prompt = `script` (enthält Emotions-Tags), model_id = `voice_model` (eleven_v4), voice_id = `voice_elevenlabs`, **generations_count 1**. Mit `creative_get_flow_run_status` (alle 30 s) warten, bis fertig; die Audio-URL der Generation nach `/tmp/voice.mp3` laden (curl). Nicht doppelt starten. Bei Fehler (Limit/Kontingent/429) → b).
   b) vidIQ: `vidiq_balance`; wenn ≥ 15 Credits: `vidiq_voiceover_generate` (script = `script_plain` ohne Tags, voiceId = `voice_vidiq`), `vidiq_job_poll` bis fertig, MP3 nach `/tmp/voice.mp3`.
   c) Sonst: `build --piper` (Ersatzstimme) und das im Bericht sagen.
4. Rendern im Hintergrund (8–12 min): `python3 render/daily.py build /tmp/voice.mp3` – bei vidIQ-Stimme zusätzlich `--tempo 0.88` (langsamer), bei Piper `build --piper`. Auf Ende warten.
5. Kontaktbogen (`sheet` im Ergebnis) EINMAL ansehen. Nur bei klar falschen Bildern (Menschen, Städte, Text, Boote ohne Bezug): Suchbegriff in der Story ändern, `git reset --hard HEAD~1`, erneut bauen.
6. Metricool `createScheduledPost`: blogId 7525052, date = `publish_at` aus dem Ergebnis (19:00 Asia/Nicosia = 18:00 deutsche Zeit),
   info: autoPublish true, media [url], providers [{"network":"youtube"}], publicationDate {dateTime, timezone "Asia/Nicosia"},
   text = description, youtubeData {title: yt_title, type "short", privacy "public", tags, category "EDUCATION", madeForKids false, isAiGeneratedContent false}.
7. Bericht an den Nutzer (Deutsch, max. 3 Zeilen): Titel, geplante Zeit, welche Stimme, kurz die wichtigste Analytics-Erkenntnis.

## Neue Teile / neue Serie schreiben
- Fakten vorher per Websuche prüfen, Quellen in `sources`. Lieber vage als falsch.
- Serien mit 4–6 Teilen über Steine (Meteoriten, berühmte Steine, Kristalle, Vulkane, Gestein) oder die vier Elemente. Idee für die nächste Serie steht in `next_series_idea`.
  Neue Serie: `stories/NN-<slug>.json` im Format von `stories/01-surtsey.json`, in `state.json` `story` umstellen und `next_part` auf 1.
- **Spannung:** Hook im ersten Satz (Rätsel/Behauptung), falsche Fährte, kurze Schläge, Auflösung, Cliffhanger auf den nächsten Teil (der kommt „übermorgen“, nie „morgen“ schreiben). `"hit": true` auf Wendepunkte, `"riser": true` vor einer Enthüllung.
- **Ruhiges Tempo:** 12–14 Shots, pro Shot ein kurzer Gedanke, `say` höchstens 1–2 kurze Sätze; gesamt 650–850 Zeichen.
- Erster Shot = das stärkste, sofort verständliche Motiv zum Hook (z. B. Lava, Ausbruch, Insel im Meer) – KEIN generischer Sternenhimmel; mit `"sub": "<Serie> · Teil N"`. Letzter Shot `{"same_as": 0}`, `"motion": "pull"`, Text „Bis dann.“, `"text_out": 0.5` → Loop.
- `description`: vor den Hashtags eine Frage an die Zuschauer, die zum Kommentieren einlädt (keine Werbung).
- Bereits produzierte/eingeplante Teile nie nachträglich ändern – Verbesserungen nur für noch nicht produzierte Teile.
- **Emotion:** pro Shot optional `"tag"` mit ElevenLabs-Tags, z. B. `[mysterious]`, `[serious]`, `[whispers]`, `[dramatically]`, `[curious]`, `[nervous]`, `[warmly]`. Ein Tag gilt bis zum nächsten – nur bei Stimmungswechsel setzen. Erster Shot immer `[mysterious]` (ohne slowly, Anfang soll zügig sein), letzter `[warmly] [softly]`. `[pause]` sparsam an echten Spannungsstellen.
- Zahlen in `say` ausschreiben. Bild-Suchbegriffe englisch, ohne Menschen. Bewegungen: push, pull, pan_l, pan_r, pan_u, pan_d, rot.
