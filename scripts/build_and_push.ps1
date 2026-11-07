# Script PowerShell: Build e Push das imagens para o Docker Hub
# Uso: .\scripts\build_and_push.ps1

$ErrorActionPreference = "Stop"

$DOCKER_USER = "lebron057"
$SERVICES = @("catalog-service", "auth-service", "log-service")

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Iniciando Build & Push para o Docker Hub ($DOCKER_USER)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Verifica se o Docker Desktop está rodando
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "O Docker Desktop não está rodando. Inicie o Docker Desktop antes de continuar."
}

foreach ($svc in $SERVICES) {
    $tag = "$DOCKER_USER/${svc}:latest"
    Write-Host "`n[1/2] Compilando imagem: $tag..." -ForegroundColor Yellow
    docker build -t $tag -f Dockerfile .

    Write-Host "[2/2] Enviando para o Docker Hub: $tag..." -ForegroundColor Green
    docker push $tag
}

Write-Host "`nTodas as imagens foram compiladas e enviadas para o Docker Hub com sucesso!" -ForegroundColor Green
Write-Host "Agora vá ao Portainer, ative 'Re-pull image and redeploy' e clique em 'Update the stack'." -ForegroundColor Cyan

