# Configurazione Nginx per Webhook Wildix

## 🔧 Setup Nginx Reverse Proxy

Configurazione Nginx per esporre il webhook su HTTPS mentre il server Python rimane in HTTP locale.

### 📋 Configurazione Nginx

Aggiungi al tuo file di configurazione Nginx:

```nginx
# /etc/nginx/sites-available/wildix-webhook
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # Certificati SSL (gestiti da certbot/Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Configurazione SSL sicura
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Headers di sicurezza
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Reverse proxy per il webhook
    location /webhook/wildix {
        proxy_pass http://127.0.0.1:9001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout per webhook
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
        
        # Log specifici per webhook
        access_log /var/log/nginx/wildix-webhook.access.log;
        error_log /var/log/nginx/wildix-webhook.error.log;
    }
    
    # Endpoint di monitoraggio (opzionale)
    location /webhook/health {
        proxy_pass http://127.0.0.1:9001/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Endpoint statistiche (opzionale)
    location /webhook/stats {
        proxy_pass http://127.0.0.1:9001/messages/count;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Limita accesso solo da IP interni (opzionale)
        # allow 192.168.0.0/16;
        # deny all;
    }
}

# Redirect HTTP a HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 🚀 Attivazione Configurazione

```bash
# Abilita il sito
sudo ln -s /etc/nginx/sites-available/wildix-webhook /etc/nginx/sites-enabled/

# Test configurazione
sudo nginx -t

# Ricarica Nginx
sudo systemctl reload nginx
```

### 🎯 URL Finali

Con questa configurazione:
- **Webhook Wildix**: `https://yourdomain.com/webhook/wildix`
- **Health Check**: `https://yourdomain.com/webhook/health`
- **Statistiche**: `https://yourdomain.com/webhook/stats`

### 📊 Vantaggi Nginx

- ✅ **SSL Termination**: Nginx gestisce HTTPS, Python rimane semplice
- ✅ **Performance**: Nginx è ottimizzato per traffico HTTP
- ✅ **Security**: Headers di sicurezza e rate limiting
- ✅ **Monitoring**: Log separati per il webhook
- ✅ **Scalability**: Facile aggiungere load balancing

### 🔒 Sicurezza Aggiuntiva

```nginx
# Rate limiting per webhook
http {
    limit_req_zone $remote_addr zone=webhook:10m rate=10r/m;
    
    server {
        location /webhook/wildix {
            limit_req zone=webhook burst=5 nodelay;
            # ... resto della configurazione
        }
    }
}
```

### 🏃‍♂️ Test Configurazione

```bash
# Test HTTPS
curl https://yourdomain.com/webhook/health

# Test webhook
curl -X POST https://yourdomain.com/webhook/wildix \
  -H "Content-Type: application/json" \
  -d '{"test": "nginx"}'
```

### 📝 Note

1. **Sostituisci** `yourdomain.com` con il tuo dominio
2. **Verifica** che i percorsi dei certificati siano corretti
3. **Configura** il firewall per aprire la porta 443
4. **Controlla** i log in `/var/log/nginx/` per eventuali problemi