from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
import uuid
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
MESSAGES_DIR = "messages"
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
    """Inizializza il pool di connessioni e crea la tabella se non esiste"""
    global db_pool
    try:
        # Crea il pool di connessioni
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            **DB_CONFIG
        )
        
        logger.info(f"Pool di connessioni PostgreSQL creato")
        
        # Crea la tabella se non esiste
        create_table_if_not_exists()
        
        return True
        
    except Exception as e:
        logger.error(f"Errore nell'inizializzazione del database: {str(e)}")
        logger.warning("Continuero' con salvataggio su file JSON")
        return False

def create_table_if_not_exists():
    """Crea la tabella messaggi_wildix se non esiste"""
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id SERIAL PRIMARY KEY,
        cliente_id VARCHAR(255) NOT NULL,
        message JSONB NOT NULL,
        data_creazione TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        processato BOOLEAN DEFAULT FALSE,
        data_processato TIMESTAMP WITH TIME ZONE NULL
    );
    
    -- Crea indici per ottimizzare le query
    CREATE INDEX IF NOT EXISTS idx_cliente_id ON {TABLE_NAME} (cliente_id);
    CREATE INDEX IF NOT EXISTS idx_processato ON {TABLE_NAME} (processato);
    CREATE INDEX IF NOT EXISTS idx_data_creazione ON {TABLE_NAME} (data_creazione);
    """
    
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()
            logger.info(f"✅ Tabella {TABLE_NAME} verificata/creata")
            
    except Exception as e:
        logger.error(f"❌ Errore nella creazione della tabella: {str(e)}")
        if conn:
            conn.rollback()
        raise
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
        logger.warning("⚠️  Database non disponibile, salvo su file")
        return save_message_to_file(message_data)
    
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            # Insert del messaggio nella tabella
            insert_sql = f"""
            INSERT INTO {TABLE_NAME} (cliente_id, message, processato) 
            VALUES (%s, %s, %s) 
            RETURNING id, data_creazione
            """
            
            cur.execute(insert_sql, (cliente_id, json.dumps(message_data), False))
            result = cur.fetchone()
            
            conn.commit()
            
            message_id = result[0]
            data_creazione = result[1]
            
            logger.info(f"🗄️  Messaggio salvato nel DB: ID={message_id}, Cliente={cliente_id}")
            return str(message_id)
            
    except Exception as e:
        logger.error(f"❌ Errore nel salvare nel database: {str(e)}")
        if conn:
            conn.rollback()
        # Fallback su file in caso di errore DB
        logger.info("💾 Fallback: salvataggio su file")
        return save_message_to_file(message_data)
        
    finally:
        if conn:
            db_pool.putconn(conn)

def save_message_to_file(message_data):
    """Salva il messaggio in un file JSON (fallback)"""
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
        
        logger.info(f"💾 Messaggio salvato su file: {message_id} in {filepath}")
        return message_id
        
    except Exception as e:
        logger.error(f"Errore nel salvare il messaggio: {str(e)}")
        raise

@app.route('/', methods=['POST'])
@app.route('/<string:cliente_id>', methods=['POST'])
def wildix_webhook(cliente_id=None):
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
        
        # Usa il cliente_id dal path se disponibile, altrimenti estrailo dall'URL
        if not cliente_id:
            cliente_id = get_cliente_id_from_url(request.url)
        
        logger.info(f"Cliente ID identificato: {cliente_id}")
        
        # Salva il messaggio nel database (con fallback su file)
        message_id = save_message_to_database(message_data, cliente_id)
        
        # Risposta di successo
        response = {
            "status": "success",
            "message": "Webhook ricevuto e salvato",
            "message_id": message_id,
            "cliente_id": cliente_id,
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