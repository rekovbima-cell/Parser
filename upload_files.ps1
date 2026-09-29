# PowerShell скрипт для загрузки файлов на GitHub
# Для Windows 11

# Настройки
$repoPath = "D:\bbbb\git\Parser"
$githubRepo = "rekovbima-cell/Parser"
$githubBranch = "main"

# Проверяем, находимся ли мы в директории репозитория
Set-Location $repoPath

# Проверяем наличие Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git не установлен. Установите Git для Windows." -ForegroundColor Red
    exit
}

Write-Host "=== Загрузка файлов на GitHub ===" -ForegroundColor Green
Write-Host "Репозиторий: $githubRepo" -ForegroundColor Cyan
Write-Host "Ветка: $githubBranch" -ForegroundColor Cyan
Write-Host ""

# Инициализируем репозиторий, если его еще нет
if (-not (Test-Path .git)) {
    Write-Host "Инициализация Git репозитория..." -ForegroundColor Yellow
    git init
    git remote add origin "https://github.com/$githubRepo.git"
} else {
    Write-Host "Git репозиторий уже инициализирован." -ForegroundColor Green
}

# Добавляем все файлы
Write-Host "Добавление файлов..." -ForegroundColor Yellow
git add -A

# Проверяем, есть ли изменения
$status = git status --porcelain
if ([string]::IsNullOrEmpty($status)) {
    Write-Host "Нет новых файлов для загрузки." -ForegroundColor Yellow
    exit
}

# Коммитим изменения
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commitMessage = "Загрузка файлов Parser - $timestamp"

Write-Host "Создание коммита: '$commitMessage'" -ForegroundColor Yellow
git commit -m $commitMessage

# Проверяем текущую ветку
$currentBranch = git rev-parse --abbrev-ref HEAD
if ($currentBranch -ne $githubBranch) {
    Write-Host "Переключение на ветку '$githubBranch'..." -ForegroundColor Yellow
    git checkout -b $githubBranch 2>$null
}

# Загружаем на GitHub
Write-Host "Загрузка на GitHub..." -ForegroundColor Yellow
git push -u origin $githubBranch

Write-Host ""
Write-Host "✅ Все файлы успешно загружены!" -ForegroundColor Green
Write-Host "Репозиторий: https://github.com/$githubRepo" -ForegroundColor Cyan
Write-Host ""
pause
