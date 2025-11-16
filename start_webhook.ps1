# Script di avvio per il webhook Wildix
# Uso: .\start_webhook.ps1

Write-Host "🚀 Avvio webhook Wildix..." -ForegroundColor Green

# Controlla se l'ambiente virtuale esiste
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Ambiente virtuale non trovato. Creazione in corso..." -ForegroundColor Red
    python -m venv venv
    Write-Host "✅ Ambiente virtuale creato" -ForegroundColor Green
}

# Attiva l'ambiente virtuale
Write-Host "🔄 Attivazione ambiente virtuale..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Installa/aggiorna le dipendenze se necessario
if (-not (Test-Path "venv\Lib\site-packages\flask")) {
    Write-Host "📦 Installazione dipendenze..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Crea le cartelle necessarie
New-Item -ItemType Directory -Force -Path "messages" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

Write-Host "📊 Configurazione (HTTP locale, HTTPS via Nginx):"
Write-Host "   🌐 URL Webhook: http://localhost:9001/webhook/wildix"
Write-Host "   💚 Health Check: http://localhost:9001/health"
Write-Host "   📈 Statistiche: http://localhost:9001/messages/count"
Write-Host "   🔒 HTTPS: Gestito da Nginx" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎯 Server in avvio..." -ForegroundColor Green

# Avvia il server
python app.py