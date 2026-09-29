#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIVERSAL SCRAPER v7.1 — ИСПРАВЛЕННАЯ ВЕРСИЯ v7.0

ИСПРАВЛЕНИЯ v7.1 (почему v7.0 "не выводил" JavaScript):
  1. JS-рендеринг: раньше страница читалась через 5 секунд после driver.get().
     Тяжёлые сайты на JavaScript не успевали отрисоваться -> пустой вывод.
     Теперь: ожидание document.readyState == 'complete', прокрутка страницы
     (ленивая загрузка) и ожидание СТАБИЛЬНОСТИ текста (контент перестал расти).
  2. Headless-режим Firefox: '-headless' вместо '--headless' (корректный флаг
     Firefox), плюс настраиваемый таймаут загрузки страницы.
  3. Fallback: если браузер недоступен (нет Selenium/Firefox Portable) или сайт
     заблокировал браузер, автоматический переход на HTTP-режим и обратно.
  4. Gmail: в v7.0 логин/пароль были объявлены, но НЕ ИСПОЛЬЗОВАЛИСЬ — входа в
     Gmail не было вообще. Теперь есть периодический вход в Gmail через браузер
     (постоянный профиль хранит cookies, проверка раз в GMAIL_CHECK_INTERVAL_HOURS).
  5. Полный лог в LOGS/scraper_log.txt для диагностики.
