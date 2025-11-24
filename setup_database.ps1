#!/usr/bin/env powershell
<#
.SYNOPSIS
    Script per la configurazione del database PostgreSQL per il webhook Wildix

.DESCRIPTION
    Questo script automatizza la configurazione del database PostgreSQL,
    creando il database, l'utente e le tabelle necessarie.

.PARAMETER DBHost
    Host del database PostgreSQL (default: localhost)

.PARAMETER DBPort  
    Porta del database PostgreSQL (default: 5432)

.PARAMETER AdminUser
    Username amministratore PostgreSQL (default: postgres)

.PARAMETER DBName
    Nome del database da creare (default: wildix_webhook)

.PARAMETER DBUser
    Nome utente del database da creare (default: wildix_user)

.PARAMETER DBPassword
    Password per l'utente del database

.EXAMPLE
    .\setup_database.ps1 -DBPassword "mypassword123"
#>

param(
    [string]$DBHost = "localhost",
    [int]$DBPort = 5432,
    [string]$AdminUser = "postgres", 
    [string]$DBName = "wildix_webhook",
    [string]$DBUser = "wildix_user",
    [Parameter(Mandatory=$true)]
    [string]$DBPassword
)

Write-Host "🗄️  Setup Database PostgreSQL per Webhook Wildix" -ForegroundColor Green
Write-Host "=" * 50

# Verifica che psql sia disponibile
try {
    $psqlVersion = psql --version
    Write-Host "✅ PostgreSQL client trovato: $psqlVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ PostgreSQL client (psql) non trovato nel PATH" -ForegroundColor Red
    Write-Host "   Installa PostgreSQL o aggiungi psql al PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📋 Configurazione:" -ForegroundColor Cyan
Write-Host "   Host: $DBHost"
Write-Host "   Port: $DBPort" 
Write-Host "   Admin User: $AdminUser"
Write-Host "   Database: $DBName"
Write-Host "   App User: $DBUser"

Write-Host ""
Write-Host "🔐 Inserisci la password dell'utente amministratore PostgreSQL ($AdminUser):"
$AdminPassword = Read-Host -AsSecureString
$AdminPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($AdminPassword))

# Crea il database e l'utente
$sqlCommands = @"
-- Crea il database se non esiste
SELECT 'CREATE DATABASE $DBName'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DBName')\gexec

-- Connetti al nuovo database
\c $DBName

-- Crea l'utente se non esiste
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DBUser') THEN
        CREATE USER $DBUser WITH PASSWORD '$DBPassword';
    END IF;
END
`$`$;

-- Garantisci i permessi
GRANT ALL PRIVILEGES ON DATABASE $DBName TO $DBUser;
GRANT ALL PRIVILEGES ON SCHEMA public TO $DBUser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DBUser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DBUser;

-- Crea la tabella
CREATE TABLE IF NOT EXISTS messaggi_wildix (
    id SERIAL PRIMARY KEY,
    cliente_id VARCHAR(255) NOT NULL,
    message JSONB NOT NULL,
    data_creazione TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processato BOOLEAN DEFAULT FALSE,
    data_processato TIMESTAMP WITH TIME ZONE NULL
);

-- Crea indici per ottimizzare le query
CREATE INDEX IF NOT EXISTS idx_messaggi_wildix_cliente_id ON messaggi_wildix (cliente_id);
CREATE INDEX IF NOT EXISTS idx_messaggi_wildix_processato ON messaggi_wildix (processato);
CREATE INDEX IF NOT EXISTS idx_messaggi_wildix_data_creazione ON messaggi_wildix (data_creazione);

-- Mostra struttura tabella
\d messaggi_wildix

-- Mostra statistiche
SELECT 'Database setup completato!' as status;
SELECT version() as postgresql_version;
"@

# Salva i comandi SQL in un file temporaneo
$tempSqlFile = [System.IO.Path]::GetTempFileName() + ".sql"
$sqlCommands | Out-File -FilePath $tempSqlFile -Encoding UTF8

try {
    Write-Host ""
    Write-Host "🚀 Esecuzione setup database..." -ForegroundColor Yellow
    
    # Esegui i comandi SQL
    $env:PGPASSWORD = $AdminPasswordPlain
    $result = psql -h $DBHost -p $DBPort -U $AdminUser -f $tempSqlFile 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Database setup completato con successo!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📝 Aggiorna il file .env con:" -ForegroundColor Cyan
        Write-Host "POSTGRES_HOST=$DBHost"
        Write-Host "POSTGRES_PORT=$DBPort"
        Write-Host "POSTGRES_USER=$DBUser"
        Write-Host "POSTGRES_PASSWORD=$DBPassword"
        Write-Host "POSTGRES_DATABASE=$DBName"
        Write-Host "POSTGRES_TABLE=messaggi_wildix"
        
        Write-Host ""
        Write-Host "🧪 Test della connessione..." -ForegroundColor Yellow
        
        # Test connessione con nuovo utente
        $env:PGPASSWORD = $DBPassword
        $testResult = psql -h $DBHost -p $DBPort -U $DBUser -d $DBName -c "SELECT COUNT(*) as total_messages FROM messaggi_wildix;" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Connessione test OK!" -ForegroundColor Green
            Write-Host $testResult
        } else {
            Write-Host "⚠️  Warning: Test connessione non riuscito" -ForegroundColor Yellow
            Write-Host $testResult -ForegroundColor Red
        }
        
    } else {
        Write-Host ""
        Write-Host "❌ Errore durante il setup:" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        exit 1
    }
    
} finally {
    # Pulisci file temporaneo e variabili ambiente
    if (Test-Path $tempSqlFile) {
        Remove-Item $tempSqlFile -Force
    }
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "🎉 Setup completato! Il webhook è pronto per PostgreSQL" -ForegroundColor Green