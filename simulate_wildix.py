import hmac
import hashlib
import json
import sys

def generate_curl_command(customer_id, secret, data):
    """
    Genera un comando curl con la firma HMAC-SHA256 corretta per simulare Wildix.
    """
    # 1. Prepara il body come stringa JSON compatta (senza spazi)
    # Wildix invia il JSON compatto, e il nostro server lo normalizza così
    body_str = json.dumps(data, separators=(',', ':'))
    
    # 2. Calcola la firma HMAC-SHA256
    signature = hmac.new(
        secret.encode('utf-8'),
        body_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"--- Dettagli Simulazione ---")
    print(f"Customer ID: {customer_id}")
    print(f"Secret usato: {secret}")
    print(f"Body (compact): {body_str}")
    print(f"Signature calcolata: {signature}")
    print(f"--------------------------\n")
    
    # 3. Costruisci il comando curl
    # Nota: Su Windows PowerShell bisogna fare attenzione agli escape delle virgolette
    # Questo formato dovrebbe funzionare su Bash e PowerShell (con qualche accortezza)
    
    print("Comando CURL (copia e incolla nel terminale):")
    print(f'curl -X POST "http://localhost:9001/{customer_id}" -H "Content-Type: application/json" -H "X-Signature: {signature}" -d \'{body_str}\'')

if __name__ == "__main__":
    # CONFIGURAZIONE TEST
    # Sostituisci con i valori reali che hai nel database
    CUSTOMER_ID = "5c2FHlZcbf5fikLedLMB" 
    SECRET = "FNmSzk5xAd2gaxnyUQZZSVq8bao30G" # Il valore che vedevi nei log (assumendo sia il secret)
    
    DATA = {
        "event": "new_call",
        "caller": "123456",
        "callee": "789012",
        "timestamp": 1234567890
    }
    
    generate_curl_command(CUSTOMER_ID, SECRET, DATA)
