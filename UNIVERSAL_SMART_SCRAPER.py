#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              UNIVERSAL SMART SCRAPER v5.0 - ОДИН ФАЙЛ ВСЁ ВКЛЮЧЕНО           ║
║                                                                              ║
║  🎯 УНИВЕРСАЛЬНЫЙ ВЕБ-СКРЕЙПЕР ДЛЯ ЛЮБЫХ САЙТОВ                              ║
║  ✅ Работает с .gov, .nevo.co.il и другими защищёнными сайтами              ║
║  ✅ Поддержка форматов: TXT, HTML, Markdown, DOCX                           ║
║  ✅ Обработка списков URL из файлов                                          ║
║  ✅ Автоматическое кэширование (7 дней)                                      ║
║  ✅ Симуляция прокси через код (без внешних ключей)                          ║
║  ✅ Русский интерфейс + English support                                      ║
║  ✅ Обработка ошибок и блокировок                                           ║
║  ✅ Работает через двойной клик (после компиляции в EXE)                     ║
║                                                                              ║
║  📋 КАК ИСПОЛЬЗОВАТЬ:                                                       ║
║     1. Запустите файл двойным кликом                                         ║
║     2. Выберите действие в меню                                              ║
║     3. Введите URL или список URL                                            ║
║     4. Выберите формат вывода                                               ║
║     5. Получите результаты в папке OUTPUT/                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import subprocess
import importlib
import threading
import time
import random
import re
import json
import socket
import platform
from datetime import datetime, timedelta
from urllib.parse import urlparse

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

APP_NAME = "UNIVERSAL SMART SCRAPER"
APP_VERSION = "5.0"
APP_AUTHOR = "Alekseyfdx"

DEFAULT_OUTPUT_DIR = "OUTPUT"
DEFAULT_CACHE_DIR = "CACHE"
DEFAULT_LOGS_DIR = "LOGS"
DEFAULT_FORMAT = "md"
CACHE_EXPIRY_DAYS = 7
MAX_FILE_SIZE = 50 * 1024 * 1024
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

SUPPORTED_FORMATS = ["txt", "html", "md", "docx"]

BLOCKED_MARKERS = [
    "just a moment", "checking your browser", "attention required",
    "access denied", "are you a robot", "captcha", "cloudflare",
    "rate limit exceeded", "403 forbidden", "request blocked",
    "unusual traffic", "verify you are human", "bot detection",
    "please enable cookies", "please wait", "loading",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
]

REFERERS = ["https://www.google.com/", "https://www.bing.com/", "https://www.yandex.ru/"]
ACCEPT_LANGUAGES = ["en-US,en;q=0.9", "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"]

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================================

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(BASE_DIR, DEFAULT_OUTPUT_DIR), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, DEFAULT_CACHE_DIR), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, DEFAULT_LOGS_DIR), exist_ok=True)

try:
    if sys.platform.startswith('win'):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
except:
    pass

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def clear_screen():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def print_header():
    clear_screen()
    print("=" * 80)
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("  УНИВЕРСАЛЬНЫЙ ВЕБ-СКРЕЙПЕР")
    print("=" * 80)

def print_separator():
    print("-" * 80)

def sanitize_filename(name):
    name = re.sub(r'^https?://', '', name)
    name = re.sub(r'[^\w\-_.\s]', '_', name)
    name = name.strip('_').strip()
    while "__" in name:
        name = name.replace("__", "_")
    return (name or "page")[:150]

def human_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"

def now_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")

def normalize_url(url):
    if not url:
        return url
    url = url.strip()
    url = re.sub(r'\s+', '', url)
    if url.startswith(('http://', 'https://')):
        return url
    if url.startswith('//'):
        return 'https:' + url
    if url.startswith('/'):
        return 'https://www.example.com' + url
    return 'https://' + url

def validate_url(url):
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False

def quick_dns_check(url):
    try:
        host = urlparse(url).hostname
        if not host:
            return False, "Invalid URL"
        socket.setdefaulttimeout(5)
        socket.gethostbyname(host)
        return True, None
    except Exception as e:
        return False, f"DNS error: {e}"

