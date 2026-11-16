import calendar
import json
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk
from uuid import uuid4


AUFGABEN_DATEI = Path(__file__).with_name("aufgaben.json")
MONATE = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)
WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
WOCHENTAGE_LANG = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)


def datum_in_sechs_monaten(start):
    """Berechnet das Datum sechs Monate später und berücksichtigt kurze Monate."""
    monat_index = start.month - 1 + 6
    jahr = start.year + monat_index // 12
    monat = monat_index % 12 + 1
    letzter_tag = calendar.monthrange(jahr, monat)[1]
    return date(jahr, monat, min(start.day, letzter_tag))


def monat_verschieben(jahr, monat, schritt):
    """Gibt Jahr und Monat zurück, nachdem der Monat verschoben wurde."""
    monat_index = jahr * 12 + monat - 1 + schritt
    return monat_index // 12, monat_index % 12 + 1


def aufgaben_laden():
    if not AUFGABEN_DATEI.exists():
        return []

    with AUFGABEN_DATEI.open("r", encoding="utf-8") as datei:
        aufgaben = json.load(datei)

    if not isinstance(aufgaben, list):
        raise ValueError("Die Aufgabendatei enthält keine gültige Aufgabenliste.")

    for aufgabe in aufgaben:
        if not isinstance(aufgabe, dict) or not all(
            key in aufgabe for key in ("id", "text", "datum", "uhrzeit")
        ):
            raise ValueError("Ein Eintrag in der Aufgabendatei ist ungültig.")
        if not isinstance(aufgabe["id"], str) or not isinstance(
            aufgabe["text"], str
        ):
            raise ValueError("Ein Eintrag enthält ungültige Aufgaben-Daten.")
        aufgabe.setdefault("details", "")
        if not isinstance(aufgabe["details"], str):
            raise ValueError("Die Details einer Aufgabe sind ungültig.")
        aufgabe.setdefault("vergessen", False)
        if not isinstance(aufgabe["vergessen"], bool):
            raise ValueError("Der Vergessen-Status einer Aufgabe ist ungültig.")
        try:
            if aufgabe["datum"] is not None and (
                not isinstance(aufgabe["datum"], str)
                or date.fromisoformat(aufgabe["datum"]).isoformat()
                != aufgabe["datum"]
            ):
                raise ValueError
            if aufgabe["uhrzeit"] is not None and (
                not isinstance(aufgabe["uhrzeit"], str)
                or datetime.strptime(aufgabe["uhrzeit"], "%H:%M").strftime("%H:%M")
                != aufgabe["uhrzeit"]
            ):
                raise ValueError
        except ValueError as fehler:
            raise ValueError("Ein Eintrag enthält ein ungültiges Datum oder eine ungültige Uhrzeit.") from fehler
    return aufgaben


def aufgaben_speichern(aufgaben):
    with AUFGABEN_DATEI.open("w", encoding="utf-8") as datei:
        json.dump(aufgaben, datei, ensure_ascii=False, indent=2)


