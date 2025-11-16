from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
import uuid
import logging
import hmac
import hashlib
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Configurazione logging
log_level = os.getenv('LOG_LEVEL', 'INFO')

# Crea directory logs se non esiste
os.makedirs("logs", exist_ok=True)

# Configurazione logging con file e console
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("logs", f"wildix_webhook_{datetime.now().strftime('%Y-%m-%d')}.log")),
        logging.StreamHandler()  # Per vedere i log anche in console
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurazione cartelle
MESSAGES_DIR = "messages"
LOGS_DIR = "logs"

def ensure_directories():
    """Crea le cartelle necessarie se non esistono"""
    os.makedirs(MESSAGES_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

def validate_wildix_secret(request_data, signature, secret):
    """Valida il secret Wildix usando HMAC-SHA256"""
    logger.info(f"🔍 Inizio validazione secret")
    logger.info(f"🔍 Secret presente: {'Sì' if secret else 'No'}")
    logger.info(f"🔍 Signature presente: {'Sì' if signature else 'No'}")
    
    if not secret:
        logger.warning("⚠️ Nessun secret configurato - accetto tutte le richieste")
        return True
    
    if not signature:
        logger.warning("⚠️ Nessuna signature ricevuta da Wildix")
        return False
    
    try:
        original_signature = signature
        logger.info(f"🔍 Signature originale: {original_signature}")
        
        # Wildix non usa prefisso sha256=, è solo l'hash hex
        # Non rimuoviamo nessun prefisso
        
        # Per Wildix, dobbiamo usare il JSON string del body, non i raw data
        # Se i dati sono JSON, li convertiamo in stringa come fa Wildix
        try:
            # Prova a parsare come JSON e riconvertire in stringa (come fa Node.js)
            json_data = json.loads(request_data.decode('utf-8'))
            data_for_hmac = json.dumps(json_data, separators=(',', ':'))
            logger.info(f"🔍 Uso JSON string per HMAC: {data_for_hmac}")
        except:
            # Se non è JSON valido, usa i raw data come stringa
            data_for_hmac = request_data.decode('utf-8')
            logger.info(f"🔍 Uso raw data per HMAC: {data_for_hmac}")
        
        # Calcola HMAC della richiesta (come fa Wildix)
        logger.info(f"🔍 Calcolo HMAC con secret lunghezza: {len(secret)}")
        logger.info(f"🔍 Dati per HMAC lunghezza: {len(data_for_hmac)}")
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            data_for_hmac.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.info(f"🔍 Signature calcolata: {expected_signature}")
        logger.info(f"🔍 Signature ricevuta: {signature}")
        
        # Confronto sicuro
        match = hmac.compare_digest(expected_signature, signature)
        logger.info(f"🔍 Match delle signature: {match}")
        return match
        
    except Exception as e:
        logger.error(f"Errore nella validazione del secret: {str(e)}")
        return False

def save_message_to_file(message_data):
    """Salva il messaggio in un file JSON"""
    try:
        # Genera un ID univoco per il messaggio
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Prepara i dati del messaggio
        message_record = {
            "id": message_id,
            "timestamp": timestamp,
            "data": message_data,
            "source": "wildix_webhook"
        }
        
        # Nome del file basato sulla data
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"wildix_messages_{date_str}.json"
        filepath = os.path.join(MESSAGES_DIR, filename)
        
        # Se il file esiste, carica i messaggi esistenti
        messages = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        
        # Aggiungi il nuovo messaggio
        messages.append(message_record)
        
        # Salva tutti i messaggi
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Messaggio salvato: {message_id} in {filepath}")
        return message_id
        
    except Exception as e:
        logger.error(f"Errore nel salvare il messaggio: {str(e)}")
        raise

@app.route('/webhook/wildix', methods=['POST'])
def wildix_webhook():
    """Endpoint principale per ricevere i webhook da Wildix"""
    try:
        # Log dettagliato della richiesta in arrivo
        logger.info(f"🔄 Richiesta ricevuta da {request.remote_addr}")
        logger.info(f"📋 Method: {request.method}")
        logger.info(f"🌐 URL: {request.url}")
        logger.info(f"📄 Content-Type: {request.content_type}")
        logger.info(f"📏 Content-Length: {request.headers.get('Content-Length', 'N/A')}")
        
        # Ottieni i dati della richiesta
        content_type = request.content_type
        raw_data = request.get_data()
        
        logger.info(f"📦 Raw data length: {len(raw_data)} bytes")
        if raw_data:
            logger.info(f"📝 Raw data preview: {raw_data[:200]}..." if len(raw_data) > 200 else f"📝 Raw data: {raw_data}")
        
        # Validazione del secret Wildix
        wildix_secret = os.getenv('WILDIX_SECRET')
        signature = request.headers.get('x-signature') or request.headers.get('X-Signature')
        
        # Log dettagliato per debug autenticazione
        logger.info(f"🔐 Headers ricevuti: {dict(request.headers)}")
        logger.info(f"🔑 Secret configurato: {'Sì' if wildix_secret else 'No'}")
        logger.info(f"✍️ Signature ricevuta: {signature}")
        
        if signature:
            logger.info(f"📏 Lunghezza signature: {len(signature)}")
            logger.info(f"🎯 Tipo signature: {type(signature)}")
        
        auth_result = validate_wildix_secret(raw_data, signature, wildix_secret)
        logger.info(f"🛡️ Risultato validazione: {auth_result}")
        
        if not auth_result:
            logger.warning(f"❌ Richiesta NON AUTORIZZATA da {request.remote_addr}")
            logger.warning(f"❌ Secret presente: {'Sì' if wildix_secret else 'No'}")
            logger.warning(f"❌ Signature presente: {'Sì' if signature else 'No'}")
            return jsonify({
                "status": "error",
                "message": "Unauthorized - Secret non valido",
                "timestamp": datetime.now().isoformat()
            }), 401
        
        # Log della richiesta ricevuta (dopo validazione)
        logger.info(f"Richiesta webhook autorizzata - Content-Type: {content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Gestisci diversi tipi di contenuto
        if content_type and 'application/json' in content_type:
            message_data = request.get_json(force=True)
        else:
            # Se non è JSON, prova a ottenere i dati come form o raw
            if request.form:
                message_data = dict(request.form)
            else:
                message_data = {
                    "raw_data": raw_data.decode('utf-8'),
                    "content_type": content_type
                }
        
        # Aggiungi informazioni sulla richiesta
        message_data["request_info"] = {
            "method": request.method,
            "headers": dict(request.headers),
            "remote_addr": request.remote_addr,
            "url": request.url,
            "authenticated": bool(wildix_secret),
            "signature_validated": True
        }
        
        # Salva il messaggio
        message_id = save_message_to_file(message_data)
        
        # Risposta di successo
        response = {
            "status": "success",
            "message": "Webhook ricevuto e salvato",
            "message_id": message_id,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Errore nell'elaborazione del webhook: {str(e)}")
        error_response = {
            "status": "error",
            "message": "Errore nell'elaborazione del webhook",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return jsonify(error_response), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint di health check"""
    return jsonify({
        "status": "healthy",
        "service": "Wildix Webhook Receiver",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/messages/count', methods=['GET'])
def messages_count():
    """Endpoint per contare i messaggi salvati"""
    try:
        total_messages = 0
        files_info = []
        
        if os.path.exists(MESSAGES_DIR):
            for filename in os.listdir(MESSAGES_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(MESSAGES_DIR, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        messages = json.load(f)
                        count = len(messages)
                        total_messages += count
                        files_info.append({
                            "file": filename,
                            "count": count
                        })
        
        return jsonify({
            "total_messages": total_messages,
            "files": files_info,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Errore nel conteggio messaggi: {str(e)}")
        return jsonify({
            "error": "Errore nel conteggio messaggi",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    # Crea le cartelle necessarie
    ensure_directories()
    
    # Configurazione da variabili d'ambiente
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 9001))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Avvia il server
    logger.info(f"Avvio del webhook server Wildix su {host}:{port} (debug={debug})")
    logger.info(f"Secret configurato: {'Sì' if os.getenv('WILDIX_SECRET') else 'No'}")
    app.run(host=host, port=port, debug=debug)