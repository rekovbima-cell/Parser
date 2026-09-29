#!/usr/bin/env python3
-- coding: utf-8 --
"""
================================================================================
 MEGA TANK v3.0 EXT — UNIVERSAL DOCUMENTATION SCRAPER
 Пересобран: 30.06.2026  |  Extended Edition: 29.09.2026
================================================================================
 БАЗА (v3.0):
   • Список URL → PDF / HTML / TXT / DOCX / Markdown
   • Объединение в один файл для ЛЮБОГО формата
   • Папка MEGATANK: файлы + MEGAFULL.* + manifest.json
     + INDEX.md + RUN.log + storage_state.json
   • Автоустановка зависимостей и браузера при первом запуске
   • Параллельность 1–5 потоков, повторы с ротацией UA/fingerprint
   • DNS-предпроверка, доскролл lazy-load, эвристика блокировок
   • Fallback requests+BeautifulSoup, кнопки «Стоп» / «Открыть папку»

 EXTENDED (эта сборка) — интеграция внешних браузеров и профилей:
   1. ExternalBrowserManager: обнаружение портативных и системных браузеров
      (Chrome/Edge/Brave/Opera/Chromium Portable, Firefox Portable, LibreWolf).
   2. Три режима подключения:
        bundled    — стандартный Chromium/Chrome от Playwright;
        persistent — launchpersistentcontext(userdatadir) → живые cookies,
                     local storage, история, «прогретый» fingerprint;
        cdp        — connectovercdp() к УЖЕ ЗАПУЩЕННОМУ браузеру пользователя
                     (авторизация выполнена вручную, скрипт её не трогает).
   3. Гетерогенность движков: Blink (CDP) и Gecko (Juggler). Честная диагностика:
      Playwright управляет Firefox только через патченную сборку, поэтому внешний
      Firefox/LibreWolf автоматически уходит в цепочку фоллбэков.
   4. Изолированная КОПИЯ профиля (кнопка «Копия») — оригинал не блокируется
      и не модифицируется; кэш/Service Worker/Singleton-локи не копируются.
   5. Chrome 136+: --remote-debugging-port игнорируется для профиля по умолчанию,
      поэтому CDP работает только с явным user-data-dir; порт — только 127.0.0.1.
   6. Жизненный цикл: подключённый браузер пользователя НИКОГДА не закрывается
      скриптом (owns_browser=False), закрывается только наша вкладка.
   7. PROFILE_LOCK: один user-data-dir не может быть открыт двумя процессами,
      поэтому при работе с профилем/CDP потоки сериализуются автоматически.
   8. PDF на Gecko: page.pdf() существует только в Chromium → рендер сохранённого
      HTML отдельным headless-Chromium, иначе деградация в .html с пометкой.

 ГОРЯЧИЕ ПРАВКИ ЯДРА (унаследованы от hotfix-сборки):
   • UTF-8 в консоли Windows (иначе краш на эмодзи ДО открытия GUI)
   • «Агрессивный режим» больше НЕ делает паузы длиннее щадящего (была инверсия)
   • Атомарное резервирование имён файлов между потоками (PATH_LOCK)
   • safexmltext() — python-docx падал на управляющих символах XML
   • locale / Accept-Language / navigator.languages / --lang согласованы
   • merge_pdf() не падает целиком из-за одного битого или зашифрованного PDF
   • requests-фоллбэк читает charset из Content-Type (кириллица без можибаки)
   • absolutize() — относительные href/src больше не ведут в никуда
   • browser.close() в finally — нет зависших процессов
================================================================================
"""

import sys
import os
import subprocess
import importlib
import threading
import queue
import time
import random
import re
import json
import socket
import shutil
import webbrowser
from datetime import datetime
from urllib.parse import urlparse, urljoin

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

==============================================================================
ГЛУШКА КОНСОЛИ (Windows cp866/cp1251 → UnicodeEncodeError на эмодзи)
==============================================================================
def fixconsole():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

fixconsole()

==============================================================================
КОНСТАНТЫ
==============================================================================
APP_NAME = "MEGA TANK"
APP_VERSION = "3.0 EXT"
BUILD_DATE = "29.09.2026"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(file))

PROFILEROOT = os.path.join(BASEDIR, "MEGATANKprofiles")
CREATENOWINDOW = subprocess.CREATENOWINDOW if os.name == "nt" else 0

SYSTEM_BROWSER = "System Default (Playwright bundled)"

REQUIRED_PACKAGES = [
    ("requests", "requests"),
    ("playwright", "playwright"),
    ("pypdf", "pypdf"),
    ("python-docx", "docx"),
    ("beautifulsoup4", "bs4"),
    ("markdownify", "markdownify"),
]

FORMAT_MAP = {
    "PDF": "pdf",
    "HTML": "html",
    "TXT": "txt",
    "DOCX": "docx",
    "Markdown": "md",
}

BLOCKED_MARKERS = [
    "just a moment", "checking your browser", "attention required",
    "access denied", "are you a robot", "captcha", "cloudflare",
    "rate limit exceeded", "403 forbidden", "request blocked",
    "unusual traffic", "verify you are human", "bot detection",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10157) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
]

