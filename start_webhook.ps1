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

# Trova l'IP della rete locale
$ipAddress = try {
    $networkAdapter = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.InterfaceAlias -notlike "*Loopback*" -and 
        $_.IPAddress -notlike "169.254.*" -and
        $_.IPAddress -notlike "127.*" -and
        $_.PrefixOrigin -eq "Dhcp" -or $_.PrefixOrigin -eq "Manual"
    } | Sort-Object InterfaceIndex | Select-Object -First 1
    if ($networkAdapter) { $networkAdapter.IPAddress } else { $null }
} catch {
    $null
}

if (-not $ipAddress) { 
    # Fallback: usa ipconfig
    $ipAddress = try {
        (ipconfig | Select-String "IPv4.*: (\d+\.\d+\.\d+\.\d+)" | Select-Object -First 1).Matches.Groups[1].Value
    } catch {
        "your-server-ip"
    }
}

Write-Host "📊 Configurazione (accessibile dalla rete):"
Write-Host "   🌐 URL Webhook: http://$ipAddress:9001/webhook/wildix"
Write-Host "   🏠 Locale: http://localhost:9001/webhook/wildix"
Write-Host "   💚 Health Check: http://$ipAddress:9001/health"
Write-Host "   📈 Statistiche: http://$ipAddress:9001/messages/count"
Write-Host "   🔒 HTTPS: Configura Nginx per reverse proxy" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎯 Server in avvio..." -ForegroundColor Green

# Avvia il server
python app.py