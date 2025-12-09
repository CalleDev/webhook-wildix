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

# Carica variabili d'ambiente
load_dotenv()

# Configurazione logging
log_level = os.getenv('LOG_LEVEL', 'INFO')

# Crea directory logs se non esiste
os.makedirs("logs", exist_ok=True)

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

def get_cliente_id_from_url(url):
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
            cliente_id = path_parts[0]
            # Verifica se sembra un codice client valido
            if re.match(r'^[a-zA-Z0-9]{3,}$', cliente_id):
                logger.info(f"Cliente ID estratto dall'URL: {cliente_id}")
                return cliente_id
        
        # Fallback: usa l'indirizzo IP del client
        logger.warning("⚠️  Impossibile estrarre cliente_id dall'URL, uso 'unknown'")
        return 'unknown'
        
    except Exception as e:
        logger.error(f"❌ Errore nell'estrazione del cliente_id: {str(e)}")
        return 'error'

def ensure_directories():
    """Crea le cartelle necessarie se non esistono"""
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
        
        # Confronto sicuro (case-insensitive per la signature hex)
        match = hmac.compare_digest(expected_signature, signature.lower())
        logger.info(f"🔍 Match delle signature: {match}")
        return match
        
    except Exception as e:
        logger.error(f"Errore nella validazione del secret: {str(e)}")
        return False

def save_message_to_database(message_data, cliente_id):
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
            INSERT INTO {TABLE_NAME} (cliente_id, message, processato) 
            VALUES (%s, %s, %s)
            """
            
            json_message = json.dumps(message_data)
            logger.info(f"📝 Esecuzione SQL: {insert_sql}")
            logger.info(f"📝 Parametri: cliente_id={cliente_id}, message length={len(json_message)}")
            
            cur.execute(insert_sql, (cliente_id, json_message, False))
            
            conn.commit()
            
            logger.info(f"🗄️  Messaggio salvato nel DB per Cliente={cliente_id}")
            return "inserted"
            
    except Exception as e:
        logger.error(f"❌ Errore nel salvare nel database: {str(e)}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        if conn:
            db_pool.putconn(conn)

def get_client_secret(cliente_id):
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
            query = "SELECT secret FROM webhook_secret WHERE client_id = %s"
            cur.execute(query, (cliente_id,))
            result = cur.fetchone()
            
            if result:
                return result[0]
            return None
            
    except Exception as e:
        logger.error(f"Errore nel recupero del secret per {cliente_id}: {str(e)}")
        return None
    finally:
        if conn:
            db_pool.putconn(conn)

@app.route('/', methods=['POST'])
@app.route('/<string:cliente_id>', methods=['POST'])
def wildix_webhook(cliente_id=None):
    """Endpoint principale per ricevere i webhook da Wildix"""
    try:
        # Log dettagliato della richiesta in arrivo
        logger.info(f"🔄 Richiesta ricevuta da {request.remote_addr}")
        logger.info(f"📋 Method: {request.method}")
        logger.info(f"🌐 URL: {request.url}")
        
        # 1. Identifica il cliente_id (dal path o dall'URL)
        if not cliente_id:
            cliente_id = get_cliente_id_from_url(request.url)
            
        logger.info(f"Cliente ID identificato: {cliente_id}")
        
        # 2. Recupera il secret specifico per il cliente dal DB
        wildix_secret = get_client_secret(cliente_id)
        
        if not wildix_secret:
            logger.warning(f"⚠️ Nessun secret trovato per il cliente {cliente_id} - Richiesta rifiutata")
            return jsonify({
                "status": "error",
                "message": "Unauthorized - Client unknown or no secret",
                "timestamp": datetime.now().isoformat()
            }), 401

        # 3. Ottieni i dati e valida la firma
        content_type = request.content_type
        raw_data = request.get_data()
        signature = request.headers.get('x-signature') or request.headers.get('X-Signature')
        
        logger.info(f"🔐 Validazione secret per cliente {cliente_id}")
        auth_result = validate_wildix_secret(raw_data, signature, wildix_secret)
        
        if not auth_result:
            logger.warning(f"❌ Richiesta NON AUTORIZZATA da {request.remote_addr} per cliente {cliente_id}")
            return jsonify({
                "status": "error",
                "message": "Unauthorized - Invalid signature",
                "timestamp": datetime.now().isoformat()
            }), 401
        
        logger.info(f"✅ Richiesta webhook autorizzata per cliente {cliente_id}")
        
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
        message_id = save_message_to_database(message_data, cliente_id)
        
        return jsonify({
            "status": "success",
            "message": "Webhook ricevuto e salvato",
            "message_id": message_id,
            "cliente_id": cliente_id,
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