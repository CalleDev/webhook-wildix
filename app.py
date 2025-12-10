from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
import logging
import hmac
import hashlib
import re
from urllib.parse import urlparse
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.pool
import base64
from cryptography.fernet import Fernet

# Carica variabili d'ambiente
load_dotenv()

# Configurazione logging
log_level = os.getenv('LOG_LEVEL', 'INFO')

# Crea directory logs se non esiste
os.makedirs("logs", exist_ok=True)
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")

# Configurazione logging con file e console (UTF-8 encoding)
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.join("logs", f"wildix_webhook_{datetime.now().strftime('%Y-%m-%d')}.log"),
            encoding='utf-8'
        ),
        logging.StreamHandler()  # Per vedere i log anche in console
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurazione cartelle
LOGS_DIR = "logs"

# Configurazione PostgreSQL
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'user': os.getenv('POSTGRES_USER', 'wildix_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'wildix_password'),
    'database': os.getenv('POSTGRES_DATABASE', 'wildix_webhook')
}

TABLE_NAME = os.getenv('POSTGRES_TABLE', 'messaggi_wildix')

# Pool di connessioni PostgreSQL
db_pool = None

def init_database():
    """Inizializza il pool di connessioni e verifica che la tabella esista"""
    global db_pool
    try:
        # Crea il pool di connessioni
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            **DB_CONFIG
        )
        
        logger.info(f"Pool di connessioni PostgreSQL creato")
        
        # Verifica che la tabella esista
        if not check_table_exists():
            logger.error(f"❌ CRITICO: La tabella {TABLE_NAME} non esiste nel database!")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Errore nell'inizializzazione del database: {str(e)}")
        return False

def check_table_exists():
    """Verifica se la tabella esiste"""
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Verifica esistenza tabella
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)", (TABLE_NAME,))
            exists = cur.fetchone()[0]
            
            if exists:
                logger.info(f"✅ Tabella {TABLE_NAME} trovata")
                return True
            else:
                logger.error(f"❌ Tabella {TABLE_NAME} NON trovata")
                return False
            
    except Exception as e:
        logger.error(f"❌ Errore nella verifica della tabella: {str(e)}")
        return False
    finally:
        if conn:
            db_pool.putconn(conn)

def get_customer_id_from_url(url):
    """Estrae il cliente_id dall'URL della richiesta"""
    try:
        # Parse dell'URL per ottenere il path
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Estrae la prima parte del path (dopo il primo /)
        # Esempio: /9efd89dfg9f8gd79 -> 9efd89dfg9f8gd79
        path_parts = path.strip('/').split('/')
        
        # Se c'è almeno una parte nel path, usa quella come client_id
        if path_parts and path_parts[0]:
            customer_id = path_parts[0]
            # Verifica se sembra un codice client valido
            if re.match(r'^[a-zA-Z0-9]{3,}$', customer_id):
                logger.info(f"Cliente ID estratto dall'URL: {customer_id}")
                return customer_id
        
        # Fallback: usa l'indirizzo IP del client
        logger.warning("⚠️  Impossibile estrarre cliente_id dall'URL, uso 'unknown'")
        return 'unknown'
        
    except Exception as e:
        logger.error(f"❌ Errore nell'estrazione del cliente_id: {str(e)}")
        return 'error'

def ensure_directories():
    """Crea le cartelle necessarie se non esistono"""
    os.makedirs(LOGS_DIR, exist_ok=True)

# Encryption helpers
def get_cipher_suite():
    # Derive a 32-byte key from the app SECRET_KEY
    key = hashlib.sha256(SECRET_KEY.encode()).digest()
    key_b64 = base64.urlsafe_b64encode(key)
    return Fernet(key_b64)

def encrypt_value(value: str) -> str:
    if not value: return None
    cipher = get_cipher_suite()
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    if not value: return None
    try:
        cipher = get_cipher_suite()
        return cipher.decrypt(value.encode()).decode()
    except Exception:
        return value # Return as is if decryption fails

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
         # Rimuovi prefisso se presente (es. "sha256=")
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        # Calcola HMAC della richiesta
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            request_data,
            hashlib.sha256
        ).hexdigest()
        
        # Confronto sicuro
        return hmac.compare_digest(expected_signature, signature)

        
    except Exception as e:
        logger.error(f"Errore nella validazione del secret: {str(e)}")
        return False

