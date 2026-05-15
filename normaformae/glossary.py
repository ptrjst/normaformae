"""
glossary.py

Central registry of German content constants for the Normaformae system.

Rules:
- Keys are English, snake_case — safe for use in code and JSON.
- All values shown to the user (labels, descriptions, UI strings) are in German.
- Each discipline ships its own glossary extension; this module holds the
  application-level UI strings and the HEMA Liechtenauer longsword domain content
  as the reference implementation.
"""

# ---------------------------------------------------------------------------
# Application-level UI strings (German)
# These are used by ALL disciplines in PyQt6 widget labels, dialogs, buttons.
# ---------------------------------------------------------------------------

UI = {
    # Startup / navigation
    "app_title":              "Normaformae",
    "select_domain":          "Bereich auswählen",
    "select_discipline":      "Disziplin auswählen",
    "select_role":            "Rolle auswählen",
    "role_author":            "Autor",
    "role_user":              "Benutzer",
    "role_trainer":           "Trainer",
    "cancel":                 "Abbrechen",
    "close":                  "Schließen",

    # Author tool
    "author_window_title":    "Autorenwerkzeug",
    "load_video":             "Video laden",
    "new_flow":               "Neuer {flow}",
    "open_flow":              "{flow} öffnen",
    "save_draft":             "Entwurf speichern",
    "publish_flow":           "Veröffentlichen",
    "frame_label_stance":     "Hut",
    "frame_label_transition": "Übergang",
    "frame_label_ignore":     "Ignorieren",
    "label_select":           "Bezeichnung auswählen oder neu eingeben",
    "description_field":      "Beschreibung",
    "common_errors_field":    "Häufige Fehler",
    "reference_image":        "Referenzbild (optional)",
    "no_reference_image":     "Kein Referenzbild vorhanden",
    "browse":                 "Durchsuchen",
    "search_wiki":            "In Wiktenauer suchen",
    "status_draft":           "Entwurf",
    "status_published":       "Veröffentlicht",
    "timestamp_auto":         "Zeitstempel (automatisch berechnet)",

    # User tool
    "user_window_title":      "Bewegungsanalyse",
    "upload_video":           "Video hochladen",
    "video_url":              "Video-URL (ab Version 3)",
    "url_disabled":           "URL-Eingabe noch nicht verfügbar",
    "start_analysis":         "Analyse starten",
    "analysis_running":       "Analyse läuft…",
    "analysis_complete":      "Analyse abgeschlossen",
    "export_document":        "Dokument exportieren",
    "export_video":           "Augmentiertes Video exportieren",
    "no_flow_selected":       "Kein {flow} ausgewählt",  # Slice 3: shown when user submits without a flow

    # Recognition result display
    "result_detected_stances":    "Erkannte Huten",
    "result_detected_sequences":  "Erkannte Sequenzen",
    "result_matched_flows":       "Übereinstimmende {flows}",
    "result_unrecognised":        "Nicht erkannte Abschnitte",
    "result_confidence":          "Sicherheit",
    "result_deviation":           "Abweichung",
    "result_timestamp":           "Zeitstempel",

    # Trainer tool (Slice 5 — strings defined now, used later)
    "trainer_window_title":   "Trainerverwaltung",
    "assign_flow":            "{flow} zuweisen",  # Slice 5: Trainer UI
    "filter_by_level":        "Nach Niveau filtern",
    "practitioner_history":   "Übungsverlauf",

    # Common
    "error_no_video":         "Kein Video geladen.",
    "error_no_discipline":    "Keine Disziplin ausgewählt.",
    "error_incomplete_stance":"Hut unvollständig — kein extrahiertes Bild vorhanden.",
    "confirm_publish":        "Soll dieser {flow} veröffentlicht werden? Entwürfe können weiterhin bearbeitet werden.",
    "file_saved":             "Datei gespeichert",
    "output_written":         "Ausgabedatei erstellt",
}


# ---------------------------------------------------------------------------
# HEMA — Liechtenauer Longsword discipline content
# Discipline ID: liechtenauer_longsword
# Domain: hema
# ---------------------------------------------------------------------------

