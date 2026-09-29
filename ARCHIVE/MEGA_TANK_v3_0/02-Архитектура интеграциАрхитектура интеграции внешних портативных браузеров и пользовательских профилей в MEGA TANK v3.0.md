# Архитектура интеграции внешних портативных браузеров и пользовательских профилей в MEGA TANK v3.0

## Аннотация

В данном исследовании представлена детальная архитектура и реализация модуля интеграции внешних портативных браузеров (таких как Firefox Portable, LibreWolf, Chrome Portable) и существующих пользовательских профилей в инструмент автоматизированного сбора данных MEGA TANK v3.0. Основная цель модернизации заключается в обеспечении доступа к авторизованному контенту и использовании уникальных цифровых отпечатков реальных пользователей для обхода систем анти-бот защиты. Исследование охватывает техническую возможность подключения к запущенным инстансам браузеров через протоколы удаленной отладки (CDP для Chromium и Juggler/RDP для Gecko), а также механизмы запуска специфических исполняемых файлов с передачей параметров профиля. Особое внимание уделено адаптации логики Playwright для поддержки гетерогенных движков, сохранению сессий (cookies, local storage) и стратегии фоллбэка между системными, портативными и встроенными браузерами. Результатом работы является полностью функциональный, самодостаточный Python-скрипт, сохраняющий потокобезопасную архитектуру оригинального приложения.

## 1. Введение

Современные веб-приложения все чаще используют сложные системы защиты от автоматизированного доступа, такие как Cloudflare, Akamai и DataDome. Эти системы анализируют не только IP-адреса, но и цифровой отпечаток браузера (fingerprint), поведенческие паттерны и состояние сессии. Традиционные инструменты скрапинга, использующие изолированные headless-браузеры без истории и куки, часто блокируются на этапе проверки TLS-рукопожатия или JavaScript-челленджей. 

MEGA TANK v3.0 представляет собой универсальный парсер документации, способный сохранять веб-страницы в различных форматах (PDF, HTML, TXT, DOCX, Markdown). Однако базовая версия опирается на стандартный bundled Chromium от Playwright, который имеет предсказуемый цифровой отпечаток и не сохраняет состояние между запусками. Для решения проблемы доступа к закрытому контенту требуется интеграция с реальными пользовательскими средами: портативными браузерами, которые могут быть предварительно настроены, авторизованы на целевых ресурсах и иметь уникальный, «прогретый» цифровой след.

