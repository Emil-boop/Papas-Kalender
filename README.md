# QR-Code-Werkzeug

Die Webanwendung verwendet Flask (Python) und HTML-Formulare. Sie erstellt QR-Codes mit maximal 200 Zeichen und bietet eine Galerie pro Browser-Sitzung. Sie verwendet kein JavaScript und kein CSS. Ein Live-Kamerascanner ist nicht enthalten.

## Lokal starten

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Danach `http://127.0.0.1:5000` im Browser öffnen.

Die QR-Code-Einträge werden in der lokalen SQLite-Datenbank im Flask-Ordner `instance` gespeichert und über ein signiertes Sitzungscookie dem jeweiligen Browser zugeordnet. Die QR-Code-Inhalte werden daher auf dem Server gespeichert. Für ein öffentliches Deployment sollte `SECRET_KEY` als geschützte Umgebungsvariable gesetzt werden.

## Aufgabenplaner auf dem iPhone installieren

Der Aufgabenplaner ist als installierbare Web-App unter `/planer/` erreichbar. Er speichert seine Aufgaben nur im Browserspeicher des jeweiligen Geräts. Es gibt keine Synchronisierung mit dem PC oder anderen Geräten. Das Entfernen der Web-App oder Löschen der Safari-Websitedaten kann die Aufgaben löschen.

Für die Installation muss der Aufgabenplaner über HTTPS erreichbar sein. Nach dem Deployment:

1. Öffne `https://<deine-domain>/planer/` in Safari auf dem iPhone.
2. Tippe auf „Teilen“ und danach auf „Zum Home-Bildschirm“.
3. Aktiviere bei Bedarf „Als Web-App öffnen“ und tippe auf „Hinzufügen“.

Die Web-App kann nach dem ersten Laden auch offline geöffnet werden. Für die Entwicklung auf dem PC kannst du lokal `http://127.0.0.1:5000/planer/` aufrufen; diese lokale HTTP-Adresse lässt sich nicht als iPhone-Web-App installieren. Ein iPhone kann alternativ die lokale Entwicklungsseite über die Netzwerkadresse des PCs öffnen, benötigt für die PWA-Installation aber weiterhin eine HTTPS-Adresse.

## Öffentlich bereitstellen

Die Datei `render.yaml` enthält eine Render-Konfiguration. Für eine öffentliche Bereitstellung:

1. Die Projektdateien in ein GitHub-Repository hochladen.
2. Bei Render ein neues Blueprint aus diesem Repository anlegen.
3. Den von Render bereitgestellten HTTPS-Link öffnen.

Der kostenlose Dienst kann bei Inaktivität pausieren und beim nächsten Aufruf einige Sekunden zum Starten benötigen. Die Galerie wird serverseitig in SQLite gespeichert und über eine Sitzung dem jeweiligen Browser zugeordnet.

Nach dem Deployment ist der Aufgabenplaner unter derselben Domain unter `/planer/` verfügbar. Die Aufgaben selbst werden dabei nicht an Render gesendet; sie liegen ausschließlich lokal im Speicher von Safari auf dem iPhone.
