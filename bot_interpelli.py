import json
import os
import requests
from bs4 import BeautifulSoup

# Recupera le credenziali dai Secrets di GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

URL_INTERPELLI = (
    "https://www.mim.gov.it/web/brescia/interpelli-ricerca-supplenti"
)
DB_FILE = "interpelli_brescia.json"


def invia_messaggio_telegram(testo):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": testo,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        return response.ok
    except Exception as e:
        print(f"Errore nell'invio a Telegram: {e}")
        return False


def carica_visti():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def salva_visti(visti):
    lista_visti = list(visti)[-200:]
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(lista_visti, f, ensure_ascii=False, indent=2)


def controlla_interpelli():
    visti = carica_visti()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }

    try:
        response = requests.get(URL_INTERPELLI, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Errore connessione al sito MIM: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Cerca i blocchi che contengono i singoli post
    blocchi = soup.find_all(
        ["article", "div"],
        class_=lambda c: c
        and any(
            x in c for x in ["asset-abstract", "journal-content-article", "post"]
        ),
    )

    # Se la ricerca per classe fallisce, usa una ricerca basata sui link di titolo
    if not blocchi:
        blocchi = [
            a.find_parent(["article", "div"])
            for a in soup.find_all("a", href=True)
            if ("/web/brescia/" in a["href"] or "documents/" in a["href"])
            and len(a.get_text(strip=True)) > 10
        ]

    nuovi_interpelli = []

    for blocco in blocchi:
        if not blocco:
            continue

        a = blocco.find("a", href=True)
        if not a:
            continue

        href = a["href"].strip()
        titolo = a.get_text(strip=True)

        if (
            "/web/brescia/" in href or "documents/" in href
        ) and len(titolo) > 10:
            url_completo = (
                f"https://www.mim.gov.it{href}"
                if href.startswith("/")
                else href
            )

            # Estrai la descrizione (il testo nei paragrafi <p> del blocco)
            paragrafi = blocco.find_all("p")
            descrizione = " ".join([p.get_text(strip=True) for p in paragrafi])

            # Se non trova paragrafi <p>, prende il testo visibile esclusi i titoli
            if not descrizione:
                descrizione = blocco.get_text(separator=" ", strip=True).replace(
                    titolo, ""
                )

            if url_completo not in visti:
                nuovi_interpelli.append((titolo, descrizione, url_completo))

    nuovi_inviati = False
    for titolo, descrizione, url in reversed(nuovi_interpelli):
        testo_descrizione = (
            f"\n\n📝 <i>{descrizione}</i>" if descrizione else ""
        )

        messaggio = (
            f"🚨 <b>NUOVO INTERPELLO - UST BRESCIA</b>\n\n"
            f"📌 <b>{titolo}</b>"
            f"{testo_descrizione}\n\n"
            f"🔗 <a href='{url}'>Visualizza Avviso / Allegato</a>"
        )

        if invia_messaggio_telegram(messaggio):
            print(f"Notifica inviata per: {titolo}")
            visti.add(url)
            nuovi_inviati = True

    if nuovi_inviati:
        salva_visti(visti)
    else:
        print("Nessun nuovo interpello pubblicato.")


if __name__ == "__main__":
    controlla_interpelli()