"""

import sys
import os
import time
import re
import json
import platform
from datetime import datetime
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, "OUTPUT"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "CACHE"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "LOGS"), exist_ok=True)

try:
    if sys.platform.startswith('win'):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
except Exception:
    pass

# ============================ НАСТРОЙКИ ============================

GMAIL_EMAIL = "malkodiro@gmail.com"
GMAIL_PASSWORD = "Linakada!11O"
GMAIL_CHECK_INTERVAL_HOURS = 24   # периодическая проверка сессии Gmail (через браузер)

FIREFOX_PATH = os.path.join(BASE_DIR, "BROWSER", "FirefoxPortable", "FirefoxPortable.exe")
PROFILE_DIR = os.path.join(BASE_DIR, "BROWSER", "firefox_profile")

PAGE_LOAD_TIMEOUT = 60            # макс. ожидание загрузки страницы (сек)
JS_STABLE_TIMEOUT = 30            # макс. ожидание стабилизации JS-контента (сек)

SUPPORTED_FORMATS = ["txt", "html", "md", "docx"]
BLOCKED_MARKERS = ["cloudflare", "checking your browser", "access denied", "captcha", "403"]
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"]

# ============================ ЛОГ ============================

LOG_FILE = os.path.join(BASE_DIR, "LOGS", "scraper_log.txt")

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except Exception:
        pass

# ============================ УТИЛИТЫ ============================

def sanitize_filename(name):
    name = re.sub(r'^https?://', '', name)
    name = re.sub(r'[^\w\-_.\s]', '_', name)
    return (name or "page")[:100]

def human_size(b):
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}" if u != "B" else f"{int(b)} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def normalize_url(url):
    url = url.strip().replace(" ", "")
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return "https:" + url
    return "https://" + url

def validate_url(url):
    try:
        p = urlparse(url)
        return bool(p.scheme and p.netloc)
    except Exception:
        return False

# ============================ БРАУЗЕР (SELENIUM + FIREFOX PORTABLE) ============================

def create_driver(headless=True):
    """Создаёт Firefox Portable с постоянным профилем (cookies/Gmail хранятся)."""
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        from webdriver_manager.firefox import GeckoDriverManager

        options = Options()
        if os.path.exists(FIREFOX_PATH):
            options.binary_location = FIREFOX_PATH
        if headless:
            options.add_argument("-headless")  # ПРАВИЛЬНЫЙ флаг Firefox ('--headless' в v7.0 работал нестабильно)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("general.useragent.override", USER_AGENTS[0])
        options.set_preference("dom.max_script_run_time", 30)

        os.makedirs(PROFILE_DIR, exist_ok=True)
        options.add_argument("-profile")
        options.add_argument(PROFILE_DIR)

        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        return driver
    except Exception as e:
        log(f"[browser] Браузер недоступен: {e}")
        return None

def wait_for_js_content(driver, timeout=JS_STABLE_TIMEOUT, stable_sec=3):
    """
    ГЛАВНОЕ ИСПРАВЛЕНИЕ 'JavaScript не выводит':
    1. ждём document.readyState == 'complete';
    2. прокручиваем страницу (активирует ленивую загрузку);
    3. ждём, пока объём текста перестанет расти (JS отрисовался).
    """
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass  # даже если readyState завис — пробуем снять контент

    last_len = -1
    stable = 0
    deadline = time.time() + timeout
    while time.time() < deadline and stable < stable_sec:
        try:
            driver.execute_script(
                "window.scrollTo(0, Math.max(document.body.scrollHeight,"
                " document.documentElement.scrollHeight));"
            )
        except Exception:
            pass
        time.sleep(1)
        try:
            cur = driver.execute_script(
                "return (document.body ? (document.body.innerText || '').length : 0)"
            )
        except Exception:
            break
        if cur == last_len:
            stable += 1
        else:
            stable = 0
            last_len = cur

def scrape_with_browser(url, headless=True):
    driver = create_driver(headless=headless)
    if not driver:
        return {"status": "error", "error": "Browser not available"}

    try:
        driver.get(url)
        wait_for_js_content(driver)  # <-- ждём реальной отрисовки JS, а не sleep(5)

        title = driver.title or ""
        html = driver.page_source

        if any(marker.lower() in html.lower() for marker in BLOCKED_MARKERS):
            return {"status": "blocked", "error": "Cloudflare/блокировка обнаружена"}

        if len(html.strip()) < 500:
            return {"status": "empty", "error": "Страница пуста (JS не отрисовался?)"}

        return {"status": "ok", "title": title, "html": html, "url": driver.current_url}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        try:
            driver.quit()
        except Exception:
            pass

def scrape_with_http(url):
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {"User-Agent": USER_AGENTS[0]}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = soup.title.get_text() if soup.title else ""
        html = str(soup)

        if any(marker.lower() in html.lower() for marker in BLOCKED_MARKERS):
            return {"status": "blocked", "error": "Blocked"}

        return {"status": "ok", "title": title, "html": html, "url": url}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def smart_scrape(url):
    """Браузер (JS-рендеринг) -> при сбое/блокировке HTTP -> при блокировке снова браузер."""
    result = scrape_with_browser(url)
    if result["status"] == "ok":
        return result
    log(f"[scrape] Браузер: {result['status']} ({result.get('error', '')}) — пробую HTTP")
    http_result = scrape_with_http(url)
    if http_result["status"] == "ok":
        return http_result
    if http_result["status"] == "blocked":
        log("[scrape] HTTP заблокирован — повтор через браузер")
        retry = scrape_with_browser(url)
        if retry["status"] == "ok":
            return retry
    return http_result if http_result["status"] != "error" else result

# ============================ GMAIL: ПОСТОЯННАЯ СЕССИЯ ЧЕРЕЗ БРАУЗЕР ============================

def gmail_session_fresh():
    """Сессия Gmail свежая, если проверка была недавно (маркер в профиле)."""
    marker = os.path.join(PROFILE_DIR, ".gmail_last_check")
    try:
        return (time.time() - os.path.getmtime(marker)) < GMAIL_CHECK_INTERVAL_HOURS * 3600
    except Exception:
        return False

def ensure_gmail_session():
    """
    ПЕРИОДИЧЕСКИЙ ВХОД В GMAIL ЧЕРЕЗ БРАУЗЕР.
    В v7.0 почта была объявлена (GMAIL_EMAIL/GMAIL_PASSWORD), но кода входа
    НЕ БЫЛО. Здесь: раз в GMAIL_CHECK_INTERVAL_HOURS открываем Gmail в
    ОВИДИМОМ окне Firefox Portable. Автоматический вход выполняется, если
    Google его не блокирует; иначе окно остаётся открытым 90 секунд для
    ручного подтверждения. Cookies сохраняются в постоянном профиле, поэтому
    скрейпинг продолжает работать от вошедшего аккаунта.
    """
    if gmail_session_fresh():
        return True

    driver = create_driver(headless=False)  # Google блокирует автовход в headless
    if not driver:
        log("[gmail] Браузер недоступен — проверка Gmail пропущена")
        return False

    ok = False
    try:
        driver.get("https://mail.google.com/")
        time.sleep(3)

        if "accounts.google.com" not in driver.current_url:
            log("[gmail] Сессия жива (cookies из профиля) — вход не нужен")
            ok = True
        else:
            log("[gmail] Сессия истекла — выполняем вход...")
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "identifierId"))
                )
                driver.find_element(By.ID, "identifierId").send_keys(GMAIL_EMAIL)
                driver.find_element(By.ID, "identifierNext").click()
                time.sleep(3)
                pwd = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "input[type='password']")
                    )
                )
                pwd.send_keys(GMAIL_PASSWORD)
                driver.find_element(By.ID, "passwordNext").click()
                time.sleep(8)
                ok = "accounts.google.com" not in driver.current_url
            except Exception as e:
                log(f"[gmail] Автовход не удался ({e}) — окно открыто для ручного входа, 90 сек...")
                deadline = time.time() + 90
                while time.time() < deadline:
                    time.sleep(5)
                    if "accounts.google.com" not in driver.current_url:
                        ok = True
                        break

        if ok:
            marker = os.path.join(PROFILE_DIR, ".gmail_last_check")
            try:
                with open(marker, "w") as f:
                    f.write(datetime.now().isoformat())
            except Exception:
                pass
        log(f"[gmail] Результат входа: {'OK' if ok else 'FAIL'}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return ok

# ============================ СОХРАНЕНИЕ ============================

def save_result(result, fmt="md"):
    if result["status"] != "ok":
        return None

    url = result["url"]
    safe_name = sanitize_filename(url)
    output_dir = os.path.join(BASE_DIR, "OUTPUT")
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, f"{safe_name}.{fmt}")
    counter = 2
    while os.path.exists(file_path):
        file_path = os.path.join(output_dir, f"{safe_name}_{counter}.{fmt}")
        counter += 1

    html = result["html"]
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "header", "footer"]):
        tag.decompose()

    if fmt == "html":
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
    elif fmt == "txt":
        text = soup.get_text("\n", strip=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
    elif fmt == "md":
        try:
            from markdownify import markdownify as md
            md_text = md(str(soup), heading_style="ATX")
        except Exception:
            md_text = soup.get_text("\n", strip=True)
        header = f"# {result['title'] or url}\n\n**Source:** {url}\n\n---\n\n"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header + md_text)
    elif fmt == "docx":
        try:
            from docx import Document
            doc = Document()
            doc.add_heading(result['title'] or url, 0)
            doc.add_paragraph(f"Source: {url}")
            for p in soup.get_text("\n", strip=True).split('\n'):
                if p.strip():
                    doc.add_paragraph(p.strip())
            doc.save(file_path)
        except Exception:
            return None

    return file_path

# ============================ MAIN ============================

def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description='UNIVERSAL SCRAPER v7.1')
    parser.add_argument('--url', help='URL to scrape')
    parser.add_argument('--urls', nargs='+', help='Multiple URLs')
    parser.add_argument('--file', help='File with URLs')
    parser.add_argument('--format', default='md', choices=SUPPORTED_FORMATS)
    parser.add_argument('--mode', default='smart', choices=['http', 'browser', 'smart'],
                        help="smart = браузер с JS-рендерингом + HTTP-fallback")
    parser.add_argument('--output', default=None)
    parser.add_argument('--gmail', action='store_true', help='Проверить/обновить сессию Gmail перед скрейпингом')
    parser.add_argument('--no-headless', action='store_true', help='Показывать окно браузера (отладка)')

    args = parser.parse_args()

    urls = args.urls or []
    if args.url:
        urls.append(args.url)
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)

    if not urls and not args.gmail:
        parser.print_help()
        return

    # Периодический вход в Gmail через браузер (постоянный профиль)
    if args.gmail or urls:
        try:
            ensure_gmail_session()
        except Exception as e:
            log(f"[gmail] Ошибка сессии: {e}")

    output_dir = args.output or os.path.join(BASE_DIR, "OUTPUT")
    os.makedirs(output_dir, exist_ok=True)

    ok_count = 0
    for url in urls:
        url = normalize_url(url)
        if not validate_url(url):
            print(f"Invalid URL: {url}")
            continue

        print(f"Processing: {url}")

        if args.mode == "browser":
            result = scrape_with_browser(url, headless=not args.no_headless)
        elif args.mode == "http":
            result = scrape_with_http(url)
        else:
            result = smart_scrape(url)

        if result["status"] == "ok":
            file_path = save_result(result, args.format)
            if file_path:
                size = os.path.getsize(file_path)
                print(f"SUCCESS: {file_path} ({human_size(size)})")
                ok_count += 1
            else:
                print(f"ERROR: Could not save {url}")
        else:
            print(f"ERROR: {result.get('error', 'Unknown')}")

    log(f"Готово: {ok_count}/{len(urls)} URL успешно")

if __name__ == '__main__':
    main()
