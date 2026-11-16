import os
import secrets
import sqlite3
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import segno
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)


MAX_QR_LENGTH = 200
QR_BACKGROUNDS = {
    "Weiß": "#FFFFFF",
    "Hellblau": "#DCEEFF",
    "Creme": "#FFF4CC",
    "Hellgrün": "#DDF5E1",
    "Rosa": "#FFE0E6",
    "Lavendel": "#E9DFFF",
    "Hellgrau": "#EEEEEE",
    "Mint": "#D8F3EA",
    "Apricot": "#FFE1C2",
    "Hellgelb": "#FFF9B0",
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["DATABASE"] = str(Path(app.instance_path) / "qr_codes.sqlite3")


def verbinde_datenbank():
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    verbindung = sqlite3.connect(app.config["DATABASE"])
    verbindung.row_factory = sqlite3.Row
    return verbindung


@contextmanager
def datenbank_verbindung():
    verbindung = verbinde_datenbank()
    try:
        with verbindung:
            yield verbindung
    finally:
        verbindung.close()


def initialisiere_datenbank():
    with datenbank_verbindung() as verbindung:
        verbindung.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                galerie_id TEXT NOT NULL,
                name TEXT NOT NULL,
                daten TEXT NOT NULL,
                hintergrund TEXT NOT NULL,
                erstellt_am TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def galerie_id():
    kennung = session.get("galerie_id")
    if kennung is None:
        kennung = secrets.token_urlsafe(32)
        session["galerie_id"] = kennung
    session.permanent = True
    return kennung


def lade_galerie(kennung):
    with datenbank_verbindung() as verbindung:
        return verbindung.execute(
            """
            SELECT id, name, daten, hintergrund
            FROM qr_codes
            WHERE galerie_id = ?
            ORDER BY erstellt_am DESC, id DESC
            """,
            (kennung,),
        ).fetchall()


def erzeuge_qr_bild(daten, hintergrund):
    bild = BytesIO()
    segno.make_qr(daten).save(
        bild,
        kind="png",
        scale=10,
        light=hintergrund,
        dark="black",
    )
    bild.seek(0)
    return bild


def zeige_startseite(status=200, daten="", name="", hintergrund="#FFFFFF"):
    kennung = galerie_id()
    return (
        render_template(
            "index.html",
            max_qr_length=MAX_QR_LENGTH,
            qr_backgrounds=QR_BACKGROUNDS,
            gallery=lade_galerie(kennung),
            form_data=daten,
            form_name=name,
            form_background=hintergrund,
        ),
        status,
    )


initialisiere_datenbank()


@app.get("/planer/")
def aufgabenplaner():
    return render_template("aufgabenplaner.html")


@app.get("/planer/manifest.webmanifest")
def aufgabenplaner_manifest():
    return send_from_directory(
        app.static_folder,
        "aufgabenplaner.webmanifest",
        mimetype="application/manifest+json",
    )


@app.get("/planer/service-worker.js")
def aufgabenplaner_service_worker():
    antwort = send_from_directory(
        app.static_folder,
        "aufgabenplaner-sw.js",
        mimetype="application/javascript",
    )
    antwort.headers["Service-Worker-Allowed"] = "/planer/"
    return antwort


@app.get("/")
def startseite():
    return zeige_startseite()


@app.post("/")
def qr_erstellen():
    daten = request.form.get("data", "").strip()
    name = request.form.get("name", "").strip()
    hintergrund = request.form.get("background", "")
    if not daten:
        flash("Bitte gib Text für den QR-Code ein.", "error")
        return zeige_startseite(400, name=name)
    if len(daten) > MAX_QR_LENGTH:
        flash(f"Der Text darf höchstens {MAX_QR_LENGTH} Zeichen enthalten.", "error")
        return zeige_startseite(400, daten=daten, name=name)
    if hintergrund not in QR_BACKGROUNDS.values():
        flash("Die ausgewählte Hintergrundfarbe ist ungültig.", "error")
        return zeige_startseite(400, daten=daten, name=name)
    if len(name) > 80:
        flash("Der Name darf höchstens 80 Zeichen enthalten.", "error")
        return zeige_startseite(
            400, daten=daten, name=name, hintergrund=hintergrund
        )

    try:
        with datenbank_verbindung() as verbindung:
            verbindung.execute(
                """
                INSERT INTO qr_codes (galerie_id, name, daten, hintergrund)
                VALUES (?, ?, ?, ?)
                """,
                (galerie_id(), name or "QR-Code", daten, hintergrund),
            )
    except sqlite3.Error as fehler:
        app.logger.exception("QR-Code konnte nicht in der Galerie gespeichert werden.")
        flash(f"QR-Code konnte nicht gespeichert werden: {fehler}", "error")
        return zeige_startseite(500, daten=daten, name=name, hintergrund=hintergrund)

    flash("QR-Code wurde erstellt und in deiner Galerie gespeichert.", "success")
    return redirect(url_for("startseite"))


@app.get("/qr/<int:eintrag_id>")
def qr_bild(eintrag_id):
    with datenbank_verbindung() as verbindung:
        eintrag = verbindung.execute(
            """
            SELECT daten, name, hintergrund
            FROM qr_codes
            WHERE id = ? AND galerie_id = ?
            """,
            (eintrag_id, galerie_id()),
        ).fetchone()
    if eintrag is None:
        return "QR-Code nicht gefunden.", 404

    dateiname = "".join(
        zeichen if zeichen.isalnum() or zeichen in "-_ " else "_"
        for zeichen in eintrag["name"]
    ).strip()
    return send_file(
        erzeuge_qr_bild(eintrag["daten"], eintrag["hintergrund"]),
        mimetype="image/png",
        as_attachment=request.args.get("download") == "1",
        download_name=f"{dateiname or 'qr_code'}.png",
    )


@app.post("/galerie/loeschen/<int:eintrag_id>")
def qr_loeschen(eintrag_id):
    with datenbank_verbindung() as verbindung:
        verbindung.execute(
            "DELETE FROM qr_codes WHERE id = ? AND galerie_id = ?",
            (eintrag_id, galerie_id()),
        )
    flash("QR-Code wurde aus deiner Galerie entfernt.", "success")
    return redirect(url_for("startseite"))


@app.post("/galerie/leeren")
def galerie_leeren():
    with datenbank_verbindung() as verbindung:
        verbindung.execute(
            "DELETE FROM qr_codes WHERE galerie_id = ?",
            (galerie_id(),),
        )
    flash("Deine Galerie wurde geleert.", "success")
    return redirect(url_for("startseite"))


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "5000")))
