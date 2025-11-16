import os
from app import app
from dotenv import load_dotenv

# Carica le variabili d'ambiente
load_dotenv()

if __name__ == '__main__':
    # Configurazione per produzione (HTTP locale, HTTPS via Nginx)
    host = os.getenv('HOST', '127.0.0.1')  # Solo localhost per sicurezza
    port = int(os.getenv('PORT', 9001))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Avvio server in produzione HTTP su {host}:{port} (HTTPS via Nginx)")
    app.run(host=host, port=port, debug=debug)