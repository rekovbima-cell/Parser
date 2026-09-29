#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import threading
import time
import random
import re
import json
import socket
import platform
from datetime import datetime, timedelta
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
except: pass

GMAIL_EMAIL = "malkodiro@gmail.com"
GMAIL_PASSWORD = "Linakolada!11O"
FIREFOX_PATH = os.path.join(BASE_DIR, "BROWSER", "FirefoxPortable", "FirefoxPortable.exe")
PROFILE_DIR = os.path.join(BASE_DIR, "BROWSER", "firefox_profile")

SUPPORTED_FORMATS = ["txt", "html", "md", "docx"]
BLOCKED_MARKERS = ["cloudflare", "checking your browser", "access denied", "captcha", "403"]
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"]

def sanitize_filename(name):
    name = re.sub(r'^https?://', '', name)
    name = re.sub(r'[^\w\-_.\s]', '_', name)
    return (name or "page")[:100]

def human_size(b):
    for u in ["B","KB","MB","GB"]:
        if b < 1024: return f"{b:.1f} {u}" if u != "B" else f"{int(b)} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def normalize_url(url):
    url = url.strip().replace(" ", "")
    if url.startswith(("http://", "https://")): return url
    if url.startswith("//"): return "https:" + url
    return "https://" + url

def validate_url(url):
    try:
        p = urlparse(url)
        return bool(p.scheme and p.netloc)
    except: return False

def check_driver():
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        from webdriver_manager.firefox import GeckoDriverManager
        return True
    except ImportError: return False

def create_driver():
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        from webdriver_manager.firefox import GeckoDriverManager
        
        options = Options()
        options.binary_location = FIREFOX_PATH
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")
        
        profile = webdriver.FirefoxProfile(PROFILE_DIR)
        profile.set_preference("dom.webdriver.enabled", False)
        profile.set_preference("useAutomationExtension", False)
        
        service = Service(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options, firefox_profile=profile)
    except Exception as e:
        return None

def scrape_with_browser(url):
    driver = create_driver()
    if not driver: return {"status": "error", "error": "Browser not available"}
    
    try:
        driver.get(url)
        time.sleep(5)
        
        title = driver.title
        html = driver.page_source
        
        if any(marker.lower() in html.lower() for marker in BLOCKED_MARKERS):
            return {"status": "blocked", "error": "Cloudflare detected"}
        
        return {"status": "ok", "title": title, "html": html, "url": driver.current_url}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        try: driver.quit()
        except: pass

def scrape_with_http(url):
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {"User-Agent": USER_AGENTS[0]}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script","style","noscript"]): tag.decompose()
        
        title = soup.title.get_text() if soup.title else ""
        html = str(soup)
        
        if any(marker.lower() in html.lower() for marker in BLOCKED_MARKERS):
            return {"status": "blocked", "error": "Blocked"}
        
        return {"status": "ok", "title": title, "html": html, "url": url}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def save_result(result, fmt="md"):
    if result["status"] != "ok": return None
    
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
    for tag in soup(["script","style","noscript","svg","iframe","nav","header","footer"]):
        tag.decompose()
    
    if fmt == "html":
        with open(file_path, 'w', encoding='utf-8') as f: f.write(html)
    elif fmt == "txt":
        text = soup.get_text("\n", strip=True)
        with open(file_path, 'w', encoding='utf-8') as f: f.write(text)
    elif fmt == "md":
        try:
            from markdownify import markdownify as md
            md_text = md(str(soup), heading_style="ATX")
        except:
            md_text = soup.get_text("\n", strip=True)
        header = f"# {result['title'] or url}\n\n**Source:** {url}\n\n---\n\n"
        with open(file_path, 'w', encoding='utf-8') as f: f.write(header + md_text)
    elif fmt == "docx":
        try:
            from docx import Document
            doc = Document()
            doc.add_heading(result['title'] or url, 0)
            doc.add_paragraph(f"Source: {url}")
            for p in soup.get_text("\n", strip=True).split('\n'):
                if p.strip(): doc.add_paragraph(p.strip())
            doc.save(file_path)
        except: return None
    
    return file_path

def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description='UNIVERSAL SCRAPER v7.0')
    parser.add_argument('--url', help='URL to scrape')
    parser.add_argument('--urls', nargs='+', help='Multiple URLs')
    parser.add_argument('--file', help='File with URLs')
    parser.add_argument('--format', default='md', choices=SUPPORTED_FORMATS)
    parser.add_argument('--mode', default='browser', choices=['http', 'browser'])
    parser.add_argument('--output', default=None)
    
    args = parser.parse_args()
    
    urls = args.urls or []
    if args.url: urls.append(args.url)
    if args.file:
        with open(args.file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
    
    if not urls:
        parser.print_help()
        return
    
    output_dir = args.output or os.path.join(BASE_DIR, "OUTPUT")
    os.makedirs(output_dir, exist_ok=True)
    
    for url in urls:
        url = normalize_url(url)
        if not validate_url(url):
            print(f"Invalid URL: {url}")
            continue
        
        print(f"Processing: {url}")
        
        if args.mode == "browser":
            result = scrape_with_browser(url)
        else:
            result = scrape_with_http(url)
        
        if result["status"] == "ok":
            file_path = save_result(result, args.format)
            if file_path:
                size = os.path.getsize(file_path)
                print(f"SUCCESS: {file_path} ({human_size(size)})")
            else:
                print(f"ERROR: Could not save {url}")
        else:
            print(f"ERROR: {result.get('error', 'Unknown')}")

if __name__ == '__main__':
    main()
