# Script per configurare il secret Wildix
# Uso: .\setup_wildix_secret.ps1 -Secret "your-secret-here"

param(
    [Parameter(Mandatory=$true)]
    [string]$Secret
)

Write-Host "🔐 Configurazione Secret Wildix" -ForegroundColor Green
Write-Host "=" * 40

# Verifica che il secret non sia vuoto
if ([string]::IsNullOrWhiteSpace($Secret)) {
    Write-Host "❌ Secret non può essere vuoto!" -ForegroundColor Red
    exit 1
}

# Leggi il file .env esistente o crea uno nuovo
$envFile = ".env"
$envContent = @()

if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
    Write-Host "📄 File .env esistente trovato" -ForegroundColor Yellow
} else {
    Write-Host "📄 Creazione nuovo file .env" -ForegroundColor Yellow
    # Copia da .env.example se esiste
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" $envFile
        $envContent = Get-Content $envFile
    }
}

# Cerca e aggiorna la linea WILDIX_SECRET
$secretUpdated = $false
$newContent = @()

foreach ($line in $envContent) {
    if ($line -match "^WILDIX_SECRET=") {
        $newContent += "WILDIX_SECRET=$Secret"
        $secretUpdated = $true
        Write-Host "✅ Secret aggiornato nel file .env" -ForegroundColor Green
    } else {
        $newContent += $line
    }
}

# Se non trovato, aggiungi il secret
if (-not $secretUpdated) {
    $newContent += ""
    $newContent += "# Sicurezza Wildix"
    $newContent += "WILDIX_SECRET=$Secret"
    Write-Host "✅ Secret aggiunto al file .env" -ForegroundColor Green
}

# Salva il file aggiornato
$newContent | Out-File -FilePath $envFile -Encoding UTF8

Write-Host ""
Write-Host "🎯 Configurazione completata!" -ForegroundColor Green
Write-Host "🔒 Secret configurato per validazione webhook" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚙️ Prossimi passi:" -ForegroundColor Yellow
Write-Host "1. Riavvia il server webhook" -ForegroundColor White
Write-Host "2. Configura lo stesso secret nel pannello Wildix" -ForegroundColor White
Write-Host "3. Testa il webhook con il secret" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Test:" -ForegroundColor Yellow
Write-Host ".\test_webhook_with_secret.ps1" -ForegroundColor White