class Aufgabenplaner:
    def __init__(self, fenster, aufgaben):
        self.fenster = fenster
        self.aufgaben = aufgaben
        self.aufgabe_im_bearbeiten = None
        self.ablauf_after_id = None
        self.heute = date.today()
        self.ausgewaehltes_datum = self.heute
        self.kalender_jahr = self.heute.year
        self.kalender_monat = self.heute.month
        self.letzter_monat = datum_in_sechs_monaten(self.heute)

        fenster.title("Mein Aufgabenplaner")
        fenster.geometry("850x720")
        fenster.minsize(680, 600)

        self.reiter = ttk.Notebook(fenster)

        self.aufgaben_seite = ttk.Frame(self.reiter, padding=16)
        self.kalender_seite = ttk.Frame(self.reiter, padding=16)
        self.vergessene_seite = ttk.Frame(self.reiter, padding=16)
        self.reiter.add(self.aufgaben_seite, text="Meine Aufgaben")
        self.reiter.add(self.kalender_seite, text="Kalender")
        self.reiter.add(self.vergessene_seite, text="Vergessene Aufgaben")

        self.baue_eingabe()
        self.reiter.pack(fill="both", expand=True, padx=12, pady=12)
        self.baue_tagesansicht()
        self.baue_kalender()
        self.baue_vergessene_ansicht()
        self.aktualisiere_anzeigen()
        self.pruefe_abgelaufene_aufgaben()

    def baue_eingabe(self):
        eingabe = ttk.LabelFrame(self.fenster, text="Neue Aufgabe", padding=10)
        eingabe.pack(fill="x", padx=12, pady=(0, 12))

        ttk.Label(eingabe, text="Aufgabe:").grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=4
        )
        self.text_eingabe = ttk.Entry(eingabe)
        self.text_eingabe.grid(
            row=0, column=1, columnspan=7, sticky="ew", pady=4
        )
        self.text_eingabe.bind(
            "<Return>", self.enter_aufgabe
        )

        ttk.Label(eingabe, text="Datum (Pflicht):").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=4
        )
        self.datum_auswahl = self.baue_datum_auswahl(
            eingabe, row=1, column=1, start=self.heute
        )
        ttk.Label(eingabe, text="Uhrzeit (Pflicht):").grid(
            row=1, column=4, sticky="e", padx=(8, 4), pady=4
        )
        self.uhrzeit_auswahl = self.baue_uhrzeit_auswahl(
            eingabe, row=1, column=5
        )

        ttk.Label(eingabe, text="Details (optional):").grid(
            row=2, column=0, sticky="nw", padx=(0, 6), pady=4
        )
        self.details_eingabe = tk.Text(eingabe, height=3, wrap="word")
        self.details_eingabe.grid(
            row=2, column=1, columnspan=7, sticky="ew", pady=4
        )

        ttk.Button(
            eingabe, text="Hinzufügen", command=self.aufgabe_hinzufuegen
        ).grid(row=3, column=7, sticky="e", pady=(4, 0))
        eingabe.columnconfigure(1, weight=1)
        eingabe.columnconfigure(2, weight=1)
        eingabe.columnconfigure(3, weight=1)
        eingabe.columnconfigure(5, weight=0)

    def baue_datum_auswahl(self, parent, row, column, start):
        jahre = tuple(
            str(jahr)
            for jahr in range(
                min(date.today().year, start.year),
                max(date.today().year + 6, start.year) + 1,
            )
        )
        jahr_var = tk.StringVar(value=str(start.year))
        monat_var = tk.StringVar(value=MONATE[start.month - 1])
        tag_var = tk.StringVar(value=str(start.day))

        jahr_box = ttk.Combobox(
            parent,
            textvariable=jahr_var,
            values=jahre,
            width=6,
            state="readonly",
        )
        monat_box = ttk.Combobox(
            parent,
            textvariable=monat_var,
            values=MONATE,
            width=11,
            state="readonly",
        )
        tag_box = ttk.Combobox(
            parent, textvariable=tag_var, width=3, state="readonly"
        )
        jahr_box.grid(row=row, column=column, padx=(0, 3), sticky="w")
        monat_box.grid(row=row, column=column + 1, padx=3, sticky="w")
        tag_box.grid(row=row, column=column + 2, padx=3, sticky="w")

        def aktualisiere_auswahl(ereignis):
            if ereignis.widget in (jahr_box, monat_box):
                self.aktualisiere_tage(
                    jahr_var, monat_var, tag_var, tag_box
                )

        jahr_box.bind("<<ComboboxSelected>>", aktualisiere_auswahl)
        monat_box.bind("<<ComboboxSelected>>", aktualisiere_auswahl)
        self.aktualisiere_tage(jahr_var, monat_var, tag_var, tag_box)
        return jahr_var, monat_var, tag_var

    @staticmethod
    def aktualisiere_tage(jahr_var, monat_var, tag_var, tag_box):
        anzahl_tage = calendar.monthrange(
            int(jahr_var.get()), MONATE.index(monat_var.get()) + 1
        )[1]
        tage = tuple(str(tag) for tag in range(1, anzahl_tage + 1))
        ausgewaehlter_tag = tag_var.get()
        tag_box.configure(values=tage)
        tag_var.set(
            ausgewaehlter_tag if ausgewaehlter_tag in tage else str(anzahl_tage)
        )

    def baue_uhrzeit_auswahl(self, parent, row, column, start=None):
        if start is None:
            jetzt = datetime.now()
            minute = ((jetzt.minute + 2) // 5) * 5
            stunde = jetzt.hour
            if minute == 60:
                minute = 0
                stunde = (stunde + 1) % 24
        else:
            stunde = start.hour
            minute = start.minute - start.minute % 5

        stunden = tuple(f"{wert:02d}" for wert in range(24))
        minuten = tuple(f"{wert:02d}" for wert in range(0, 60, 5))
        stunde_var = tk.StringVar(value=f"{stunde:02d}")
        minute_var = tk.StringVar(value=f"{minute:02d}")
        stunde_box = ttk.Spinbox(
            parent,
            textvariable=stunde_var,
            values=stunden,
            wrap=True,
            width=4,
            state="readonly",
        )
        minute_box = ttk.Spinbox(
            parent,
            textvariable=minute_var,
            values=minuten,
            wrap=True,
            width=4,
            state="readonly",
        )
        stunde_box.grid(row=row, column=column, sticky="w")
        ttk.Label(parent, text=":").grid(
            row=row, column=column + 1, padx=2, sticky="w"
        )
        minute_box.grid(row=row, column=column + 2, sticky="w")
        self.bind_scrollrad(stunde_box, stunde_var, stunden)
        self.bind_scrollrad(minute_box, minute_var, minuten)
        return stunde_var, minute_var

    def bind_scrollrad(self, widget, variable, werte):
        widget.bind(
            "<MouseWheel>",
            lambda ereignis: self.scrolle_spinbox(
                ereignis, variable, werte
            ),
        )
        widget.bind(
            "<Button-4>",
            lambda ereignis: self.scrolle_spinbox(
                ereignis, variable, werte, 1
            ),
        )
        widget.bind(
            "<Button-5>",
            lambda ereignis: self.scrolle_spinbox(
                ereignis, variable, werte, -1
            ),
        )

    @staticmethod
    def scrolle_spinbox(ereignis, variable, werte, richtung=None):
        if richtung is None:
            richtung = 1 if ereignis.delta > 0 else -1
        aktueller_index = werte.index(variable.get())
        variable.set(werte[(aktueller_index + richtung) % len(werte)])
        return "break"

    def enter_aufgabe(self, ereignis):
        if ereignis.widget is self.text_eingabe:
            self.aufgabe_hinzufuegen()

    def baue_tagesansicht(self):
        ttk.Label(
            self.aufgaben_seite,
            text="Aufgaben für heute",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        self.tages_datum_label = ttk.Label(self.aufgaben_seite)
        self.tages_datum_label.pack(anchor="w", pady=(0, 12))

        rahmen = ttk.Frame(self.aufgaben_seite)
        rahmen.pack(fill="both", expand=True)
        self.tages_liste = self.erzeuge_aufgabenliste(rahmen)
        self.tages_liste.bind("<Button-3>", self.zeige_aufgabenmenue)

        ttk.Button(
            self.aufgaben_seite,
            text="Ausgewählte Aufgabe löschen",
            command=lambda: self.aufgabe_loeschen(self.tages_liste),
        ).pack(anchor="e", pady=(10, 0))

    def baue_vergessene_ansicht(self):
        ttk.Label(
            self.vergessene_seite,
            text="Vergessene Aufgaben",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            self.vergessene_seite,
            text="Überfällige Aufgaben bleiben hier, bis du sie löschst.",
        ).pack(anchor="w", pady=(0, 12))

        rahmen = ttk.Frame(self.vergessene_seite)
        rahmen.pack(fill="both", expand=True)
        self.vergessene_liste = self.erzeuge_aufgabenliste(
            rahmen, anzahl_zeilen=15, zeige_datum=True
        )
        self.vergessene_liste.bind(
            "<Button-3>", self.zeige_aufgabenmenue
        )
        ttk.Button(
            self.vergessene_seite,
            text="Ausgewählte Aufgabe löschen",
            command=lambda: self.aufgabe_loeschen(self.vergessene_liste),
        ).pack(anchor="e", pady=(10, 0))

    def baue_kalender(self):
        rahmen = ttk.Frame(self.kalender_seite)
        rahmen.pack(fill="both", expand=True)

        self.kalender_canvas = tk.Canvas(
            rahmen, highlightthickness=0, borderwidth=0
        )
        scrollbar = ttk.Scrollbar(
            rahmen, orient="vertical", command=self.kalender_canvas.yview
        )
        self.kalender_canvas.configure(yscrollcommand=scrollbar.set)
        self.kalender_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.kalender_inhalt = ttk.Frame(self.kalender_canvas)
        self.kalender_fenster_id = self.kalender_canvas.create_window(
            (0, 0), window=self.kalender_inhalt, anchor="nw"
        )
        self.kalender_inhalt.bind(
            "<Configure>", self.kalender_inhalt_geaendert
        )
        self.kalender_canvas.bind(
            "<Configure>", self.kalender_canvas_vergroessert
        )
        self.fenster.bind_all(
            "<MouseWheel>", self.scrolle_kalender, add="+"
        )

        kopf = ttk.Frame(self.kalender_inhalt)
        kopf.pack(fill="x", pady=(0, 10))
        self.vorheriger_button = ttk.Button(
            kopf, text="‹ Vorheriger Monat", command=lambda: self.monat_aendern(-1)
        )
        self.vorheriger_button.pack(side="left")
        self.monat_label = ttk.Label(
            kopf, font=("Segoe UI", 16, "bold"), anchor="center"
        )
        self.monat_label.pack(side="left", expand=True)
        self.naechster_button = ttk.Button(
            kopf, text="Nächster Monat ›", command=lambda: self.monat_aendern(1)
        )
        self.naechster_button.pack(side="right")

        self.kalender_raster = ttk.Frame(self.kalender_inhalt)
        self.kalender_raster.pack(fill="x")
        for spalte, wochentag in enumerate(WOCHENTAGE):
            ttk.Label(
                self.kalender_raster,
                text=wochentag,
                anchor="center",
                font=("Segoe UI", 10, "bold"),
            ).grid(row=0, column=spalte, sticky="ew", padx=2, pady=3)
            self.kalender_raster.columnconfigure(spalte, weight=1)

        self.tag_zellen = []
        for index in range(42):
            zeile = index // 7 + 1
            spalte = index % 7
            zelle = tk.Frame(
                self.kalender_raster,
                background="white",
                borderwidth=1,
                relief="solid",
            )
            zelle.grid(
                row=zeile, column=spalte, sticky="nsew", padx=2, pady=2
            )
            datum_button = tk.Button(
                zelle,
                text="",
                command=lambda nummer=index: self.tag_auswaehlen(nummer),
                borderwidth=0,
                font=("Segoe UI", 11, "bold"),
                padx=4,
                pady=3,
            )
            datum_button.pack(fill="x")
            anzahl_label = tk.Label(
                zelle,
                text="",
                font=("Segoe UI", 8),
                padx=2,
                pady=2,
            )
            anzahl_label.pack(fill="x")
            self.tag_zellen.append((zelle, datum_button, anzahl_label))
            self.kalender_raster.rowconfigure(zeile, weight=1)

        ttk.Label(
            self.kalender_inhalt,
            text="Termine am ausgewählten Tag",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(14, 6))
        self.kalender_datum_label = ttk.Label(self.kalender_inhalt)
        self.kalender_datum_label.pack(anchor="w", pady=(0, 6))

        listen_rahmen = ttk.Frame(self.kalender_inhalt)
        listen_rahmen.pack(fill="x", expand=True)
        self.kalender_liste = self.erzeuge_aufgabenliste(
            listen_rahmen, anzahl_zeilen=15
        )
        self.kalender_liste.bind("<Button-3>", self.zeige_aufgabenmenue)
        ttk.Button(
            self.kalender_inhalt,
            text="Ausgewählte Aufgabe löschen",
            command=lambda: self.aufgabe_loeschen(self.kalender_liste),
        ).pack(anchor="e", pady=(8, 0))

    def kalender_inhalt_geaendert(self, ereignis):
        if ereignis.widget is self.kalender_inhalt:
            self.kalender_canvas.configure(
                scrollregion=self.kalender_canvas.bbox("all")
            )

    def kalender_canvas_vergroessert(self, ereignis):
        self.kalender_canvas.itemconfigure(
            self.kalender_fenster_id, width=ereignis.width
        )

    def scrolle_kalender(self, ereignis):
        if self.reiter.select() != str(self.kalender_seite):
            return
        if isinstance(ereignis.widget, ttk.Treeview):
            return
        schritte = max(1, abs(ereignis.delta) // 120)
        richtung = -schritte if ereignis.delta > 0 else schritte
        self.kalender_canvas.yview_scroll(richtung, "units")
        return "break"

    @staticmethod
    def erzeuge_aufgabenliste(
        rahmen, anzahl_zeilen=10, zeige_datum=False
    ):
        liste = ttk.Treeview(
            rahmen,
            columns=("uhrzeit", "aufgabe"),
            show="headings",
            selectmode="browse",
            height=anzahl_zeilen,
        )
        liste.heading(
            "uhrzeit", text="Termin" if zeige_datum else "Uhrzeit"
        )
        liste.heading("aufgabe", text="Aufgabe")
        liste.column("uhrzeit", width=90, stretch=False, anchor="center")
        liste.column("aufgabe", width=500, anchor="w")
        liste.tag_configure(
            "vergessen", foreground="#B00020", background="#FFF0F0"
        )
        scrollbar = ttk.Scrollbar(rahmen, orient="vertical", command=liste.yview)
        liste.configure(yscrollcommand=scrollbar.set)
        liste.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return liste

    def aufgabe_hinzufuegen(self):
        text = self.text_eingabe.get().strip()
        if not text:
            messagebox.showwarning("Eingabe fehlt", "Bitte eine Aufgabe eingeben.")
            self.text_eingabe.focus_set()
            return

        aufgabe = {
            "id": uuid4().hex,
            "text": text,
            "datum": self.datum_auswahl_wert(self.datum_auswahl).isoformat(),
            "uhrzeit": (
                f"{self.uhrzeit_auswahl[0].get()}:"
                f"{self.uhrzeit_auswahl[1].get()}"
            ),
            "details": self.details_eingabe.get("1.0", "end-1c").strip(),
            "vergessen": False,
        }
        self.aufgaben.append(aufgabe)
        try:
            aufgaben_speichern(self.aufgaben)
        except OSError as fehler:
            self.aufgaben.pop()
            messagebox.showerror(
                "Speichern fehlgeschlagen",
                f"Die Aufgabe konnte nicht gespeichert werden:\n{fehler}",
            )
            return

        self.text_eingabe.delete(0, tk.END)
        self.details_eingabe.delete("1.0", tk.END)
        self.text_eingabe.focus_set()
        self.aktualisiere_anzeigen()
        self.plane_ablaufpruefung()

    @staticmethod
    def datum_auswahl_wert(auswahl):
        jahr_var, monat_var, tag_var = auswahl
        return date(
            int(jahr_var.get()),
            MONATE.index(monat_var.get()) + 1,
            int(tag_var.get()),
        )

    def suche_aufgabe(self, aufgaben_id):
        return next(
            (
                aufgabe
                for aufgabe in self.aufgaben
                if aufgabe["id"] == aufgaben_id
            ),
            None,
        )

    def zeige_aufgabenmenue(self, ereignis):
        liste = ereignis.widget
        zeile = liste.identify_row(ereignis.y)
        if not zeile:
            return "break"

        liste.selection_set(zeile)
        menue = tk.Menu(self.fenster, tearoff=0)
        menue.add_command(
            label="Details anzeigen",
            command=lambda: self.zeige_aufgabendetails(zeile),
        )
        menue.add_command(
            label="Bearbeiten",
            command=lambda: self.aufgabe_bearbeiten(zeile),
        )
        menue.add_command(
            label="Löschen",
            command=lambda: self.aufgabe_loeschen(liste),
        )
        try:
            menue.tk_popup(ereignis.x_root, ereignis.y_root)
        finally:
            menue.grab_release()
        return "break"

    def zeige_aufgabendetails(self, aufgaben_id):
        aufgabe = self.suche_aufgabe(aufgaben_id)
        if aufgabe is None:
            return
        datum_text = (
            date.fromisoformat(aufgabe["datum"]).strftime("%d.%m.%Y")
            if aufgabe.get("datum")
            else "Nicht festgelegt"
        )
        uhrzeit_text = aufgabe.get("uhrzeit") or "Nicht festgelegt"
        details = aufgabe.get("details", "").strip() or "Keine Details eingetragen."
        messagebox.showinfo(
            aufgabe["text"],
            f"Datum: {datum_text}\nUhrzeit: {uhrzeit_text}\n\n{details}",
            parent=self.fenster,
        )

    def aufgabe_bearbeiten(self, aufgaben_id):
        aufgabe = self.suche_aufgabe(aufgaben_id)
        if aufgabe is None:
            return

        eingetragenes_datum = (
            date.fromisoformat(aufgabe["datum"])
            if aufgabe.get("datum")
            else self.heute
        )
        eingetragene_uhrzeit = (
            datetime.strptime(aufgabe["uhrzeit"], "%H:%M")
            if aufgabe.get("uhrzeit")
            else datetime.now()
        )
        self.aufgabe_im_bearbeiten = aufgaben_id
        self.plane_ablaufpruefung()

        dialog = tk.Toplevel(self.fenster)
        dialog.title("Aufgabe bearbeiten")
        dialog.transient(self.fenster)
        dialog.resizable(False, False)
        rahmen = ttk.Frame(dialog, padding=14)
        rahmen.pack(fill="both", expand=True)

        ttk.Label(rahmen, text="Aufgabe:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=5
        )
        text_eingabe = ttk.Entry(rahmen, width=48)
        text_eingabe.grid(row=0, column=1, columnspan=6, sticky="ew", pady=5)
        text_eingabe.insert(0, aufgabe["text"])

        ttk.Label(rahmen, text="Datum (Pflicht):").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=5
        )
        datum_auswahl = self.baue_datum_auswahl(
            rahmen, row=1, column=1, start=eingetragenes_datum
        )
        ttk.Label(rahmen, text="Uhrzeit (Pflicht):").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=5
        )
        uhrzeit_auswahl = self.baue_uhrzeit_auswahl(
            rahmen, row=2, column=1, start=eingetragene_uhrzeit
        )

        ttk.Label(rahmen, text="Details (optional):").grid(
            row=3, column=0, sticky="nw", padx=(0, 8), pady=5
        )
        details_eingabe = tk.Text(rahmen, width=48, height=5, wrap="word")
        details_eingabe.grid(row=3, column=1, columnspan=6, sticky="ew", pady=5)
        details_eingabe.insert("1.0", aufgabe.get("details", ""))

        def speichere_aenderungen():
            neuer_text = text_eingabe.get().strip()
            if not neuer_text:
                messagebox.showwarning(
                    "Eingabe fehlt",
                    "Bitte eine Aufgabe eingeben.",
                    parent=dialog,
                )
                text_eingabe.focus_set()
                return

            alte_aufgabe = aufgabe.copy()
            aufgabe.update(
                {
                    "text": neuer_text,
                    "datum": self.datum_auswahl_wert(datum_auswahl).isoformat(),
                    "uhrzeit": (
                        f"{uhrzeit_auswahl[0].get()}:"
                        f"{uhrzeit_auswahl[1].get()}"
                    ),
                    "details": details_eingabe.get("1.0", "end-1c").strip(),
                }
            )
            try:
                aufgaben_speichern(self.aufgaben)
            except OSError as fehler:
                aufgabe.update(alte_aufgabe)
                messagebox.showerror(
                    "Speichern fehlgeschlagen",
                    f"Die Änderungen konnten nicht gespeichert werden:\n{fehler}",
                    parent=dialog,
                )
                return

            dialog.destroy()
            self.aktualisiere_anzeigen()

        knoepfe = ttk.Frame(rahmen)
        knoepfe.grid(row=4, column=1, columnspan=6, sticky="e", pady=(8, 0))
        ttk.Button(
            knoepfe, text="Abbrechen", command=dialog.destroy
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            knoepfe, text="Speichern", command=speichere_aenderungen
        ).pack(side="right")
        dialog.grab_set()
        text_eingabe.focus_set()
        dialog.wait_window()
        self.aufgabe_im_bearbeiten = None
        self.pruefe_abgelaufene_aufgaben()

    def aufgabe_loeschen(self, liste):
        auswahl = liste.selection()
        if not auswahl:
            messagebox.showinfo(
                "Keine Aufgabe ausgewählt",
                "Bitte zuerst eine Aufgabe in der Liste auswählen.",
            )
            return

        aufgaben_id = auswahl[0]
        index = next(
            (nummer for nummer, aufgabe in enumerate(self.aufgaben)
             if aufgabe["id"] == aufgaben_id),
            None,
        )
        if index is None:
            return

        if not messagebox.askyesno(
            "Aufgabe löschen",
            "Soll diese Aufgabe wirklich gelöscht werden?",
            parent=self.fenster,
        ):
            return

        geloeschte_aufgabe = self.aufgaben.pop(index)
        try:
            aufgaben_speichern(self.aufgaben)
        except OSError as fehler:
            self.aufgaben.insert(index, geloeschte_aufgabe)
            messagebox.showerror(
                "Speichern fehlgeschlagen",
                f"Die Änderung konnte nicht gespeichert werden:\n{fehler}",
            )
            return

        self.aktualisiere_anzeigen()
        self.plane_ablaufpruefung()

    def monat_aendern(self, schritt):
        neuer_jahr_monat = monat_verschieben(
            self.kalender_jahr, self.kalender_monat, schritt
        )
        erster_monat = (self.heute.year, self.heute.month)
        letzter_monat = (self.letzter_monat.year, self.letzter_monat.month)
        if erster_monat <= neuer_jahr_monat <= letzter_monat:
            self.kalender_jahr, self.kalender_monat = neuer_jahr_monat
            self.aktualisiere_kalender()

    def tag_auswaehlen(self, index):
        datum = self.kalender_tage[index]
        if datum is not None:
            self.ausgewaehltes_datum = datum
            self.aktualisiere_kalender()

    def aufgaben_fuer_datum(self, datum):
        # Aufgaben ohne eingetragenes Datum gelten als Aufgaben für heute.
        aufgaben_mit_datum = [
            aufgabe
            for aufgabe in self.aufgaben
            if aufgabe["datum"] is not None
            and date.fromisoformat(aufgabe["datum"]) == datum
        ]
        if datum == self.heute:
            return aufgaben_mit_datum + [
                aufgabe
                for aufgabe in self.aufgaben
                if not aufgabe.get("datum")
            ]
        return aufgaben_mit_datum

    @staticmethod
    def aufgabe_abgelaufen(aufgabe, jetzt):
        datum_text = aufgabe.get("datum")
        uhrzeit_text = aufgabe.get("uhrzeit")
        if not datum_text or not uhrzeit_text:
            return False

        datum = date.fromisoformat(datum_text)
        uhrzeit = datetime.strptime(uhrzeit_text, "%H:%M").time()
        faellig_um = datetime.combine(datum, uhrzeit)
        return jetzt >= faellig_um + timedelta(minutes=15)

    def pruefe_abgelaufene_aufgaben(self):
        self.ablauf_after_id = None
        jetzt = datetime.now()
        aktualisierte_aufgaben = [aufgabe.copy() for aufgabe in self.aufgaben]
        status_geaendert = False
        for aufgabe in aktualisierte_aufgaben:
            if (
                aufgabe["id"] != self.aufgabe_im_bearbeiten
                and not aufgabe["vergessen"]
                and self.aufgabe_abgelaufen(aufgabe, jetzt)
            ):
                aufgabe["vergessen"] = True
                status_geaendert = True

        if status_geaendert:
            try:
                aufgaben_speichern(aktualisierte_aufgaben)
            except OSError as fehler:
                messagebox.showerror(
                    "Aufgaben konnten nicht gespeichert werden",
                    f"Vergessene Aufgaben konnten nicht gespeichert "
                    f"werden:\n{fehler}",
                    parent=self.fenster,
                )
                self.ablauf_after_id = self.fenster.after(
                    300000, self.pruefe_abgelaufene_aufgaben
                )
                return
            else:
                self.aufgaben = aktualisierte_aufgaben
                self.aktualisiere_anzeigen()

        self.plane_ablaufpruefung()

    def plane_ablaufpruefung(self):
        if self.ablauf_after_id is not None:
            self.fenster.after_cancel(self.ablauf_after_id)
            self.ablauf_after_id = None

        jetzt = datetime.now()
        ablaufzeiten = []
        for aufgabe in self.aufgaben:
            if (
                aufgabe["id"] == self.aufgabe_im_bearbeiten
                or aufgabe["vergessen"]
                or not aufgabe.get("datum")
                or not aufgabe.get("uhrzeit")
            ):
                continue
            termin = datetime.combine(
                date.fromisoformat(aufgabe["datum"]),
                datetime.strptime(aufgabe["uhrzeit"], "%H:%M").time(),
            )
            ablaufzeiten.append(termin + timedelta(minutes=15))

        if ablaufzeiten:
            naechster_ablauf = min(ablaufzeiten)
            verzoegerung = max(
                1, int((naechster_ablauf - jetzt).total_seconds() * 1000)
            )
            self.ablauf_after_id = self.fenster.after(
                verzoegerung, self.pruefe_abgelaufene_aufgaben
            )

    def fuelle_liste(self, liste, datum):
        for eintrag in liste.get_children():
            liste.delete(eintrag)

        ist_vergessene_liste = liste is self.vergessene_liste
        if ist_vergessene_liste:
            aufgaben = [
                aufgabe for aufgabe in self.aufgaben if aufgabe["vergessen"]
            ]
        else:
            aufgaben = self.aufgaben_fuer_datum(datum)
        aufgaben.sort(
            key=lambda aufgabe: (
                aufgabe.get("datum") or "" if ist_vergessene_liste else "",
                aufgabe["uhrzeit"] or "99:99",
                aufgabe["text"].casefold(),
            )
        )
        for aufgabe in aufgaben:
            if ist_vergessene_liste:
                termin = " ".join(
                    teil
                    for teil in (
                        date.fromisoformat(aufgabe["datum"]).strftime("%d.%m.%Y")
                        if aufgabe.get("datum")
                        else "",
                        aufgabe.get("uhrzeit") or "",
                    )
                    if teil
                ) or "—"
            else:
                termin = aufgabe["uhrzeit"] or "—"
            liste.insert(
                "",
                "end",
                iid=aufgabe["id"],
                values=(termin, aufgabe["text"]),
                tags=("vergessen",) if aufgabe["vergessen"] else (),
            )

    def aktualisiere_anzeigen(self):
        self.heute = date.today()
        self.tages_datum_label.config(
            text=f"Heute ist der {self.heute.strftime('%d.%m.%Y')}."
        )
        self.fuelle_liste(self.tages_liste, self.heute)
        self.aktualisiere_kalender()
        self.fuelle_liste(self.vergessene_liste, self.heute)

    def aktualisiere_kalender(self):
        self.monat_label.config(
            text=f"{MONATE[self.kalender_monat - 1]} {self.kalender_jahr}"
        )
        erster_monat = (self.heute.year, self.heute.month)
        letzter_monat = (self.letzter_monat.year, self.letzter_monat.month)
        aktueller_monat = (self.kalender_jahr, self.kalender_monat)
        self.vorheriger_button.state(
            ["disabled"] if aktueller_monat <= erster_monat else ["!disabled"]
        )
        self.naechster_button.state(
            ["disabled"] if aktueller_monat >= letzter_monat else ["!disabled"]
        )

        erster_wochentag, anzahl_tage = calendar.monthrange(
            self.kalender_jahr, self.kalender_monat
        )
        self.kalender_tage = [None] * 42
        for index in range(42):
            tag = index - erster_wochentag + 1
            if 1 <= tag <= anzahl_tage:
                self.kalender_tage[index] = date(
                    self.kalender_jahr, self.kalender_monat, tag
                )

        for (rahmen, datum_button, anzahl_label), datum in zip(
            self.tag_zellen, self.kalender_tage
        ):
            if datum is None:
                rahmen.configure(background="#F5F5F5")
                datum_button.configure(
                    text="", state="disabled", background="#F5F5F5"
                )
                anzahl_label.configure(text="", background="#F5F5F5")
                continue

            anzahl_aufgaben = len(self.aufgaben_fuer_datum(datum))
            ist_heute = datum == self.heute
            ist_ausgewaehlt = datum == self.ausgewaehltes_datum
            if ist_heute and ist_ausgewaehlt:
                hintergrund, schrift, anzahl_hintergrund = (
                    "#1769AA",
                    "white",
                    "#DCEEFF",
                )
                rand = "#0D4775"
            elif ist_heute:
                hintergrund, schrift, anzahl_hintergrund = (
                    "#DCEEFF",
                    "#12466E",
                    "#EDF6FF",
                )
                rand = "#2673B8"
            elif ist_ausgewaehlt:
                hintergrund, schrift, anzahl_hintergrund = (
                    "#E9E1F7",
                    "#4A326B",
                    "#F5F0FC",
                )
                rand = "#8064A2"
            else:
                hintergrund, schrift, anzahl_hintergrund = (
                    "white",
                    "#222222",
                    "#F1F3F5",
                )
                rand = "#D0D5DD"

            rahmen.configure(
                background=rand,
                highlightbackground=rand,
                highlightcolor=rand,
                highlightthickness=2 if ist_heute or ist_ausgewaehlt else 1,
            )
            datum_button.configure(
                text=str(datum.day),
                state="normal",
                background=hintergrund,
                foreground=schrift,
                activebackground=hintergrund,
                activeforeground=schrift,
            )
            anzahl_label.configure(
                text=f"{anzahl_aufgaben} "
                f"{'Aufgabe' if anzahl_aufgaben == 1 else 'Aufgaben'}",
                foreground="#52606D",
                background=anzahl_hintergrund,
            )

        self.kalender_datum_label.config(
            text=(
                f"{WOCHENTAGE_LANG[self.ausgewaehltes_datum.weekday()]}, "
                f"{self.ausgewaehltes_datum:%d.%m.%Y}"
            )
        )
        self.fuelle_liste(self.kalender_liste, self.ausgewaehltes_datum)


def main():
    fenster = tk.Tk()
    try:
        aufgaben = aufgaben_laden()
    except (OSError, json.JSONDecodeError, ValueError) as fehler:
        messagebox.showerror(
            "Aufgaben konnten nicht geladen werden",
            f"Die gespeicherten Aufgaben konnten nicht gelesen werden:\n{fehler}",
            parent=fenster,
        )
        fenster.destroy()
        return

    Aufgabenplaner(fenster, aufgaben)
    fenster.mainloop()


if __name__ == "__main__":
    main()