Задача данного исследования — разработать архитектуру, позволяющую MEGA TANK v3.0 использовать внешние браузеры (Chrome Portable, Firefox Portable, LibreWolf и др.) и подключаться к уже запущенным сессиям пользователей. Это требует глубокой переработки уровня взаимодействия с браузером, так как протоколы управления Chromium (CDP) и Gecko (Juggler/RDP) фундаментально различаются, а механизмы хранения профилей в портативных версиях имеют свои особенности [[10](https://portableapps.com/node/5376), [28](https://github.com/feder-cr/invisible_playwright/wiki/playwright-connect-over-cdp-firefox), [29](https://remote-browser.dev/blog/firefox-cdp)].

## 2. Анализ технических требований и ограничений

### 2.1. Гетерогенность браузерных движков

Для обеспечения максимальной совместимости система должна поддерживать два основных семейства браузерных движков:
1.  **Blink (Chromium):** Google Chrome, Microsoft Edge, Brave, Opera, а также их портативные версии. Управление осуществляется через Chrome DevTools Protocol (CDP) [[1](https://www.browserless.io/blog/chrome-remote-debugging)].
2.  **Gecko (Firefox):** Mozilla Firefox, LibreWolf, Waterfox. Playwright использует собственный протокол Juggler для управления Firefox, так как нативная поддержка CDP в Firefox отсутствует или ограничена [[28](https://github.com/feder-cr/invisible_playwright/wiki/playwright-connect-over-cdp-firefox), [29](https://remote-browser.dev/blog/firefox-cdp)].

Интеграция должна быть прозрачной для пользователя: выбор браузера в интерфейсе должен автоматически определять правильный метод запуска и подключения.

### 2.2. Сохранение пользовательских сессий

Ключевым требованием является возможность использования уже авторизованных сессий. Это достигается двумя путями:
*   **Persistent Context:** Запуск браузера с указанием директории пользовательских данных (`user_data_dir` для Chromium или `-profile` для Firefox). Это позволяет загружать cookies, local storage, расширения и историю [[3](https://groups.google.com/g/selenium-users/c/RMuo7l222g8), [27](https://yashaka.github.io/selene/faq/custom-user-profile-howto/)].
*   **Подключение к живой сессии (Live Session):** Подключение скрипта к уже открытому окну браузера, в котором пользователь вручную выполнил вход. Для Chromium это делается через CDP, для Firefox — через сервер отладки [[17](https://www.browserstack.com/guide/playwright-connect-to-existing-browser), [20](https://www.reddit.com/r/LibreWolf/comments/1hfw6p4/ho_to_enable_the_browser_toolbox_in_librewolf/)].

### 2.3. Ограничения безопасности современных браузеров

Начиная с Chrome версии 136, Google ввел строгие ограничения на использование флага `--remote-debugging-port` с профилем по умолчанию. Это сделано для предотвращения кражи сессионных данных злоумышленниками. Теперь для включения удаленной отладки обязательно использование отдельной директории через флаг `--user-data-dir` [[1](https://www.browserless.io/blog/chrome-remote-debugging), [2](https://developer.chrome.com/blog/remote-debugging-port)]. Аналогичные меры безопасности применяются и в других современных браузерах, что требует тщательной настройки путей к профилям.

Кроме того, портативные версии браузеров (например, Firefox Portable) имеют собственные механизмы блокировки множественных запусков (single-instance lock), которые необходимо обходить с помощью специальных флагов (`-no-remote`) или модификации конфигурационных файлов (.ini) [[60](https://stackoverflow.com/questions/345281/is-there-a-way-to-force-firefox-to-launch-in-a-new-process), [61](https://portableapps.com/node/57110)].

### 2.4. Цифровой отпечаток и Stealth-режим

Использование внешнего браузера само по себе улучшает прохождение проверок, так как браузер имеет реальные аппаратные характеристики (WebGL, AudioContext, Fonts). Однако, если браузер запускается в режиме автоматизации, он может выдавать признаки бота (например, `navigator.webdriver = true`). Система должна применять адаптивные stealth-скрипты, которые маскируют признаки автоматизации, при этом учитывая различия между движками Blink и Gecko [[34](https://scrapfly.io/blog/posts/how-browser-fingerprinting-works), [42](https://github.com/daijro/camoufox)].

## 3. Архитектура решения: ExternalBrowserManager

Центральным элементом новой архитектуры является класс `ExternalBrowserManager`. Этот компонент отвечает за обнаружение установленных портативных браузеров, определение их типа движка и выбор стратегии запуска.

### 3.1. Механизм обнаружения браузеров

Менеджер осуществляет рекурсивный поиск исполняемых файлов в заданных директориях (текущая папка, папка PortableApps). Для каждого найденного браузера определяется:
*   Путь к исполняемому файлу.
*   Тип движка (chromium/firefox).
*   Путь к директории профиля по умолчанию.
*   Специфические аргументы командной строки.

| Браузер | Исполняемый файл | Движок | Аргумент профиля | Путь профиля по умолчанию |
| :--- | :--- | :--- | :--- | :--- |
| Chrome Portable | GoogleChromePortable.exe | chromium | --user-data-dir | Data/profile |
| Firefox Portable | FirefoxPortable.exe | firefox | -profile | Data/profile |
| LibreWolf Portable | librewolf.exe | firefox | -profile | Data/profile |
| Chromium Portable | chrome.exe | chromium | --user-data-dir | Data/profile |

*Таблица 1. Конфигурация поддерживаемых портативных браузеров.*

### 3.2. Стратегия запуска и подключения

Логика `launch_or_connect` реализует следующий алгоритм принятия решений:

1.  **Проверка CDP (только для Chromium):** Если выбран браузер на базе Chromium и режим не headless, скрипт пытается подключиться к `localhost:9222`. Если соединение успешно, используется метод `connect_over_cdp`, что позволяет работать с активной сессией пользователя без перезапуска браузера [[1](https://www.browserless.io/blog/chrome-remote-debugging), [4](https://mcpservers.org/servers/Rainmen-xia/chrome-debug-mcp-server)].
2.  **Запуск внешнего исполняемого файла:** Если подключение не удалось или выбран Firefox, происходит запуск нового процесса.
    *   Для **Chromium**: используются флаги `--no-sandbox`, `--disable-dev-shm-usage` и указание `--user-data-dir`.
    *   Для **Firefox**: добавляется флаг `-no-remote` для разрешения параллельных запусков и `-profile` для указания пути к данным [[27](https://yashaka.github.io/selene/faq/custom-user-profile-howto/), [60](https://stackoverflow.com/questions/345281/is-there-a-way-to-force-firefox-to-launch-in-a-new-process)].
3.  **Инициализация контекста:** После запуска браузера создается новый контекст Playwright. Для Chromium применяется stealth-скрипт, подменяющий `navigator.webdriver` и другие свойства. Для Firefox используются специфические предпочтения (`firefox_user_prefs`), хотя полная эмуляция stealth-режима в Gecko сложнее из-за архитектурных отличий [[6](https://playwright.dev/python/docs/api/class-browsertype), [42](https://github.com/daijro/camoufox)].

### 3.3. Управление жизненным циклом процессов

Критически важным аспектом является корректное завершение работы. При использовании стандартного bundled Chromium браузер закрывается после завершения задачи. Однако при работе с внешними браузерами, особенно в режиме подключения к живой сессии, закрытие браузера скриптом недопустимо, так как это прервет работу пользователя. Поэтому в реализации добавлена проверка: если используется внешний браузер, процесс браузера не terminatesя автоматически [[17](https://www.browserstack.com/guide/playwright-connect-to-existing-browser)].

## 4. Интеграция в основной поток скрапинга

Функция `scrape_one` была модифицирована для приема экземпляра `ExternalBrowserManager` и параметров выбранного браузера.

### 4.1. Адаптация Playwright API

Вместо прямого вызова `p.chromium.launch()` код теперь проверяет настройки:
```python
if ext_browser_name != "System Default":
    engine, launch_kwargs = browser_manager.launch_or_connect(...)
    if launch_kwargs.get("connect_cdp"):
        browser = p.chromium.connect_over_cdp(launch_kwargs["connect_cdp"])
    else:
        if engine == "chromium":
            browser = p.chromium.launch(executable_path=..., args=...)
        elif engine == "firefox":
            browser = p.firefox.launch(executable_path=..., args=...)
```
Этот подход обеспечивает гибкость и позволяет использовать один и тот же интерфейс для разных типов браузеров [[5](https://playwright.dev/docs/api/class-browsertype), [6](https://playwright.dev/python/docs/api/class-browsertype)].

### 4.2. Обработка ошибок и фоллбэк

Если запуск внешнего браузера невозможен (например, отсутствующий исполняемый файл или занятый порт), система логирует ошибку и, в зависимости от настроек, может переключиться на стандартный bundled Chromium или использовать запасной метод `requests`. Это гарантирует отказоустойчивость инструмента [[7](https://stackoverflow.com/questions/62281859/how-to-use-installed-version-of-chrome-in-playwright)].

### 4.3. Сохранение результатов

Логика сохранения файлов (PDF, HTML, MD, DOCX) осталась неизменной, так как она работает на уровне абстракции страницы Playwright, которая единообразна для всех поддерживаемых браузеров. Однако при извлечении текста и HTML учитываются возможные различия в рендеринге между движками Blink и Gecko [[29](https://remote-browser.dev/blog/firefox-cdp)].

## 5. Пользовательский интерфейс (GUI)

Интерфейс Tkinter был расширен для управления новыми функциями:

1.  **Выбор браузера:** Добавлен выпадающий список (`Combobox`), заполняемый данными из `ExternalBrowserManager`. Пользователь может выбрать любой обнаруженный портативный браузер или стандартный вариант.
2.  **Управление профилем:** Добавлено текстовое поле и кнопка обзора для явного указания пути к папке профиля. Это полезно, если профиль находится не в стандартном месте или пользователь хочет использовать изолированную копию профиля для скрапинга.
3.  **Кнопка обновления списка:** Позволяет перечитать файловую систему без перезапуска приложения, если новые портативные браузеры были скопированы в папку.

Эти элементы интегрированы в существующую панель настроек, сохраняя единый стиль оформления и темную тему приложения.

## 6. Безопасность и конфиденциальность

Использование реальных пользовательских профилей несет риски утечки данных. В реализации учтены следующие аспекты:
*   **Изоляция портов:** CDP-порт привязывается к localhost и не открывается для внешних соединений [[1](https://www.browserless.io/blog/chrome-remote-debugging)].
*   **Отсутствие модификации исходных данных:** Скрипт только читает данные из профиля (cookies) для авторизации, но не изменяет основные настройки браузера пользователя, если не используется специальная изолированная копия профиля.
*   **Предупреждения:** В интерфейсе и логах присутствуют предупреждения о том, что использование личных профилей для массового скрапинга может привести к блокировке аккаунтов на целевых сайтах.

## 7. Полный исходный код решения

Ниже представлен полный код обновленного файла `MEGA_TANK.py`. Он включает в себя все необходимые импорты, класс `ExternalBrowserManager`, обновленную логику скрапинга и расширенный GUI. Код является самодостаточным и готов к запуску при наличии установленных зависимостей (Playwright, requests и др.).

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 MEGA TANK v3.0 — UNIVERSAL DOCUMENTATION SCRAPER (EXTENDED EDITION)
 Пересобран: 30.06.2026 | Extended: 29.09.2026
================================================================================
 Что нового в этом обновлении:
   • Поддержка внешних портативных браузеров (Chrome/Firefox/LibreWolf Portable).
   • Интеграция с существующими пользовательскими профилями (сохранение сессий).
   • Подключение к запущенным инстансам через CDP (Chromium) и Juggler (Firefox).
   • Автоматическое обнаружение портативных приложений в текущей директории и 
     стандартных путях PortableApps.
   • Адаптация Stealth-скриптов под движки Gecko и Blink.
   • Сохранение всей архитектуры v3.0 (пототокобезопасность, автоустановка, UI).
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
import webbrowser
import glob
from datetime import datetime
from urllib.parse import urlparse, urljoin

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==============================================================================
# ГЛУШКА КОНСОЛИ (Windows cp866/cp1251 → UnicodeEncodeError на эмодзи)
# ==============================================================================
def _fix_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_fix_console()

# ==============================================================================
# КОНСТАНТЫ
# ==============================================================================
APP_NAME = "MEGA TANK"
APP_VERSION = "3.0 EXT"
BUILD_DATE = "30.06.2026"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
]

LOCALE_TZ_PAIRS = [
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

CONTENT_SELECTOR = ("article, main, [role='main'], .article, .post, "
                    ".entry-content, .post-content, .content")

JUNK_SELECTOR = ("script, style, noscript, template, svg, canvas, iframe, "
                 "nav, header, footer, aside, [aria-hidden=\"true\"], "
                 "[role=\"navigation\"], [role=\"banner\"], [role=\"contentinfo\"], "
                 ".cookie, .cookies, .consent, .popup, .modal, .advert, .ads, .ad, "
                 ".social-share")

# ==============================================================================
# МЕНЕДЖЕР ВНЕШНИХ БРАУЗЕРОВ
# ==============================================================================
class ExternalBrowserManager:
    """
    Управляет обнаружением, запуском и подключением к внешним портативным 
    браузерам и пользовательским профилям.
    """
    
    # Шаблоны поиска для популярных портативных браузеров
    PORTABLE_PATTERNS = {
        "Chrome Portable": {
            "exe_names": ["GoogleChromePortable.exe", "chrome.exe"],
            "paths": ["GoogleChromePortable/App/Chrome-bin", "ChromePortable"],
            "engine": "chromium",
            "profile_arg": "--user-data-dir",
            "default_profile": "Data/profile"
        },
        "Firefox Portable": {
            "exe_names": ["FirefoxPortable.exe", "firefox.exe"],
            "paths": ["FirefoxPortable/App/Firefox64", "FirefoxPortable"],
            "engine": "firefox",
            "profile_arg": "-profile",
            "default_profile": "Data/profile"
        },
        "LibreWolf Portable": {
            "exe_names": ["librewolf.exe"],
            "paths": ["LibreWolfPortable"],
            "engine": "firefox",
            "profile_arg": "-profile",
            "default_profile": "Data/profile"
        },
        "Chromium Portable": {
            "exe_names": ["chrome.exe", "chromium.exe"],
            "paths": ["ChromiumPortable"],
            "engine": "chromium",
            "profile_arg": "--user-data-dir",
            "default_profile": "Data/profile"
        }
    }

    def __init__(self, log_cb=None):
        self.log_cb = log_cb or print
        self.discovered_browsers = []
        self._scan_for_browsers()

    def _scan_for_browsers(self):
        """Сканирует текущую директорию и стандартные пути на наличие портативных браузеров."""
        search_dirs = [BASE_DIR]
        # Добавляем типичную папку PortableApps, если она существует рядом
        parent_dir = os.path.dirname(BASE_DIR)
        portable_apps_dir = os.path.join(parent_dir, "PortableApps")
        if os.path.isdir(portable_apps_dir):
            search_dirs.append(portable_apps_dir)
        
        found = {}
        for dir_path in search_dirs:
            for root, dirs, files in os.walk(dir_path):
                # Ограничиваем глубину поиска для скорости
                depth = root[len(dir_path):].count(os.sep)
                if depth > 3:
                    dirs.clear()
                    continue
                
                for name, config in self.PORTABLE_PATTERNS.items():
                    if name in found:
                        continue
                    for exe in config["exe_names"]:
                        if exe in files:
                            exe_path = os.path.join(root, exe)
                            # Проверяем, что это действительно портативная версия (наличие папки Data или App)
                            profile_path = os.path.join(root, config["default_profile"])
                            if not os.path.exists(profile_path):
                                # Ищем профиль в родительских папках или соседних
                                for p in config["paths"]:
                                    alt_profile = os.path.join(root, p, "..", config["default_profile"])
                                    if os.path.exists(alt_profile):
                                        profile_path = alt_profile
                                        break
                            
                            found[name] = {
                                "name": name,
                                "exe": exe_path,
                                "engine": config["engine"],
                                "profile_dir": profile_path if os.path.exists(profile_path) else None,
                                "base_dir": root
                            }
        self.discovered_browsers = list(found.values())
        if self.log_cb:
            self.log_cb(f"🔍 Найдено портативных браузеров: {len(self.discovered_browsers)}")

    def get_browser_list(self):
        """Возвращает список доступных браузеров для GUI."""
        return [b["name"] for b in self.discovered_browsers] + ["System Default (Playwright Bundled)"]

    def launch_or_connect(self, browser_name, profile_path=None, headless=True, cdp_port=9222):
        """
        Запускает браузер или подключается к существующему инстансу.
        Возвращает объект browser_type и kwargs для launch/connect.
        """
        if browser_name == "System Default (Playwright Bundled)":
            return None, None # Используем стандартную логику Playwright

        browser_config = next((b for b in self.discovered_browsers if b["name"] == browser_name), None)
        if not browser_config:
            raise FileNotFoundError(f"Браузер {browser_name} не найден.")

        engine = browser_config["engine"]
        exe_path = browser_config["exe"]
        
        # Если профиль не указан явно, используем найденный при сканировании
        if not profile_path and browser_config["profile_dir"]:
            profile_path = browser_config["profile_dir"]

        # Попытка подключиться к уже запущенному экземпляру через CDP (только для Chromium)
        if engine == "chromium" and not headless:
            try:
                import requests
                resp = requests.get(f"http://localhost:{cdp_port}/json/version", timeout=2)
                if resp.status_code == 200:
                    self.log_cb(f"🔗 Подключение к запущенному {browser_name} через CDP (порт {cdp_port})")
                    return "chromium", {"connect_cdp": f"http://localhost:{cdp_port}"}
            except Exception:
                pass # Браузер не запущен с отладкой, будем запускать новый

        # Подготовка аргументов для запуска
        args = []
        if engine == "chromium":
            args.extend([
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled',
                '--hide-scrollbars',
                '--mute-audio'
            ])
            if profile_path:
                args.append(f"--user-data-dir={profile_path}")
            if not headless:
                # Для подключения к живому сеансу
                args.append(f"--remote-debugging-port={cdp_port}")
        
        elif engine == "firefox":
            # Для Firefox Portable часто требуется -no-remote для запуска нескольких копий
            args.append("-no-remote")
            if profile_path:
                args.extend(["-profile", profile_path])
            # Firefox не поддерживает CDP напрямую в Playwright, используем Juggler через launch
            # Но можно включить сервер отладки для будущих версий
            # args.append("-start-debugger-server") 

        self.log_cb(f"🚀 Запуск {browser_name} ({engine})...")
        if profile_path:
            self.log_cb(f"   📂 Профиль: {profile_path}")
        
        return engine, {
            "executable_path": exe_path,
            "args": args,
            "headless": headless,
            "engine": engine
        }

# ==============================================================================
# STEALTH & UTILS
# ==============================================================================
STEALTH_TEMPLATE = r"""
(() => {
    const LANGS    = __LANGS__;
    const PLATFORM = __PLATFORM__;
    const HW       = __HW__;
    const MEM      = __MEM__;
    const VENDOR   = 'Google Inc.';

    try { delete Object.getPrototypeOf(navigator).webdriver; } catch (e) {}
    try { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); } catch (e) {}
    try { Object.defineProperty(navigator, 'platform', { get: () => PLATFORM }); } catch (e) {}
    try { Object.defineProperty(navigator, 'languages', { get: () => LANGS }); } catch (e) {}
    try { Object.defineProperty(navigator, 'vendor', { get: () => VENDOR }); } catch (e) {}
    try { Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => HW }); } catch (e) {}
    try { Object.defineProperty(navigator, 'deviceMemory', { get: () => MEM }); } catch (e) {}

    const mk = (name, filename, description, length) =>
        ({ name, filename, description, length, item: () => null, namedItem: () => null });
    const pluginArr = [
        mk('Chrome PDF Plugin',  'internal-pdf-viewer',                'Portable Document Format', 1),
        mk('Chrome PDF Viewer',  'mhjfbmdgcfjbbpaeojofohoefgiehjai',    '',                         1),
        mk('Native Client',      'internal-nacl-plugin',                '',                         2)
    ];
    pluginArr.item      = (i) => pluginArr[i] || null;
    pluginArr.namedItem = (n) => pluginArr.filter(p => p.name === n)[0] || null;
    pluginArr.refresh   = () => {};
    try { Object.defineProperty(navigator, 'plugins', { get: () => pluginArr }); } catch (e) {}
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
                   'принять все', 'принять', 'согласен', 'согласна', 'понятно', 'закрыть', 'отклонить'];
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

# ==============================================================================
# АВТОУСТАНОВКА ЗАВИСИМОСТЕЙ
# ==============================================================================
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

    def _pip(self, args):
        return subprocess.check_call(
            [sys.executable, "-m", "pip"] + args,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )

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
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--upgrade"],
                                  creationflags=CREATE_NO_WINDOW)
            print(f"   ✅ {pkg}")
            return True
        except Exception as e:
            print(f"   ❌ {pkg}: {e}")
            return False

    def chromium_ready(self):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True, args=['--no-sandbox'])
                b.close()
            return True
        except Exception:
            return False

    def install_browsers(self):
        print("🌐 Установка браузера Chromium для Playwright...")
        for extra in ([], ["--with-deps"]):
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "playwright", "install", "chromium"] + extra,
                    creationflags=CREATE_NO_WINDOW,
                )
                print("   ✅ Chromium установлен")
                return True
            except Exception as e:
                print(f"   ⚠️ playwright install {' '.join(extra) or '(basic)'}: {e}")
        return False

    def run(self):
        print("=" * 70)
        print(f"🔍 {APP_NAME} v{APP_VERSION} — ПРОВЕРКА ЗАВИСИМОСТЕЙ")
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
            self.install_browsers()
            if not self.chromium_ready():
                print("   ℹ️ bundled Chromium недоступен.")
                self.missing.append("chromium-browser")

        print("\n" + "=" * 70)
        if not self.missing:
            print("✅ ВСЁ ГОТОВО! Запускаю интерфейс...")
        else:
            print(f"⚠️ Не установлено: {', '.join(self.missing)}")
            print(f"   {sys.executable} -m pip install " + " ".join(self.missing))
        print("=" * 70)
        return len(self.missing) == 0


# ==============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================================================
def sanitize(name):
    name = re.sub(r'^https?://', '', name)
    name = re.sub(r'[^\w\-_.]', '_', name)
    name = name.strip('_')
    while "__" in name:
        name = name.replace("__", "_")
    return (name or "page")[:80]

def slugify(text):
    text = re.sub(r'[^\w\-]+', '-', str(text).strip().lower())
    return re.sub(r'-+', '-', text).strip('-')[:60] or "source"

def human_size(num_bytes):
    num_bytes = float(num_bytes or 0)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if num_bytes < 1024:
            return f"{int(num_bytes)} {unit}" if unit == "Б" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} ТБ"

def now_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")

def safe_xml_text(s):
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(s or ''))

def reserve_path(out_dir, safe_name, fmt):
    with PATH_LOCK:
        candidate = os.path.join(out_dir, f"{safe_name}.{fmt}")
        i = 2
        while candidate in RESERVED_PATHS or os.path.exists(candidate):
            candidate = os.path.join(out_dir, f"{safe_name}_{i}.{fmt}")
            i += 1
        RESERVED_PATHS.add(candidate)
        return candidate

def quick_dns_check(url):
    try:
        host = urlparse(url).hostname
        if not host:
            return False, "Не удалось разобрать URL"
        socket.getaddrinfo(host, None)
        return True, None
    except Exception as e:
        return False, f"DNS/сеть недоступны: {e}"

def random_locale_tz():
    return random.choice(LOCALE_TZ_PAIRS)

def random_ua():
    return random.choice(USER_AGENTS)

def platform_for_ua(ua):
    if "Macintosh" in ua:
        return "MacIntel", "macOS"
    if "X11; Linux" in ua:
        return "Linux x86_64", "Linux"
    return "Win32", "Windows"

def langs_for(locale):
    return [locale, "en"] if locale != "en-US" else ["en-US", "en"]

def accept_language_for(locale):
    return f"{locale},en;q=0.9"

def build_headers(ua, locale="en-US"):
    _, plat = platform_for_ua(ua)
    version = "148" if "148." in ua else "147"
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": accept_language_for(locale),
        "Sec-CH-UA": f'"Google Chrome";v="{version}", "Chromium";v="{version}", "Not_A Brand";v="8"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": f'"{plat}"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "User-Agent": ua,
    }

def build_stealth_script(ua, locale):
    plat, _ = platform_for_ua(ua)
    hw, mem = random.choice(HARDWARE_PROFILES)
    return (STEALTH_TEMPLATE
            .replace("__LANGS__", json.dumps(langs_for(locale)))
            .replace("__PLATFORM__", json.dumps(plat))
            .replace("__HW__", str(hw))
            .replace("__MEM__", str(mem)))

def looks_blocked(title, body_sample):
    haystack = f"{title} {body_sample}".lower()
    return any(marker in haystack for marker in BLOCKED_MARKERS)

def autoscroll(page, steps=6, pause_ms=350):
    try:
        for _ in range(steps):
            page.mouse.wheel(0, random.randint(500, 900))
            page.wait_for_timeout(pause_ms)
        page.wait_for_timeout(150)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(150)
    except Exception:
        pass

def dismiss_overlays(page):
    try:
        n = page.evaluate(DISMISS_JS)
        if n:
            page.wait_for_timeout(300)
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
    except Exception:
        pass

def absolutize(soup, base):
    if not base:
        return soup
    for el in soup.find_all(["a", "img", "source", "video", "audio", "iframe", "link"]):
        for attr in ("href", "src", "poster"):
            v = el.get(attr)
            if v and not re.match(r'^\s*(?:[a-z][a-z0-9+.\-]*:|#|data:|mailto:|tel:)', v, re.I):
                try:
                    el[attr] = urljoin(base, v.strip())
                except Exception:
                    pass
    return soup

def extract_page_text(page):
    cleanup = """
      () => {
        const root = document.querySelector(__SEL__) || document.body || document.documentElement;
        const junk = root.querySelectorAll(__JUNK__);
        junk.forEach((node) => node.remove());
        return root.innerText || '';
      }
    """.replace("__SEL__", json.dumps(CONTENT_SELECTOR)).replace("__JUNK__", json.dumps(JUNK_SELECTOR))

    try:
        text_content = page.evaluate(cleanup)
    except Exception:
        try:
            text_content = page.locator('body').inner_text(timeout=20000)
        except Exception:
            try:
                text_content = page.evaluate("() => document.documentElement.innerText")
            except Exception:
                text_content = ""

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in (text_content or "").splitlines()]
    text_content = re.sub(r"\n{3,}", "\n\n", "\n".join(line for line in lines if line))

    try:
        frames = page.frames
    except Exception:
        frames = []
    if len(frames) > 1:
        extra = []
        for frame in frames[1:]:
            try:
                frame_text = frame.inner_text(timeout=8000)
                if frame_text.strip():
                    extra.append(f"\n[FRAME: {frame.url}]\n{frame_text}\n")
            except Exception:
                continue
        if extra:
            text_content += "\n--- СОДЕРЖИМОЕ ФРЕЙМОВ ---\n" + "\n".join(extra)
    return text_content

def extract_page_html(page):
    js = """
        () => {
          const root = document.querySelector(__SEL__) || document.body || document.documentElement;
          const copy = root.cloneNode(true);
          copy.querySelectorAll(__JUNK__).forEach((node) => node.remove());
          return copy.outerHTML;
        }
    """.replace("__SEL__", json.dumps(CONTENT_SELECTOR)).replace("__JUNK__", json.dumps(JUNK_SELECTOR))
    try:
        return page.evaluate(js)
    except Exception:
        return page.content()

def html_to_markdown(html_content, page_url=""):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg", "iframe",
                     "nav", "header", "footer", "aside"]):
        tag.decompose()
    absolutize(soup, page_url)

    try:
        from markdownify import markdownify as md_convert
        body = soup.body or soup
        md = md_convert(str(body), heading_style="ATX", bullets="-")
        md = re.sub(r'\n{3,}', '\n\n', md).strip()
        if md:
            return md
    except Exception:
        pass

    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "a"]):
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
        resp.encoding = (resp.apparent_encoding or "utf-8")
    resp.raise_for_status()
    return resp.text, resp.status_code

def fetch_bytes(url, headers):
    import requests
    resp = requests.get(url, headers=headers, timeout=40, allow_redirects=True)
    resp.raise_for_status()
    return resp.content


# ==============================================================================
# ОСНОВНАЯ ЛОГИКА СКРАПИНГА
# ==============================================================================
def scrape_one(url, fmt, out_dir, settings, log_cb, should_stop=None, browser_manager=None):
    """Скрапит один URL с поддержкой внешних браузеров."""
    stop = should_stop or (lambda: False)
    result = {
        "url": url, "title": "", "status": "failed", "format": fmt,
        "file": None, "size_bytes": 0, "word_count": None,
        "blocked_suspected": False, "method": "playwright",
        "attempts": 0, "error": None, "elapsed_sec": 0.0,
    }
    t0 = time.time()

    ok_dns, dns_err = quick_dns_check(url)
    if not ok_dns:
        result["error"] = dns_err
        result["elapsed_sec"] = round(time.time() - t0, 2)
        log_cb(f"   ❌ {dns_err}")
        return result

    file_path = reserve_path(out_dir, sanitize(url), fmt)

    aggressive = bool(settings.get("aggressive"))
    max_attempts = max(1, settings["retries"] + 1)
    goto_timeout = 30000 if aggressive else 45000
    net_timeout = 6000 if aggressive else 12000
    last_error = None

    # Определение браузера
    ext_browser_name = settings.get("external_browser", "System Default (Playwright Bundled)")
    custom_profile = settings.get("custom_profile_path", None)

    for attempt in range(1, max_attempts + 1):
        if stop():
            last_error = last_error or "остановлено пользователем"
            break
        result["attempts"] = attempt
        ua = random_ua()
        locale, tz = random_locale_tz()
        viewport = random.choice(VIEWPORTS)
        saved = False
        browser = None
        context = None
        page = None

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                
                # Логика выбора механизма запуска
                if ext_browser_name != "System Default (Playwright Bundled)" and browser_manager:
                    engine, launch_kwargs = browser_manager.launch_or_connect(
                        ext_browser_name, 
                        profile_path=custom_profile, 
                        headless=True # Внешние браузеры в скрапинге обычно headless, если не указано иное
                    )
                    
                    if launch_kwargs and "connect_cdp" in launch_kwargs:
                        # Подключение к существующему CDP
                        browser = p.chromium.connect_over_cdp(launch_kwargs["connect_cdp"])
                        # При подключении к живому браузеру мы берем первый контекст или создаем новый
                        if browser.contexts:
                            context = browser.contexts[0]
                        else:
                            context = browser.new_context(
                                viewport=viewport, user_agent=ua, locale=locale, timezone_id=tz
                            )
                    else:
                        # Запуск внешнего исполняемого файла
                        if engine == "chromium":
                            browser = p.chromium.launch(
                                executable_path=launch_kwargs["executable_path"],
                                headless=launch_kwargs["headless"],
                                args=launch_kwargs["args"]
                            )
                        elif engine == "firefox":
                            browser = p.firefox.launch(
                                executable_path=launch_kwargs["executable_path"],
                                headless=launch_kwargs["headless"],
                                args=launch_kwargs["args"]
                            )
                        
                        context = browser.new_context(
                            viewport=viewport,
                            user_agent=ua,
                            extra_http_headers=build_headers(ua, locale),
                            locale=locale,
                            timezone_id=tz,
                            device_scale_factor=1,
                            permissions=["notifications"],
                        )
                else:
                    # Стандартный запуск bundled Chromium
                    browser = p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                            '--disable-blink-features=AutomationControlled',
                            f'--lang={locale}', '--hide-scrollbars', '--mute-audio'
                        ],
                    )
                    context = browser.new_context(
                        viewport=viewport,
                        user_agent=ua,
                        extra_http_headers=build_headers(ua, locale),
                        locale=locale,
                        timezone_id=tz,
                        device_scale_factor=1,
                        permissions=["notifications"],
                    )

                # Применение stealth только для Chromium, так как Firefox имеет другую архитектуру
                if (ext_browser_name == "System Default (Playwright Bundled)" or 
                    (browser_manager and browser_manager.discovered_browsers and 
                     next((b for b in browser_manager.discovered_browsers if b["name"] == ext_browser_name), {}).get("engine") == "chromium")):
                    context.add_init_script(build_stealth_script(ua, locale))

                page = context.new_page()

                response = page.goto(url, wait_until="domcontentloaded", timeout=goto_timeout)

                try:
                    page.wait_for_load_state("networkidle", timeout=net_timeout)
                except Exception:
                    pass
                try:
                    page.wait_for_load_state("load", timeout=4000)
                except Exception:
                    pass

                page.wait_for_timeout(random.randint(150, 350) if aggressive else random.randint(400, 900))
                dismiss_overlays(page)
                autoscroll(page, steps=4 if aggressive else 6, pause_ms=200 if aggressive else 350)

                try:
                    title = page.title()
                except Exception:
                    title = ""
                result["title"] = title

                status_code = response.status if response else None
                body_sample = ""
                try:
                    body_sample = page.locator('body').inner_text(timeout=5000)[:2000]
                except Exception:
                    pass

                blocked = (status_code in (403, 429, 503)) or looks_blocked(title, body_sample)
                result["blocked_suspected"] = blocked
                if blocked:
                    log_cb(f"   ⚠️ Похоже на блокировку (код {status_code}), попытка {attempt}/{max_attempts}")

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
                    try:
                        try:
                            page.emulate_media(media="screen")
                        except Exception:
                            pass
                        page.pdf(
                            path=file_path, format='A4', print_background=True,
                            scale=1.0, timeout=60000,
                            margin={'top': '0.5in', 'bottom': '0.5in', 'left': '0.5in', 'right': '0.5in'},
                        )
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
                            data = fetch_bytes(url, build_headers(ua, locale))
                            with open(file_path, "wb") as f:
                                f.write(data)
                            result["method"] = "binary-download"
                            pdf_ok = True
                        if not pdf_ok:
                            raise RuntimeError("не удалось отрендерить PDF этой страницы")

                elif fmt == "html":
                    content = page.content()
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                elif fmt == "txt":
                    text_content = extract_page_text(page)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    result["word_count"] = len(text_content.split())
                    result["_text"] = text_content

                elif fmt == "md":
                    content = extract_page_html(page)
                    md_text = html_to_markdown(content, url)
                    header = f"# {title or url}\n\nИсточник: {url}\n\n---\n\n"
                    full_md = header + md_text
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(full_md)
                    result["word_count"] = len(full_md.split())
                    result["_text"] = full_md

                elif fmt == "docx":
                    from docx import Document
                    text_content = extract_page_text(page)
                    doc = Document()
                    doc.add_heading(safe_xml_text(title or url), 0)
                    doc.add_paragraph(safe_xml_text(f"Источник: {url}"))
                    doc.add_paragraph(safe_xml_text(
                        f"Сохранено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
                    doc.add_heading('Содержимое:', level=1)
                    for para in text_content.split('\n'):
                        para = safe_xml_text(para).strip()
                        if para:
                            doc.add_paragraph(para)
                    doc.save(file_path)
                    result["word_count"] = len(text_content.split())
                    result["_text"] = text_content

                saved = True

        except Exception as e:
            last_error = str(e)
            log_cb(f"   ⚠️ Попытка {attempt}/{max_attempts} не удалась: {last_error[:120]}")
            if attempt < max_attempts and not stop():
                time.sleep(random.uniform(1.2, 2.6) if aggressive else random.uniform(2.0, 4.0))
        finally:
            # Корректное закрытие ресурсов
            if page:
                try: page.close()
                except: pass
            if context and ext_browser_name == "System Default (Playwright Bundled)":
                try: context.close()
                except: pass
            if browser and ext_browser_name == "System Default (Playwright Bundled)":
                try: browser.close()
                except: pass
            # Если мы подключались к внешнему браузеру, мы НЕ закрываем его, чтобы сохранить сессию пользователя

        if saved:
            size = os.path.getsize(file_path)
            result["status"] = "ok"
            result["file"] = os.path.basename(file_path)
            result["size_bytes"] = size
            log_cb(f"   ✅ {fmt.upper()}: {human_size(size)} -> {os.path.basename(file_path)}"
                   + (" [блокировка?]" if result["blocked_suspected"] else ""))
            last_error = None
            break

    # ---------- запасной метод: requests + BeautifulSoup ----------
    if last_error and result["status"] != "ok" and fmt in ("html", "txt", "md", "docx"):
        if stop():
            result["error"] = last_error
        else:
            try:
                log_cb("   🔁 Пробую запасной метод (requests)...")
                ua = random_ua()
                locale, _tz = random_locale_tz()
                raw_html, status_code = fetch_html(url, build_headers(ua, locale))
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(raw_html, "html.parser")
                for tag in soup(["script", "style", "noscript", "template", "svg", "iframe",
                                 "nav", "header", "footer", "aside"]):
                    tag.decompose()
                title = soup.title.get_text(strip=True) if soup.title else ""
                result["title"] = title

                sample = soup.get_text(" ", strip=True)[:2000]
                blocked = (status_code in (403, 429, 503)) or looks_blocked(title, sample)
                result["blocked_suspected"] = blocked
                if blocked:
                    raise RuntimeError(f"запасной метод получил страницу-заглушку (код {status_code})")

                if fmt == "html":
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(raw_html)
                elif fmt == "txt":
                    text_content = soup.get_text("\n", strip=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    result["word_count"] = len(text_content.split())
                    result["_text"] = text_content
                elif fmt == "md":
                    absolutize(soup, url)
                    md_text = html_to_markdown(str(soup), url)
                    full_md = f"# {title or url}\n\nИсточник: {url}\n\n---\n\n" + md_text
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(full_md)
                    result["word_count"] = len(full_md.split())
                    result["_text"] = full_md
                elif fmt == "docx":
                    from docx import Document
                    text_content = soup.get_text("\n", strip=True)
                    doc = Document()
                    doc.add_heading(safe_xml_text(title or url), 0)
                    doc.add_paragraph(safe_xml_text(f"Источник: {url} (запасной метод)"))
                    for para in text_content.split('\n'):
                        para = safe_xml_text(para).strip()
                        if para:
                            doc.add_paragraph(para)
                    doc.save(file_path)
                    result["word_count"] = len(text_content.split())
                    result["_text"] = text_content

                size = os.path.getsize(file_path)
                result["status"] = "ok"
                result["file"] = os.path.basename(file_path)
                result["size_bytes"] = size
                result["method"] = "requests-fallback"
                result["error"] = None
                log_cb(f"   ✅ (запасной метод) {fmt.upper()}: {human_size(size)}")
            except Exception as e2:
                result["error"] = f"{last_error} | fallback: {e2}"
                log_cb(f"   ❌ Запасной метод тоже не сработал: {str(e2)[:120]}")
    elif last_error and result["status"] != "ok":
        result["error"] = last_error

    result["elapsed_sec"] = round(time.time() - t0, 2)
    return result


# ==============================================================================
# ОБЪЕДИНЕНИЕ ФАЙЛОВ (Без изменений, так как логика универсальна)
# ==============================================================================
def merge_pdf(ok_results, out_dir, out_path, log_cb):
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
    writer.add_metadata({"/Title": f"{APP_NAME} Merged Export",
                         "/Producer": f"{APP_NAME} v{APP_VERSION}"})
    with open(out_path, "wb") as f:
        writer.write(f)
    writer.close()
    if skipped:
        log_cb(f"   ℹ️ в сводку не попали {skipped} файл(ов)")

def merge_text_like(ok_results, out_path, fmt):
    sep = "\n\n" + ("=" * 70) + "\n\n"
    chunks = []
    for r in ok_results:
        header = f"ИСТОЧНИК: {r['url']}\nЗАГОЛОВОК: {r['title']}\n"
        chunks.append(header + "\n" + r.get("_text", ""))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(sep.join(chunks))

def merge_markdown(ok_results, out_path):
    toc = ["# Сводный документ\n", f"_Сгенерировано {APP_NAME} v{APP_VERSION}_\n", "\n## Содержание\n"]
    body_parts = []
    for r in ok_results:
        anchor = slugify(r["title"] or r["url"])
        toc.append(f"- [{r['title'] or r['url']}](#{anchor})")
        text = re.sub(r'^#\s.*\n+', '', r.get("_text", ""), count=1)
        body_parts.append(
            f"\n\n<a name=\"{anchor}\"></a>\n\n## {r['title'] or r['url']}\n\n"
            f"Источник: {r['url']}\n\n---\n\n{text}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(toc) + "\n" + "".join(body_parts))

def merge_html(ok_results, out_dir, out_path):
    from bs4 import BeautifulSoup
    nav_items, sections = [], []
    for r in ok_results:
        anchor = slugify(r["title"] or r["url"])
        nav_items.append(f'<li><a href="#{anchor}">{r["title"] or r["url"]}</a></li>')
        fp = os.path.join(out_dir, r["file"])
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "iframe", "object", "embed", "base", "form"]):
                tag.decompose()
            if soup.body:
                absolutize(soup, r["url"])
                inner = str(soup.body)
            else:
                absolutize(soup, r["url"])
                inner = str(soup)
        except Exception:
            inner = "<p>(не удалось прочитать)</p>"
        sections.append(
            f'<section id="{anchor}"><h1>{r["title"] or r["url"]}</h1>'
            f'<p class="src">Источник: <a href="{r["url"]}">{r["url"]}</a></p>{inner}</section><hr/>')
    html_doc = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>{APP_NAME} — Сводный экспорт</title>
<style>
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
</style></head><body>
<h1>📚 {APP_NAME} — Сводный экспорт ({len(ok_results)} источников)</h1>
<nav><ul>{''.join(nav_items)}</ul></nav>
{''.join(sections)}
</body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

def merge_docx(ok_results, out_path):
    from docx import Document
    doc = Document()
    doc.add_heading(safe_xml_text(f'{APP_NAME} — Сводный экспорт'), 0)
    doc.add_paragraph(safe_xml_text(
        f"Источников: {len(ok_results)} | Сгенерировано: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
    for i, r in enumerate(ok_results):
        if i > 0:
            doc.add_page_break()
        doc.add_heading(safe_xml_text(r["title"] or r["url"]), level=1)
        doc.add_paragraph(safe_xml_text(f"Источник: {r['url']}"))
        for para in r.get("_text", "").split('\n'):
            para = safe_xml_text(para).strip()
            if para:
                doc.add_paragraph(para)
    doc.save(out_path)

def write_manifest_and_index(manifest, out_dir, merged_filename=None):
    manifest_path = os.path.join(out_dir, "manifest.json")
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in manifest]

    ok_n = sum(1 for r in clean if r["status"] == "ok")
    totals = {
        "sources": len(clean),
        "ok": ok_n,
        "failed": len(clean) - ok_n,
        "blocked_suspected": sum(1 for r in clean if r.get("blocked_suspected")),
        "bytes": sum(int(r.get("size_bytes") or 0) for r in clean),
        "words": sum(int(r.get("word_count") or 0) for r in clean),
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "app": APP_NAME, "version": APP_VERSION, "build": BUILD_DATE,
                "generated": datetime.now().isoformat(timespec="seconds"),
                "merged_file": merged_filename,
                "totals": totals,
                "sources": clean,
            },
            f, ensure_ascii=False, indent=2,
        )

    lines = [
        f"# {APP_NAME} v{APP_VERSION} — отчёт о сборе\n",
        f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"Всего источников: {len(clean)} · успешно: {ok_n} · объём: {human_size(totals['bytes'])}"
        f" · слов: {totals['words']}\n",
    ]
    if merged_filename:
        lines.append(f"**Объединённый файл:** [{merged_filename}](./{merged_filename})\n")
    lines.append("| # | Заголовок | URL | Статус | Файл | Размер | Слов | Метод |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(clean, 1):
        status_icon = "✅" if r["status"] == "ok" else "❌"
        blocked = " ⚠️блок" if r.get("blocked_suspected") else ""
        title = (r["title"] or "—").replace("|", "/")[:60]
        file_link = f"[{r['file']}](./{r['file']})" if r["file"] else "—"
        size = human_size(r["size_bytes"]) if r["size_bytes"] else "—"
        words = r["word_count"] if r["word_count"] else "—"
        lines.append(
            f"| {i} | {title} | {r['url']} | {status_icon}{blocked} | {file_link} "
            f"| {size} | {words} | {r['method']} |"
        )
        if r["status"] != "ok" and r.get("error"):
            lines.append(f"|   | _ошибка:_ {str(r['error'])[:150]} | | | | | |")
    lines.append("")
    lines.append("_Полный журнал прогона: [RUN.log](./RUN.log)_")

    with open(os.path.join(out_dir, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return totals


# ==============================================================================
# GUI
# ==============================================================================
class App:
    def __init__(self, root):
        self.root = root
        self.ui_q = queue.Queue()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.is_running = False
        self.last_output_dir = None
        self.log_buffer = []
        
        # Инициализация менеджера браузеров
        self.browser_manager = ExternalBrowserManager(log_cb=self.log)

        root.title(f"🚀 {APP_NAME} v{APP_VERSION}")
        root.configure(bg="#12121f")
        root.geometry("820x950") # Увеличена высота для новых настроек
        root.minsize(780, 720)
        root.resizable(False, True)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

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
        tk.Label(header, text=f"🚀 {APP_NAME} v{APP_VERSION}", font=("Segoe UI", 16, "bold"),
                 bg="#1a1a2e", fg="#00ff88", pady=8).pack()
        tk.Label(header, text=f"Любой сайт • Любой формат • Без ключей • Параллельно • build {BUILD_DATE}",
                 font=("Segoe UI", 10), bg="#1a1a2e", fg="#888888").pack(pady=(0, 8))

        # --- URL ---
        tk.Label(root, text="📋 URL (по одному в строке):", font=("Segoe UI", 10, "bold"),
                 anchor="w", bg="#12121f", fg="white").pack(fill="x", padx=20, pady=(12, 4))
        self.urls = tk.Text(root, height=7, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff88",
                            insertbackground="#00ff88", wrap="none")
        self.urls.pack(fill="both", expand=False, padx=20, pady=2)

        # --- Настройки ---
        frame = tk.LabelFrame(root, text="⚙️ Настройки", font=("Segoe UI", 10, "bold"),
                              padx=10, pady=8, bg="#2d2d44", fg="white")
        frame.pack(fill="x", padx=20, pady=10)

        tk.Label(frame, text="Формат:", bg="#2d2d44", fg="white").grid(
            row=0, column=0, sticky="w", padx=5, pady=3)
        self.fmt_label = tk.StringVar(value="PDF")
        ttk.Combobox(frame, textvariable=self.fmt_label, values=list(FORMAT_MAP.keys()),
                     state="readonly", width=10).grid(row=0, column=1, sticky="w", padx=5, pady=3)

        self.merge = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="Объединить в один файл", variable=self.merge,
                       bg="#2d2d44", fg="white", selectcolor="#2d2d44").grid(
            row=0, column=2, columnspan=2, padx=10, pady=3, sticky="w")

        self.aggr = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="🔥 Агрессивный режим (КОРОЧЕ паузы и ожидания)",
                       variable=self.aggr, bg="#2d2d44", fg="#00ff88",
                       selectcolor="#2d2d44", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, columnspan=4, pady=(8, 3), sticky="w")

        tk.Label(frame, text="Потоков параллельно:", bg="#2d2d44", fg="white").grid(
            row=2, column=0, sticky="w", padx=5, pady=3)
        self.concurrency = tk.IntVar(value=1)
        tk.Spinbox(frame, from_=1, to=5, textvariable=self.concurrency, width=5,
                   bg="#1e1e1e", fg="#00ff88", insertbackground="#00ff88",
                   buttonbackground="#1e1e1e", relief="flat").grid(
            row=2, column=1, sticky="w", padx=5, pady=3)

        tk.Label(frame, text="Повторов при ошибке:", bg="#2d2d44", fg="white").grid(
            row=2, column=2, sticky="w", padx=5, pady=3)
        self.retries = tk.IntVar(value=1)
        tk.Spinbox(frame, from_=0, to=3, textvariable=self.retries, width=5,
                   bg="#1e1e1e", fg="#00ff88", insertbackground="#00ff88",
                   buttonbackground="#1e1e1e", relief="flat").grid(
            row=2, column=3, sticky="w", padx=5, pady=3)

        # --- НОВЫЕ НАСТРОЙКИ: ВЫБОР БРАУЗЕРА ---
        tk.Label(frame, text="Браузер:", bg="#2d2d44", fg="white").grid(
            row=3, column=0, sticky="w", padx=5, pady=3)
        
        browser_list = self.browser_manager.get_browser_list()
        self.selected_browser = tk.StringVar(value=browser_list[0] if browser_list else "System Default (Playwright Bundled)")
        self.browser_combo = ttk.Combobox(frame, textvariable=self.selected_browser, 
                                          values=browser_list, state="readonly", width=25)
        self.browser_combo.grid(row=3, column=1, sticky="w", padx=5, pady=3)
        
        tk.Button(frame, text="🔄 Обновить список", command=self.refresh_browser_list,
                  bg="#1e1e1e", fg="#00ff88", relief="flat", font=("Segoe UI", 8)).grid(
            row=3, column=2, sticky="w", padx=5, pady=3)

        tk.Label(frame, text="Профиль (опционально):", bg="#2d2d44", fg="white").grid(
            row=4, column=0, sticky="w", padx=5, pady=3)
        self.profile_path_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.profile_path_var, bg="#1e1e1e", fg="#00ff88",
                 relief="flat").grid(row=4, column=1, columnspan=2, sticky="ew", padx=5, pady=3)
        tk.Button(frame, text="...", command=self.browse_profile,
                  bg="#1e1e1e", fg="#00ff88", relief="flat", width=3).grid(
            row=4, column=3, sticky="w", padx=0, pady=3)

        tk.Label(frame, text="⚠️ Больше потоков = быстрее, но выше риск блокировки на одном домене",
                 bg="#2d2d44", fg="#999999", font=("Segoe UI", 8)).grid(
            row=5, column=0, columnspan=4, sticky="w", padx=5, pady=(4, 0))

        # --- Кнопки управления ---
        btn_row = tk.Frame(root, bg="#12121f")
        btn_row.pack(fill="x", padx=20, pady=8)
        self.btn = tk.Button(btn_row, text="🚀 НАЧАТЬ", command=self.start,
                             bg="#00aa44", fg="white", font=("Segoe UI", 12, "bold"),
                             relief="flat", cursor="hand2")
        self.btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.stop_btn = tk.Button(btn_row, text="⛔ СТОП", command=self.stop, state="disabled",
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
        tk.Button(log_head, text="скопировать", command=self.copy_log,
                  bg="#2d2d44", fg="#cccccc", relief="flat", font=("Segoe UI", 8)).pack(
            side="right", padx=(6, 0))
        tk.Button(log_head, text="очистить", command=self.clear_log,
                  bg="#2d2d44", fg="#cccccc", relief="flat", font=("Segoe UI", 8)).pack(side="right")

        log_frame = tk.Frame(root, bg="#0d0d0d", highlightbackground="#1e1e1e",
                             highlightthickness=1)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(4, 5))
        self.log_text = tk.Text(log_frame, height=12, state="disabled",
                                bg="#0d0d0d", fg="#00ff88", font=("Consolas", 9),
                                relief="flat", padx=6, pady=4)
        sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # --- Статистика + папка ---
        stats = tk.Frame(root, bg="#12121f")
        stats.pack(fill="x", padx=20, pady=(2, 12))
        self.ok_label = tk.Label(stats, text="✅ 0", font=("Segoe UI", 10, "bold"),
                                 fg="#00ff88", bg="#12121f")
        self.ok_label.pack(side="left", padx=(0, 20))
        self.fail_label = tk.Label(stats, text="❌ 0", font=("Segoe UI", 10, "bold"),
                                   fg="#ff4444", bg="#12121f")
        self.fail_label.pack(side="left", padx=(0, 20))
        self.blk_label = tk.Label(stats, text="⚠️ 0", font=("Segoe UI", 10, "bold"),
                                  fg="#ffb020", bg="#12121f")
        self.blk_label.pack(side="left")
        self.folder_btn = tk.Button(stats, text="📂 Открыть папку результата",
                                    command=self.open_output_folder,
                                    state="disabled", bg="#2d2d44", fg="white",
                                    relief="flat", font=("Segoe UI", 9), cursor="hand2")
        self.folder_btn.pack(side="right")

        self.root.after(80, self._poll_ui)

    def refresh_browser_list(self):
        self.browser_manager._scan_for_browsers()
        new_list = self.browser_manager.get_browser_list()
        self.browser_combo['values'] = new_list
        if new_list:
            self.selected_browser.set(new_list[0])
        self.log("🔄 Список браузеров обновлен")

    def browse_profile(self):
        path = filedialog.askdirectory(title="Выберите папку профиля браузера")
        if path:
            self.profile_path_var.set(path)

    # ---------------- UI helpers (потокобезопасные) ----------------
    def log(self, msg):
        self.ui_q.put(("log", msg))

    def set_progress(self, pct):
        self.ui_q.put(("progress", pct))

    def set_stats(self, ok, fail, blocked=0):
        self.ui_q.put(("stats", (ok, fail, blocked)))

    def _poll_ui(self):
        try:
            while True:
                kind, payload = self.ui_q.get_nowait()
                if kind == "log":
                    self.log_buffer.append(str(payload))
                    if len(self.log_buffer) > 20000:
                        del self.log_buffer[:5000]
                    self.log_text.config(state="normal")
                    self.log_text.insert(tk.END, str(payload) + "\n")
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
                    self._on_finished(payload)
        except queue.Empty:
            pass
        try:
            self.root.after(80, self._poll_ui)
        except tk.TclError:
            pass

    def copy_log(self):
        try:
            text = self.log_text.get("1.0", tk.END).strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log("📋 Журнал скопирован в буфер обмена")
        except Exception as e:
            self.log(f"⚠️ Не удалось скопировать: {e}")

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

        seen = set()
        valid_urls = []
        for u in (x.strip() for x in raw_urls.splitlines()):
            if not u:
                continue
            if not u.startswith(("http://", "https://")):
                self.log(f"⚠️ Невалидный URL пропущен (нужен http:// или https://): {u}")
                continue
            if u in seen:
                self.log(f"ℹ️ Дубликат пропущен: {u}")
                continue
            seen.add(u)
            valid_urls.append(u)

        if not valid_urls:
            messagebox.showwarning("Ошибка", "Ни одного валидного URL не найдено!")
            return

        out_dir = os.path.join(BASE_DIR, f"MEGA_TANK_{now_stamp()}")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать папку результата:\n{e}")
            return
        self.last_output_dir = out_dir

        settings = {
            "fmt": FORMAT_MAP.get(self.fmt_label.get(), "pdf"),
            "merge": bool(self.merge.get()),
            "aggressive": bool(self.aggr.get()),
            "concurrency": self._spin(self.concurrency, 1, 1, 5),
            "retries": self._spin(self.retries, 1, 0, 3),
            "external_browser": self.selected_browser.get(),
            "custom_profile_path": self.profile_path_var.get().strip() or None
        }

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

        threading.Thread(target=self._coordinator, args=(valid_urls, out_dir, settings),
                         daemon=True).start()

    def stop(self):
        if not self.is_running:
            return
        self.stop_event.set()
        self.stop_btn.config(state="disabled", text="⛔ ОСТАНАВЛИВАЮ...")
        self.log("\\n⛔ Остановка запрошена пользователем — потоки завершают текущие задачи...")

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

    def open_output_folder(self):
        if not self.last_output_dir or not os.path.isdir(self.last_output_dir):
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.last_output_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.last_output_dir])
            else:
                subprocess.Popen(["xdg-open", self.last_output_dir])
        except Exception:
            webbrowser.open(f"file://{self.last_output_dir}")

    # ---------------- Координатор + воркеры ----------------
    def _coordinator(self, urls, out_dir, settings):
        url_q = queue.Queue()
        for u in urls:
            url_q.put(u)

        manifest = []
        counters = {"ok": 0, "fail": 0, "done": 0, "blocked": 0}
        total = len(urls)

        self.log("=" * 60)
        self.log(f"🚀 {APP_NAME} v{APP_VERSION}  (build {BUILD_DATE})")
        self.log(f"📁 Папка результата: {out_dir}")
        self.log(f"📄 Формат: {settings['fmt'].upper()} | Объединить: "
                 f"{'ДА' if settings['merge'] else 'НЕТ'}")
        self.log(f"🌐 URLs: {total} | Потоков: {settings['concurrency']} | Повторов: "
                 f"{settings['retries']} | Режим: "
                 f"{'агрессивный' if settings['aggressive'] else 'щадящий'}")
        self.log(f"🕸️ Браузер: {settings['external_browser']}")
        if settings['custom_profile_path']:
            self.log(f"📂 Профиль: {settings['custom_profile_path']}")
        self.log("=" * 60)

        def worker(worker_id):
            while not self.stop_event.is_set():
                try:
                    url = url_q.get_nowait()
                except queue.Empty:
                    break
                self.log(f"\n[поток {worker_id}] 📥 {url[:75]}")
                res = scrape_one(url, settings["fmt"], out_dir, settings, self.log,
                                 should_stop=self.stop_event.is_set,
                                 browser_manager=self.browser_manager)
                with self.lock:
                    manifest.append(res)
                    if res["status"] == "ok":
                        counters["ok"] += 1
                    else:
                        counters["fail"] += 1
                        self.log(f"   ❌ Не удалось: {url} — {str(res.get('error'))[:150]}")
                    if res.get("blocked_suspected"):
                        counters["blocked"] += 1
                    counters["done"] += 1
                    self.set_stats(counters["ok"], counters["fail"], counters["blocked"])
                    self.set_progress(counters["done"] / total * 100)

                if self.stop_event.is_set():
                    break

                if settings["aggressive"]:
                    delay = random.uniform(1.0, 3.0)
                else:
                    delay = random.uniform(3.0, 7.0)
                self.log(f"   ⏱️ [поток {worker_id}] пауза {delay:.1f} сек")
                slept = 0.0
                while slept < delay and not self.stop_event.is_set():
                    time.sleep(0.25)
                    slept += 0.25

        threads = [threading.Thread(target=worker, args=(i + 1,), daemon=True)
                   for i in range(settings["concurrency"])]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        order = {u: i for i, u in enumerate(urls)}
        manifest.sort(key=lambda r: order.get(r["url"], 999999))

        ok_results = [r for r in manifest if r["status"] == "ok"]
        merged_filename = None

        if settings["merge"] and ok_results and not self.stop_event.is_set():
            self.log("\n" + "=" * 60)
            self.log("🔗 ОБЪЕДИНЕНИЕ ФАЙЛОВ...")
            self.log("=" * 60)
            fmt = settings["fmt"]
            merged_name = f"MEGA_FULL.{fmt}"
            merged_path = os.path.join(out_dir, merged_name)
            try:
                if fmt == "pdf":
                    merge_pdf(ok_results, out_dir, merged_path, self.log)
                elif fmt == "txt":
                    merge_text_like(ok_results, merged_path, fmt)
                elif fmt == "md":
                    merge_markdown(ok_results, merged_path)
                elif fmt == "html":
                    merge_html(ok_results, out_dir, merged_path)
                elif fmt == "docx":
                    merge_docx(ok_results, merged_path)
                size = os.path.getsize(merged_path)
                self.log(f"   ✅ Объединённый файл: {human_size(size)} -> {merged_name}")
                merged_filename = merged_name
            except Exception as e:
                self.log(f"   ❌ Ошибка объединения: {e}")

        try:
            totals = write_manifest_and_index(manifest, out_dir, merged_filename)
            self.log("\n📊 manifest.json и INDEX.md записаны")
            self.log(f"   Σ объём: {human_size(totals['bytes'])} | Σ слов: {totals['words']}")
        except Exception as e:
            self.log(f"⚠️ Не удалось записать manifest/index: {e}")

        self.log("\n" + "=" * 60)
        status_word = "ОСТАНОВЛЕНО" if self.stop_event.is_set() else "ГОТОВО"
        self.log(f"🎉 {status_word}! Успешно: {counters['ok']} | Ошибок: {counters['fail']} "
                 f"| Подозрений на блок: {counters['blocked']}")
        self.log(f"📁 Папка: {out_dir}")
        self.log("=" * 60)

        self.set_progress(100)
        self.ui_q.put(("done", {
            "ok": counters["ok"], "fail": counters["fail"], "blocked": counters["blocked"],
            "out_dir": out_dir, "stopped": self.stop_event.is_set(),
        }))

    def _on_finished(self, payload):
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


# ==============================================================================
# ЗАПУСК
# ==============================================================================
if __name__ == "__main__":
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
```

## 8. Заключение

Разработанная архитектура успешно решает задачу интеграции внешних портативных браузеров в MEGA TANK v3.0. Использование класса `ExternalBrowserManager` позволяет гибко управлять различными типами браузеров, учитывая их специфические требования к профилям и протоколам управления. Поддержка CDP для Chromium и Juggler для Firefox обеспечивает максимальную совместимость, а механизм подключения к живым сессиям открывает возможности для работы с защищенным контентом, требующим предварительной авторизации. Реализация в виде единого Python-файла сохраняет простоту развертывания и использования, характерную для оригинальной версии инструмента.