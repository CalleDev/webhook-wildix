import requests
import json
import hmac
import hashlib
import os
from dotenv import load_dotenv

# Carica configurazione
load_dotenv()

WEBHOOK_URL = "http://localhost:9001/webhook/wildix"
WILDIX_SECRET = os.getenv('WILDIX_SECRET')

def create_signature(data, secret):
    """Crea signature HMAC-SHA256"""
    if not secret:
        return None
    
    if isinstance(data, dict):
        data = json.dumps(data, separators=(',', ':'))
    
    signature = hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"

def test_webhook():
    """Test base del webhook"""
    print("🧪 Test Webhook Wildix")
    print("-" * 30)
    
    # Test health check
    try:
        response = requests.get("http://localhost:9001/health")
        if response.status_code == 200:
            print("✅ Health check OK")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except:
        print("❌ Server non raggiungibile")
        return
    
    # Test messaggio con secret
    test_message = {
        "event_type": "test",
        "message": "Test webhook",
        "timestamp": "2025-11-16T12:00:00Z"
    }
    
    if WILDIX_SECRET:
        json_data = json.dumps(test_message, separators=(',', ':'))
        signature = create_signature(json_data, WILDIX_SECRET)
        headers = {
            'Content-Type': 'application/json',
            'X-Wildix-Signature': signature
        }
        
        try:
            response = requests.post(WEBHOOK_URL, data=json_data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Messaggio inviato - ID: {result.get('message_id', 'N/A')}")
            else:
                print(f"❌ Errore: {response.status_code}")
        except Exception as e:
            print(f"❌ Errore: {e}")
    else:
        print("⚠️ WILDIX_SECRET non configurato")
    
    # Test conteggio messaggi
    try:
        response = requests.get("http://localhost:9001/messages/count")
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Messaggi salvati: {data['total_messages']}")
        else:
            print(f"❌ Errore conteggio: {response.status_code}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    test_webhook()