HEMA_LIECHTENAUER = {

    "discipline_display_name": "Liechtenauer — Langschwert",
    "domain_display_name":     "Historische Europäische Kampfkünste (HEMA)",

    # Practitioner levels — Liechtenauer tradition terminology
    "practitioner_levels": [
        {
            "level_id":    "schueler",
            "label":       "Schüler",
            "description": "Anfänger — erlernt Grundhuten und einfache Haue",
        },
        {
            "level_id":    "geselle",
            "label":       "Geselle",
            "description": "Fortgeschrittener — kennt alle Meisterhäue und grundlegende Bindungsarbeit",
        },
        {
            "level_id":    "freifechter",
            "label":       "Freifechter",
            "description": "Erfahrener Fechter — beherrscht Mensurarbeit und taktische Kombinationen",
        },
        {
            "level_id":    "meister",
            "label":       "Meister",
            "description": "Meister des langen Schwertes — vollständige Beherrschung des Systems",
        },
    ],

    # Scoring criteria — used in AnalysisResult deviation notes
    "scoring_criteria": [
        {
            "criterion_id": "struktur",
            "label":        "Struktur",
            "description":  "Körperhaltung und Ausrichtung hinter dem Schwert",
        },
        {
            "criterion_id": "mensur",
            "label":        "Mensur",
            "description":  "Abstandskontrolle zum Gegner",
        },
        {
            "criterion_id": "linie",
            "label":        "Linie",
            "description":  "Ausrichtung von Spitze oder Schneide zur Bedrohungslinie",
        },
        {
            "criterion_id": "timing",
            "label":        "Timing",
            "description":  "Zeitliche Ausführung der Bewegung",
        },
        {
            "criterion_id": "krafteinsatz",
            "label":        "Krafteinsatz",
            "description":  "Angemessener Einsatz von Kraft und Weichheit (Hart und Weich)",
        },
    ],

    # Stances (Huten) — canonical guards of the Liechtenauer system
    # extracted_frame and keypoints are populated by the Author tool at annotation time.
    # These entries serve as the vocabulary the Author selects from.
    "stances": {
        "vom_tag": {
            "label":         "Vom Tag",
            "description":   (
                "Hochdeckung — das Schwert wird über der Schulter oder am Haupt gehalten. "
                "Starke Ausgangsposition für kraftvolle Oberhäue. "
                "Zwei Varianten: Schwert an der Schulter (niedriger Vom Tag) oder über dem Haupt (hoher Vom Tag)."
            ),
            "common_errors": [
                "Ellbogen zu weit vom Körper abgespreizt",
                "Gewicht nicht auf dem hinteren Fuß",
                "Spitze zeigt zu weit nach oben statt leicht nach vorn",
            ],
        },
        "ochs": {
            "label":         "Ochs",
            "description":   (
                "Ochsenhut — das Schwert wird auf Kopfhöhe gehalten, Spitze droht dem Gesicht "
                "oder der Brust des Gegners. Starke Deckung gegen hohe Angriffe. "
                "Links und rechts möglich."
            ),
            "common_errors": [
                "Spitze zeigt zu hoch statt zum Gesicht des Gegners",
                "Hände nicht auf Kopfhöhe",
                "Körper nicht hinter der Klinge ausgerichtet",
            ],
        },
        "pflug": {
            "label":         "Pflug",
            "description":   (
                "Pflugschar — das Schwert wird auf Hüfthöhe gehalten, Spitze droht der Brust "
                "oder dem Bauch des Gegners. Deckung gegen niedrige und mittlere Angriffe. "
                "Links und rechts möglich."
            ),
            "common_errors": [
                "Spitze zeigt nach unten statt zum Gegner",
                "Hände zu tief, Klinge ohne Bedrohungslinie",
                "Vorderer Arm zu gestreckt — keine Kontrolle bei Bindung",
            ],
        },
        "alber": {
            "label":         "Alber",
            "description":   (
                "Alber (Tor) — das Schwert hängt mit der Spitze nach unten vor dem Körper. "
                "Scheinbar offene Position, die Angriffe provoziert und zum Absetzen einlädt. "
                "Einer der vier Haupthuten nach Liechtenauer."
            ),
            "common_errors": [
                "Klinge zu weit vom Körper entfernt",
                "Keine Bereitschaft zum sofortigen Aufwärtsschnitt",
                "Gewicht falsch verteilt — Reaktionszeit zu lang",
            ],
        },
        "zornhut": {
            "label":         "Zornhut",
            "description":   (
                "Zornhut — kraftvolle seitliche Hochdeckung, Schwert weit hinter der Schulter. "
                "Ausgangsposition für den Zornhau. Betont den zornigen, kraftvollen Charakter des Hiebes."
            ),
            "common_errors": [
                "Schwert nicht weit genug zurückgenommen",
                "Schulter zu verspannt — Bewegungsradius eingeschränkt",
            ],
        },
        "schrankhut": {
            "label":         "Schrankhut",
            "description":   (
                "Schrankhut — tief gekreuzte Deckung, Klinge schräg vor dem Körper. "
                "Schutz gegen niedrige Angriffe und Vorbereitung für aufsteigende Schnitte."
            ),
            "common_errors": [
                "Kreuzung der Klinge zu flach — kein Schutz der Beine",
                "Körperschwerpunkt zu hoch",
            ],
        },
        "nebenhut": {
            "label":         "Nebenhut",
            "description":   (
                "Nebenhut — tiefe seitliche Deckung, Schwert neben dem Körper mit Spitze nach hinten-unten. "
                "Einladende Position für Unterhäue und Aufwärtsschnitte."
            ),
            "common_errors": [
                "Spitze zeigt zu weit nach hinten — keine Kontrolle",
                "Zu aufrecht stehend — Mobilität eingeschränkt",
            ],
        },
    },

    # Transitions (Übergänge) — named cuts, thrusts, and actions
    "transitions": {
        "zornhau": {
            "label":         "Zornhau",
            "description":   (
                "Der Zornhau — zorniger Hieb diagonal von oben. "
                "Erster der fünf Meisterhäue. Bricht die Deckung des Ochs. "
                "Ausgeführt aus dem Zornhut mit vollem Körpereinsatz."
            ),
            "common_errors": [
                "Hieb zu arm — kein Körpereinsatz",
                "Linie zur Mitte nicht gehalten (Fehler: Weichen)",
                "Trittfolge stimmt nicht mit dem Hieb überein",
            ],
        },
        "krumphau": {
            "label":         "Krumphau",
            "description":   (
                "Der Krumphau — gekrümmter Hieb über die Klinge des Gegners. "
                "Zweiter der fünf Meisterhäue. Bricht den Vom Tag. "
                "Charakteristisch: die Hände kreuzen während des Hiebes."
            ),
            "common_errors": [
                "Hände kreuzen nicht — nur einfacher Oberhau",
                "Zu wenig Seitwärtsbewegung — eigene Linie wird nicht gewechselt",
            ],
        },
        "zwerchhau": {
            "label":         "Zwerchhau",
            "description":   (
                "Der Zwerchhau — waagerechter Querhieb aus dem Ochs. "
                "Dritter der fünf Meisterhäue. Bricht Vom Tag. "
                "Trifft mit der Kurzen Schneide, Klinge quer zur Bewegungsrichtung."
            ),
            "common_errors": [
                "Kurze Schneide nicht genutzt — mit langer Schneide getroffen",
                "Kopf nicht hinter der Klinge geschützt",
                "Keine Drehbewegung des Körpers",
            ],
        },
        "schielhau": {
            "label":         "Schielhau",
            "description":   (
                "Der Schielhau — schielender Hieb, der den Pflug bricht. "
                "Vierter der fünf Meisterhäue. Führt die Spitze scheinbar an der "
                "gegnerischen Klinge vorbei, um sie dann zu binden."
            ),
            "common_errors": [
                "Keine Verstellung des Körpers — zu direkter Angriff",
                "Spitze verliert die Bedrohungslinie",
            ],
        },
        "scheitelhau": {
            "label":         "Scheitelhau",
            "description":   (
                "Der Scheitelhau — senkrechter Scheitelschlag, der Alber bricht. "
                "Fünfter der fünf Meisterhäue. Senkrechter Hieb auf den Scheitel, "
                "erzwingt eine Reaktion aus dem Alber."
            ),
            "common_errors": [
                "Hieb zu weit — keine Kontrolle bei Kontakt",
                "Körper zu aufrecht — keine Kraftübertragung",
            ],
        },
        "oberhau": {
            "label":         "Oberhau",
            "description":   (
                "Oberhau — absteigender Hieb von oben, allgemeine Kategorie. "
                "Umfasst alle Schnitte, die von oben nach unten geführt werden. "
                "Grundlegende Angriffsbewegung des Langschwerts."
            ),
            "common_errors": [
                "Klinge nicht auf der Linie — trifft nicht den direkten Weg",
                "Arme zu gestreckt am Anfang — Reichweite verschenkt",
            ],
        },
        "unterhau": {
            "label":         "Unterhau",
            "description":   (
                "Unterhau — aufsteigender Hieb von unten. "
                "Geführt aus Nebenhut oder Schrankhut. "
                "Bedroht tiefe Linien und kann hohe Deckungen umgehen."
            ),
            "common_errors": [
                "Zu wenig Körpereinsatz — Hieb ohne Kraft",
                "Linie nach dem Hieb nicht gehalten",
            ],
        },
        "mittelhau": {
            "label":         "Mittelhau",
            "description":   (
                "Mittelhau — waagerechter Hieb auf mittlerer Höhe. "
                "Trifft den Leib oder die Arme des Gegners. "
                "Kann mit langer oder kurzer Schneide geführt werden."
            ),
            "common_errors": [
                "Ellbogen sinken — Hieb verliert die Linie",
                "Keine Deckungsposition nach dem Hieb",
            ],
        },
        "stich": {
            "label":         "Stich",
            "description":   (
                "Stich — direkter Stoß mit der Spitze. "
                "Aus Ochs oder Pflug geführt. Schnellste Angriffstechnik. "
                "Hohe oder tiefe Variante je nach Ausgangsposition."
            ),
            "common_errors": [
                "Spitze nicht auf der Linie — trifft nicht",
                "Zu viel Ausholbewegung — Angriff kündigt sich an",
                "Körper nicht hinter dem Stoß",
            ],
        },
        "absetzen": {
            "label":         "Absetzen",
            "description":   (
                "Absetzen — Abweisen und gleichzeitiges Stechen. "
                "Defensiv-offensive Technik: gegnerischen Angriff mit der Klinge absetzen "
                "und sofort mit einem Stich kontern."
            ),
            "common_errors": [
                "Absetzen und Stechen zeitlich getrennt — kein Simultanzug",
                "Zu wenig Seitwärtsbewegung beim Absetzen",
            ],
        },
        "winden": {
            "label":         "Winden",
            "description":   (
                "Winden — Drehen am Schwert in der Bindung. "
                "Aus der Bindung heraus die Stärke gegen die Schwäche des gegnerischen "
                "Schwertes nutzen, um Linien zu öffnen."
            ),
            "common_errors": [
                "Winden ohne Fühlen — Kraft statt Sensibilität",
                "Eigene Linie beim Winden verloren",
            ],
        },
    },

    # Frame annotation labels — used in the Author tool dropdown
    "annotation_labels": {
        "stance":     "Hut",
        "transition": "Übergang",
        "ignore":     "Ignorieren",
    },

    # Output document section headers
    "output_headers": {
        "document_title":         "{flow}-Analyse",
        "discipline_label":       "Disziplin",
        "flow_label":             "{flow}",
        "analysis_date":          "Analysedatum",
        "detected_stances":       "Erkannte Huten",
        "detected_sequences":     "Erkannte Sequenzen",
        "matched_flows":          "Übereinstimmende {flows}",
        "unrecognised_segments":  "Nicht erkannte Abschnitte",
        "description":            "Beschreibung",
        "common_errors":          "Häufige Fehler",
        "confidence":             "Sicherheit",
        "deviation_notes":        "Abweichungen",
        "extracted_frame":        "Extrahiertes Bild",
        "reference_image":        "Referenzbild",
        "timestamp":              "Zeitstempel",
        "duration":               "Dauer",
        "no_reference_image":     "Kein Referenzbild vorhanden",
        "draft_warning":          "Entwurf — nicht zur Weitergabe bestimmt",
    },
}


# ---------------------------------------------------------------------------
# Runtime UI string resolution
# Fills {flow} / {flows} placeholders using discipline vocabulary.
# Call once after loading a discipline, cache the result.
# ---------------------------------------------------------------------------

def resolve_ui(vocab: dict) -> dict:
    """
    Return a copy of the UI dict with {flow} and {flows} placeholders
    replaced by discipline-specific vocabulary labels.

    Args:
        vocab: output of discipline_loader.get_vocabulary()
               expects vocab["flow"]["singular"] and vocab["flow"]["plural"]

    Returns:
        New dict — UI is unchanged (it is the template).
    """
    flow_singular = vocab.get("flow", {}).get("singular", "Ablauf")
    flow_plural   = vocab.get("flow", {}).get("plural",   "Abläufe")

    resolved = {}
    for key, value in UI.items():
        if isinstance(value, str):
            value = value.replace("{flow}", flow_singular)
            value = value.replace("{flows}", flow_plural)
        resolved[key] = value
    return resolved