def save_message_to_database(message_data, customer_id):
    """Salva il messaggio nel database PostgreSQL"""
    if not db_pool:
        logger.error("⚠️  Database non disponibile, impossibile salvare il messaggio")
        raise Exception("Database non disponibile")
    
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Insert del messaggio nella tabella
            insert_sql = f"""
            INSERT INTO {TABLE_NAME} (customer_id, message, processed) 
            VALUES (%s, %s, %s)
            """
            
            json_message = json.dumps(message_data)
            logger.info(f"📝 Esecuzione SQL: {insert_sql}")
            logger.info(f"📝 Parametri: customer_id={customer_id}, message length={len(json_message)}")
            
            cur.execute(insert_sql, (customer_id, json_message, False))
            
            conn.commit()
            
            logger.info(f"🗄️  Messaggio salvato nel DB per Cliente={customer_id}")
            return "inserted"
            
    except Exception as e:
        logger.error(f"❌ Errore nel salvare nel database: {str(e)}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        if conn:
            db_pool.putconn(conn)

def get_client_secret(customer_id):
    """Recupera il secret del cliente dal database"""
    if not db_pool:
        logger.error("Database non disponibile per recupero secret")
        return None
    
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Recupera il secret dalla tabella webhook_secret
            # TODO: Se il secret è criptato, implementare la decriptazione (es. pgp_sym_decrypt)
            query = "SELECT secret FROM webhook_secret WHERE customer_id = %s"
            cur.execute(query, (customer_id,))
            result = cur.fetchone()
            
            if result:
                return result[0]
            return None
            
    except Exception as e:
        logger.error(f"Errore nel recupero del secret per {customer_id}: {str(e)}")
        return None
    finally:
        if conn:
            db_pool.putconn(conn)

@app.route('/', methods=['POST'])
@app.route('/<string:customer_id>', methods=['POST'])
def wildix_webhook(customer_id=None):
    """Endpoint principale per ricevere i webhook da Wildix"""
    try:
        # Log dettagliato della richiesta in arrivo
        logger.info(f"🔄 Richiesta ricevuta da {request.remote_addr}")
        logger.info(f"📋 Method: {request.method}")
        logger.info(f"🌐 URL: {request.url}")
        
        # 1. Identifica il cliente_id (dal path o dall'URL)
        if not customer_id:
            customer_id = get_customer_id_from_url(request.url)
            
        logger.info(f"Cliente ID identificato: {customer_id}")
        
        # 2. Recupera il secret specifico per il cliente dal DB
        db_wildix_secret = get_client_secret(customer_id)
        wildix_secret = decrypt_value(db_wildix_secret)

        logger.info(f"------SECRET_KEY: {SECRET_KEY}")
        logger.info(f"------db_wildix_secret: {db_wildix_secret}")
        logger.info(f"------wildix_secret: {wildix_secret}")


        
        if not wildix_secret:
            logger.warning(f"⚠️ Nessun secret trovato per il cliente {customer_id} - Richiesta rifiutata")
            return jsonify({
                "status": "error",
                "message": "Unauthorized - Client unknown or no secret",
                "timestamp": datetime.now().isoformat()
            }), 401

        # 3. Ottieni i dati e valida la firma
        content_type = request.content_type
        raw_data = request.get_data()
        signature = request.headers.get('X-Wildix-Signature') or request.headers.get('X-Hub-Signature-256')
        
        logger.info(f"🔐 Validazione secret per cliente {customer_id}")
        auth_result = validate_wildix_secret(raw_data, signature, wildix_secret)
        
        if not auth_result:
            logger.warning(f"❌ Richiesta NON AUTORIZZATA da {request.remote_addr} per cliente {customer_id}")
            return jsonify({
                "status": "error",
                "message": "Unauthorized - Invalid signature",
                "timestamp": datetime.now().isoformat()
            }), 401
        
        logger.info(f"✅ Richiesta webhook autorizzata per cliente {customer_id}")
        
        # 4. Elabora il contenuto
        if content_type and 'application/json' in content_type:
            message_data = request.get_json(force=True)
        else:
            if request.form:
                message_data = dict(request.form)
            else:
                message_data = {
                    "raw_data": raw_data.decode('utf-8'),
                    "content_type": content_type
                }
        
        # Aggiungi metadati
        message_data["request_info"] = {
            "method": request.method,
            "headers": dict(request.headers),
            "remote_addr": request.remote_addr,
            "url": request.url,
            "authenticated": True,
            "signature_validated": True
        }
        
        # 5. Salva nel DB
        message_id = save_message_to_database(message_data, customer_id)
        
        return jsonify({
            "status": "success",
            "message": "Webhook ricevuto e salvato",
            "message_id": message_id,
            "customer_id": customer_id,
            "timestamp": datetime.now().isoformat()
        }), 200
        
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
        if not db_pool:
            return jsonify({
                "error": "Database non disponibile",
                "timestamp": datetime.now().isoformat()
            }), 503

        conn = None
        try:
            conn = db_pool.getconn()
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
                count = cur.fetchone()[0]
                
                return jsonify({
                    "total_messages": count,
                    "timestamp": datetime.now().isoformat()
                }), 200
        finally:
            if conn:
                db_pool.putconn(conn)
        
    except Exception as e:
        logger.error(f"Errore nel conteggio messaggi: {str(e)}")
        return jsonify({
            "error": "Errore nel conteggio messaggi",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    # Crea le cartelle necessarie
    ensure_directories()
    
    # Inizializza il database
    db_available = init_database()
    
    # Configurazione da variabili d'ambiente
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 9001))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Avvia il server
    logger.info(f"Avvio del webhook server Wildix su {host}:{port} (debug={debug})")
    logger.info(f"Secret configurato: {'Sì' if os.getenv('WILDIX_SECRET') else 'No'}")
    logger.info(f"Database PostgreSQL: {'Attivo' if db_available else 'Non disponibile (fallback su file)'}")
    app.run(host=host, port=port, debug=debug)