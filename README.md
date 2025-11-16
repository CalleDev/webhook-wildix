# Webhook Wildix

Un webhook server in Python per ricevere e gestire messaggi da un centralino Wildix.

## ✨ Caratteristiche

- **Server Flask**: Riceve webhook HTTP da Wildix sulla rete
- **Autenticazione**: HMAC-SHA256 con secret condiviso  
- **Salvataggio JSON**: Messaggi organizzati per data
- **Health Check**: Monitoraggio stato servizio
- **Logging**: Sistema integrato per debug e audit

## 📁 Struttura

```
webhook-wildix/
├── app.py                    # Server Flask principale
├── requirements.txt          # Dipendenze Python  
├── .env.example             # Template configurazione
├── start_webhook.ps1        # Script avvio Windows
├── setup_wildix_secret.ps1  # Configurazione secret
├── check_config.ps1         # Verifica configurazione
├── test.py                  # Test webhook
├── messages/                # Messaggi salvati (auto-creata)
└── logs/                    # Log applicazione (auto-creata)
```

## 🚀 Setup Rapido

```powershell
# 1. Crea ambiente virtuale
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Installa dipendenze  
pip install -r requirements.txt

# 3. Configura secret Wildix
.\setup_wildix_secret.ps1 -Secret "your-wildix-secret"

# 4. Avvia server
.\start_webhook.ps1
```

## 🎯 Endpoint

- **Webhook**: `http://your-server-ip:9001/webhook/wildix`
- **Health**: `http://your-server-ip:9001/health`  
- **Stats**: `http://your-server-ip:9001/messages/count`

## ⚙️ Configurazione Wildix

Nel pannello admin Wildix:
1. Vai su **Integrations** > **Webhooks**
2. **URL**: `http://your-server-ip:9001/webhook/wildix`
3. **Secret**: Lo stesso configurato nel webhook
4. **Method**: POST, Content-Type: application/json
5. Seleziona gli eventi che vuoi ricevere (chiamate, messaggi, ecc.)

## 🔐 Sicurezza

Il webhook richiede autenticazione tramite secret HMAC-SHA256:

```powershell
# Configura secret (obbligatorio)
.\setup_wildix_secret.ps1 -Secret "your-secret-from-wildix"
```

⚠️ **Importante**: Usa sempre lo stesso secret su Wildix e webhook!

## 📋 Endpoint API

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/webhook/wildix` | POST | Riceve webhook da Wildix (JSON/form-data/raw) |
| `/health` | GET | Health check del servizio |
| `/messages/count` | GET | Statistiche messaggi salvati |

## 💾 Formato Dati

I messaggi vengono salvati come JSON organizzati per data:

```json
[
  {
    "id": "uuid-messaggio",
    "timestamp": "2024-11-15T10:30:00.123456",
    "data": { /* Dati Wildix */ },
    "source": "wildix_webhook",
    "request_info": {
      "method": "POST",
      "remote_addr": "192.168.1.100"
    }
  }
]
```

**File salvati**: `messages/wildix_messages_YYYY-MM-DD.json`

## 🏗️ Architettura Produzione

```
Wildix PBX → HTTPS → Nginx (443) → HTTP → Flask (9001)
```

Server Flask ascolta su `0.0.0.0:9001` per accesso di rete.

## 🧪 Test

```powershell
# Test webhook locale
python test.py

# Test health check
curl http://localhost:9001/health

# Test con dati personalizzati
curl -X POST http://localhost:9001/webhook/wildix \
  -H "Content-Type: application/json" \
  -d '{"tipo": "chiamata", "numero": "+391234567890"}'
```

## 🔧 Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| Server non si avvia | Verifica porta 9001 libera e ambiente virtuale attivo |
| Wildix non invia webhook | Controlla URL raggiungibile e firewall |
| Messaggi non salvati | Verifica permessi cartella `messages/` |
| Errore autenticazione | Controlla secret identico su Wildix e webhook |

## 🚀 Roadmap

- [ ] Database (PostgreSQL/MySQL) 
- [ ] Sistema code asincrono
- [ ] Dashboard web monitoraggio
- [ ] Backup automatico