LOCALETZPAIRS = [
    ("en-US", "America/New_York"),
    ("en-US", "America/Los_Angeles"),
    ("en-US", "America/Chicago"),
    ("en-GB", "Europe/London"),
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

HARDWARE_PROFILES = [(8, 8), (12, 8), (4, 4), (16, 8), (8, 4)]

PATH_LOCK = threading.Lock()
RESERVED_PATHS = set()
Один user-data-dir / один живой браузер не выдерживают двух процессов сразу.
PROFILE_LOCK = threading.RLock()

CONTENT_SELECTOR = ("article, main, [role='main'], .article, .post, "
                    ".entry-content, .post-content, .content")

JUNK_SELECTOR = ("script, style, noscript, template, svg, canvas, iframe, nav, header, "
                 "footer, aside, [aria-hidden=\"true\"], [role=\"navigation\"], "
                 "[role=\"banner\"], [role=\"contentinfo\"], .cookie, .cookies, .consent, "
                 ".popup, .modal, .advert, .ads, .ad, .social-share")

Что НЕ копируем в изолированную копию профиля
PROFILEIGNORE = shutil.ignorepatterns(
    "Cache", "Code Cache", "GPUCache", "DawnCache", "ShaderCache", "GrShaderCache",
    "Service Worker", "CacheStorage", "componentcrxcache", "extensionscrxcache",
    "Singleton", ".lock", "lockfile", "parent.lock", ".parentlock",
    "Crashpad", "Crash Reports", "blobstorage", "optimizationguide_*",
)

==============================================================================
STEALTH (Blink) + PREFS (Gecko)
==============================================================================
STEALTH_TEMPLATE = r"""
(() => {
    const LANGS    = LANGS;
    const PLATFORM = PLATFORM;
    const HW       = HW;
    const MEM      = MEM;

    try { delete Object.getPrototypeOf(navigator).webdriver; } catch (e) {}
    try { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); } catch (e) {}
    try { Object.defineProperty(navigator, 'platform',  { get: () => PLATFORM }); } catch (e) {}
    try { Object.defineProperty(navigator, 'languages', { get: () => LANGS }); } catch (e) {}
    try { Object.defineProperty(navigator, 'vendor',    { get: () => 'Google Inc.' }); } catch (e) {}
    try { Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => HW }); } catch (e) {}
    try { Object.defineProperty(navigator, 'deviceMemory', { get: () => MEM }); } catch (e) {}

    const mk = (name, filename, description) => ({ name, filename, description, length: 1 });
    const pluginArr = [
        mk('Chrome PDF Plugin', 'internal-pdf-viewer',             'Portable Document Format'),
        mk('Chrome PDF Viewer', 'mhjfbmdgcfjbbpaeojofohoefgiehjai', ''),
        mk('Native Client',     'internal-nacl-plugin',             '')
    ];
    pluginArr.item      = (i) => pluginArr[i] || null;
    pluginArr.namedItem = (n) => pluginArr.filter(p => p.name === n)[0] || null;
    pluginArr.refresh   = () => {};
    try { Object.defineProperty(navigator, 'plugins',   { get: () => pluginArr }); } catch (e) {}
    try { Object.defineProperty(navigator, 'mimeTypes', { get: () => [] }); } catch (e) {}

    window.chrome = window.chrome || { runtime: {}, loadTimes: () => ({}), csi: () => ({}) };

    try {
        const origQuery = window.navigator.permissions && window.navigator.permissions.query;
        if (origQuery) {
            window.navigator.permissions.query = (parameters) => (
                parameters && parameters.name === 'notifications'
                    ? Promise.resolve({ state: (typeof Notification !== 'undefined' && Notification.permission) || 'granted' })
                    : origQuery(parameters)
            );
        }
    } catch (e) {}

    try {
        const patch = (proto) => {
            if (!proto) return;
            const orig = proto.getParameter;
            proto.getParameter = function (parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return orig.call(this, parameter);
            };
        };
        patch(window.WebGLRenderingContext && WebGLRenderingContext.prototype);
        patch(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);
    } catch (e) {}
})();
"""

DISMISS_JS = r"""
() => {
    const words = ['accept all', 'accept', 'agree', 'i agree', 'got it', 'okay', 'ok',
                   'reject all', 'no thanks', 'close', 'dismiss',
                   'принять все', 'принять', 'согласен', 'согласна', 'понятно',
                   'закрыть', 'отклонить'];
    const nodes = Array.from(document.querySelectorAll(
        'button, input[type="button"], input[type="submit"], [role="button"]'));
    let clicked = 0;
    for (const n of nodes) {
        const t = ((n.innerText || n.value || n.getAttribute('aria-label') || '') + '').trim().toLowerCase();
        if (!t || t.length > 40) continue;
        if (words.some(w => t === w || t.indexOf(w) === 0)) {
            try {
                const r = n.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) { n.click(); clicked++; }
            } catch (e) {}
            if (clicked >= 2) break;
        }
    }
    return clicked;
}
"""

Минимальный «человеческий» набор prefs для Gecko
GECKO_PREFS = {
    "dom.webdriver.enabled": False,
    "general.useragent.override": "",
    "privacy.resistFingerprinting": False,
    "toolkit.telemetry.reportingpolicy.firstRun": False,
    "datareporting.policy.firstRunURL": "",
    "browser.startup.homepage_override.mstone": "ignore",
    "browser.shell.checkDefaultBrowser": False,
}

==============================================================================
МЕНЕДЖЕР ВНЕШНИХ БРАУЗЕРОВ
==============================================================================
class ExternalBrowserManager:
    """Обнаружение, запуск и подключение внешних портативных/системных браузеров.

    Возвращает ПЛАН запуска (dict), а не сам браузер: реальное открытие выполняет
    BrowserSession внутри sync_playwright-контекста воркера.
    """

    PORTABLE_PATTERNS = {
        "Chrome Portable": {
            "exe_names": ["GoogleChromePortable.exe", "chrome.exe"],
            "sub_paths": ["GoogleChromePortable/App/Chrome-bin", "GoogleChromePortable",
                          "ChromePortable/App/Chrome-bin", "ChromePortable"],
            "engine": "chromium",
            "profile_arg": "--user-data-dir",
            "default_profile": ["Data/profile", "App/Chrome-bin/Data/profile"],
        },
        "Chromium Portable": {
            "exe_names": ["chrome.exe", "chromium.exe"],
            "sub_paths": ["ChromiumPortable", "ChromiumPortable/App/Chromium-bin"],
            "engine": "chromium",
            "profile_arg": "--user-data-dir",
            "default_profile": ["Data/profile"],
        },
        "Firefox Portable": {
            "exe_names": ["FirefoxPortable.exe", "firefox.exe"],
            "sub_paths": ["FirefoxPortable/App/Firefox64", "FirefoxPortable/App/Firefox",
                          "FirefoxPortable"],
            "engine": "firefox",
            "profile_arg": "-profile",
            "default_profile": ["Data/profile"],
        },
        "LibreWolf Portable": {
            "exe_names": ["librewolf.exe", "LibreWolfPortable.exe"],
            "sub_paths": ["LibreWolfPortable", "LibreWolfPortable/App/LibreWolf", "LibreWolf"],
            "engine": "firefox",
            "profile_arg": "-profile",
            "default_profile": ["Data/profile"],
        },
        "Brave Portable": {
            "exe_names": ["brave.exe"],
            "sub_paths": ["BravePortable", "BravePortable/App/Brave-bin"],
            "engine": "chromium",
            "profile_arg": "--user-data-dir",
            "default_profile": ["Data/profile"],
        },
    }

    SYSTEM_CANDIDATES = [
        ("Google Chrome", "chromium", "chrome", [
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        ]),
        ("Microsoft Edge", "chromium", "msedge", [
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        ]),
        ("Brave (system)", "chromium", "brave", [
            r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
        ]),
        ("Mozilla Firefox", "firefox", None, [
            r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
            r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
            "/usr/bin/firefox",
            "/Applications/Firefox.app/Contents/MacOS/firefox",
        ]),
        ("LibreWolf (system)", "firefox", None, [
            r"%ProgramFiles%\LibreWolf\librewolf.exe",
            "/usr/bin/librewolf",
            "/Applications/LibreWolf.app/Contents/MacOS/librewolf",
        ]),
        ("Chromium (linux)", "chromium", None, [
            "/usr/bin/chromium", "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
        ]),
        ("Google Chrome (mac)", "chromium", "chrome", [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]),
        ("Microsoft Edge (mac)", "chromium", "msedge", [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]),
    ]

    def init(self, log_cb=None):
        self.logcb = logcb or (lambda m: None)
        self.discovered = []
        self._lock = threading.Lock()
        self.scan()

    # ------------------------------------------------------------------ scan
    def _expand(self, path):
        return os.path.expandvars(os.path.expanduser(path))

    def scanportable(self):
        """Рекурсивный поиск портативных сборок рядом со скриптом и в PortableApps."""
        found = {}
        searchdirs = [BASEDIR]
        parent = os.path.dirname(BASE_DIR)
        for cand in (os.path.join(parent, "PortableApps"), parent,
                     os.path.join(os.path.dirname(parent), "PortableApps")):
            if os.path.isdir(cand) and cand not in search_dirs:
                search_dirs.append(cand)

        for base in search_dirs:
            try:
                walker = os.walk(base)
            except Exception:
                continue
            for root, dirs, files in walker:
                try:
                    depth = root[len(base):].count(os.sep)
                except Exception:
                    depth = 99
                if depth > 3:
                    dirs[:] = []
                    continue
                dirs[:] = [d for d in dirs if d.lower() not in
                           ("node_modules", ".git", "pycache", "windows", "system32")]
                for name, cfg in self.PORTABLE_PATTERNS.items():
                    if name in found:
                        continue
                    exe = next((e for e in cfg["exe_names"] if e in files), None)
                    if not exe:
                        continue
                    exe_path = os.path.join(root, exe)
                    profile_dir = ""
                    for rel in cfg["default_profile"]:
                        cand = os.path.join(root, *rel.split("/"))
                        if os.path.isdir(cand):
                            profile_dir = cand
                            break
                    if not profile_dir:
                        for sub in cfg["sub_paths"]:
                            cand = os.path.join(root, *sub.split("/"), "Data", "profile")
                            if os.path.isdir(cand):
                                profile_dir = cand
                                break
                    found[name] = {
                        "name": name,
                        "exe": exe_path,
                        "engine": cfg["engine"],
                        "channel": None,
                        "profilearg": cfg["profilearg"],
                        "profiledir": profiledir,
                        "base_dir": root,
                        "kind": "portable",
                    }
        return list(found.values())

    def scansystem(self):
        out = []
        for name, engine, channel, paths in self.SYSTEM_CANDIDATES:
            for raw in paths:
                path = self._expand(raw)
                if path and os.path.isfile(path):
                    out.append({
                        "name": name, "exe": path, "engine": engine, "channel": channel,
                        "profile_arg": "--user-data-dir" if engine == "chromium" else "-profile",
                        "profiledir": "", "basedir": os.path.dirname(path),
                        "kind": "system",
                    })
                    break
        return out

    def scan(self):
        with self._lock:
            try:
                self.discovered = self.scanportable() + self.scansystem()
            except Exception as e:
                self.discovered = []
                self.log_cb(f"   ⚠️ сканирование браузеров не удалось: {e}")
            names = [b["name"] for b in self.discovered]
        self.log_cb(f"🔎 Найдено браузеров: {len(names)}"
                    + (f" → {', '.join(names)}" if names else ""))
        return names

    # ------------------------------------------------------------------ lists
    def getbrowserlist(self):
        with self._lock:
            names = [b["name"] for b in self.discovered]
        return [SYSTEM_BROWSER] + names

    def find(self, name):
        with self._lock:
            return next((b for b in self.discovered if b["name"] == name), None)

    # -------------------------------------------------------------------- cdp
    @staticmethod
    def probe_cdp(port, timeout=1.5):
        """Живой CDP-эндпоинт на 127.0.0.1:. Возвращает ws-URL или None."""
        try:
            import requests
            r = requests.get(f"http://127.0.0.1:{int(port)}/json/version", timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                ws = data.get("webSocketDebuggerUrl")
                if ws:
                    return ws, data.get("Browser", "?")
        except Exception:
            pass
        return None, None

    # ------------------------------------------------------------------ plan
    def buildplan(self, browsername, profilepath="", useprofile=False,
                   attachcdp=False, cdpport=9222, headless=True,
                   copyprofile=False, logcb=None):
        """Собирает план запуска. Ничего не запускает — только данные."""
        cb = logcb or self.logcb
        plan = {
            "mode": "bundled",          # bundled | persistent | cdp | executable
            "engine": "chromium",
            "channel": None,
            "executable_path": None,
            "args": [],
            "userdatadir": None,
            "cdp_url": None,
            "owns_browser": True,
            "owns_context": True,
            "label": SYSTEM_BROWSER,
            "profileiscopy": False,
            "serial": False,            # сериализовать доступ (профиль/CDP)
            "warnings": [],
        }

        # --- 1) CDP к живому браузеру ---
        if attach_cdp:
            ws, ver = self.probecdp(cdpport)
            if ws:
                plan.update(mode="cdp", engine="chromium", cdp_url=ws,
                            ownsbrowser=False, ownscontext=False, serial=True,
                            label=f"CDP 127.0.0.1:{cdp_port}")
                cb(f"🔌 Найден запущенный браузер: {ver} → подключаюсь через CDP "
                   f"(ws на 127.0.0.1:{cdp_port})")
                plan["warnings"].append("Браузер пользователя не закрывается скриптом")
                return plan
            cb(f"⚠️ На 127.0.0.1:{cdp_port} нет CDP. Chrome 136+ игнорирует "
               f"--remote-debugging-port для профиля ПО УМОЛЧАНИЮ: нужен отдельный "
               f"--user-data-dir. Запустите браузер так:\n"
               f'      chrome.exe --remote-debugging-port={cdp_port} '
               f'--remote-debugging-address=127.0.0.1 --user-data-dir=""')
            plan["warnings"].append(f"CDP на порту {cdp_port} не найден")

        # --- 2) bundled ---
        if not browsername or browsername == SYSTEM_BROWSER:
            plan["label"] = SYSTEM_BROWSER
            if profilepath and useprofile:
                eff, iscopy = self.prepareprofile(profilepath, copyprofile, cb)
                plan.update(mode="persistent", userdatadir=eff,
                            profileiscopy=is_copy, serial=True,
                            label=f"bundled + профиль {os.path.basename(eff)}")
            return plan

        # --- 3) внешний браузер ---
        cfg = self.find(browser_name)
        if not cfg:
            cb(f"⚠️ Браузер «{browser_name}» не найден — откат на bundled Chromium")
            plan["warnings"].append(f"{browser_name}: исполняемый файл не найден")
            return plan

        plan["engine"] = cfg["engine"]
        plan["channel"] = cfg.get("channel")
        plan["executable_path"] = cfg["exe"]
        plan["label"] = cfg["name"]

        if cfg["engine"] == "firefox":
            plan["warnings"].append(
                "Playwright управляет Firefox через Juggler и требует патченной сборки; "
                "внешний Firefox/LibreWolf обычно не запускается — будет фоллбэк")
            cb("ℹ️ Выбран Gecko-движок. Playwright работает только со своей сборкой "
               "Firefox: внешний Firefox/LibreWolf будет尝试 запущен, при отказе — "
               "автоматический фоллбэк на bundled Firefox/Chromium.")

        eff_profile = ""
        if profile_path:
            effprofile = profilepath
        elif cfg.get("profile_dir"):
            effprofile = cfg["profiledir"]

        if effprofile and useprofile:
            eff, iscopy = self.prepareprofile(effprofile, copyprofile, cb)
            plan["userdatadir"] = eff
            plan["mode"] = "persistent"
            plan["profileiscopy"] = is_copy
            plan["serial"] = True
            cb(f"👤 Профиль: {eff}" + ("  (изолированная копия)" if is_copy else ""))
        else:
            plan["mode"] = "executable"
            plan["serial"] = False

        if cfg["engine"] == "chromium":
            args = ["--no-first-run", "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled"]
            if not headless:
                args.append("--remote-debugging-address=127.0.0.1")
            plan["args"] = args
        else:
            plan["args"] = ["-no-remote"]     # обход single-instance lock Portable
        return plan

    # --------------------------------------------------------------- profile
    def prepareprofile(self, profilepath, copy_profile, cb):
        """Возвращает (effectivedir, iscopy). Создаёт каталог или его копию."""
        profilepath = os.path.abspath(os.path.expandvars(os.path.expanduser(profilepath or "")))
        if not profile_path:
            return "", False

        if not copy_profile:
            try:
                os.makedirs(profilepath, existok=True)
            except Exception as e:
                cb(f"⚠️ не удалось использовать профиль {profile_path}: {e}")
            return profile_path, False

        name = re.sub(r'[^\w\-.]', '', os.path.basename(profile_path.rstrip("\\/"))) or "profile"
        dest = os.path.join(PROFILE_ROOT, name)
        try:
            os.makedirs(dest, exist_ok=True)
            if os.path.isdir(profile_path):
                cb(f"📑 Копирую профиль {profile_path} → {dest} (кэш исключён)...")
                t0 = time.time()
                shutil.copytree(profilepath, dest, ignore=PROFILEIGNORE,
                                dirsexistok=True, symlinks=False)
                cb(f"   ✅ копия готова за {time.time() - t0:.1f} с — оригинал не трогается")
            return dest, True
        except Exception as e:
            cb(f"⚠️ копирование профиля не удалось ({str(e)[:120]}) — работаю с оригиналом")
            return profile_path, False

==============================================================================
BROWSER SESSION — единая обёртка над launch / persistent / connectovercdp
==============================================================================
class BrowserSession:
    """Владеет browser/context/page и знает, ЧТО именно разрешено закрывать.

    Ключевое правило Extended-сборки: подключённый браузер пользователя
    (CDP) и его контекст не закрываются никогда — только наша вкладка.
    """

    def init(self, browser=None, context=None, owns_browser=True,
                 owns_context=True, engine="chromium", label=""):
        self.browser = browser
        self.context = context
        self.ownsbrowser = ownsbrowser
        self.ownscontext = ownscontext
        self.engine = engine
        self.label = label
        self.page = None
        self._closed = False

    def new_page(self):
        self.page = self.context.new_page()
        return self.page

    def close(self):
        if self._closed:
            return
        self._closed = True
        for target, owner in ((self.page, True), (self.context, self.owns_context),
                              (self.browser, self.owns_browser)):
            if target is None or not owner:
                continue
            try:
                target.close()
            except Exception:
                pass

    def enter(self):
        return self

    def exit(self, exc_type, exc, tb):
        self.close()
        return False

def ctxoptions(ua, locale, tz, viewport, plan, keep_headers=True):
    """Опции контекста. В профильном режиме НЕ подменяем UA/заголовки:
    смысл использования реального профиля — его собственный «прогретый» отпечаток."""
    opts = {
        "viewport": viewport,
        "locale": locale,
        "timezone_id": tz,
        "devicescalefactor": 1,
    }
    spoof = plan["mode"] not in ("persistent", "cdp")
    if spoof:
        opts["user_agent"] = ua
        if keep_headers:
            opts["extrahttpheaders"] = build_headers(ua, locale)
        opts["permissions"] = ["notifications"]
    return opts

def opensession(p, plan, ua, locale, tz, viewport, stealthon, log_cb):
    """Реализует план запуска. Бросает исключение — вызывающий решает, что делать."""
    engine = plan.get("engine", "chromium")
    btype = p.chromium if engine == "chromium" else p.firefox
    opts = ctxoptions(ua, locale, tz, viewport, plan)
    headless = bool(plan.get("headless", True))

    # ---------- CDP: подключение к живой сессии ----------
    if plan["mode"] == "cdp":
        browser = p.chromium.connectovercdp(plan["cdp_url"], timeout=20000)
        if browser.contexts:
            context = browser.contexts[0]
            owns_context = False
            log_cb("   🔌 Использую существующий контекст пользователя (cookies/сессия живые)")
        else:
            context = browser.new_context(opts)
            owns_context = True
        return BrowserSession(browser, context, owns_browser=False,
                              ownscontext=ownscontext, engine="chromium",
                              label=plan["label"])

    # ---------- persistent context (профиль) ----------
    if plan["mode"] == "persistent" and plan.get("userdatadir"):
        kwargs = dict(opts)
        kwargs.pop("permissions", None)          # в Gecko набор прав отличается
        kwargs["headless"] = headless
        if engine == "chromium":
            if plan.get("executable_path"):
                kwargs["executablepath"] = plan["executablepath"]
            elif plan.get("channel"):
                kwargs["channel"] = plan["channel"]
            kwargs["args"] = list(plan.get("args", []))
        else:
            if plan.get("executable_path"):
                kwargs["executablepath"] = plan["executablepath"]
            kwargs["args"] = list(plan.get("args", []))
            kwargs["firefoxuserprefs"] = dict(GECKO_PREFS)
        context = btype.launchpersistentcontext(plan["userdatadir"], kwargs)
        session = BrowserSession(None, context, ownsbrowser=False, ownscontext=True,
                                 engine=engine, label=plan["label"])
        session.browser = getattr(context, "browser", None)
        if stealth_on and engine == "chromium":
            try:
                context.addinitscript(buildstealthscript(ua, locale))
            except Exception:
                pass
        return session

    # ---------- обычный запуск (bundled / внешний exe) ----------
    launch_kwargs = {"headless": headless}
    if plan.get("executable_path"):
        launchkwargs["executablepath"] = plan["executable_path"]
    elif plan.get("channel"):
        launch_kwargs["channel"] = plan["channel"]
    if engine == "chromium":
        launchkwargs["args"] = list(plan.get("args", [])) or buildlaunch_args(locale)
    else:
        launch_kwargs["args"] = list(plan.get("args", []))
        launchkwargs["firefoxuserprefs"] = dict(GECKOPREFS)

    browser = btype.launch(launch_kwargs)
    context = safenewcontext(browser, opts, log_cb)
    if stealth_on and engine == "chromium":
        try:
            context.addinitscript(buildstealthscript(ua, locale))
        except Exception:
            pass
    return BrowserSession(browser, context, ownsbrowser=True, ownscontext=True,
                          engine=engine, label=plan["label"])

def safenewcontext(browser, opts, log_cb):
    """Часть опций контекста может не поддерживаться конкретным движком/сборкой —
    деградируем пошагово, а не роняем весь URL."""
    keysorder = ["permissions", "devicescalefactor", "extrahttp_headers"]
    attempt = dict(opts)
    last = None
    for  in range(len(keysorder) + 1):
        try:
            return browser.new_context(attempt)
        except Exception as e:
            last = e
            drop = next((k for k in keys_order if k in attempt), None)
            if not drop:
                break
            attempt.pop(drop, None)
            log_cb(f"   ℹ️ контекст без «{drop}»: {str(e)[:90]}")
    raise last or RuntimeError("не удалось создать контекст")

==============================================================================
АВТОУСТАНОВКА ЗАВИСИМОСТЕЙ
==============================================================================
class AutoInstaller:
    def init(self):
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

    def _pip(self, args, quiet=True):
        cmd = [sys.executable, "-m", "pip"] + args
        if quiet:
            return subprocess.check_call(cmd, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL,
                                         creationflags=CREATENOWINDOW)
        return subprocess.checkcall(cmd, creationflags=CREATENO_WINDOW)

    def install(self, pkg):
        print(f"📦 Установка {pkg}...")
        base = ["install", pkg, "--upgrade", "--disable-pip-version-check", "--quiet"]
        for attempt in (base, base + ["--user"]):
            try:
                self._pip(attempt)
                print(f"   ✅ {pkg}")
                return True
            except Exception:
                continue
        try:
            self._pip(["install", pkg, "--upgrade"], quiet=False)
            print(f"   ✅ {pkg}")
            return True
        except Exception as e:
            print(f"   ❌ {pkg}: {e}")
            return False

    def chromium_ready(self):
        try:
            from playwright.syncapi import syncplaywright
            with sync_playwright() as p:
                b = launchchromiumfallback(p, buildlaunchargs("en-US"))
                b.close()
            return True
        except Exception:
            return False

    def install_browsers(self, what="chromium"):
        print(f"🌐 Установка браузера {what} для Playwright...")
        for extra in ([], ["--with-deps"]):
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "playwright", "install", what] + extra,
                    creationflags=CREATENOWINDOW)
                print(f"   ✅ {what} установлен")
                return True
            except Exception as e:
                print(f"   ⚠️ playwright install {what} {' '.join(extra) or '(basic)'}: {e}")
        return False

    def run(self):
        print("=" * 70)
        print(f"🔍 {APPNAME} v{APPVERSION} — ПРОВЕРКА ЗАВИСИМОСТЕЙ")
        print("=" * 70)
        for pkg, imp in REQUIRED_PACKAGES:
            ok = self.check(pkg, imp)
            print(f"{'✅' if ok else '❌'} {pkg}")

        if self.missing:
            print("\n" + "=" * 70)
            print(f"🚀 УСТАНАВЛИВАЮ {len(self.missing)} ПАКЕТ(ОВ)...")
            print("=" * 70)
            for p in list(self.missing):
                if self.install(p):
                    self.missing.remove(p)

        if not self.chromium_ready():
            print("\n" + "=" * 70)
            print("🌐 БРАУЗЕР НЕ ГОТОВ — УСТАНАВЛИВАЮ CHROMIUM...")
            print("=" * 70)
            self.install_browsers("chromium")
            if not self.chromium_ready():
                print("   ℹ️ bundled Chromium недоступен → будут использованы "
                      "системный Chrome/Edge (channel=...) или внешние браузеры.")
                self.missing.append("chromium-browser")

        print("\n" + "=" * 70)
        if not self.missing:
            print("✅ ВСЁ ГОТОВО! Запускаю интерфейс...")
        else:
            print(f"⚠️ Не установлено: {', '.join(self.missing)}")
            print("   Повтори запуск или установи вручную:")
            print(f"   {sys.executable} -m pip install " + " ".join(self.missing))
        print("=" * 70)
        return len(self.missing) == 0

