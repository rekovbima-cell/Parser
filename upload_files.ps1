# PowerShell скрипт для загрузки файлов на GitHub (исправленная версия)
# Для Windows 11
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Настройки
$repoPath = "D:\bbbb\git\Parser"
$githubRepo = "rekovbima-cell/Parser"
$githubBranch = "main"
$remoteUrl = "https://github.com/$githubRepo.git"

# Проверяем существование локальной папки
if (-not (Test-Path $repoPath)) {
    Write-Host "❌ Ошибка: Указанный путь не существует: $repoPath" -ForegroundColor Red
    pause
    exit 1
}

# Переходим в директорию репозитория
Set-Location $repoPath

# Проверяем наличие Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git не установлен. Установите Git для Windows." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "=== Загрузка файлов на GitHub ===" -ForegroundColor Green
Write-Host "Репозиторий: $githubRepo" -ForegroundColor Cyan
Write-Host "Ветка: $githubBranch" -ForegroundColor Cyan
Write-Host ""

# Инициализируем репозиторий, если его еще нет
if (-not (Test-Path .git)) {
    Write-Host "Инициализация Git репозитория..." -ForegroundColor Yellow
    git init
} else {
    Write-Host "Git репозиторий уже инициализирован." -ForegroundColor Green
}

# Настраиваем remote origin (создаем или обновляем URL)
$remotes = @(git remote)
if ($remotes -contains "origin") {
    git remote set-url origin $remoteUrl
} else {
    git remote add origin $remoteUrl
}

# Устанавливаем имя текущей ветки (замена ненадежного 'git checkout -b')
git branch -M $githubBranch

# Синхронизация с GitHub: подтягиваем изменения, сделанные через веб-интерфейс
Write-Host "Синхронизация с GitHub (fetch + pull --rebase)..." -ForegroundColor Yellow
git fetch origin $githubBranch 2>$null
git pull origin $githubBranch --rebase 2>$null

# Добавляем все файлы
Write-Host "Добавление файлов..." -ForegroundColor Yellow
git add -A

# Проверяем, есть ли изменения (безопасная обработка массива строк)
$status = @(git status --porcelain)
if ($status.Count -eq 0) {
    Write-Host "ℹ️ Нет новых изменений для коммита." -ForegroundColor Yellow
} else {
    # Создаем коммит (исправлена ошибка '$commit
Message' из исходного скрипта)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $commitMessage = "Загрузка файлов Parser - $timestamp"
    Write-Host "Создание коммита: '$commitMessage'" -ForegroundColor Yellow
    git commit -m $commitMessage
}

# Загружаем на GitHub
Write-Host "Загрузка на GitHub (push)..." -ForegroundColor Yellow
git push -u origin $githubBranch

# Проверяем результат push по коду возврата
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Все файлы успешно загружены!" -ForegroundColor Green
    Write-Host "Репозиторий: https://github.com/$githubRepo" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Ошибка при отправке на GitHub. Проверьте подключение, права доступа или авторизацию (gh auth / credential manager)." -ForegroundColor Red
}

Write-Host ""
pause
