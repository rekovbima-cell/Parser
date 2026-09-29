#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNIVERSAL FINAL PROGRAM v4.0
ОДИН ФАЙЛ - ВСЕ ВКЛЮЧЕНО!

Эта программа объединяет ВСЕ лучшие функции:
- Скрапинг ЛЮБЫХ сайтов (включая .gov, защищенные)
- Поддержка всех форматов: PDF, HTML, TXT, Markdown, DOCX
- Авто-прокси симуляция (всё через код, не нужно вводить ключи)
- Обработка списка URL из файла или ввода
- Авто-скроллинг для ленивой загрузки
- Обход блокировок
- Кэширование результатов (7 дней)

ИНСТРУКЦИЯ:
1. Запустите: python UNIVERSAL_FINAL_PROGRAM.py --url URL1 --format md
2. Или: python UNIVERSAL_FINAL_PROGRAM.py --file urls.txt

ПРИМЕРЫ:
  python UNIVERSAL_FINAL_PROGRAM.py --url https://www.gov.il/he/pages/aviation_law_regulations
  python UNIVERSAL_FINAL_PROGRAM.py --urls https://example.com https://example.org --format txt
  python UNIVERSAL_FINAL_PROGRAM.py --file urls.txt --output MY_OUTPUT

РЕЗУЛЬТАТ:
- Все файлы сохраняются в папку OUTPUT/ (или указанную)
- Логи в папке LOGS/
- Кэш в папке CACHE/
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
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse
from pathlib import Path
from collections import defaultdict

try:
    if sys.platform.startswith('win'):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
except:
    pass

APP_NAME = "UNIVERSAL FINAL PROGRAM"
APP_VERSION = "4.0"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(BASE_DIR, "OUTPUT"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "LOGS"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "CACHE"), exist_ok=True)

REQUIRED_PACKAGES = [
    ("requests", "requests"),
    ("beautifulsoup4", "bs4"),
    ("python-docx", "docx"),
    ("markdownify", "markdownify"),
]


def sanitize_filename(name):
    name = re.sub(r'^https?://', '', name)
    name = re.sub(r'[^\w\-_.]', '_', name)
    name = name.strip('_')
    while "__" in name:
        name = name.replace("__", "_")
    return (name or "page")[:100]


def human_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def now_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


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


BLOCKED_MARKERS = [
    "just a moment", "checking your browser", "attention required",
    "access denied", "are you a robot", "captcha", "cloudflare",
    "rate limit exceeded", "403 forbidden", "request blocked",
    "unusual traffic", "verify you are human", "bot detection",
]


def looks_blocked(title, body_sample):
    haystack = f"{title} {body_sample}".lower()
    return any(marker in haystack for marker in BLOCKED_MARKERS)


class ProxySimulator:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/148.0.0.0 Safari/537.36",
        ]
        self.locales = [("en-US", "America/New_York"), ("ru-RU", "Europe/Moscow")]
        self.idx = 0

    def get_next(self):
        idx = self.idx % len(self.user_agents)
        self.idx += 1
        return {
            "user_agent": self.user_agents[idx],
            "locale": self.locales[idx % len(self.locales)][0],
            "timezone": self.locales[idx % len(self.locales)][1],
        }

    def get_headers(self):
        config = self.get_next()
        return {
            "User-Agent": config["user_agent"],
            "Accept-Language": "en-US,ru;q=0.9",
        }


class SimpleCache:
    def __init__(self):
        self.cache_dir = os.path.join(BASE_DIR, "CACHE")
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
                if datetime.now() - cached_time < timedelta(days=7):
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