def installplaywrightbrowser(what, log_cb):
    """Установка браузера Playwright из GUI (в отдельном потоке)."""
    log_cb(f"🌐 playwright install {what} ...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", what],
                              creationflags=CREATENOWINDOW)
        log_cb(f"   ✅ {what} установлен")
        return True
    except Exception as e:
        log_cb(f"   ❌ не удалось установить {what}: {e}")
        return False

==============================================================================
ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
==============================================================================
def sanitize(name):
    name = re.sub(r'^https?://', '', name)
    name = re.sub(r'[^\w\-.]', '', name)
    name = name.strip('_')
    while "" in name:
        name = name.replace("", "_")
    return (name or "page")[:80]

def slugify(text):
    text = re.sub(r'[^\w\-]+', '-', str(text).strip().lower())
    return re.sub(r'-+', '-', text).strip('-')[:60] or "source"

def humansize(numbytes):
    numbytes = float(numbytes or 0)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num_bytes  {
  const root = document.querySelector(SEL) || document.body || document.documentElement;
  root.querySelectorAll(JUNK).forEach((n) => n.remove());
  return root.innerText || '';
}
"""

JSEXTRACTHTML = """
() => {
  const root = document.querySelector(SEL) || document.body || document.documentElement;
  const copy = root.cloneNode(true);
  copy.querySelectorAll(JUNK).forEach((n) => n.remove());
  return copy.outerHTML;
}
"""

def extractpagetext(page):
    try:
        textcontent = page.evaluate(js(JSEXTRACTTEXT))
    except Exception:
        try:
            textcontent = page.locator('body').innertext(timeout=20000)
        except Exception:
            try:
                text_content = page.evaluate("() => document.documentElement.innerText")
            except Exception:
                text_content = ""

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in (text_content or "").splitlines()]
    text_content = re.sub(r"\n{3,}", "\n\n", "\n".join(l for l in lines if l))

    try:
        frames = page.frames
    except Exception:
        frames = []
    if len(frames) > 1:
        extra = []
        for frame in frames[1:]:
            try:
                ft = frame.inner_text(timeout=8000)
                if ft.strip():
                    extra.append(f"\n[FRAME: {frame.url}]\n{ft}\n")
            except Exception:
                continue
        if extra:
            text_content += "\n--- СОДЕРЖИМОЕ ФРЕЙМОВ ---\n" + "\n".join(extra)
    return text_content

def extractpagehtml(page):
    try:
        return page.evaluate(js(JSEXTRACT_HTML))
    except Exception:
        return page.content()

def htmltomarkdown(htmlcontent, pageurl=""):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg", "iframe",
                     "nav", "header", "footer", "aside"]):
        tag.decompose()
    absolutize(soup, page_url)

    try:
        from markdownify import markdownify as md_convert
        body = soup.body or soup
        md = mdconvert(str(body), headingstyle="ATX", bullets="-")
        md = re.sub(r'\n{3,}', '\n\n', md).strip()
        if md:
            return md
    except Exception:
        pass

    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        if el.name and re.match(r'h[1-6]', el.name):
            txt = el.get_text(strip=True)
            if txt:
                lines.append(f"{'#' * int(el.name[1])} {txt}")
        elif el.name == "li":
            txt = el.get_text(strip=True)
            if txt:
                lines.append(f"- {txt}")
        elif el.name == "p":
            txt = el.get_text(strip=True)
            if txt:
                lines.append(txt)
    return "\n\n".join(lines) if lines else soup.get_text("\n", strip=True)

def fetch_html(url, headers):
    """charset из Content-Type, иначе apparent_encoding: без этого кириллица
    приходит как ISO-8859-1 и превращается в можибаку."""
    import requests
    resp = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
    ctype = resp.headers.get("content-type", "") or ""
    m = re.search(r'charset=([\w\-]+)', ctype, re.I)
    if m:
        try:
            resp.encoding = m.group(1)
        except Exception:
            resp.encoding = "utf-8"
    else:
        resp.encoding = resp.apparent_encoding or "utf-8"
    resp.raiseforstatus()
    return resp.text, resp.status_code

def fetch_bytes(url, headers):
    import requests
    resp = requests.get(url, headers=headers, timeout=40, allow_redirects=True)
    resp.raiseforstatus()
    return resp.content

def pdffromhtml(htmlbody, title, url, outpath, log_cb):
    """PDF для Gecko: page.pdf() есть только в Chromium, поэтому рендерим
    сохранённый HTML отдельным headless-Chromium."""
    from playwright.syncapi import syncplaywright
    doc = f"""
{title or url}
body{{font-family:'Segoe UI',Arial,sans-serif;font-size:12pt;line-height:1.55;color:#111;margin:0}}
h1{{font-size:19pt;color:#0b6b3a;margin:0 0 4px}} .meta{{color:#666;font-size:9pt;border-bottom:1px solid #ddd;
padding-bottom:6px;margin-bottom:14px;word-break:break-all}} img{{max-width:100%}}
pre{{background:#f5f5f5;border:1px solid #ddd;padding:8px;font-size:9pt;white-space:pre-wrap}}
table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:4px;font-size:10pt}}
a{{color:#0a6b3d;text-decoration:none}}
{title or url}
Источник: {url}Сохранено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · {APPNAME} v{APPVERSION}
{html_body}"""
    with sync_playwright() as p:
        browser = launchchromiumfallback(p, buildlaunchargs("en-US"))
        try:
            page = browser.new_page()
            page.setcontent(doc, waituntil="domcontentloaded")
            page.waitfortimeout(400)
            page.emulate_media(media="screen")
            page.pdf(path=outpath, format='A4', printbackground=True, timeout=60000,
                     margin={'top': '0.5in', 'bottom': '0.5in',
                             'left': '0.5in', 'right': '0.5in'})
        finally:
            try:
                browser.close()
            except Exception:
                pass
    log_cb("   🧾 PDF собран через headless-Chromium (Gecko не умеет page.pdf)")

==============================================================================
ОСНОВНАЯ ЛОГИКА СКРАПИНГА
==============================================================================
def scrapeone(url, fmt, outdir, settings, logcb, shouldstop=None, browser_manager=None):
    stop = should_stop or (lambda: False)
    result = {
        "url": url, "title": "", "status": "failed", "format": fmt,
        "file": None, "sizebytes": 0, "wordcount": None,
        "blocked_suspected": False, "method": "playwright",
        "attempts": 0, "error": None, "elapsed_sec": 0.0,
        "browser": settings.get("externalbrowser", SYSTEMBROWSER),
        "engine": "chromium", "session_mode": "bundled",
    }
    t0 = time.time()

    okdns, dnserr = quickdnscheck(url)
    if not ok_dns:
        result["error"] = dns_err
        result["elapsed_sec"] = round(time.time() - t0, 2)
        logcb(f"   ❌ {dnserr}")
        return result

    filepath = reservepath(out_dir, sanitize(url), fmt)

    aggressive = bool(settings.get("aggressive"))
    max_attempts = max(1, settings["retries"] + 1)
    goto_timeout = 30000 if aggressive else 45000
    net_timeout = 6000 if aggressive else 12000
    last_error = None

    # ---- план запуска браузера (один на все попытки, но пересобирается при отказе)
    plan = None
    if browser_manager is not None:
        plan = browsermanager.buildplan(
            settings.get("externalbrowser", SYSTEMBROWSER),
            profilepath=settings.get("customprofile_path") or "",
            useprofile=bool(settings.get("useprofile")),
            attachcdp=bool(settings.get("attachcdp")),
            cdpport=int(settings.get("cdpport", 9222)),
            headless=bool(settings.get("headless", True)),
            copyprofile=bool(settings.get("copyprofile")),
            logcb=logcb,
        )
        plan["headless"] = bool(settings.get("headless", True))
    if plan is None:
        plan = {"mode": "bundled", "engine": "chromium", "channel": None,
                "executablepath": None, "args": buildlaunch_args("en-US"),
                "userdatadir": None, "cdpurl": None, "ownsbrowser": True,
                "ownscontext": True, "label": SYSTEMBROWSER, "headless": True,
                "serial": False, "warnings": [], "profileiscopy": False}

    result["session_mode"] = plan["mode"]
    result["engine"] = plan["engine"]
    result["browser"] = plan["label"]
    for w in plan.get("warnings", []):
        log_cb(f"   ℹ️ {w}")

    serial = bool(plan.get("serial"))
    stealth_on = bool(settings.get("stealth", True)) and plan["mode"] not in ("persistent", "cdp")

    for attempt in range(1, max_attempts + 1):
        if stop():
            lasterror = lasterror or "остановлено пользователем"
            break
        result["attempts"] = attempt
        ua = random_ua()
        locale, tz = randomlocaletz()
        viewport = random.choice(VIEWPORTS)
        saved = False
        session = None

        try:
            from playwright.syncapi import syncplaywright
            with sync_playwright() as p:
                if serial:
                    PROFILE_LOCK.acquire()
                try:
                    session = openwith_fallback(p, plan, ua, locale, tz, viewport,
                                                  stealthon, logcb)
                finally:
                    if serial:
                        PROFILE_LOCK.release()

                if serial:
                    PROFILE_LOCK.acquire()
                try:
                    page = session.new_page()
                    result["engine"] = session.engine

                    response = page.goto(url, wait_until="domcontentloaded",
                                         timeout=goto_timeout)
                    try:
                        page.waitforloadstate("networkidle", timeout=nettimeout)
                    except Exception:
                        pass
                    try:
                        page.waitforload_state("load", timeout=4000)
                    except Exception:
                        pass

                    page.waitfortimeout(random.randint(150, 350) if aggressive
                                          else random.randint(400, 900))
                    dismiss_overlays(page)
                    autoscroll(page, steps=4 if aggressive else 6,
                               pause_ms=200 if aggressive else 350)

                    try:
                        title = page.title()
                    except Exception:
                        title = ""
                    result["title"] = title

                    status_code = response.status if response else None
                    body_sample = ""
                    try:
                        bodysample = page.locator('body').innertext(timeout=5000)[:2000]
                    except Exception:
                        pass

                    blocked = (statuscode in (403, 429, 503)) or looksblocked(title, body_sample)
                    result["blocked_suspected"] = blocked
                    if blocked:
                        logcb(f"   ⚠️ Похоже на блокировку (код {statuscode}), "
                               f"попытка {attempt}/{max_attempts}")
                    if plan["mode"] == "cdp" and not blocked:
                        log_cb("   🍪 Сессия пользователя использована (cookies/live-профиль)")

                    # ---------- сохранение по формату ----------
                    if fmt == "pdf":
                        try:
                            probe = page.evaluate(
                                "() => (document.querySelector(%s) || document.body || {}).innerText || ''"
                                % json.dumps(CONTENT_SELECTOR))
                            result["word_count"] = len(str(probe).split()) or None
                        except Exception:
                            result["word_count"] = None

                        pdf_ok = False
                        if session.engine == "chromium":
                            try:
                                try:
                                    page.emulate_media(media="screen")
                                except Exception:
                                    pass
                                page.pdf(path=filepath, format='A4', printbackground=True,
                                         scale=1.0, timeout=60000,
                                         margin={'top': '0.5in', 'bottom': '0.5in',
                                                 'left': '0.5in', 'right': '0.5in'})
                                pdf_ok = True
                            except Exception as ep:
                                log_cb(f"   ⚠️ page.pdf не удался: {str(ep)[:110]}")

                        if not pdf_ok:
                            ct = ""
                            try:
                                ct = (response.headers.get("content-type") or "") if response else ""
                            except Exception:
                                pass
                            if "pdf" in ct.lower():
                                with open(file_path, "wb") as f:
                                    f.write(fetchbytes(url, buildheaders(ua, locale)))
                                result["method"] = "binary-download"
                                pdf_ok = True

                        if not pdf_ok and session.engine != "chromium":
                            body = cleanforprint(extractpagehtml(page), url)
                            pdffromhtml(body, title, url, filepath, logcb)
                            pdf_ok = True
                            result["method"] = "gecko->chromium-print"

                        if not pdf_ok:
                            raise RuntimeError("не удалось отрендерить PDF этой страницы")

                    elif fmt == "html":
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(page.content())

                    elif fmt == "txt":
                        textcontent = extractpage_text(page)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(text_content)
                        result["wordcount"] = len(textcontent.split())
                        result["text"] = textcontent

                    elif fmt == "md":
                        mdtext = htmltomarkdown(extractpage_html(page), url)
                        fullmd = f"# {title or url}\n\nИсточник: {url}\n\n---\n\n" + mdtext
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(full_md)
                        result["wordcount"] = len(fullmd.split())
                        result["text"] = fullmd

                    elif fmt == "docx":
                        from docx import Document
                        textcontent = extractpage_text(page)
                        doc = Document()
                        doc.addheading(safexml_text(title or url), 0)
                        doc.addparagraph(safexml_text(f"Источник: {url}"))
                        doc.addparagraph(safexml_text(
                            f"Сохранено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
                        doc.addparagraph(safexml_text(
                            f"Браузер: {plan['label']} · режим: {plan['mode']}"))
                        doc.add_heading('Содержимое:', level=1)
                        for para in text_content.split('\n'):
                            para = safexmltext(para).strip()
                            if para:
                                doc.add_paragraph(para)
                        doc.save(file_path)
                        result["wordcount"] = len(textcontent.split())
                        result["text"] = textcontent

                    # ---------- экспорт сессии (cookies) ----------
                    if settings.get("exportstorage") and session.ownscontext is False:
                        pass      # чужой контекст не дампим — это данные пользователя
                    saved = True

                finally:
                    if session is not None:
                        if serial:
                            PROFILE_LOCK.acquire()
                        try:
                            session.close()
                        finally:
                            if serial:
                                PROFILE_LOCK.release()

            if saved:
                size = os.path.getsize(file_path)
                result["status"] = "ok"
                result["file"] = os.path.basename(file_path)
                result["size_bytes"] = size
                if result["method"] == "playwright":
                    result["method"] = f"{plan['mode']}:{session.engine if session else 'chromium'}"
                logcb(f"   ✅ {fmt.upper()}: {humansize(size)} -> {os.path.basename(file_path)}"
                       + (" [блокировка?]" if result["blocked_suspected"] else ""))
                last_error = None
                break

        except Exception as e:
            last_error = str(e)
            logcb(f"   ⚠️ Попытка {attempt}/{maxattempts} не удалась: {last_error[:140]}")
            low = last_error.lower()
            if "singleton" in low or "process already running" in low or "in use" in low:
                log_cb("   💡 Профиль уже открыт в браузере. Закройте его, "
                       "включите «Копия профиля» или перейдите на CDP-подключение.")
                plan = dict(plan, mode="executable", userdatadir=None, serial=False)
                log_cb("   🔁 Переключаюсь на запуск без профиля (изолированный контекст)")
            if attempt  0:
                log_cb(f"   🔁 фоллбэк браузера: {variant['label']}")
            return session
        except Exception as e:
            last = e
            msg = str(e)
            log_cb(f"   ⚠️ {variant['label']}: {msg[:130]}")
            low = msg.lower()
            if "executable doesn't exist" in low or "install" in low:
                log_cb("   💡 выполни: python -m playwright install "
                       f"{variant.get('engine', 'chromium')}")
    raise last or RuntimeError("ни один браузер не запустился")

def cleanforprint(htmlfragment, baseurl):
    """Лёгкая чистка HTML перед печатью в PDF (убираем скрипты и мусор)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_fragment, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "iframe", "object", "embed"]):
        tag.decompose()
    absolutize(soup, base_url)
    return str(soup)

def dumpstoragestate(sessionorcontext, outdir, logcb):
    """Сохраняет cookies/localStorage нашего контекста в storage_state.json.
    Работает только если контекст создан нами (чужой не дампим)."""
    try:
        ctx = getattr(sessionorcontext, "context", sessionorcontext)
        path = os.path.join(outdir, "storagestate.json")
        ctx.storage_state(path=path)
        logcb(f"🍪 storagestate.json сохранён ({human_size(os.path.getsize(path))})")
        return path
    except Exception as e:
        log_cb(f"⚠️ не удалось экспортировать сессию: {str(e)[:120]}")
        return None

==============================================================================
ОБЪЕДИНЕНИЕ ФАЙЛОВ
==============================================================================
def mergepdf(okresults, outdir, outpath, log_cb):
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    skipped = 0
    for r in ok_results:
        fp = os.path.join(out_dir, r["file"])
        if not os.path.exists(fp):
            skipped += 1
            continue
        try:
            reader = PdfReader(fp)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    raise RuntimeError("зашифрован")
            for page in reader.pages:
                writer.add_page(page)
        except Exception as e:
            skipped += 1
            log_cb(f"   ⚠️ пропущен повреждённый PDF: {r['file']} — {str(e)[:80]}")
    if len(writer.pages) == 0:
        raise RuntimeError("ни одного читаемого PDF для объединения")
    writer.addmetadata({"/Title": f"{APPNAME} Merged Export",
                         "/Producer": f"{APPNAME} v{APPVERSION}"})
    with open(out_path, "wb") as f:
        writer.write(f)
    writer.close()
    if skipped:
        log_cb(f"   ℹ️ в сводку не попали {skipped} файл(ов)")

def mergetextlike(okresults, outpath, fmt):
    sep = "\n\n" + ("=" * 70) + "\n\n"
    chunks = []
    for r in ok_results:
        header = f"ИСТОЧНИК: {r['url']}\nЗАГОЛОВОК: {r['title']}\n"
        chunks.append(header + "\n" + r.get("_text", ""))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(sep.join(chunks))

def mergemarkdown(okresults, out_path):
    toc = ["# Сводный документ\n", f"Сгенерировано {APPNAME} v{APPVERSION}\n",
           "\n## Содержание\n"]
    body_parts = []
    for r in ok_results:
        anchor = slugify(r["title"] or r["url"])
        toc.append(f"- [{r['title'] or r['url']}](#{anchor})")
        text = re.sub(r'^#\s.*\n+', '', r.get("_text", ""), count=1)
        body_parts.append(
            f"\n\n\n\n## {r['title'] or r['url']}\n\n"
            f"Источник: {r['url']}\n\n---\n\n{text}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(toc) + "\n" + "".join(body_parts))

def mergehtml(okresults, outdir, outpath):
    from bs4 import BeautifulSoup
    nav_items, sections = [], []
    for r in ok_results:
        anchor = slugify(r["title"] or r["url"])
        nav_items.append(f'{r["title"] or r["url"]}')
        fp = os.path.join(out_dir, r["file"])
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "iframe", "object", "embed", "base", "form"]):
                tag.decompose()
            absolutize(soup, r["url"])
            inner = str(soup.body) if soup.body else str(soup)
        except Exception:
            inner = "(не удалось прочитать)"
        sections.append(
            f'{r["title"] or r["url"]}'
            f'Источник: {r["url"]}{inner}'
        )
    html_doc = f"""

{APP_NAME} — Сводный экспорт

body{{font-family:Segoe UI,Arial,sans-serif;background:#0d0d12;color:#e4e4e4;max-width:980px;margin:0 auto;padding:30px;line-height:1.6;}}
nav{{background:#1a1a2e;padding:15px 20px;border-radius:8px;margin-bottom:30px;}}
nav a{{color:#00ff88;text-decoration:none;}}
nav a:hover{{text-decoration:underline;}}
section{{margin-bottom:40px;}}
.src{{color:#888;font-size:0.9em;word-break:break-all;}}
hr{{border-color:#333;}}
h1{{color:#00ff88;}}
a{{color:#5aa9ff;}}
img{{max-width:100%;height:auto;}}
pre{{background:#111;padding:12px;border-radius:8px;overflow:auto;}}
table{{border-collapse:collapse;}} td,th{{border:1px solid #333;padding:6px;}}

📚 {APPNAME} — Сводный экспорт ({len(okresults)} источников)
{''.join(nav_items)}
{''.join(sections)}
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

def mergedocx(okresults, out_path):
    from docx import Document
    doc = Document()
    doc.addheading(safexmltext(f'{APPNAME} — Сводный экспорт'), 0)
    doc.addparagraph(safexml_text(
        f"Источников: {len(ok_results)} | Сгенерировано: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    for i, r in enumerate(ok_results):
        if i > 0:
            doc.addpagebreak()
        doc.addheading(safexml_text(r["title"] or r["url"]), level=1)
        doc.addparagraph(safexml_text(f"Источник: {r['url']}"))
        for para in r.get("_text", "").split('\n'):
            para = safexmltext(para).strip()
            if para:
                doc.add_paragraph(para)
    doc.save(out_path)

def writemanifestandindex(manifest, outdir, mergedfilename=None, browserinfo=None):
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in manifest]
    ok_n = sum(1 for r in clean if r["status"] == "ok")
    totals = {
        "sources": len(clean),
        "ok": ok_n,
        "failed": len(clean) - ok_n,
        "blockedsuspected": sum(1 for r in clean if r.get("blockedsuspected")),
        "bytes": sum(int(r.get("size_bytes") or 0) for r in clean),
        "words": sum(int(r.get("word_count") or 0) for r in clean),
    }

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({
            "app": APPNAME, "version": APPVERSION, "build": BUILD_DATE,
            "generated": datetime.now().isoformat(timespec="seconds"),
            "mergedfile": mergedfilename,
            "browser": browser_info or {},
            "totals": totals,
            "sources": clean,
        }, f, ensure_ascii=False, indent=2)

    lines = [
        f"# {APPNAME} v{APPVERSION} — отчёт о сборе\n",
        f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"Всего источников: {len(clean)} · успешно: {ok_n} · "
        f"объём: {human_size(totals['bytes'])} · слов: {totals['words']}\n",
    ]
    if browser_info:
        lines.append(f"Браузер: {browser_info.get('label', '—')} · "
                     f"движок: {browser_info.get('engine', '—')} · "
                     f"режим: {browser_info.get('mode', '—')}\n")
    if merged_filename:
        lines.append(f"Объединённый файл: {merged_filename}\n")
    lines.append("| # | Заголовок | URL | Статус | Файл | Размер | Слов | Метод |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(clean, 1):
        status_icon = "✅" if r["status"] == "ok" else "❌"
        blocked = " ⚠️блок" if r.get("blocked_suspected") else ""
        title = (r["title"] or "—").replace("|", "/")[:60]
        file_link = f"[{r['file']}](./{r['file']})" if r["file"] else "—"
        size = humansize(r["sizebytes"]) if r["size_bytes"] else "—"
        words = r["wordcount"] if r["wordcount"] else "—"
        lines.append(f"| {i} | {title} | {r['url']} | {statusicon}{blocked} | {filelink} "
                     f"| {size} | {words} | {r['method']} |")
        if r["status"] != "ok" and r.get("error"):
            lines.append(f"|   | ошибка: {str(r['error'])[:150]} | | | | | |")
    lines.append("")
    lines.append("Полный журнал прогона: RUN.log")

    with open(os.path.join(out_dir, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return totals

==============================================================================
GUI
==============================================================================
class App:
    def init(self, root):
        self.root = root
        self.ui_q = queue.Queue()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.is_running = False
        self.lastoutputdir = None
        self.log_buffer = []
        self.browsermanager = ExternalBrowserManager(logcb=self.log)

        root.title(f"🚀 {APPNAME} v{APPVERSION}")
        root.configure(bg="#12121f")
        root.geometry("880x1000")
        root.minsize(820, 760)
        root.resizable(True, True)
        root.protocol("WMDELETEWINDOW", self.on_close)

        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TProgressbar", troughcolor="#1e1e1e", background="#00aa44", thickness=14)
        style.configure("TCombobox", fieldbackground="#1e1e1e", background="#1e1e1e",
                        foreground="#ffffff", arrowcolor="#00ff88")
        style.map("TCombobox", fieldbackground=[("readonly", "#1e1e1e")],
                  foreground=[("readonly", "#ffffff")])

        # --- Заголовок ---
        header = tk.Frame(root, bg="#1a1a2e")
        header.pack(fill="x")
        tk.Label(header, text=f"🚀 {APPNAME} v{APPVERSION}", font=("Segoe UI", 16, "bold"),
                 bg="#1a1a2e", fg="#00ff88", pady=8).pack()
        tk.Label(header, text="Внешние браузеры • Профили и cookies • CDP • "
                              "Любой формат • Параллельно",
                 font=("Segoe UI", 10), bg="#1a1a2e", fg="#888888").pack(pady=(0, 8))

        # --- URL ---
        tk.Label(root, text="📋 URL (по одному в строке):", font=("Segoe UI", 10, "bold"),
                 anchor="w", bg="#12121f", fg="white").pack(fill="x", padx=20, pady=(12, 4))
        self.urls = tk.Text(root, height=6, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff88",
                            insertbackground="#00ff88", wrap="none")
        self.urls.pack(fill="both", expand=False, padx=20, pady=2)

        # --- Настройки сбора ---
        frame = tk.LabelFrame(root, text="⚙️ Настройки сбора", font=("Segoe UI", 10, "bold"),
                              padx=10, pady=8, bg="#2d2d44", fg="white")
        frame.pack(fill="x", padx=20, pady=(10, 6))

        tk.Label(frame, text="Формат:", bg="#2d2d44", fg="white").grid(
            row=0, column=0, sticky="w", padx=5, pady=3)
        self.fmt_label = tk.StringVar(value="Markdown")
        ttk.Combobox(frame, textvariable=self.fmtlabel, values=list(FORMATMAP.keys()),
                     state="readonly", width=12).grid(row=0, column=1, sticky="w", padx=5, pady=3)

        self.merge = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="Объединить в один файл", variable=self.merge,
                       bg="#2d2d44", fg="white", selectcolor="#2d2d44").grid(
            row=0, column=2, columnspan=2, padx=10, pady=3, sticky="w")

        self.aggr = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="🔥 Агрессивный режим (КОРОЧЕ паузы и ожидания)",
                       variable=self.aggr, bg="#2d2d44", fg="#00ff88",
                       selectcolor="#2d2d44", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, columnspan=4, pady=(6, 3), sticky="w")

        self.stealth = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="🥷 Stealth-скрипт (webdriver/plugins/WebGL) — "
                                   "не применяется к реальному профилю",
                       variable=self.stealth, bg="#2d2d44", fg="#cccccc",
                       selectcolor="#2d2d44").grid(row=2, column=0, columnspan=4, sticky="w")

        tk.Label(frame, text="Потоков:", bg="#2d2d44", fg="white").grid(
            row=3, column=0, sticky="w", padx=5, pady=3)
        self.concurrency = tk.IntVar(value=1)
        tk.Spinbox(frame, from_=1, to=5, textvariable=self.concurrency, width=5,
                   bg="#1e1e1e", fg="#00ff88", insertbackground="#00ff88",
                   buttonbackground="#1e1e1e", relief="flat").grid(
            row=3, column=1, sticky="w", padx=5, pady=3)

        tk.Label(frame, text="Повторов:", bg="#2d2d44", fg="white").grid(
            row=3, column=2, sticky="w", padx=5, pady=3)
        self.retries = tk.IntVar(value=1)
        tk.Spinbox(frame, from_=0, to=3, textvariable=self.retries, width=5,
                   bg="#1e1e1e", fg="#00ff88", insertbackground="#00ff88",
                   buttonbackground="#1e1e1e", relief="flat").grid(
            row=3, column=3, sticky="w", padx=5, pady=3)

        # --- Браузер и профиль ---
        bframe = tk.LabelFrame(root, text="🌐 Браузер, профиль и сессия",
                               font=("Segoe UI", 10, "bold"), padx=10, pady=8,
                               bg="#252540", fg="white")
        bframe.pack(fill="x", padx=20, pady=6)

        tk.Label(bframe, text="Браузер:", bg="#252540", fg="white").grid(
            row=0, column=0, sticky="w", padx=5, pady=4)
        browserlist = self.browsermanager.getbrowserlist()
        self.selectedbrowser = tk.StringVar(value=browserlist[0])
        self.browsercombo = ttk.Combobox(bframe, textvariable=self.selectedbrowser,
                                          values=browser_list, state="readonly", width=34)
        self.browser_combo.grid(row=0, column=1, columnspan=2, sticky="w", padx=5, pady=4)
        self.browsercombo.bind(">", self.onbrowserpick)

        tk.Button(bframe, text="🔄 Обновить список", command=self.refreshbrowserlist,
                  bg="#1e1e1e", fg="#00ff88", relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").grid(row=0, column=3, sticky="w", padx=5, pady=4)

        tk.Label(bframe, text="Профиль (user-data-dir):", bg="#252540", fg="white").grid(
            row=1, column=0, sticky="w", padx=5, pady=4)
        self.profilepathvar = tk.StringVar()
        tk.Entry(bframe, textvariable=self.profilepathvar, bg="#1e1e1e", fg="#00ff88",
                 insertbackground="#00ff88", relief="flat",
                 font=("Consolas", 9)).grid(row=1, column=1, columnspan=2,
                                            sticky="we", padx=5, pady=4)
        tk.Button(bframe, text="...", command=self.browse_profile, bg="#1e1e1e",
                  fg="#00ff88", relief="flat", width=3, cursor="hand2").grid(
            row=1, column=3, sticky="w", padx=5, pady=4)
        bframe.columnconfigure(2, weight=1)

        self.use_profile = tk.BooleanVar(value=False)
        tk.Checkbutton(bframe, text="👤 Использовать профиль (cookies / local storage / "
                                    "история = живая сессия)",
                       variable=self.use_profile, bg="#252540", fg="#00ff88",
                       selectcolor="#252540", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, columnspan=4, sticky="w", padx=5, pady=(4, 2))

        self.copy_profile = tk.BooleanVar(value=True)
        tk.Checkbutton(bframe, text="📑 Работать с КОПИЕЙ профиля (безопасно: оригинал "
                                    "не блокируется и не меняется)",
                       variable=self.copy_profile, bg="#252540", fg="#cccccc",
                       selectcolor="#252540").grid(row=3, column=0, columnspan=4,
                                                   sticky="w", padx=5, pady=2)

        self.attach_cdp = tk.BooleanVar(value=False)
        tk.Checkbutton(bframe, text="🔌 Подключаться к УЖЕ ЗАПУЩЕННОМУ браузеру (CDP)",
                       variable=self.attach_cdp, bg="#252540", fg="#5aa9ff",
                       selectcolor="#252540", font=("Segoe UI", 9, "bold"),
                       command=self.oncdp_toggle).grid(row=4, column=0, columnspan=3,
                                                         sticky="w", padx=5, pady=2)

        tk.Label(bframe, text="CDP-порт:", bg="#252540", fg="white").grid(
            row=4, column=3, sticky="e", padx=(5, 0), pady=2)
        self.cdp_port = tk.IntVar(value=9222)
        tk.Spinbox(bframe, from=1024, to=65535, textvariable=self.cdpport, width=6,
                   bg="#1e1e1e", fg="#00ff88", insertbackground="#00ff88",
                   buttonbackground="#1e1e1e", relief="flat").grid(
            row=5, column=3, sticky="e", padx=5, pady=2)

        self.headless = tk.BooleanVar(value=True)
        tk.Checkbutton(bframe, text="🙈 Headless (скрывать окно браузера)",
                       variable=self.headless, bg="#252540", fg="#cccccc",
                       selectcolor="#252540").grid(row=6, column=0, columnspan=2,
                                                   sticky="w", padx=5, pady=2)

        self.export_storage = tk.BooleanVar(value=False)
        tk.Checkbutton(bframe, text="🍪 Экспортировать storage_state.json в папку результата",
                       variable=self.export_storage, bg="#252540", fg="#cccccc",
                       selectcolor="#252540").grid(row=6, column=2, columnspan=2,
                                                   sticky="w", padx=5, pady=2)

        brow_btns = tk.Frame(bframe, bg="#252540")
        brow_btns.grid(row=7, column=0, columnspan=4, sticky="w", padx=5, pady=(8, 2))
        tk.Button(browbtns, text="🔍 Проверить CDP-порт", command=self.testcdp,
                  bg="#1e1e1e", fg="#5aa9ff", relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(browbtns, text="🧪 Тест браузера", command=self.testbrowser,
                  bg="#1e1e1e", fg="#00ff88", relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(brow_btns, text="⬇️ Установить Firefox (Playwright)",
                  command=lambda: self.installbg("firefox"),
                  bg="#1e1e1e", fg="#ffb020", relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(brow_btns, text="⬇️ Chromium",
                  command=lambda: self.installbg("chromium"),
                  bg="#1e1e1e", fg="#ffb020", relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").pack(side="left")

        tk.Label(bframe, text="⚠️ Массовый скрапинг под личным профилем может привести "
                              "к блокировке аккаунтов на целевых сайтах.\n"
                              "⚠️ Профиль/CDP = ОДИН браузер на процесс: потоки будут "
                              "сериализованы автоматически (иначе Chrome заблокирует "
                              "user-data-dir).\n"
                              "⚠️ Chrome 136+ игнорирует --remote-debugging-port для "
                              "профиля по умолчанию — нужен отдельный --user-data-dir.",
                 bg="#252540", fg="#9a9ab5", font=("Segoe UI", 8),
                 justify="left").grid(row=8, column=0, columnspan=4, sticky="w",
                                      padx=5, pady=(6, 0))

        # --- Кнопки ---
        btn_row = tk.Frame(root, bg="#12121f")
        btn_row.pack(fill="x", padx=20, pady=8)
        self.btn = tk.Button(btn_row, text="🚀 НАЧАТЬ", command=self.start,
                             bg="#00aa44", fg="white", font=("Segoe UI", 12, "bold"),
                             relief="flat", cursor="hand2")
        self.btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.stopbtn = tk.Button(btnrow, text="⛔ СТОП", command=self.stop, state="disabled",
                                  bg="#aa2222", fg="white", font=("Segoe UI", 12, "bold"),
                                  relief="flat", cursor="hand2")
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # --- Прогресс ---
        self.progress = tk.DoubleVar()
        ttk.Progressbar(root, variable=self.progress, maximum=100,
                        style="TProgressbar").pack(fill="x", padx=20, pady=5)

        # --- Журнал ---
        log_head = tk.Frame(root, bg="#12121f")
        log_head.pack(fill="x", padx=20, pady=(6, 0))
        tk.Label(log_head, text="📋 Журнал", font=("Segoe UI", 9, "bold"),
                 bg="#12121f", fg="#00ff88").pack(side="left")
        tk.Button(loghead, text="скопировать", command=self.copylog, bg="#2d2d44",
                  fg="#cccccc", relief="flat", font=("Segoe UI", 8),
                  cursor="hand2").pack(side="right", padx=(6, 0))
        tk.Button(loghead, text="очистить", command=self.clearlog, bg="#2d2d44",
                  fg="#cccccc", relief="flat", font=("Segoe UI", 8),
                  cursor="hand2").pack(side="right")

        log_frame = tk.Frame(root, bg="#0d0d0d", highlightbackground="#1e1e1e",
                             highlightthickness=1)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(4, 5))
        self.logtext = tk.Text(logframe, height=12, state="disabled", bg="#0d0d0d",
                                fg="#00ff88", font=("Consolas", 9), relief="flat",
                                padx=6, pady=4)
        sb = ttk.Scrollbar(logframe, orient="vertical", command=self.logtext.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for tag, color in (("ok", "#00ff88"), ("warn", "#ffb020"), ("err", "#ff5470"),
                           ("info", "#9fd7ff"), ("mut", "#7a7a95")):
            self.logtext.tagconfigure(tag, foreground=color)

        # --- Статистика + папка ---
        stats = tk.Frame(root, bg="#12121f")
        stats.pack(fill="x", padx=20, pady=(2, 12))
        self.ok_label = tk.Label(stats, text="✅ 0", font=("Segoe UI", 10, "bold"),
                                 fg="#00ff88", bg="#12121f")
        self.ok_label.pack(side="left", padx=(0, 18))
        self.fail_label = tk.Label(stats, text="❌ 0", font=("Segoe UI", 10, "bold"),
                                   fg="#ff4444", bg="#12121f")
        self.fail_label.pack(side="left", padx=(0, 18))
        self.blk_label = tk.Label(stats, text="⚠️ 0", font=("Segoe UI", 10, "bold"),
                                  fg="#ffb020", bg="#12121f")
        self.blk_label.pack(side="left")
        self.folder_btn = tk.Button(stats, text="📂 Открыть папку результата",
                                    command=self.openoutputfolder, state="disabled",
                                    bg="#2d2d44", fg="white", relief="flat",
                                    font=("Segoe UI", 9), cursor="hand2")
        self.folder_btn.pack(side="right")

        self.root.after(80, self.pollui)
        self.root.after(200, self.startuplog)

    # ---------------- браузерные помощники ----------------
    def onbrowserpick(self, event=None):
        cfg = self.browsermanager.find(self.selectedbrowser.get())
        if cfg:
            if cfg.get("profiledir") and not self.profilepath_var.get().strip():
                self.profilepathvar.set(cfg["profile_dir"])
            self.log(f"ℹ️ Выбран «{cfg['name']}» · движок {cfg['engine']} · exe: {cfg['exe']}")
            if cfg["engine"] == "firefox":
                self.log("⚠️ Gecko: Playwright нужен патченный Firefox. Внешний скорее всего "
                         "не запустится — сработает фоллбэк. Кнопка «Установить Firefox» ниже.", "warn")

    def oncdp_toggle(self):
        if self.attach_cdp.get():
            self.headless.set(False)
            self.log("🔌 CDP-режим: скрипт подключится к живому браузеру и НЕ будет его "
                     "закрывать. Браузер должен быть запущен с --remote-debugging-port "
                     "и отдельным --user-data-dir.", "info")

    def refreshbrowserlist(self):
        cur = self.selected_browser.get()
        self.browsermanager.logcb = self.log
        names = self.browser_manager.scan()
        full = self.browsermanager.getbrowser_list()
        self.browser_combo['values'] = full
        self.selected_browser.set(cur if cur in full else full[0])
        self.log(f"🔄 Список браузеров обновлён: {len(names)} найдено")

    def browse_profile(self):
        path = filedialog.askdirectory(title="Папка профиля браузера (user-data-dir)")
        if path:
            self.profilepathvar.set(path)
            self.use_profile.set(True)
            self.log(f"👤 Профиль: {path}")

    def test_cdp(self):
        port = self.spin(self.cdpport, 9222, 1024, 65535)
        ws, ver = ExternalBrowserManager.probe_cdp(port, timeout=2.0)
        if ws:
            self.log(f"✅ CDP жив на 127.0.0.1:{port} → {ver}", "ok")
            self.log(f"   ws: {ws[:90]}", "mut")
            self.attach_cdp.set(True)
        else:
            self.log(f"❌ На 127.0.0.1:{port} никто не слушает. Запусти браузер так:", "err")
            self.log(f'   chrome.exe --remote-debugging-port={port} '
                     f'--remote-debugging-address=127.0.0.1 --user-data-dir="C:\\mt_profile"', "mut")

    def test_browser(self):
        threading.Thread(target=self.testbrowser_worker, daemon=True).start()

    def testbrowser_worker(self):
        name = self.selected_browser.get()
        self.log("=" * 60)
        self.log(f"🧪 ТЕСТ БРАУЗЕРА: {name}")
        try:
            from playwright.syncapi import syncplaywright
        except Exception as e:
            self.log(f"❌ playwright не импортируется: {e}", "err")
            return
        plan = self.browsermanager.buildplan(
            name, self.profilepathvar.get().strip(), bool(self.use_profile.get()),
            bool(self.attachcdp.get()), self.spin(self.cdp_port, 9222, 1024, 65535),
            bool(self.headless.get()), bool(self.copyprofile.get()), logcb=self.log)
        plan["headless"] = bool(self.headless.get())
        self.log(f"   план: mode={plan['mode']} engine={plan['engine']} "
                 f"exe={plan['executablepath'] or '—'} profile={plan['userdata_dir'] or '—'}")
        ua = random_ua()
        locale, tz = randomlocaletz()
        try:
            with sync_playwright() as p:
                session = openwith_fallback(p, plan, ua, locale, tz,
                                              random.choice(VIEWPORTS),
                                              bool(self.stealth.get()), self.log)
                try:
                    page = session.new_page()
                    page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
                    page.waitfortimeout(600)
                    self.log(f"   ✅ страница открыта: {page.title()}", "ok")
                    info = page.evaluate("() => ({ua: navigator.userAgent, wd: navigator.webdriver, "
                                          "plat: navigator.platform, lang: navigator.languages, "
                                          "hw: navigator.hardwareConcurrency})")
                    self.log(f"   navigator.webdriver = {info.get('wd')}", "info")
                    self.log(f"   platform = {info.get('plat')} | languages = {info.get('lang')} "
                             f"| hw = {info.get('hw')}", "mut")
                    self.log(f"   UA = {str(info.get('ua'))[:110]}", "mut")
                    try:
                        ck = session.context.cookies()
                        self.log(f"   🍪 cookies в контексте: {len(ck)}", "info")
                    except Exception:
                        pass
                finally:
                    session.close()
            self.log("🧪 ТЕСТ ЗАВЕРШЁН УСПЕШНО", "ok")
        except Exception as e:
            self.log(f"❌ тест провален: {str(e)[:220]}", "err")
        self.log("=" * 60)

    def installbg(self, what):
        threading.Thread(target=installplaywrightbrowser, args=(what, self.log),
                         daemon=True).start()

    def startuplog(self):
        self.browsermanager.logcb = self.log
        self.log("=" * 62)
        self.log(f"🚀 {APPNAME} v{APPVERSION} · build {BUILD_DATE}", "head")
        self.log("=" * 62)
        self.log(f"📁 рабочая папка: {BASE_DIR}", "mut")
        names = self.browser_manager.scan()
        if not names:
            self.log("ℹ️ портативные/системные браузеры не найдены — доступен bundled "
                     "режим (Playwright Chromium).", "warn")
        self.log("💡 чтобы подключиться к своему браузеру: закрой его, затем запусти с флагами", "mut")
        self.log('   chrome.exe --remote-debugging-port=9222 '
                 '--remote-debugging-address=127.0.0.1 --user-data-dir="C:\\mt_profile"', "mut")
        self.log("   войди вручную на нужных сайтах → нажми «🔌 CDP» и «НАЧАТЬ»", "mut")
        self.log("", "mut")

    # ---------------- UI helpers (потокобезопасные) ----------------
    def log(self, msg, level="mut"):
        self.ui_q.put(("log", (str(msg), level)))

    def set_progress(self, pct):
        self.ui_q.put(("progress", pct))

    def set_stats(self, ok, fail, blocked=0):
        self.ui_q.put(("stats", (ok, fail, blocked)))

    def pollui(self):
        try:
            while True:
                kind, payload = self.uiq.getnowait()
                if kind == "log":
                    text, level = payload
                    self.log_buffer.append(text)
                    if len(self.log_buffer) > 20000:
                        del self.log_buffer[:5000]
                    self.log_text.config(state="normal")
                    self.log_text.insert(tk.END, text + "\n", level)
                    self.log_text.see(tk.END)
                    self.log_text.config(state="disabled")
                elif kind == "progress":
                    self.progress.set(payload)
                elif kind == "stats":
                    ok, fail, blocked = payload
                    self.ok_label.config(text=f"✅ {ok}")
                    self.fail_label.config(text=f"❌ {fail}")
                    self.blk_label.config(text=f"⚠️ {blocked}")
                elif kind == "done":
                    self.onfinished(payload)
        except queue.Empty:
            pass
        try:
            self.root.after(80, self.pollui)
        except tk.TclError:
            pass

    def copy_log(self):
        try:
            self.root.clipboard_clear()
            self.root.clipboardappend(self.logtext.get("1.0", tk.END).strip())
            self.log("📋 Журнал скопирован в буфер обмена", "info")
        except Exception as e:
            self.log(f"⚠️ не удалось скопировать: {e}", "warn")

    def clear_log(self):
        self.log_buffer.clear()
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    @staticmethod
    def _spin(var, default, lo, hi):
        try:
            v = int(var.get())
        except Exception:
            v = default
        return max(lo, min(hi, v))

    # ---------------- Запуск / остановка ----------------
    def start(self):
        if self.is_running:
            return
        raw_urls = self.urls.get("1.0", tk.END).strip()
        if not raw_urls:
            messagebox.showwarning("Ошибка", "Введите хотя бы один URL!")
            return

        seen, valid_urls = set(), []
        for u in (x.strip() for x in raw_urls.splitlines()):
            if not u:
                continue
            if not u.startswith(("http://", "https://")):
                self.log(f"⚠️ Невалидный URL пропущен (нужен http:// или https://): {u}", "warn")
                continue
            if u in seen:
                self.log(f"ℹ️ Дубликат пропущен: {u}", "mut")
                continue
            seen.add(u)
            valid_urls.append(u)

        if not valid_urls:
            messagebox.showwarning("Ошибка", "Ни одного валидного URL не найдено!")
            return

        useprofile = bool(self.useprofile.get())
        profilepath = self.profilepath_var.get().strip()
        attach = bool(self.attach_cdp.get())
        if useprofile and not profilepath:
            cfg = self.browsermanager.find(self.selectedbrowser.get())
            if cfg and cfg.get("profile_dir"):
                profilepath = cfg["profiledir"]
                self.profilepathvar.set(profile_path)
            else:
                messagebox.showwarning("Профиль", "Укажи папку профиля (user-data-dir) "
                                                 "или сними галку «Использовать профиль».")
                return

        outdir = os.path.join(BASEDIR, f"MEGATANK{now_stamp()}")
        try:
            os.makedirs(outdir, existok=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать папку результата:\n{e}")
            return
        self.lastoutputdir = out_dir

        settings = {
            "fmt": FORMATMAP.get(self.fmtlabel.get(), "md"),
            "merge": bool(self.merge.get()),
            "aggressive": bool(self.aggr.get()),
            "stealth": bool(self.stealth.get()),
            "concurrency": self._spin(self.concurrency, 1, 1, 5),
            "retries": self._spin(self.retries, 1, 0, 3),
            "externalbrowser": self.selectedbrowser.get(),
            "customprofilepath": profile_path or None,
            "useprofile": useprofile,
            "attach_cdp": attach,
            "cdpport": self.spin(self.cdp_port, 9222, 1024, 65535),
            "headless": bool(self.headless.get()),
            "copyprofile": bool(self.copyprofile.get()),
            "exportstorage": bool(self.exportstorage.get()),
        }

        if attach and settings["headless"]:
            settings["headless"] = False
            self.headless.set(False)
            self.log("ℹ️ CDP-подключение к живому браузеру → headless выключен", "info")

        self.stop_event.clear()
        self.is_running = True
        self.btn.config(state="disabled", text="⏳ РАБОТАЮ...")
        self.stop_btn.config(state="normal", text="⛔ СТОП")
        self.folder_btn.config(state="disabled")
        self.log_buffer.clear()
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")
        self.set_progress(0)
        self.set_stats(0, 0, 0)

        threading.Thread(target=self.coordinator, args=(validurls, out_dir, settings),
                         daemon=True).start()

    def stop(self):
        if not self.is_running:
            return
        self.stop_event.set()
        self.stop_btn.config(state="disabled", text="⛔ ОСТАНАВЛИВАЮ...")
        self.log("\n⛔ Остановка запрошена — потоки завершают текущие задачи "
                 "(браузер пользователя закрыт не будет)...", "warn")

    def on_close(self):
        if self.is_running:
            if not messagebox.askyesno("Подтверждение", "Скрапинг ещё идёт. Закрыть всё равно?"):
                return
            self.stop_event.set()
            time.sleep(0.4)
        try:
            self.root.destroy()
        except Exception:
            pass

    def openoutputfolder(self):
        if not self.lastoutputdir or not os.path.isdir(self.lastoutputdir):
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.lastoutputdir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.lastoutputdir])
            else:
                subprocess.Popen(["xdg-open", self.lastoutputdir])
        except Exception:
            webbrowser.open(f"file://{self.lastoutputdir}")

    # ---------------- Координатор + воркеры ----------------
    def coordinator(self, urls, outdir, settings):
        url_q = queue.Queue()
        for u in urls:
            url_q.put(u)

        manifest = []
        counters = {"ok": 0, "fail": 0, "done": 0, "blocked": 0}
        total = len(urls)

        # Профиль/CDP = один браузер на процесс → принудительно один поток
        sharedsession = bool(settings["useprofile"] or settings["attach_cdp"])
        if shared_session and settings["concurrency"] > 1:
            self.log(f"⚠️ Профиль/CDP не допускают {settings['concurrency']} потоков: "
                     f"user-data-dir блокируется одним процессом. Ставлю 1 поток.", "warn")
            settings["concurrency"] = 1

        self.log("=" * 62, "head")
        self.log(f"🚀 {APPNAME} v{APPVERSION}  (build {BUILD_DATE})", "head")
        self.log(f"📁 Папка результата: {out_dir}", "info")
        self.log(f"📄 Формат: {settings['fmt'].upper()} | Объединить: "
                 f"{'ДА' if settings['merge'] else 'НЕТ'}", "info")
        self.log(f"🌐 URLs: {total} | Потоков: {settings['concurrency']} | Повторов: "
                 f"{settings['retries']} | Режим: "
                 f"{'агрессивный' if settings['aggressive'] else 'щадящий'}", "info")
        self.log(f"🧭 Браузер: {settings['external_browser']}", "info")
        if settings["use_profile"]:
            self.log(f"👤 Профиль: {settings['customprofilepath']}"
                     + ("  [будет скопирован]" if settings["copy_profile"] else "  [оригинал]"),
                     "info")
        if settings["attach_cdp"]:
            self.log(f"🔌 CDP: 127.0.0.1:{settings['cdp_port']} (только localhost)", "info")
        self.log(f"🙈 Headless: {'ДА' if settings['headless'] else 'НЕТ'} | "
                 f"Stealth: {'ДА' if settings['stealth'] else 'НЕТ'}", "info")
        self.log("=" * 62, "head")

        self.browsermanager.logcb = self.log
        storage_dumped = [None]

        def worker(worker_id):
            while not self.stopevent.isset():
                try:
                    url = urlq.getnowait()
                except queue.Empty:
                    break
                self.log(f"\n[поток {worker_id}] 📥 {url[:75]}", "info")
                res = scrapeone(url, settings["fmt"], outdir, settings, self.log,
                                 shouldstop=self.stopevent.is_set,
                                 browsermanager=self.browsermanager)
                with self.lock:
                    manifest.append(res)
                    if res["status"] == "ok":
                        counters["ok"] += 1
                    else:
                        counters["fail"] += 1
                        self.log(f"   ❌ Не удалось: {url} — {str(res.get('error'))[:150]}", "err")
                    if res.get("blocked_suspected"):
                        counters["blocked"] += 1
                    counters["done"] += 1
                    self.set_stats(counters["ok"], counters["fail"], counters["blocked"])
                    self.set_progress(counters["done"] / total * 100)

                if self.stopevent.isset():
                    break
                delay = random.uniform(1.0, 3.0) if settings["aggressive"] \
                    else random.uniform(3.0, 7.0)
                self.log(f"   ⏱️ [поток {worker_id}] пауза {delay:.1f} сек", "mut")
                slept = 0.0
                while slept  {mergedname}", "ok")
                mergedfilename = mergedname
            except Exception as e:
                self.log(f"   ❌ Ошибка объединения: {e}", "err")

        browser_info = {
            "label": settings["external_browser"],
            "engine": (manifest[0].get("engine") if manifest else "chromium"),
            "mode": (manifest[0].get("session_mode") if manifest else "bundled"),
            "profile": settings["customprofilepath"],
            "profileisolatedcopy": bool(settings["copyprofile"] and settings["useprofile"]),
            "cdp": (f"127.0.0.1:{settings['cdpport']}" if settings["attachcdp"] else None),
            "headless": bool(settings["headless"]),
        }

        try:
            totals = writemanifestandindex(manifest, outdir, mergedfilename, browserinfo)
            self.log("\n📊 manifest.json и INDEX.md записаны", "ok")
            self.log(f"   Σ объём: {human_size(totals['bytes'])} | Σ слов: {totals['words']}", "mut")
        except Exception as e:
            self.log(f"⚠️ Не удалось записать manifest/index: {e}", "warn")

        self.log("\n" + "=" * 62, "head")
        statusword = "ОСТАНОВЛЕНО" if self.stopevent.is_set() else "ГОТОВО"
        self.log(f"🎉 {status_word}! Успешно: {counters['ok']} | Ошибок: {counters['fail']} "
                 f"| Подозрений на блок: {counters['blocked']}", "head")
        self.log(f"📁 Папка: {out_dir}", "info")
        self.log("=" * 62, "head")

        self.set_progress(100)
        self.ui_q.put(("done", {
            "ok": counters["ok"], "fail": counters["fail"], "blocked": counters["blocked"],
            "outdir": outdir, "stopped": self.stopevent.isset(),
        }))

    def exportstorage(self, out_dir, settings):
        """Открывает тот же браузер/профиль и выгружает storage_state.json."""
        try:
            from playwright.syncapi import syncplaywright
            plan = self.browsermanager.buildplan(
                settings["externalbrowser"], settings["customprofile_path"] or "",
                settings["useprofile"], False, settings["cdpport"],
                True, settings["copyprofile"], logcb=self.log)
            plan["headless"] = True
            ua = random_ua()
            locale, tz = randomlocaletz()
            with sync_playwright() as p:
                session = openwith_fallback(p, plan, ua, locale, tz,
                                              random.choice(VIEWPORTS), False, self.log)
                try:
                    if session.owns_context:
                        dumpstoragestate(session, out_dir, self.log)
                    else:
                        self.log("   ℹ️ контекст принадлежит браузеру пользователя — "
                                 "cookies не выгружаем (приватность)", "warn")
                finally:
                    session.close()
        except Exception as e:
            self.log(f"⚠️ экспорт сессии не удался: {str(e)[:140]}", "warn")

    def onfinished(self, payload):
        self.is_running = False
        self.btn.config(state="normal", text="🚀 НАЧАТЬ")
        self.stop_btn.config(state="disabled", text="⛔ СТОП")
        self.folder_btn.config(state="normal")
        try:
            with open(os.path.join(payload["out_dir"], "RUN.log"), "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_buffer))
        except Exception:
            pass
        title = "Остановлено" if payload["stopped"] else "Готово"
        messagebox.showinfo(
            title,
            f"✅ Успешно: {payload['ok']}\n❌ Ошибок: {payload['fail']}\n"
            f"⚠️ Подозрений на блок: {payload.get('blocked', 0)}\n"
            f"📁 Папка:\n{payload['out_dir']}",
        )

==============================================================================
ЗАПУСК
==============================================================================
if name == "main":
    installer = AutoInstaller()
    deps_ok = installer.run()

    if not deps_ok:
        print("\n⚠️ Не все зависимости установлены — приложение может работать нестабильно.")
        try:
            answer = input("Запустить всё равно? (y/n): ").strip().lower()
        except EOFError:
            answer = "n"
        if answer != "y":
            input("\nНажмите Enter для выхода...")
            sys.exit(1)

    try:
        root = tk.Tk()
    except Exception as e:
        print(f"❌ Не удалось открыть GUI-окно: {e}")
        print("   Если это сервер без дисплея — запускай через: xvfb-run python MEGA_TANK.py")
        sys.exit(2)

    App(root)
    root.mainloop()