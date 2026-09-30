#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PREVIEW_SERVER v1.0 — локальный сервер рендеринга для 00-bad-tank.html

Почему он нужен: публичные CORS-прокси (allorigins и т.п.) НЕ выполняют
JavaScript целевых страниц и часто блокируются. Этот сервер рендерит
страницу настоящим браузером (Firefox Portable + Selenium) и отдаёт
готовый HTML. 00-bad-tank.html автоматически пробует этот сервер
ПЕРВЫМ (http://127.0.0.1:8765/render?url=...), а при неудаче откатывается
на публичные прокси.

Запуск:  python PREVIEW_SERVER.py
Затем:   откройте http://127.0.0.1:8765/  (там же лежит 00-bad-tank.html)
"""

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8765
TANK_FILE = os.path.join(BASE_DIR, "00-bad-tank.html")
PAGE_TIMEOUT = 60
JS_STABLE_TIMEOUT = 25

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
FIREFOX_PATH = os.path.join(BASE_DIR, "BROWSER", "FirefoxPortable", "FirefoxPortable.exe")
BLOCKED_MARKERS = ["just a moment", "checking your browser", "access denied", "captcha", "403 forbidden"]

_driver = None
_driver_lock = threading.Lock()


def log(msg):
    print("[preview] %s" % msg, flush=True)


def get_driver():
    """Один переиспользуемый headless Firefox (Selenium)."""
    global _driver
    with _driver_lock:
        if _driver is not None:
            return _driver
        try:
            from selenium import webdriver
            from selenium.webdriver.firefox.options import Options
            from selenium.webdriver.firefox.service import Service
            from webdriver_manager.firefox import GeckoDriverManager

            options = Options()
            if os.path.exists(FIREFOX_PATH):
                options.binary_location = FIREFOX_PATH
            options.add_argument("-headless")
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            options.set_preference("general.useragent.override", USER_AGENT)
            options.set_preference("dom.max_script_run_time", 30)

            service = Service(GeckoDriverManager().install())
            _driver = webdriver.Firefox(service=service, options=options)
            _driver.set_page_load_timeout(PAGE_TIMEOUT)
            log("браузер готов (Selenium + Firefox)")
            return _driver
        except Exception as e:
            log("браузер недоступен (%s) — будет HTTP-fallback" % str(e).strip()[:120])
            return None


def wait_js(driver):
    """Ожидание реальной отрисовки JS: readyState + прокрутка + стабилизация."""
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, PAGE_TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    last, stable, deadline = -1, 0, time.time() + JS_STABLE_TIMEOUT
    while time.time() < deadline and stable < 3:
        try:
            driver.execute_script(
                "window.scrollTo(0, Math.max(document.body.scrollHeight,"
                " document.documentElement.scrollHeight));")
        except Exception:
            pass
        time.sleep(1)
        try:
            cur = driver.execute_script(
                "return (document.body ? (document.body.innerText || '').length : 0)")
        except Exception:
            break
        if cur == last:
            stable += 1
        else:
            stable = 0
            last = cur


def render_browser(url):
    driver = get_driver()
    if not driver:
        return None
    with _driver_lock:
        try:
            driver.get(url)
            wait_js(driver)
            return driver.page_source
        except Exception as e:
            log("ошибка браузера: %s" % str(e).strip()[:120])
            return None


def render_http(url):
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log("ошибка HTTP: %s" % str(e).strip()[:120])
        return None


def render(url):
    """Браузерный JS-рендеринг -> HTTP-fallback."""
    html = render_browser(url)
    if html and len(html.strip()) > 500:
        return html, "browser"
    html = render_http(url)
    if html:
        return html, "http"
    return None, "error"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype, extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/tank"):
            try:
                with open(TANK_FILE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except Exception:
                self._send(404, "00-bad-tank.html не найден рядом с PREVIEW_SERVER.py", "text/plain; charset=utf-8")
            return
        if parsed.path == "/health":
            self._send(200, "OK", "text/plain; charset=utf-8")
            return
        if parsed.path == "/render":
            url = (parse_qs(parsed.query).get("url") or [""])[0]
            if not url.startswith(("http://", "https://")):
                self._send(400, json.dumps({"error": "bad url"}), "application/json")
                return
            log("render: %s" % url)
            html, method = render(url)
            if not html:
                self._send(502, json.dumps({"error": "render failed", "url": url}), "application/json")
                return
            low = html[:4000].lower()
            blocked = any(m in low for m in BLOCKED_MARKERS)
            self._send(200, html, "text/html; charset=utf-8",
                       {"X-Preview-Method": method, "X-Preview-Status": "blocked" if blocked else "ok"})
            return
        self._send(404, "not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        pass


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
    log("PREVIEW_SERVER на http://127.0.0.1:%d/ (там же консоль 00-bad-tank.html)" % PORT)
    log("API рендеринга: http://127.0.0.1:%d/render?url=..." % PORT)
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        log("остановлено")


if __name__ == "__main__":
    main()