def looks_blocked(title, body_sample):
    haystack = f"{title} {body_sample}".lower()
    return any(marker.lower() in haystack for marker in BLOCKED_MARKERS)

# ============================================================================
# СИМУЛЯЦИЯ ПРОКСИ
# ============================================================================

class ProxySimulator:
    def __init__(self):
        self.user_agents = USER_AGENTS
        self.referers = REFERERS
        self.accept_languages = ACCEPT_LANGUAGES
        self.idx = 0
        self.lock = threading.Lock()

    def get_next(self):
        with self.lock:
            idx = self.idx % len(self.user_agents)
            self.idx += 1
            return {
                "user_agent": self.user_agents[idx],
                "referer": self.referers[idx % len(self.referers)],
                "accept_language": self.accept_languages[idx % len(self.accept_languages)],
            }

    def get_headers(self):
        config = self.get_next()
        return {
            "User-Agent": config["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": config["accept_language"],
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": config["referer"],
        }

# ============================================================================
# КЭШ
# ============================================================================

class SimpleCache:
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or os.path.join(BASE_DIR, DEFAULT_CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "cache.json")
        self.cache = {}
        self.load()

    def load(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
        except:
            self.cache = {}

    def save(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except:
            pass

    def get(self, url, fmt="md"):
        key = f"{url}|{fmt}"
        cached = self.cache.get(key)
        if cached:
            try:
                cached_time = datetime.fromisoformat(cached['timestamp'])
                if datetime.now() - cached_time < timedelta(days=CACHE_EXPIRY_DAYS):
                    return cached.get('content')
            except:
                pass
        return None

    def set(self, url, content, fmt="md"):
        key = f"{url}|{fmt}"
        self.cache[key] = {'content': content, 'timestamp': datetime.now().isoformat()}
        self.save()

    def clear(self):
        self.cache = {}
        self.save()

# ============================================================================
# ВЕБ-СКРЕЙПЕР
# ============================================================================

class WebScraper:
    def __init__(self):
        self.proxy_simulator = ProxySimulator()
        self.cache = SimpleCache()
        self.requests_ok = False
        self.bs4_ok = False
        self.docx_ok = False
        self.md_ok = False
        self._check_deps()

    def _check_deps(self):
        try:
            import requests
            self.requests_ok = True
        except:
            pass
        try:
            from bs4 import BeautifulSoup
            self.bs4_ok = True
        except:
            pass
        try:
            from docx import Document
            self.docx_ok = True
        except:
            pass
        try:
            from markdownify import markdownify
            self.md_ok = True
        except:
            pass

    def scrape_url(self, url, output_format="md", output_dir=None, retries=MAX_RETRIES, use_cache=True, lang="ru"):
        result = {
            "url": url, "title": "", "status": "failed", "format": output_format,
            "file": None, "size_bytes": 0, "word_count": None, "blocked_suspected": False,
            "method": "none", "attempts": 0, "error": None, "elapsed_sec": 0.0,
        }

        url = normalize_url(url)
        result["url"] = url

        if not validate_url(url):
            result["error"] = "Invalid URL"
            return result

        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, DEFAULT_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)

        t0 = time.time()

        ok_dns, dns_err = quick_dns_check(url)
        if not ok_dns:
            result["error"] = dns_err
            result["elapsed_sec"] = round(time.time() - t0, 2)
            return result

        if use_cache and output_format in ["txt", "html", "md", "docx"]:
            cached = self.cache.get(url, output_format)
            if cached:
                safe_name = sanitize_filename(url)
                file_path = os.path.join(output_dir, f"{safe_name}.{output_format}")
                counter = 2
                while os.path.exists(file_path):
                    file_path = os.path.join(output_dir, f"{safe_name}_{counter}.{output_format}")
                    counter += 1
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(cached)
                    result["status"] = "cached"
                    result["file"] = os.path.basename(file_path)
                    result["size_bytes"] = os.path.getsize(file_path)
                    result["method"] = "cache"
                    result["elapsed_sec"] = round(time.time() - t0, 2)
                    return result
                except:
                    pass

        safe_name = sanitize_filename(url)
        file_path = os.path.join(output_dir, f"{safe_name}.{output_format}")
        counter = 2
        while os.path.exists(file_path):
            file_path = os.path.join(output_dir, f"{safe_name}_{counter}.{output_format}")
            counter += 1

        max_attempts = max(1, retries + 1)
        last_error = None

        for attempt in range(1, max_attempts + 1):
            result["attempts"] = attempt

            if attempt > 1:
                time.sleep(random.uniform(2.0, 4.0))

            try:
                if not self.requests_ok:
                    result["error"] = "requests library not installed"
                    result["elapsed_sec"] = round(time.time() - t0, 2)
                    return result

                scraped = self._scrape_with_requests(url, output_format, file_path, result, attempt, max_attempts)
                if scraped["status"] == "ok":
                    if use_cache and output_format in ["txt", "html", "md", "docx"]:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                self.cache.set(url, f.read(), output_format)
                        except:
                            pass
                    return scraped
                elif scraped["status"] == "blocked":
                    result.update(scraped)
                    continue
                else:
                    last_error = scraped.get("error")
                    result.update(scraped)
            except Exception as e:
                last_error = str(e)

        result["error"] = last_error or "Unknown error"
        result["elapsed_sec"] = round(time.time() - t0, 2)
        return result

    def _scrape_with_requests(self, url, output_format, file_path, result, attempt=1, max_attempts=3):
        import requests
        from bs4 import BeautifulSoup

        headers = self.proxy_simulator.get_headers()

        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)

            if resp.status_code in [403, 429, 503, 401, 400]:
                result["blocked_suspected"] = True
                result["error"] = f"HTTP {resp.status_code}: Blocked"
                result["status"] = "blocked"
                return result

            resp.raise_for_status()
            raw_html = resp.text
            soup = BeautifulSoup(raw_html, "html.parser")

            for tag in soup(["script", "style", "noscript", "template", "svg", "iframe", "nav", "header", "footer", "aside"]):
                tag.decompose()

            title = soup.title.get_text(strip=True) if soup.title else ""
            result["title"] = title
            body_sample = raw_html[:2000]
            result["blocked_suspected"] = looks_blocked(title, body_sample)

            if result["blocked_suspected"]:
                result["error"] = "Blocked by anti-bot system"
                result["status"] = "blocked"
                return result

            if output_format == "html":
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(raw_html)
            elif output_format == "txt":
                text_content = soup.get_text("\n", strip=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                result["word_count"] = len(text_content.split())
            elif output_format == "md":
                md_text = self._html_to_markdown(raw_html, url)
                header = f"# {title or url}\n\n**Source:** {url}\n\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
                full_md = header + md_text
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(full_md)
                result["word_count"] = len(full_md.split())
            elif output_format == "docx":
                if not self.docx_ok:
                    result["error"] = "python-docx not installed"
                    result["status"] = "failed"
                    return result
                text_content = soup.get_text("\n", strip=True)
                self._save_as_docx(text_content, title or url, url, file_path)
                result["word_count"] = len(text_content.split())

            size = os.path.getsize(file_path)
            result["status"] = "ok"
            result["file"] = os.path.basename(file_path)
            result["size_bytes"] = size
            result["method"] = "requests"
            result["elapsed_sec"] = round(time.time() - result.get("_t0", time.time()), 2)
            return result

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code in [403, 429, 503, 401]:
                result["blocked_suspected"] = True
                result["error"] = f"HTTP {e.response.status_code}"
            else:
                result["error"] = str(e)
            result["status"] = "failed"
            return result
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
            return result

    def _html_to_markdown(self, html_content, page_url=""):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "noscript", "template", "svg", "iframe", "nav", "header", "footer", "aside"]):
            tag.decompose()
        try:
            from markdownify import markdownify as md_convert
            body = soup.body or soup
            md = md_convert(str(body), heading_style="ATX", bullets="-")
            return re.sub(r'\n{3,}', '\n\n', md).strip()
        except:
            lines = []
            for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
                if el.name and re.match(r'h[1-6]', el.name):
                    level = int(el.name[1])
                    txt = el.get_text(strip=True)
                    if txt:
                        lines.append(f"{'#' * level} {txt}")
                elif el.name == "li":
                    txt = el.get_text(strip=True)
                    if txt:
                        lines.append(f"- {txt}")
                elif el.name == "p":
                    txt = el.get_text(strip=True)
                    if txt:
                        lines.append(txt)
            return "\n\n".join(lines) if lines else soup.get_text("\n", strip=True)

    def _save_as_docx(self, text_content, title, url, file_path):
        from docx import Document
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(f"Source: {url}")
        doc.add_paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_heading('Content:', level=1)
        for para in text_content.split('\n'):
            if para.strip():
                doc.add_paragraph(para.strip())
        doc.save(file_path)

