# Webhook Wildix

Un webhook server in Python per ricevere e gestire messaggi da un centralino Wildix.
Server HTTP locale con reverse proxy Nginx per HTTPS.

## Caratteristiche

- **Server Flask**: Riceve webhook HTTP da Wildix
- **Salvataggio JSON**: I messaggi vengono salvati in file JSON organizzati per data
- **Logging**: Sistema di logging integrato per monitorare le attività
- **Health Check**: Endpoint per verificare lo stato del servizio
- **Conteggio Messaggi**: API per visualizzare statistiche sui messaggi ricevuti
- **Nginx Ready**: Configurazione per reverse proxy HTTPS

## Struttura del Progetto

```
webhook-wildix/
├── app.py              # Server principale Flask
├── requirements.txt    # Dipendenze Python
├── README.md          # Questo file
├── .env.example       # Template per variabili d'ambiente
├── NGINX_SETUP.md     # Configurazione Nginx reverse proxy
├── start_webhook.ps1  # Script di avvio Windows
├── messages/          # Cartella dove vengono salvati i messaggi
├── logs/              # Cartella per i log
└── run.py             # Script per avvio in produzione
```

## Installazione

1. **Clona o crea il progetto**:
   ```bash
   cd c:\sviluppo\python\centralino\webhook-wildix
   ```

2. **Crea un ambiente virtuale**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Su Windows
   ```

3. **Installa le dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```

## Utilizzo

### Avvio in Sviluppo

```bash
python app.py
```

Il server sarà disponibile su `http://localhost:9001`

### Avvio in Produzione

```bash
python run.py
```

Oppure usando direttamente Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:9001 app:app
```

## Endpoint Disponibili

### POST /webhook/wildix
- **Scopo**: Riceve i webhook da Wildix
- **Formato**: Accetta JSON, form-data, o raw data
- **Risposta**: JSON con status e ID messaggio

**Esempio di utilizzo**:
```bash
curl -X POST http://localhost:9001/webhook/wildix \
  -H "Content-Type: application/json" \
  -d '{"tipo": "chiamata", "numero": "+391234567890", "durata": 120}'
```

### GET /health
- **Scopo**: Health check del servizio
- **Risposta**: Status del servizio

### GET /messages/count
- **Scopo**: Conta i messaggi salvati
- **Risposta**: Statistiche sui messaggi per file

## Configurazione Wildix

Per configurare Wildix per inviare webhook a questo server:

1. Accedi all'interfaccia amministrativa di Wildix
2. Vai su **Integrations** > **Webhooks**
3. Crea un nuovo webhook con URL: `https://yourdomain.com/webhook/wildix`
4. Seleziona gli eventi che vuoi ricevere (chiamate, messaggi, ecc.)

## Formato Messaggi Salvati

I messaggi vengono salvati in file JSON con questa struttura:

```json
[
  {
    "id": "uuid-generato",
    "timestamp": "2024-11-15T10:30:00.123456",
    "data": {
      // Dati ricevuti da Wildix
    },
    "source": "wildix_webhook",
    "request_info": {
      "method": "POST",
      "headers": {...},
      "remote_addr": "192.168.1.100",
        "url": "http://localhost:9001/webhook/wildix"
    }
  }
]
```

## File di Log

I messaggi vengono organizzati per data:
- `messages/wildix_messages_2024-11-15.json`
- `messages/wildix_messages_2024-11-16.json`
- ecc.

## Architettura con Nginx

```
Wildix → HTTPS → Nginx → HTTP → Flask App (localhost:9001)
```

Vedi `NGINX_SETUP.md` per la configurazione completa del reverse proxy.

## Prossimi Sviluppi

- [ ] Integrazione con database (PostgreSQL/MySQL)
- [ ] Sistema di code per elaborazione asincrona
- [ ] API REST per gestione messaggi
- [ ] Dashboard web per monitoraggio
- [ ] Autenticazione e sicurezza
- [ ] Backup automatico messaggi

## Troubleshooting

### Problema: Server non si avvia
- Verifica che la porta 9001 non sia già in uso
- Controlla che l'ambiente virtuale sia attivo
- Verifica l'installazione delle dipendenze

### Problema: Wildix non invia webhook
- Controlla che l'URL sia raggiungibile da Wildix
- Verifica la configurazione del firewall
- Controlla i log di Wildix per errori

### Problema: Messaggi non vengono salvati
- Verifica i permessi di scrittura nella cartella `messages/`
- Controlla i log dell'applicazione per errori

## Contributi

Per contribuire al progetto:
1. Fork del repository
2. Crea un branch per la feature
3. Commit delle modifiche
4. Push del branch
5. Crea una Pull Request