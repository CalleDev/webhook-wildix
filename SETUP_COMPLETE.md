# Configurazione Wildix Webhook

## ✅ Setup Completato

Il tuo webhook Wildix è stato configurato con successo! Ecco un riepilogo di quello che hai a disposizione:

### 🎯 **Endpoint Disponibili**

**Locali (HTTP):**
- **Webhook principale**: `POST http://localhost:9001/webhook/wildix`
- **Health check**: `GET http://localhost:9001/health`
- **Statistiche messaggi**: `GET http://localhost:9001/messages/count`

**Pubblici (HTTPS via Nginx):**
- **Webhook principale**: `POST https://yourdomain.com/webhook/wildix`
- **Health check**: `GET https://yourdomain.com/webhook/health`
- **Statistiche**: `GET https://yourdomain.com/webhook/stats`

### 📁 Struttura File

```
webhook-wildix/
├── 📄 app.py                  # Server Flask principale
├── 📄 requirements.txt        # Dipendenze Python
├── 📄 start_webhook.ps1       # Script di avvio rapido
├── 📄 run.py                  # Avvio produzione
├── 📄 test_webhook.py         # Script di test
├── 📂 venv/                   # Ambiente virtuale Python
├── 📂 messages/               # Messaggi salvati (JSON)
│   └── wildix_messages_2025-11-15.json
├── 📂 logs/                   # Log applicazione
└── 📄 .env.example           # Template configurazione
```

### 🚀 Come Avviare

**Opzione 1 - Script automatico:**
```powershell
.\start_webhook.ps1
```

**Opzione 2 - Manuale:**
```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

### 🧪 Test del Webhook

Per testare che tutto funzioni:

```powershell
# Test locale (HTTP)
curl http://localhost:9001/health

# Test pubblico (HTTPS via Nginx)
curl https://yourdomain.com/webhook/health

# Test invio messaggio
curl -X POST https://yourdomain.com/webhook/wildix ^
  -H "Content-Type: application/json" ^
  -d "{\"event_type\": \"test\", \"message\": \"Hello Wildix!\"}"
```

### ⚙️ Configurazione Wildix

Nel pannello di amministrazione Wildix:

1. Vai su **Settings** > **Integrations** > **Webhooks**
2. Crea nuovo webhook con URL: `http://your-server-ip:9001/webhook/wildix`
3. Seleziona gli eventi da ricevere:
   - Call events (chiamate)
   - SMS events (messaggi)
   - Voicemail events (segreteria)
   - Chat events (chat)

### 📋 Formati Messaggio Supportati

Il webhook accetta:
- ✅ JSON (`application/json`)
- ✅ Form data (`application/x-www-form-urlencoded`)
- ✅ Raw data (qualsiasi formato)

### 📊 Messaggi Salvati

I messaggi vengono salvati in `messages/wildix_messages_YYYY-MM-DD.json` con questa struttura:

```json
{
  "id": "uuid-univoco",
  "timestamp": "2025-11-15T14:55:26.519403",
  "data": {
    // Dati ricevuti da Wildix
  },
  "source": "wildix_webhook",
  "request_info": {
    // Informazioni sulla richiesta HTTP
  }
}
```

### 🔧 Configurazione Nginx

Per esporre il webhook su HTTPS:

1. **Configura Nginx**: Vedi `NGINX_SETUP.md` per la configurazione completa
2. **Certificati**: Usa Let's Encrypt con certbot per SSL gratuito
3. **Reverse Proxy**: Nginx inoltra le richieste HTTPS al server HTTP locale

### 🔮 Prossimi Passi

Come hai menzionato, più avanti potrai:

1. **Database**: Migrare da file JSON a PostgreSQL/MySQL
2. **Code**: Implementare Redis/RabbitMQ per elaborazione asincrona
3. **API**: Creare endpoint REST per gestire i messaggi
4. **Dashboard**: Interfaccia web per monitoraggio
5. **Sicurezza**: Autenticazione e validazione webhook

### 🆘 Risoluzione Problemi

- **Porta occupata**: Cambia porta in `app.py` (default: 9001)
- **Permessi cartelle**: Verifica scrittura in `messages/` e `logs/`
- **Nginx**: Controlla configurazione reverse proxy in `NGINX_SETUP.md`
- **Certificati**: Verifica che Let's Encrypt sia configurato correttamente
- **Log**: Controlla sia i log Python che quelli Nginx

Il webhook è pronto per ricevere messaggi da Wildix! 🎉