"""Replay dimostrativo con Segnali fissi, scritti a mano sui dati reali del replay.

Serve al portale finché il ticket 09 non inietta Ambrogio. Non chiama Claude.
Rispetta gli scarti: un Segnale scartato non viene riproposto nei passi successivi.
"""

from __future__ import annotations

from ambrogio.contracts import Decisione, Evidenza, Fonte, Iniziativa, Obiettivo, Passo, Segnale

PC = "https://www.ats-milano.it/sites/default/files/comunicati-stampa/2026/06/Piano%20Caldo%202026%20ATS%20Milano.pdf"
DS205 = Fonte("ds205", "ds205-sociale-caratteristiche-demografiche-territoriali-quartiere", "2024", "")
DS2812 = Fonte("ds2812", "ds2812-rischio-ondata-calore-urbano-nil-07-2024", "luglio 2024", "")
HHWW = Fonte("HHWW (onData)", "https://github.com/ondata/ondate-calore", "estate 2025", "")
ALLERTA_23 = Fonte("Comune di Milano", "https://www2.comune.milano.it/-/maltempo.-allerta-gialla-per-rischio-temporali-35", "2-3/7/2025", "")
ALLERTA_6 = Fonte("MilanoToday", "https://www.milanotoday.it/meteo/allerta-meteo-temporale-grandine-domenica-6-luglio.html", "6/7/2025", "")
ALLERTA_7 = Fonte("Comune di Milano", "https://www2.comune.milano.it/-/maltempo.-ancora-allerta-arancione-per-rischio-temporali", "7/7/2025", "")

FINALITA = Obiettivo(
    "pc-finalita", "Prevenire gli effetti delle ondate di calore con attenzione alle persone sole",
    "Finalità: prevenire e contenere gli effetti delle ondate di calore sulla salute, con particolare attenzione a "
    "anziani, persone con patologie croniche, non autosufficienti, persone sole, lavoratori esposti e altri gruppi suscettibili.",
    "Piano Caldo 2026 ATS Milano", "p. 2 del PDF", "ATS Milano", "estate 2026", ["caldo", "anziani", "persone sole"], PC)
STRUTTURE = Obiettivo(
    "pc-strutture", "Verificare impianti di condizionamento e disponibilità di acqua nelle strutture",
    "monitoraggio delle condizioni ambientali e logistiche delle strutture territoriali, inclusa la verifica del "
    "funzionamento degli impianti di condizionamento e della disponibilità di acqua.",
    "Piano Caldo 2026 ATS Milano", "p. 9 del PDF", "ATS Milano", "estate 2026", ["luoghi freschi", "acqua"], PC)
IN_CARICO = Obiettivo(
    "pc-in-carico", "Livello di rischio caldo per i fragili già in carico",
    "è attivo un sistema di assegnazione del livello di rischio caldo ai cittadini fragili già presi in carico dai "
    "servizi comunali, previo consenso informato.",
    "Piano Caldo 2026 ATS Milano", "p. 9 del PDF", "ATS Milano", "estate 2026", ["anziani", "servizi sociali"], PC)

ESTATE = "Milano Aiuta Estate 2026"
DOMICILIO = "Milano Aiuta (pasti, spesa, farmaci a domicilio, 020202)"


def _s(id, passo, titolo, nil, finestra, evidenze, appiglio, cosa, servizi, priorita, confidenza, dipende,
       verificare, mostrano, inferito) -> Segnale:
    return Segnale(id, passo, titolo, nil, finestra, evidenze, appiglio, Iniziativa(cosa, servizi, "da individuare"),
                   priorita, confidenza, dipende, verificare, mostrano, inferito)


def _e(valore, id_nil, nil, fonte) -> Evidenza:
    return Evidenza(valore, id_nil, nil, fonte.periodo, fonte)


