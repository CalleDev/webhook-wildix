import requests
import json
import time

# URL del webhook (HTTP locale, HTTPS gestito da Nginx)
WEBHOOK_URL = "http://localhost:9001/webhook/wildix"

def test_webhook():
    """Test del webhook con dati di esempio"""
    
    # Dati di test che simulano diversi tipi di eventi Wildix
    test_messages = [
        {
            "event_type": "call_started",
            "call_id": "12345",
            "caller": "+391234567890",
            "called": "+390987654321",
            "timestamp": "2024-11-15T10:30:00Z"
        },
        {
            "event_type": "call_ended",
            "call_id": "12345",
            "duration": 120,
            "status": "answered",
            "timestamp": "2024-11-15T10:32:00Z"
        },
        {
            "event_type": "voicemail",
            "caller": "+391111111111",
            "duration": 30,
            "file_url": "https://example.com/voicemail.wav",
            "timestamp": "2024-11-15T11:00:00Z"
        },
        {
            "event_type": "sms_received",
            "sender": "+392222222222",
            "recipient": "+393333333333",
            "message": "Messaggio di test",
            "timestamp": "2024-11-15T11:15:00Z"
        }
    ]
    
    print("🔄 Avvio test del webhook...")
    print(f"📍 URL: {WEBHOOK_URL}")
    print("-" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"📤 Invio messaggio {i}/{len(test_messages)}: {message['event_type']}")
        
        try:
            response = requests.post(
                WEBHOOK_URL,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successo - ID: {result.get('message_id', 'N/A')}")
            else:
                print(f"❌ Errore {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Errore di connessione: {e}")
        
        # Pausa tra i messaggi
        time.sleep(1)
    
    print("-" * 50)
    print("✅ Test completato!")
    
    # Test degli endpoint di status
    print("\n🔍 Test endpoint di status...")
    
    try:
        # Health check
        health_url = WEBHOOK_URL.replace("/webhook/wildix", "/health")
        health_response = requests.get(health_url)
        if health_response.status_code == 200:
            print("✅ Health check OK")
        else:
            print(f"❌ Health check fallito: {health_response.status_code}")
        
        # Conteggio messaggi
        count_url = WEBHOOK_URL.replace("/webhook/wildix", "/messages/count")
        count_response = requests.get(count_url)
        if count_response.status_code == 200:
            count_data = count_response.json()
            print(f"📊 Messaggi salvati: {count_data['total_messages']}")
            for file_info in count_data['files']:
                print(f"   📄 {file_info['file']}: {file_info['count']} messaggi")
        else:
            print(f"❌ Conteggio messaggi fallito: {count_response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore nei test di status: {e}")

if __name__ == "__main__":
    test_webhook()