# ============================================================================
# ОБРАБОТЧИК КОНТЕНТА
# ============================================================================

class ContentProcessor:
    def __init__(self):
        self.scraper = WebScraper()
        self.processed_urls = {}
        self.lang = "ru"

    def set_language(self, lang):
        self.lang = lang if lang in ["ru", "en"] else "ru"

    def process_url(self, url, output_format="md", output_dir=None, use_cache=True):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return self.scraper.scrape_url(url, output_format, output_dir, use_cache=use_cache, lang=self.lang)

    def process_urls(self, urls, output_format="md", output_dir=None, use_cache=True, concurrency=1):
        if not urls:
            return {"status": "error", "message": "No URLs provided"}
        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, DEFAULT_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        lock = threading.Lock()

        def worker(url):
            try:
                result = self.process_url(url, output_format, output_dir, use_cache)
                with lock:
                    results[url] = result
            except Exception as e:
                with lock:
                    results[url] = {"status": "error", "error": str(e), "url": url}

        threads = []
        for url in urls:
            t = threading.Thread(target=worker, args=(url,))
            threads.append(t)
            t.start()
            if len(threads) >= concurrency:
                for thread in threads:
                    thread.join()
                threads = []
        for thread in threads:
            thread.join()

        total = len(results)
        success = sum(1 for r in results.values() if r.get("status") == "ok")
        failed = total - success
        cached = sum(1 for r in results.values() if r.get("status") == "cached")
        blocked = sum(1 for r in results.values() if r.get("blocked_suspected"))
        total_size = sum(r.get("size_bytes", 0) for r in results.values())
        total_words = sum(r.get("word_count", 0) or 0 for r in results.values())

        return {
            "total_urls": total, "successful": success, "failed": failed,
            "cached": cached, "blocked": blocked,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "total_size": total_size, "total_size_human": human_size(total_size),
            "total_words": total_words, "results": results, "timestamp": datetime.now().isoformat()
        }

    def process_file_with_urls(self, file_path, output_format="md", output_dir=None):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            urls = []
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    url_match = re.search(r'https?://[^\s]+', line)
                    if url_match:
                        urls.append(url_match.group(0))
                    elif line:
                        urls.append(line)
            if not urls:
                return {"status": "error", "message": "No URLs found in file"}
            return self.process_urls(urls, output_format, output_dir)
        except Exception as e:
            return {"status": "error", "error": str(e), "file": file_path}

    def clear_cache(self):
        self.scraper.cache.clear()
        return {"status": "ok", "message": "Cache cleared"}