SEGNALI: dict[int, list[Segnale]] = {
    1: [
        _s("A1", 1, "San Siro: caldo in arrivo nel NIL a rischio caldo più alto, con 1.123 anziani 80+ soli", [57],
           "25/6 – 4/7/2025",
           [_e("livello 2", 0, "Milano", HHWW), _e("1.123 residenti 80+ soli", 57, "San Siro", DS205),
            _e("indice rischio caldo 0,431 (1° su 88)", 57, "San Siro", DS2812)],
           IN_CARICO, "Verificare con Milano Aiuta Estate quanti 80+ soli sono già monitorati e proporre un contatto per gli altri.",
           [ESTATE], "alta", "media", "la copertura di Milano Aiuta Estate nel NIL non è pubblica.",
           "Copertura reale del monitoraggio; spazi freschi raggiungibili a piedi.",
           "Rischio caldo più alto della città e 1.123 residenti 80+ soli.",
           "Una parte di loro non è nota ai servizi: il monitoraggio copre solo chi è in carico."),
        _s("A2", 1, "Loreto – Casoretto – NoLo: 1.321 anziani 80+ soli e rischio caldo alto", [20], "25/6 – 4/7/2025",
           [_e("1.321 residenti 80+ soli", 20, "Loreto", DS205),
            _e("indice rischio caldo 0,413 (2° su 88)", 20, "Loreto", DS2812)],
           FINALITA, "Segnalare il NIL a Milano Aiuta Estate come prioritario per il monitoraggio.", [ESTATE],
           "media", "media", "l'indice di rischio caldo è del 2024.", "Spazi freschi aperti e orari.",
           "Secondo NIL per rischio caldo.", "Il livello 2 annuncia un livello 3 nei giorni successivi."),
    ],
    2: [
        _s("B1", 2, "San Siro: uno spazio fresco chiude mentre il caldo sale al livello 3", [57], "27/6 – 4/7/2025",
           [_e("livello 3", 0, "Milano", HHWW), _e("Segnalazione S1 (inventata): casa di quartiere chiusa", 57, "San Siro",
                                                     Fonte("Segnalazione inventata", "data/curati/segnalazioni.csv", "27/6/2025", ""))],
           STRUTTURE, "Indicare uno spazio fresco alternativo e far verificare l'impianto della casa di quartiere.", [ESTATE],
           "alta", "media", "la Segnalazione va confermata.", "Chiusura reale e durata.",
           "Caldo al livello 3 nel NIL a rischio più alto.", "Con uno spazio fresco in meno gli anziani soli hanno meno alternative."),
        _s("B2", 2, "Loreto: un anziano non raggiunge lo spazio fresco perché il tram non passa", [20], "27/6 – 4/7/2025",
           [_e("Segnalazione S2 (inventata): tram fermo da due giorni", 20, "Loreto",
               Fonte("Segnalazione inventata", "data/curati/segnalazioni.csv", "27/6/2025", ""))],
           FINALITA, "Verificare il servizio tram e proporre la consegna a domicilio per chi non può uscire.", [DOMICILIO],
           "media", "bassa", "una sola Segnalazione.", "Stato reale della linea.",
           "Caldo al livello 3 in un NIL con molti 80+ soli.", "Senza tram lo spazio fresco più vicino non è raggiungibile."),
    ],
    3: [
        _s("C1", 3, "Corsica e Buenos Aires: caldo al livello 3 e temporali, con un parco chiuso di pomeriggio", [25, 21],
           "2/7 – 4/7/2025",
           [_e("livello 3", 0, "Milano", HHWW), _e("allerta gialla temporali", 0, "nodo idraulico di Milano", ALLERTA_23),
            _e("904 residenti 80+ soli", 25, "Corsica", DS205)],
           STRUTTURE, "Indicare spazi freschi al chiuso per le ore dei temporali e i pomeriggi senza parco.", [ESTATE],
           "alta", "media", "tempi dei temporali.", "Orari reali del parco.",
           "Caldo al livello 3 e allerta gialla negli stessi giorni.", "Il parco chiuso toglie lo spazio fresco nelle ore più calde."),
    ],
    4: [
        _s("D1", 4, "NIL lungo il Seveso: allerta arancione e sottopasso allagato a Niguarda", [14, 11, 12, 13], "6/7 – 7/7/2025",
           [_e("allerta arancione temporali", 0, "nodo idraulico di Milano", ALLERTA_6),
            _e("livello 1 (caldo finito)", 0, "Milano", HHWW), _e("1.724 residenti 80+ soli", 14, "Niguarda", DS205)],
           FINALITA, "Consegne a domicilio per gli anziani soli che non possono uscire con l'allerta.", [DOMICILIO],
           "media", "bassa", "la lista dei NIL esondabili è editoriale.", "Strade e sottopassi allagati.",
           "Allerta arancione e fine dell'ondata di calore.", "I NIL del Seveso sono i più esposti agli allagamenti."),
    ],
    5: [
        _s("E1", 5, "Ponte Lambro: acqua nelle cantine vicino al Lambro, 94 anziani 80+ soli", [31], "7/7 – 9/7/2025",
           [_e("allerta arancione temporali", 0, "nodo idraulico di Milano", ALLERTA_7),
            _e("94 residenti 80+ soli", 31, "Ponte Lambro", DS205)],
           FINALITA, "Consegna a domicilio agli anziani soli del NIL finché dura l'allerta.", [DOMICILIO],
           "bassa", "bassa", "una sola Segnalazione.", "Estensione dell'allagamento.",
           "Allerta arancione su un NIL lungo il Lambro.", "Le cantine allagate indicano strade difficili per chi è solo."),
        _s("E2", 5, "Loreto: il servizio tram resta da verificare", [20], "7/7/2025", [], FINALITA,
           "Ricontrollare il servizio tram.", [DOMICILIO], "bassa", "bassa", "nessun dato nuovo.", "Linea tram.",
           "Nessun dato nuovo.", "Ripropone B2."),
    ],
}

IGNORATE = {2: [{"id": "S4", "nil": "XXII Marzo", "testo": "Buche sulla pista ciclabile di viale Piceno.",
                 "motivo": "non inerente al caldo né agli anziani soli", "inventata": True}]}


class DemoReplay:
    def esegui_passo(self, passo: Passo, decisioni: list[Decisione]) -> list[Segnale]:
        scartati_nil = {n for d in decisioni if d.esito == "scartato"
                        for s in (x for xs in SEGNALI.values() for x in xs) if s.id == d.segnale_id for n in s.nil}
        # Un Segnale che ripropone un NIL già scartato non torna (es. E2 se B2 è stato scartato).
        return [s for s in SEGNALI[passo.numero] if not (s.id == "E2" and scartati_nil & set(s.nil))]

    def note_passo(self, numero: int) -> dict:
        return {"segnalazioni_ignorate": IGNORATE.get(numero, [])}
