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
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(list(visti), f, ensure_ascii=False, indent=2)


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
    link_elementi = soup.find_all("a", href=True)

    nuovi_interpelli = []

    for a in link_elementi:
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

            if url_completo not in visti:
                nuovi_interpelli.append((titolo, url_completo))

    nuovi_inviati = False
    for titolo, url in reversed(nuovi_interpelli):
        messaggio = (
            f"🚨 <b>NUOVO INTERPELLO - UST BRESCIA</b>\n\n"
            f"📌 <b>{titolo}</b>\n\n"
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