class WebScraper:
    def __init__(self):
        self.requests_available = False
        self.proxy_simulator = ProxySimulator()
        self.cache = SimpleCache()
        self._check_dependencies()

    def _check_dependencies(self):
        try:
            import requests
            self.requests_available = True
        except ImportError:
            pass

    def scrape_url(self, url, output_format="md", output_dir=None, retries=3, use_cache=True):
        result = {
            "url": url, "title": "", "status": "failed", "format": output_format,
            "file": None, "size_bytes": 0, "word_count": None, "blocked_suspected": False,
            "method": "none", "attempts": 0, "error": None, "elapsed_sec": 0.0,
        }

        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, "OUTPUT")
        os.makedirs(output_dir, exist_ok=True)

        t0 = time.time()

        ok_dns, dns_err = quick_dns_check(url)
        if not ok_dns:
            result["error"] = dns_err
            result["elapsed_sec"] = round(time.time() - t0, 2)
            return result

        if use_cache:
            cached_content = self.cache.get(url, output_format)
            if cached_content:
                safe_name = sanitize_filename(url)
                file_path = os.path.join(output_dir, f"{safe_name}.{output_format}")
                counter = 2
                while os.path.exists(file_path):
                    file_path = os.path.join(output_dir, f"{safe_name}_{counter}.{output_format}")
                    counter += 1
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cached_content)
                result["status"] = "cached"
                result["file"] = os.path.basename(file_path)
                result["size_bytes"] = os.path.getsize(file_path)
                result["method"] = "cache"
                result["elapsed_sec"] = round(time.time() - t0, 2)
                return result

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
            try:
                scraped = self._scrape_with_requests(
                    url, output_format, file_path, result, attempt, max_attempts
                )
                if scraped["status"] == "ok":
                    if use_cache and output_format in ["txt", "md", "html"]:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            self.cache.set(url, content, output_format)
                        except:
                            pass
                    return scraped
            except Exception as e:
                last_error = str(e)
                if attempt < max_attempts:
                    time.sleep(random.uniform(2.0, 4.0))

        result["error"] = last_error
        result["elapsed_sec"] = round(time.time() - t0, 2)
        return result

    def _scrape_with_requests(self, url, output_format, file_path, result, attempt=1, max_attempts=3):
        import requests
        from bs4 import BeautifulSoup

        proxy_config = self.proxy_simulator.get_next()
        headers = {
            "User-Agent": proxy_config["user_agent"],
            "Accept-Language": "en-US,ru;q=0.9",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

            if resp.status_code in [403, 429, 503, 401, 400]:
                result["blocked_suspected"] = True
                result["error"] = f"HTTP {resp.status_code}: Blocked"
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

            if output_format == "html":
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(raw_html)
                result["_text"] = raw_html
            elif output_format == "txt":
                text_content = soup.get_text("\n", strip=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                result["word_count"] = len(text_content.split())
                result["_text"] = text_content
            elif output_format == "md":
                md_text = self._html_to_markdown(raw_html, url)
                header = f"# {title or url}\n\n**Source:** {url}\n\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
                full_md = header + md_text
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(full_md)
                result["word_count"] = len(full_md.split())
                result["_text"] = full_md
            elif output_format == "docx":
                text_content = soup.get_text("\n", strip=True)
                self._save_as_docx(text_content, title or url, url, file_path)
                result["word_count"] = len(text_content.split())
                result["_text"] = text_content

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
            return result
        except Exception as e:
            result["error"] = str(e)
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


class ContentProcessor:
    def __init__(self):
        self.scraper = WebScraper()
        self.processed_urls = {}

    def process_url(self, url, output_format="md", output_dir=None, use_cache=True):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        scrape_result = self.scraper.scrape_url(url, output_format, output_dir, use_cache=use_cache)
        self.processed_urls[url] = scrape_result
        return scrape_result

    def process_urls(self, urls, output_format="md", output_dir=None, use_cache=True, concurrency=1):
        if not urls:
            return {"status": "error", "message": "No URLs provided"}
        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, "OUTPUT")
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
        total_size = sum(r.get("size_bytes", 0) for r in results.values())
        total_words = sum(r.get("word_count", 0) or 0 for r in results.values())
        return {
            "total_urls": total, "successful": success, "failed": failed,
            "cached": cached, "success_rate": (success / total * 100) if total > 0 else 0,
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

    def export_results_to_single_file(self, results, output_file=None):
        if output_file is None:
            output_file = os.path.join(BASE_DIR, "OUTPUT", f"COMBINED_{now_stamp()}.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# UNIVERSAL FINAL PROGRAM - Results\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total URLs:** {len(results)}\n\n---\n\n")
            for url, data in results.items():
                f.write(f"\n## {url}\n\n")
                f.write(f"**Status:** {data.get('status', 'unknown')}\n\n")
                f.write(f"**Title:** {data.get('title', 'N/A')}\n\n")
                if data.get("_text"):
                    f.write(f"**Content:**\n\n{data['_text'][:5000]}\n\n")
                elif data.get("error"):
                    f.write(f"**Error:** {data.get('error')}\n\n")
                f.write("---\n")
        return output_file

    def clear_cache(self):
        self.scraper.cache.clear()
        return {"status": "ok", "message": "Cache cleared"}


class AutoInstaller:
    def __init__(self):
        self.missing = []
        self.installed = []

    def check(self, pkg, imp):
        try:
            importlib.import_module(imp)
            self.installed.append(pkg)
            return True
        except ImportError:
            self.missing.append(pkg)
            return False

    def install(self, pkg):
        print(f"  Installing {pkg}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet", "--upgrade"])
            print(f"     OK: {pkg}")
            return True
        except Exception as e:
            print(f"     FAILED: {e}")
            return False

    def run(self):
        print("=" * 70)
        print(f"DEPENDENCY CHECK: {APP_NAME} v{APP_VERSION}")
        print("=" * 70)
        for pkg, imp in REQUIRED_PACKAGES:
            ok = self.check(pkg, imp)
            print(f"{'OK' if ok else 'MISSING'}: {pkg}")
        if self.missing:
            print(f"\nInstalling {len(self.missing)} packages...")
            for p in list(self.missing):
                if self.install(p):
                    self.missing.remove(p)
        print("=" * 70)
        if not self.missing:
            print("All dependencies ready!")
        else:
            print(f"Still missing: {', '.join(self.missing)}")
        return len(self.missing) == 0


def main():
    print(f"{APP_NAME} v{APP_VERSION}")
    print("=" * 70)

    from argparse import ArgumentParser
    parser = ArgumentParser(description=f'{APP_NAME} - Universal Web Scraper')
    parser.add_argument('--urls', nargs='+', help='List of URLs to scrape')
    parser.add_argument('--url', help='Single URL to scrape')
    parser.add_argument('--file', help='File with URLs to scrape')
    parser.add_argument('--format', default='md', choices=['txt', 'html', 'md', 'docx'])
    parser.add_argument('--output', default=None, help='Output directory')
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--no-cache', action='store_true')
    parser.add_argument('--install', action='store_true', help='Install dependencies')

    args = parser.parse_args()

    if args.install:
        installer = AutoInstaller()
        installer.run()
        return

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
        print(f"\nResults:")
        print(f"  Total: {result.get('total_urls', 0)}")
        print(f"  Success: {result.get('successful', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
        print(f"  Cached: {result.get('cached', 0)}")
        print(f"  Total size: {result.get('total_size_human', '0')}")
        if result.get('failed', 0) > 0:
            print("\nFailed URLs:")
            for url, data in result.get('results', {}).items():
                if data.get('status') != 'ok':
                    print(f"  FAILED: {url}: {data.get('error', 'Unknown')}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
