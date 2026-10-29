# Rubic Shorts – Routine ca. alle 3 Tage (sparsam!)

Kanal: **Rubic (@rubic.shorts)**, Thema **Steine und die vier Elemente** (Feuer, Wasser, Erde, Wind).
Etwa alle 3 Tage (am 1., 4., 7., … 28. jedes Monats, 10× pro Monat) ein deutscher Short (Teil einer Serie), eingeplant über Metricool für 18:00 deutsche Zeit.
Keine Werbung im Video (kein Shop, kein Logo, kein Produkt). Der Shop-Link steht nur in der Kanal-Bio.

## Ablauf – wenige Schritte, kurze Ausgaben
1. Repo `Rabetv/rubic-shorts` anhängen (add_repo, push) und klonen. Setup in EINEM Bash-Aufruf:
   `pip install --break-system-packages -q piper-tts faster-whisper; mkdir -p ~/rubic-cache/voice && cd ~/rubic-cache/voice && for e in onnx onnx.json; do [ -f de_DE-thorsten-high.$e ] || curl -sSL -o de_DE-thorsten-high.$e https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/high/de_DE-thorsten-high.$e; done`
1b. **Analytics (jeder Lauf):** `vidiq_user_videos` (channelId `UC3OXnEqXsoapzesJ3LQCwxA`, limit 10, privacyStatus [public], videoType [short]; 5 Credits). Zahlen der Rubic-Shorts (ab Okt. 2026, alte englische Videos ignorieren) als Zeile in `ANALYTICS.md` unter „Verlauf“ ergänzen (Datum, Teil, Aufrufe, Likes, Kommentare, Länge). Nur Videos ≥ 2 Tage alt bewerten. Wenn sich ein klares Muster zeigt, die „Erkenntnisse“ in `ANALYTICS.md` kurz anpassen. Beim Schreiben neuer Teile die Erkenntnisse aus `ANALYTICS.md` anwenden (Titel-Stil, Länge, Hook, Kommentar-Frage). Mit dem nächsten Commit pushen.
2. `python3 render/daily.py next`
   - `MISSING_PART`: nur dann den nächsten Teil schreiben (siehe „Neue Teile“), committen, dann erneut `next`.
3. Stimme – NUR ElevenLabs, Qualität nie senken (keine Ersatzstimme, Texte nicht kürzen um Credits zu sparen):
   ElevenLabs-Connector: `creative_generate_speech` mit prompt = `script` (enthält Emotions-Tags), model_id = `voice_model` (eleven_v4), voice_id = `voice_elevenlabs`, **generations_count 1**. Mit `creative_get_flow_run_status` (alle 30 s) warten, bis fertig; die Audio-URL der Generation nach `/tmp/voice.mp3` laden (curl). Nicht doppelt starten.
   Bei Fehler (Limit/Kontingent/429): Lauf ohne Video beenden, nichts einplanen, den neu geschriebenen Teil trotzdem committen/pushen (wird beim nächsten Lauf produziert) und per PushNotification melden. Budget: 10.000 Credits/Monat, ca. 900 pro Short → 10 Shorts/Monat.
4. Rendern im Hintergrund (8–12 min): `python3 render/daily.py build /tmp/voice.mp3`. Auf Ende warten.
5. Kontaktbogen (`sheet` im Ergebnis) EINMAL ansehen. Nur bei klar falschen Bildern (Menschen, Städte, Text, Boote ohne Bezug): Suchbegriff in der Story ändern, `git reset --hard HEAD~1`, erneut bauen.
6. Metricool `createScheduledPost`: blogId 7525052, date = `publish_at` aus dem Ergebnis (19:00 Asia/Nicosia = 18:00 deutsche Zeit),
   info: autoPublish true, media [url], providers [{"network":"youtube"}], publicationDate {dateTime, timezone "Asia/Nicosia"},
   text = description, firstCommentText = Kommentar-Frage aus der description, youtubeData {title: yt_title, type "short", privacy "public", tags, category "EDUCATION", madeForKids false, isAiGeneratedContent false}.
7. Bericht an den Nutzer (Deutsch, max. 3 Zeilen): Titel, geplante Zeit, kurz die wichtigste Analytics-Erkenntnis.

## Neue Teile / neue Serie schreiben
- Fakten vorher per Websuche prüfen, Quellen in `sources`. Lieber vage als falsch.
- Serien mit 4–6 Teilen über Steine (Meteoriten, berühmte Steine, Kristalle, Vulkane, Gestein) oder die vier Elemente. Idee für die nächste Serie steht in `next_series_idea`.
  Neue Serie: `stories/NN-<slug>.json` im Format von `stories/01-surtsey.json`, in `state.json` `story` umstellen und `next_part` auf 1.
- **Spannung:** Hook im ersten Satz (Rätsel/Behauptung), falsche Fährte, kurze Schläge, Auflösung, Cliffhanger auf den nächsten Teil (der kommt „in ein paar Tagen“ / „beim nächsten Mal“, nie „morgen“ oder „übermorgen“ schreiben). `"hit": true` auf Wendepunkte, `"riser": true` vor einer Enthüllung.
- **Ruhiges Tempo:** 12–14 Shots, pro Shot ein kurzer Gedanke, `say` höchstens 1–2 kurze Sätze; gesamt 650–850 Zeichen.
- Erste 3 Sekunden = Titel-Versprechen sofort einlösen: stärkstes, sofort verständliches Motiv + spannendste Aussage, Kontext (Ort/Datum) erst danach. Erster Shot = das stärkste, sofort verständliche Motiv zum Hook (z. B. Lava, Ausbruch, Insel im Meer) – KEIN generischer Sternenhimmel; mit `"sub": "<Serie> · Teil N"`. Letzter Shot `{"same_as": 0}`, `"motion": "pull"`, `"text_out": 0.5` → Loop. **Kein Ausklingen** (kein „Bis dann.“, kein „Das erfährst du …“, keine Verabschiedung): der Cliffhanger ist der letzte Satz, kurz und hart, und soll nahtlos in den ersten Satz zurückführen.
- `description`: vor den Hashtags eine Frage an die Zuschauer, die zum Kommentieren einlädt (keine Werbung). Dieselbe Frage zusätzlich als `firstCommentText` beim Metricool-Post (nicht im Video – das Ende muss hart bleiben).
- Bereits produzierte/eingeplante Teile nie nachträglich ändern – Verbesserungen nur für noch nicht produzierte Teile.
- **Emotion:** pro Shot optional `"tag"` mit ElevenLabs-Tags, z. B. `[mysterious]`, `[serious]`, `[whispers]`, `[dramatically]`, `[curious]`, `[nervous]`, `[warmly]`. Ein Tag gilt bis zum nächsten – nur bei Stimmungswechsel setzen. Erster Shot immer `[mysterious]` (ohne slowly, Anfang soll zügig sein), letzter Shot spannungsvoll (`[mysterious]`/`[whispers]`), nicht `[warmly] [softly]`. `[pause]` sparsam an echten Spannungsstellen.
- Zahlen in `say` ausschreiben. Bild-Suchbegriffe englisch, ohne Menschen. Bewegungen: push, pull, pan_l, pan_r, pan_u, pan_d, rot.