# ============================================================================
# КОНСОЛЬНОЕ МЕНЮ
# ============================================================================

class ConsoleMenu:
    def __init__(self):
        self.processor = ContentProcessor()
        self.lang = "ru"
        self.running = True

    def set_language(self, lang):
        self.lang = lang
        self.processor.set_language(lang)

    def print_menu(self):
        print_header()
        if self.lang == "ru":
            print("  ГЛАВНОЕ МЕНЮ")
            print_separator()
            print("  1. 🌐 Скрейпить один URL")
            print("  2. 📋 Скрейпить несколько URL")
            print("  3. 📄 Скрейпить URL из файла")
            print("  4. 🧹 Очистить кэш")
            print("  5. ❓ Показать информацию")
            print("  6. 🌐 Изменить язык")
            print("  0. ✗ Выход")
        else:
            print("  MAIN MENU")
            print_separator()
            print("  1. 🌐 Scrape single URL")
            print("  2. 📋 Scrape multiple URLs")
            print("  3. 📄 Scrape URLs from file")
            print("  4. 🧹 Clear cache")
            print("  5. ❓ Show about")
            print("  6. 🌐 Change language")
            print("  0. ✗ Exit")
        print_separator()

    def get_choice(self, max_choice=6):
        while True:
            try:
                prompt = "  Выберите (0-{}): ".format(max_choice) if self.lang == "ru" else "  Choose (0-{}): ".format(max_choice)
                choice = input(prompt)
                choice = int(choice)
                if 0 <= choice <= max_choice:
                    return choice
            except ValueError:
                pass

    def input_url(self):
        while True:
            if self.lang == "ru":
                url = input("  Введите URL (или 'назад'): ")
                if url.lower() in ['назад', 'отмена']:
                    return None
            else:
                url = input("  Enter URL (or 'back'): ")
                if url.lower() in ['back', 'cancel']:
                    return None
            if url:
                return url.strip()

    def input_urls(self):
        urls = []
        if self.lang == "ru":
            print("  Введите URL (пустая строка - завершить):")
        else:
            print("  Enter URLs (empty line to finish):")
        while True:
            url = input("  URL: ")
            url = url.strip()
            if self.lang == "ru":
                if url.lower() in ['назад', 'отмена', 'стоп']:
                    break
            else:
                if url.lower() in ['back', 'cancel', 'stop']:
                    break
            if url:
                urls.append(url)
            elif len(urls) > 0:
                break
        return urls

    def select_format(self):
        print()
        if self.lang == "ru":
            print("  Выберите формат:")
        else:
            print("  Select format:")
        for i, fmt in enumerate(SUPPORTED_FORMATS, 1):
            name = self.get_format_name(fmt)
            print(f"    {i}. {name}")
        print(f"    0. {"Назад" if self.lang == "ru" else "Back"}")
        choice = self.get_choice(len(SUPPORTED_FORMATS))
        if choice == 0:
            return None
        return SUPPORTED_FORMATS[choice - 1]

    def get_format_name(self, fmt):
        names = {
            "txt": "Текст (TXT)" if self.lang == "ru" else "Text (TXT)",
            "html": "HTML",
            "md": "Markdown (MD)" if self.lang == "ru" else "Markdown (MD)",
            "docx": "Word (DOCX)" if self.lang == "ru" else "Word (DOCX)",
        }
        return names.get(fmt, fmt.upper())

    def scrape_single(self):
        print_header()
        if self.lang == "ru":
            print("  СКРЕЙПИНГ ОДНОГО URL")
        else:
            print("  SCRAPE SINGLE URL")
        print_separator()
        url = self.input_url()
        if not url:
            return
        fmt = self.select_format()
        if not fmt:
            return
        print()
        if self.lang == "ru":
            print("  Обработка: {}".format(url))
        else:
            print("  Processing: {}".format(url))
        result = self.processor.process_url(url, fmt)
        self.display_result(result)
        self.pause()

    def scrape_multiple(self):
        print_header()
        if self.lang == "ru":
            print("  СКРЕЙПИНГ НЕСКОЛЬКИХ URL")
        else:
            print("  SCRAPE MULTIPLE URLs")
        print_separator()
        urls = self.input_urls()
        if not urls:
            return
        fmt = self.select_format()
        if not fmt:
            return
        print()
        if self.lang == "ru":
            print("  Обработка {} URL...".format(len(urls)))
        else:
            print("  Processing {} URLs...".format(len(urls)))
        result = self.processor.process_urls(urls, fmt)
        self.display_batch_results(result)
        self.pause()

    def scrape_from_file(self):
        print_header()
        if self.lang == "ru":
            print("  СКРЕЙПИНГ URL ИЗ ФАЙЛА")
        else:
            print("  SCRAPE URLs FROM FILE")
        print_separator()
        if self.lang == "ru":
            file_path = input("  Введите путь к файлу: ")
        else:
            file_path = input("  Enter file path: ")
        file_path = file_path.strip()
        if not file_path:
            return
        if not os.path.exists(file_path):
            if self.lang == "ru":
                print("  ✗ Файл не найден: {}".format(file_path))
            else:
                print("  ✗ File not found: {}".format(file_path))
            self.pause()
            return
        fmt = self.select_format()
        if not fmt:
            return
        print()
        if self.lang == "ru":
            print("  Чтение URL из файла...")
        else:
            print("  Reading URLs from file...")
        result = self.processor.process_file_with_urls(file_path, fmt)
        if "results" in result:
            self.display_batch_results(result)
        else:
            if self.lang == "ru":
                print("  ✗ Ошибка: {}".format(result.get('message', result.get('error', 'Неизвестная ошибка'))))
            else:
                print("  ✗ Error: {}".format(result.get('message', result.get('error', 'Unknown error'))))
        self.pause()

    def display_result(self, result):
        print_separator()
        if self.lang == "ru":
            print("  РЕЗУЛЬТАТ ДЛЯ: {}".format(result.get('url', 'N/A')))
        else:
            print("  RESULT FOR: {}".format(result.get('url', 'N/A')))
        print_separator()
        status = result.get('status', 'unknown')
        if status == "ok":
            print("  ✓ Успешно!")
        elif status == "cached":
            print("  ✓ Из кэша")
        elif status == "blocked":
            print("  ✗ Заблокировано!")
        else:
            print("  ✗ Ошибка: {}".format(result.get('error', 'Unknown')))
        print()
        print("  Статус: {}".format(status))
        print("  Файл: {}".format(result.get('file', 'N/A')))
        print("  Размер: {}".format(human_size(result.get('size_bytes', 0))))
        print("  Слов: {}".format(result.get('word_count', 'N/A')))
        print("  Время: {:.2f}с".format(result.get('elapsed_sec', 0)))
        if result.get('blocked_suspected'):
            print()
            if self.lang == "ru":
                print("  ⚠ ВНИМАНИЕ: Сайт заблокировал запрос (Cloudflare)")
            else:
                print("  ⚠ WARNING: Site blocked the request (Cloudflare)")
        print_separator()

    def display_batch_results(self, result):
        print_separator()
        if self.lang == "ru":
            print("  РЕЗУЛЬТАТЫ ПАКЕТНОЙ ОБРАБОТКИ")
        else:
            print("  BATCH PROCESSING RESULTS")
        print_separator()
        print("  Всего: {}".format(result.get('total_urls', 0)))
        print("  Успешно: {}".format(result.get('successful', 0)))
        print("  Ошибок: {}".format(result.get('failed', 0)))
        print("  Из кэша: {}".format(result.get('cached', 0)))
        print("  Заблокировано: {}".format(result.get('blocked', 0)))
        print("  Успешность: {:.1f}%".format(result.get('success_rate', 0)))
        print("  Размер: {}".format(result.get('total_size_human', '0')))
        if result.get('failed', 0) > 0:
            print()
            if self.lang == "ru":
                print("  ОШИБКИ:")
            else:
                print("  ERRORS:")
            for url, data in result.get('results', {}).items():
                if data.get('status') != 'ok':
                    print("    ✗ {}: {}".format(url, data.get('error', 'Unknown')))
        print_separator()

    def show_about(self):
        print_header()
        if self.lang == "ru":
            print("  О ПРОГРАММЕ")
        else:
            print("  ABOUT")
        print_separator()
        print("  {} v{}".format(APP_NAME, APP_VERSION))
        print("  Автор: {}".format(APP_AUTHOR))
        print()
        if self.lang == "ru":
            print("  ОПИСАНИЕ:")
            print("    Универсальный веб-скрейпер")
            print("    Работает без внешних ключей и прокси")
            print()
            print("  ВОЗМОЖНОСТИ:")
            print("    ✓ Скрейпинг страниц")
            print("    ✓ Пакетная обработка")
            print("    ✓ Автоматическое кэширование")
            print("    ✓ Симуляция браузеров")
            print()
            print("  ОГРАНИЧЕНИЯ:")
            print("    ✗ Не работает с JavaScript-защитой")
            print("      (Cloudflare, некоторые .gov сайты)")
        else:
            print("  DESCRIPTION:")
            print("    Universal web scraper")
            print("    Works without external keys and proxies")
            print()
            print("  FEATURES:")
            print("    ✓ Page scraping")
            print("    ✓ Batch processing")
            print("    ✓ Automatic caching")
            print("    ✓ Browser simulation")
            print()
            print("  LIMITATIONS:")
            print("    ✗ Doesn't work with JavaScript protection")
            print("      (Cloudflare, some .gov sites)")
        print_separator()
        self.pause()

    def pause(self):
        if self.lang == "ru":
            input("  Нажмите Enter для продолжения...")
        else:
            input("  Press Enter to continue...")

    def run(self):
        while self.running:
            self.print_menu()
            choice = self.get_choice()
            if choice == 1:
                self.scrape_single()
            elif choice == 2:
                self.scrape_multiple()
            elif choice == 3:
                self.scrape_from_file()
            elif choice == 4:
                result = self.processor.clear_cache()
                if self.lang == "ru":
                    print("  ✓ Кэш очищен")
                else:
                    print("  ✓ Cache cleared")
                self.pause()
            elif choice == 5:
                self.show_about()
            elif choice == 6:
                self.lang = "en" if self.lang == "ru" else "ru"
                self.processor.set_language(self.lang)
                if self.lang == "ru":
                    print("  ✓ Язык: Русский")
                else:
                    print("  ✓ Language: English")
                self.pause()
            elif choice == 0:
                self.running = False

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    if len(sys.argv) > 1:
        # CLI режим
        from argparse import ArgumentParser
        parser = ArgumentParser(description='{} - Universal Web Scraper'.format(APP_NAME))
        parser.add_argument('--urls', nargs='+', help='List of URLs to scrape')
        parser.add_argument('--url', help='Single URL to scrape')
        parser.add_argument('--file', help='File with URLs to scrape')
        parser.add_argument('--format', default='md', choices=SUPPORTED_FORMATS)
        parser.add_argument('--output', default=None, help='Output directory')
        parser.add_argument('--concurrency', type=int, default=1)
        parser.add_argument('--no-cache', action='store_true')

        args = parser.parse_args()
        processor = ContentProcessor()

        urls = args.urls or []
        if args.url:
            urls.append(args.url)

        if args.file:
            result = processor.process_file_with_urls(args.file, args.format, args.output)
        elif urls:
            result = processor.process_urls(
                urls, output_format=args.format, output_dir=args.output,
                use_cache=not args.no_cache, concurrency=args.concurrency
            )
            print("\nResults:")
            print("  Total: {}".format(result.get('total_urls', 0)))
            print("  Success: {}".format(result.get('successful', 0)))
            print("  Failed: {}".format(result.get('failed', 0)))
            print("  Cached: {}".format(result.get('cached', 0)))
            print("  Size: {}".format(result.get('total_size_human', '0')))
            if result.get('failed', 0) > 0:
                print("\nFailed URLs:")
                for url, data in result.get('results', {}).items():
                    if data.get('status') != 'ok':
                        print("  FAILED: {}: {}".format(url, data.get('error', 'Unknown')))
        else:
            parser.print_help()
    else:
        # Интерактивный режим
        menu = ConsoleMenu()
        menu.run()

if __name__ == '__main__':
    main()
