import os
import re
import requests
from bs4 import BeautifulSoup
import logging

# Configurazione del logger per utils.py
logger = logging.getLogger(__name__)

# TAG DI AFFILIAZIONE - VIENE CARICATO DALLE VARIABILI D'AMBIENTE DI REPLIT
# Se non è impostato in Replit Secrets, usa un valore di fallback
AFFILIATE_TAG = os.environ.get("AMAZON_AFFILIATE_TAG", "iltuotag-21") 

# Headers per camuffarsi da browser (ESSENZIALE per lo scraping)
HEADERS = {
    # Usa uno User-Agent aggiornato per sembrare un browser reale
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

def get_product_asin(url: str) -> str or None:
    """Estrae l'ASIN (identificativo del prodotto Amazon) dall'URL."""

    # Tenta di estrarre l'ASIN da URL standard (dp/ ASIN)
    match = re.search(r"[/dp/|/gp/product/]([A-Z0-9]{10})", url)
    if match:
        return match.group(1)

    # Gestisce i link brevi amzn.to dopo l'espansione, cercando un ID a 10 caratteri
    # (Non gestisce l'espansione diretta, ma cerca l'ASIN se l'URL è già espanso)
    match = re.search(r"([A-Z0-9]{10})(?:/ref|/|$)", url)
    if match and not match.group(1).startswith("ref"):
        return match.group(1)

    return None

def get_amazon_product_details(amazon_url: str) -> dict or None:
    """
    Estrae i dettagli del prodotto tramite scraping web.
    NOTA: Questa logica è sensibile ai cambiamenti della struttura HTML di Amazon.
    """
    asin = get_product_asin(amazon_url)
    if not asin:
        logger.warning(f"Impossibile estrarre l'ASIN dall'URL: {amazon_url}")
        return None

    # Costruisce l'URL "pulito" (è essenziale per l'affidabilità)
    clean_url = f"https://www.amazon.it/dp/{asin}" 

    # Preparazione dei dati di default (in caso di fallimento)
    product_data = {
        "title": None,
        "current_price": 0.0,
        "previous_price": None,
        "image_url": "",
        "product_link": f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_TAG}"
    }

    try:
        # Eseguiamo la richiesta
        response = requests.get(clean_url, headers=HEADERS, timeout=15)

        logger.info(f"Stato della Risposta HTTP per {asin}: {response.status_code}")

        # Se Amazon blocca o c'è un errore, solleva un'eccezione
        response.raise_for_status() 

        soup = BeautifulSoup(response.content, 'html.parser')

        # --- 1. Estrazione Titolo ---
        title_element = soup.find('span', {'id': 'productTitle'})
        if title_element:
            product_data["title"] = title_element.get_text(strip=True)
        else:
            logger.warning("Errore: ID 'productTitle' non trovato o struttura cambiata.")

        # --- 2. Estrazione Prezzo Attuale ---
        # Si cerca l'elemento che contiene il prezzo completo (più affidabile)
        price_whole_element = soup.find('span', class_='a-price-whole') 
        price_fraction_element = soup.find('span', class_='a-price-fraction')

        if price_whole_element and price_fraction_element:
            # Combina intero e decimale
            price_text = price_whole_element.get_text(strip=True).replace('.', '') + '.' + price_fraction_element.get_text(strip=True)
            try:
                # Rimuove virgole o simboli (tranne il punto decimale)
                product_data["current_price"] = float(price_text)
            except ValueError:
                logger.warning(f"Errore nella conversione del prezzo attuale: {price_text}")

        # --- 3. Estrazione Prezzo Precedente (e Sconto) ---
        # Cerca il prezzo barrato (Old Price)
        old_price_element = soup.find('span', class_='a-text-strike')
        if old_price_element:
            price_text = old_price_element.get_text(strip=True).replace('€', '').replace(',', '.')
            # Filtra solo i numeri e il punto decimale
            cleaned_price = re.sub(r'[^\d.]', '', price_text)
            try:
                product_data["previous_price"] = float(cleaned_price)
            except ValueError:
                logger.warning(f"Errore nella conversione del prezzo precedente: {cleaned_price}")

        # --- 4. Estrazione Foto (Miniatura principale) ---
        # La foto è spesso nel tag img principale con id 'landingImage' o simile.
        image_element = soup.find('img', {'id': 'landingImage'}) or soup.find('img', {'id': 'imgBliss'})

        if image_element:
            image_url_data = image_element.get('data-a-dynamic-image')

            # Se esiste l'attributo dinamico (che è un JSON string di URL e dimensioni)
            if image_url_data:
                # Cerca il primo URL valido all'interno della stringa JSON
                match = re.search(r'\"(https?://[^\"]+)\"', image_url_data)
                if match:
                    product_data["image_url"] = match.group(1)
            else:
                # Fallback sull'attributo src se non c'è il dato dinamico
                product_data["image_url"] = image_element.get('src')

        # Se il titolo non è stato trovato (il fallimento primario)
        if not product_data["title"]:
            logger.error("Scraping Fallito: Titolo non trovato. Controlla se la pagina ha un CAPTCHA.")
            # Stampa i primi 1000 caratteri del codice HTML per l'analisi
            logger.debug(str(response.content[:1000]))
            return None 

        return product_data

    except requests.exceptions.HTTPError as e:
        logger.error(f"Errore HTTP ({response.status_code}) - Probabile blocco di Amazon: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Errore di richiesta (timeout o connessione) durante lo scraping: {e}")
        return None
    except Exception as e:
        logger.error(f"Errore generico nello scraping del prodotto {asin}: {e}")
        return None