# Script per visualizzare la configurazione corrente
# Uso: .\check_config.ps1

Write-Host "🔍 Verifica Configurazione Webhook Wildix" -ForegroundColor Green
Write-Host "=" * 50

# Controlla se esiste il file .env
if (Test-Path ".env") {
    Write-Host "✅ File .env trovato" -ForegroundColor Green
    
    # Legge e mostra le configurazioni principali
    $envContent = Get-Content ".env"
    
    Write-Host ""
    Write-Host "📋 Configurazioni attuali:" -ForegroundColor Yellow
    
    foreach ($line in $envContent) {
        if ($line -match "^(HOST|PORT|FLASK_DEBUG|WILDIX_SECRET|LOG_LEVEL)=(.*)") {
            $key = $matches[1]
            $value = $matches[2]
            
            # Maschera il secret per sicurezza
            if ($key -eq "WILDIX_SECRET" -and $value -ne "your-wildix-webhook-secret-here") {
                $maskedValue = $value.Substring(0, [Math]::Min(4, $value.Length)) + "*" * ([Math]::Max(0, $value.Length - 4))
                Write-Host "   $key = $maskedValue" -ForegroundColor Cyan
            } else {
                Write-Host "   $key = $value" -ForegroundColor White
            }
        }
    }
} else {
    Write-Host "⚠️  File .env non trovato" -ForegroundColor Yellow
    Write-Host "💡 Verrà creato dalla copia di .env.example" -ForegroundColor Gray
    
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ File .env creato da .env.example" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "🌐 Informazioni di rete:" -ForegroundColor Yellow

# Trova IP di rete
$ipAddress = try {
    $networkAdapter = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
        $_.InterfaceAlias -notlike "*Loopback*" -and 
        $_.IPAddress -notlike "169.254.*" -and
        $_.IPAddress -notlike "127.*"
    } | Sort-Object InterfaceIndex | Select-Object -First 1
    if ($networkAdapter) { 
        Write-Host "   🖥️  Interfaccia: $($networkAdapter.InterfaceAlias)" -ForegroundColor Gray
        $networkAdapter.IPAddress 
    } else { 
        "Non trovato" 
    }
} catch {
    "Errore nel rilevamento"
}

Write-Host "   📍 IP Locale: $ipAddress" -ForegroundColor White
Write-Host "   🏠 Localhost: 127.0.0.1" -ForegroundColor White

Write-Host ""
Write-Host "🎯 URL del webhook:" -ForegroundColor Yellow
if ($ipAddress -and $ipAddress -ne "Non trovato") {
    Write-Host "   🌐 Rete: http://$ipAddress:9001/webhook/wildix" -ForegroundColor Cyan
} else {
    Write-Host "   🌐 Rete: http://your-server-ip:9001/webhook/wildix" -ForegroundColor Gray
}
Write-Host "   🏠 Locale: http://localhost:9001/webhook/wildix" -ForegroundColor Cyan

Write-Host ""
Write-Host "🔧 Comandi utili:" -ForegroundColor Yellow
Write-Host "   .\start_webhook.ps1                    # Avvia server" -ForegroundColor White
Write-Host "   python test_webhook_with_secret.py     # Test con secret" -ForegroundColor White
Write-Host "   curl http://localhost:9001/health      # Test health" -ForegroundColor White