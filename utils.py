import os
import re
import requests
from bs4 import BeautifulSoup
import logging
import time
import random

# Configurazione del logger per utils.py
logger = logging.getLogger(__name__)

# TAG DI AFFILIAZIONE
AFFILIATE_TAG = os.environ.get("AMAZON_AFFILIATE_TAG", "") 

# --- ROTAZIONE DELLO USER-AGENT ---

# Lista di User-Agent comuni per simulare browser diversi
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
]

# Headers di base (SENZA User-Agent, verrà aggiunto casualmente per ogni richiesta)
HEADERS = {
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}
# --- FINE ROTAZIONE DELLO USER-AGENT ---

# FUNZIONE get_product_asin (CORRETTA E ROBUSTA)
def get_product_asin(url: str) -> str or None:
    """Estrae l'ASIN gestendo i reindirizzamenti per amzn.to, amzn.eu, ecc."""
    final_url = url

    # GESTIONE DEI LINK CORTI (ora include amzn.eu e altri)
    if 'amzn.' in url:
        try:
            temp_headers = HEADERS.copy()
            temp_headers['User-Agent'] = random.choice(USER_AGENTS)

            # allow_redirects=True è fondamentale per seguire il link fino alla pagina prodotto
            response = requests.get(url, headers=temp_headers, allow_redirects=True, timeout=10)

            if response.status_code == 200:
                final_url = response.url
                logger.info(f"URL corto {url} espanso a: {final_url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore durante l'espansione dell'URL corto {url}: {e}")
            return None

    # Estrazione ASIN dall'URL finale
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", final_url)
    if match:
        return match.group(1)

    match_asin_only = re.search(r"([A-Z0-9]{10})(?:[/?&]|$)", final_url)
    if match_asin_only and not match_asin_only.group(1).startswith("ref"):
        return match_asin_only.group(1)

    return None
# FINE get_product_asin

def get_amazon_product_details(amazon_url: str) -> dict or None:
    """
    Estrae Titolo e Immagine del prodotto con logica di ritentativo e rotazione dello User-Agent.
    """
    asin = get_product_asin(amazon_url)
    if not asin:
        logger.warning(f"Impossibile estrarre l'ASIN dall'URL: {amazon_url}")
        return None

    # L'URL di base (pulito) ci serve per l'affiliate link
    clean_url = f"https://www.amazon.it/dp/{asin}" 

    # Manteniamo il link originale inviato, ci serve per la logica dei bottoni
    original_url = amazon_url

    affiliate_suffix = f"?tag={AFFILIATE_TAG}" if AFFILIATE_TAG else ""

    product_data = {
        "title": None,
        "image_url": "",
        "asin": asin,
        "clean_product_link": f"{clean_url}{affiliate_suffix}",
        "original_link": original_url, # Nuovo campo per tracciare il link originale
    }

    response = None

    # --- LOGICA DI TENTATIVO (RETRY LOGIC) ---
    for attempt in range(1, 10): # Tenta 9 volte
        try:
            # ⭐️ Aggiungiamo un User-Agent casuale per questa richiesta di scraping
            current_headers = HEADERS.copy()
            current_headers['User-Agent'] = random.choice(USER_AGENTS)

            # Eseguiamo la richiesta
            response = requests.get(clean_url, headers=current_headers, timeout=15)

            logger.info(f"Stato della Risposta HTTP per {asin} (Tentativo {attempt}): {response.status_code}")

            # Se la risposta è 200, è andata a buon fine. Esci dal ciclo.
            if response.status_code == 200:
                break

            # Se la risposta è un errore comune di blocco o server (500, 503, 403, 404), ritenta
            elif response.status_code in [500, 503, 403, 404]:
                logger.warning(f"Errore {response.status_code}. Riprovo tra {attempt * 2} secondi...")
                time.sleep(attempt * 2 + random.uniform(0.5, 1.5)) # Ritardo progressivo con jitter

            # Per qualsiasi altro errore che non gestiamo (es. 400), solleva subito l'errore
            else:
                response.raise_for_status() 

        except requests.exceptions.RequestException as e:
            logger.error(f"Errore di richiesta al Tentativo {attempt}: {e}")
            if attempt < 3:
                time.sleep(attempt * 2 + random.uniform(0.5, 1.5))
                continue # Continua al prossimo tentativo
            else:
                logger.error(f"Scraping fallito dopo {attempt} tentativi.")
                return None

    # --- FINE LOGICA DI TENTATIVO ---

    # Se dopo i tentativi non abbiamo una risposta 200 (o response è None), fallisci
    if response is None or response.status_code != 200:
        logger.error(f"Scraping fallito con stato finale: {response.status_code if response else 'N/A'}")
        return None

    # Ora che abbiamo una risposta 200, procediamo con lo scraping
    try:
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- 1. Estrazione Titolo ---
        title_element = soup.find('span', {'id': 'productTitle'})
        if title_element:
            product_data["title"] = title_element.get_text(strip=True)
        else:
            logger.warning("Errore: Titolo non trovato.")
            return None # Falliamo se non troviamo il titolo

        # --- 2. Estrazione Foto (Miniatura principale) ---
        image_element = soup.find('img', {'id': 'landingImage'}) or soup.find('img', {'id': 'imgBliss'})

        if image_element:
            image_url_data = image_element.get('data-a-dynamic-image')

            if image_url_data:
                match = re.search(r'\"(https?://[^\"]+)\"', image_url_data)
                if match:
                    product_data["image_url"] = match.group(1)
            else:
                product_data["image_url"] = image_element.get('src')

        return product_data

    except Exception as e:
        logger.error(f"Errore generico nell'analisi HTML del prodotto {asin}: {e}")
        return None