#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
UNIVERSAL SMART PROCESSOR v1.0
Smartest Integration of All Repository Files

This is the ultimate unified processor that combines:
- MEGA TANK v3.0 web scraping capabilities
- Extended browser management and CDP support
- Comprehensive file analysis from MEGA_ANALYZER
- Intelligent URL processing and content extraction
- Advanced search and indexing

Features:
- Multi-engine web scraping (Playwright, Requests, CDP)
- File analysis and repository processing
- URL batch processing with smart retries
- Content extraction in multiple formats (PDF, HTML, TXT, DOCX, Markdown)
- Advanced stealth and anti-blocking mechanisms
- Comprehensive logging and reporting
- Search and query capabilities across processed content

Usage:
    python UNIVERSAL_SMART_PROCESSOR.py --urls url1 url2 url3
    python UNIVERSAL_SMART_PROCESSOR.py --file path/to/file
    python UNIVERSAL_SMART_PROCESSOR.py --analyze ./directory
    python UNIVERSAL_SMART_PROCESSOR.py --search "query" --urls url1 url2
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
import hashlib
import shutil
import webbrowser
from datetime import datetime
from urllib.parse import urlparse, urljoin
from pathlib import Path
from collections import defaultdict, Counter
import argparse
import textwrap
from typing import Dict, List, Tuple, Any, Optional, Union

# ==============================================================================
# CONSTANTS AND CONFIGURATION
# ==============================================================================

APP_NAME = "UNIVERSAL SMART PROCESSOR"
APP_VERSION = "1.0"
BUILD_DATE = "2026-01-01"

# Get base directory
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Required packages for different functionalities
REQUIRED_PACKAGES = {
    "scraping": [
        ("requests", "requests"),
        ("playwright", "playwright"),
        ("pypdf", "pypdf"),
        ("python-docx", "docx"),
        ("beautifulsoup4", "bs4"),
        ("markdownify", "markdownify"),
    ],
    "analysis": [
        ("requests", "requests"),
    ],
}

# Output formats
FORMAT_MAP = {
    "PDF": "pdf",
    "HTML": "html",
    "TXT": "txt",
    "DOCX": "docx",
    "Markdown": "md",
}

# Blocked content markers
BLOCKED_MARKERS = [
    "just a moment", "checking your browser", "attention required",
    "access denied", "are you a robot", "captcha", "cloudflare",
    "rate limit exceeded", "403 forbidden", "request blocked",
    "unusual traffic", "verify you are human", "bot detection",
]

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
]

# Locale and timezone pairs
LOCALE_TZ_PAIRS = [
    ("en-US", "America/New_York"),
    ("en-US", "America/Los_Angeles"),
    ("en-US", "America/Chicago"),
    ("en-GB", "Europe/London"),
]

# Viewport sizes for rotation
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

# Hardware profiles
HARDWARE_PROFILES = [(8, 8), (12, 8), (4, 4), (16, 8), (8, 4)]


# ==============================================================================
# AUTO INSTALLER
# ==============================================================================

class AutoInstaller:
    """Automatically install required dependencies"""
    
    def __init__(self, required_packages=None):
        self.missing = []
        self.installed = []
        self.required_packages = required_packages or []
        
    def check(self, pkg, imp):
        try:
            importlib.import_module(imp)
            self.installed.append(pkg)
            return True
        except ImportError:
            self.missing.append(pkg)
            return False
    
    def install(self, pkg):
        print(f"  📦 Installing {pkg}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet", "--upgrade"]
            )
            print(f"     ✅ {pkg}")
            return True
        except Exception as e:
            print(f"     ❌ {pkg}: {e}")
            return False
    
    def chromium_ready(self):
        """Check if Chromium browser is available for Playwright"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            return True
        except Exception:
            return False
    
    def install_browsers(self):
        print("  🌐 Installing Chromium browser for Playwright...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "playwright", "install", "chromium"]
            )
            print("     ✅ Chromium installed")
            return True
        except Exception as e:
            print(f"     ⚠️  Could not install Chromium: {e}")
            return False
    
    def run(self, mode="scraping"):
        """Run dependency check and installation"""
        packages = REQUIRED_PACKAGES.get(mode, [])
        
        print("=" * 70)
        print(f"🔧 {APP_NAME} v{APP_VERSION} — Dependency Check")
        print("=" * 70)
        
        for pkg, imp in packages:
            ok = self.check(pkg, imp)
            print(f"{'✅' if ok else '❌'} {pkg}")
        
        if self.missing:
            print("\n" + "=" * 70)
            print(f"🚀 Installing {len(self.missing)} missing packages...")
            print("=" * 70)
            for p in list(self.missing):
                if self.install(p):
                    self.missing.remove(p)
        
        if not self.chromium_ready():
            print("\n" + "=" * 70)
            print("🌐 CHROMIUM browser not ready — installing...")
            print("=" * 70)
            self.install_browsers()
            if not self.chromium_ready():
                self.missing.append("chromium-browser")
        
        print("\n" + "=" * 70)
        if not self.missing:
            print("✅ All dependencies ready! Initializing...")
        else:
            print(f"⚠️  Still missing: {', '.join(self.missing)}")
            print("   Try installing manually:")
            print(f"   {sys.executable} -m pip install " + " ".join(self.missing))
        print("=" * 70)
        return len(self.missing) == 0


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def sanitize_filename(name: str) -> str:
    """Sanitize string for use as filename"""
    name = re.sub(r'^https?://', '', name)
    name = re.sub(r'[^\w\-_.]', '_', name)
    name = name.strip('_')
    while "__" in name:
        name = name.replace("__", "_")
    return (name or "page")[:100]


def slugify(text: str) -> str:
    """Create URL slug from text"""
    text = re.sub(r'[^\w\-]+', '-', text.strip().lower())
    return re.sub(r'-+', '-', text).strip('-')[:60] or "source"


def human_size(num_bytes: int) -> str:
    """Convert bytes to human-readable format"""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def now_stamp() -> str:
    """Get current timestamp for filenames"""
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def quick_dns_check(url: str) -> Tuple[bool, str]:
    """Quick DNS check to verify URL accessibility"""
    try:
        host = urlparse(url).hostname
        if not host:
            return False, "Invalid URL"
        socket.setdefaulttimeout(5)
        socket.gethostbyname(host)
        return True, None
    except Exception as e:
        return False, f"DNS/network error: {e}"


def random_locale_tz() -> Tuple[str, str]:
    """Get random locale and timezone pair"""
    return random.choice(LOCALE_TZ_PAIRS)


def random_ua() -> str:
    """Get random user agent"""
    return random.choice(USER_AGENTS)


def build_headers(ua: str) -> Dict[str, str]:
    """Build HTTP headers for requests"""
    is_mac = "Macintosh" in ua
    is_linux = "X11; Linux" in ua
    platform = '"macOS"' if is_mac else ('"Linux"' if is_linux else '"Windows"')
    version = "148" if "148." in ua else "147"
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-CH-UA": f'"Google Chrome";v="{version}", "Chromium";v="{version}", "Not=A?Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": platform,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "User-Agent": ua,
    }


def looks_blocked(title: str, body_sample: str) -> bool:
    """Check if page appears to be blocked"""
    haystack = f"{title} {body_sample}".lower()
    return any(marker in haystack for marker in BLOCKED_MARKERS)


# ==============================================================================
# STEALTH INIT SCRIPT FOR PLAYWRIGHT
# ==============================================================================

STEALTH_INIT_SCRIPT = """
(() => {
    // Hide navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // Patch plugins/mimeTypes (headless Chromium issues)
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5].map(() => ({ name: 'Chrome PDF Plugin' })),
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });

    // window.chrome - exists in Chrome, missing in headless
    window.chrome = window.chrome || { runtime: {} };

    // Patch permissions.query to avoid automation detection
    const origQuery = window.navigator.permissions && window.navigator.permissions.query;
    if (origQuery) {
        window.navigator.permissions.query = (parameters) => (
            parameters && parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : origQuery(parameters)
        );
    }

    // Patch WebGL vendor/renderer
    try {
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function (parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        };
    } catch (e) {}
})();
"""


# ==============================================================================
# FILE ANALYZER (from MEGA_ANALYZER.py)
# ==============================================================================

class FileAnalyzer:
    """Core class for analyzing individual files"""
    
    def __init__(self, file_path: str):
        self.path = Path(file_path)
        self.name = self.path.name
        self.size = self.path.stat().st_size
        self.extension = self.path.suffix.lower()
        self.content = None
        self.lines = []
        self.stats = {}
        self.metadata = {}
        
    def read(self, max_size: int = 10 * 1024 * 1024) -> bool:
        """Read file content with size limit"""
        try:
            if self.size > max_size:
                with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.content = f.read(max_size // 2)
                    f.seek(-max_size // 2, 2)
                    self.content += f.read()
            else:
                with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.content = f.read()
            
            self.lines = self.content.splitlines()
            return True
        except Exception as e:
            self.content = f"Error reading file: {e}"
            self.lines = [self.content]
            return False
    
    def analyze(self):
        """Perform comprehensive analysis on the file"""
        if not self.content:
            return
        
        # Basic stats
        self.stats['line_count'] = len(self.lines)
        self.stats['char_count'] = len(self.content)
        self.stats['word_count'] = len(self.content.split())
        
        # Detect encoding
        try:
            with open(self.path, 'rb') as f:
                raw = f.read(1024)
            if b'\xef\xbb\xbf' in raw:
                self.stats['encoding'] = 'UTF-8 BOM'
            elif b'\xff\xfe' in raw:
                self.stats['encoding'] = 'UTF-16 LE'
            else:
                self.stats['encoding'] = 'UTF-8'
        except:
            self.stats['encoding'] = 'Unknown'
        
        # File type specific analysis
        if self.extension == '.py':
            self._analyze_python()
        elif self.extension == '.json':
            self._analyze_json()
        elif self.extension == '.html':
            self._analyze_html()
        elif self.extension == '.md':
            self._analyze_markdown()
        elif self.extension == '.txt':
            self._analyze_text()
        elif self.extension == '.js':
            self._analyze_javascript()
        
        # Content analysis
        self._analyze_content()
        
        # Calculate hash
        self.stats['md5'] = self._calculate_md5()
        
    def _analyze_python(self):
        """Analyze Python files"""
        self.metadata['type'] = 'python'
        
        # Count imports
        imports = re.findall(r'^(import|from)\s+', self.content, re.MULTILINE)
        self.stats['import_count'] = len(imports)
        
        # Count classes
        classes = re.findall(r'^class\s+(\w+)', self.content, re.MULTILINE)
        self.stats['class_count'] = len(classes)
        self.metadata['classes'] = classes
        
        # Count functions
        functions = re.findall(r'^def\s+(\w+)', self.content, re.MULTILINE)
        self.stats['function_count'] = len(functions)
        self.metadata['functions'] = functions
        
        # Find shebang
        if self.lines and self.lines[0].startswith('#!'):
            self.metadata['shebang'] = self.lines[0]
        
        # Find main guard
        if 'if __name__ == "__main__":' in self.content:
            self.metadata['has_main'] = True
        
        # Extract docstrings
        docstrings = re.findall(r'"""(.*?)"""', self.content, re.DOTALL)
        self.metadata['docstrings'] = [d.strip() for d in docstrings if d.strip()]
        
    def _analyze_json(self):
        """Analyze JSON files"""
        self.metadata['type'] = 'json'
        
        try:
            data = json.loads(self.content)
            self.metadata['json_valid'] = True
            self.metadata['json_type'] = type(data).__name__
            
            if isinstance(data, dict):
                self.stats['json_keys'] = list(data.keys())
                self.stats['json_depth'] = self._get_json_depth(data)
            elif isinstance(data, list):
                self.stats['json_length'] = len(data)
                if data:
                    self.stats['json_first_item_type'] = type(data[0]).__name__
        except:
            self.metadata['json_valid'] = False
    
    def _get_json_depth(self, obj, depth=1):
        """Calculate JSON nesting depth"""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._get_json_depth(v, depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._get_json_depth(v, depth + 1) for v in obj)
        else:
            return depth
    
    def _analyze_html(self):
        """Analyze HTML files"""
        self.metadata['type'] = 'html'
        
        # Count HTML tags
        tags = re.findall(r'<[^>]+>', self.content)
        self.stats['tag_count'] = len(tags)
        
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', self.content, re.IGNORECASE | re.DOTALL)
        if title_match:
            self.metadata['title'] = title_match.group(1).strip()
        
        # Count scripts and styles
        self.stats['script_count'] = len(re.findall(r'<script[^>]*>', self.content, re.IGNORECASE))
        self.stats['style_count'] = len(re.findall(r'<style[^>]*>', self.content, re.IGNORECASE))
        
        # Check for specific elements
        self.metadata['has_form'] = bool(re.search(r'<form[^>]*>', self.content, re.IGNORECASE))
        self.metadata['has_table'] = bool(re.search(r'<table[^>]*>', self.content, re.IGNORECASE))
        
    def _analyze_markdown(self):
        """Analyze Markdown files"""
        self.metadata['type'] = 'markdown'
        
        # Count headers
        headers = re.findall(r'^#{1,6}\s+(.*)', self.content, re.MULTILINE)
        self.stats['header_count'] = len(headers)
        self.metadata['headers'] = headers
        
        # Count code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', self.content)
        self.stats['code_block_count'] = len(code_blocks)
        
        # Count links
        links = re.findall(r'\[.*?\]\(.*?\)', self.content)
        self.stats['link_count'] = len(links)
        
        # Count images
        images = re.findall(r'!\[.*?\]\(.*?\)', self.content)
        self.stats['image_count'] = len(images)
        
    def _analyze_text(self):
        """Analyze plain text files"""
        self.metadata['type'] = 'text'
        
        # Count paragraphs
        paragraphs = re.findall(r'\n\n[^\n]+', self.content)
        self.stats['paragraph_count'] = len(paragraphs)
        
    def _analyze_javascript(self):
        """Analyze JavaScript files"""
        self.metadata['type'] = 'javascript'
        
        # Count functions
        functions = re.findall(r'function\s+(\w+)', self.content)
        functions += re.findall(r'const\s+(\w+)\s*=', self.content)
        functions += re.findall(r'let\s+(\w+)\s*=', self.content)
        self.stats['function_count'] = len(functions)
        self.metadata['functions'] = functions
        
        # Count classes
        classes = re.findall(r'class\s+(\w+)', self.content)
        self.stats['class_count'] = len(classes)
        self.metadata['classes'] = classes
        
    def _analyze_content(self):
        """General content analysis"""
        content_lower = self.content.lower()
        
        # Check for Russian text
        russian_chars = re.findall(r'[\u0400-\u04FF]', self.content)
        if russian_chars:
            self.metadata['language'] = 'russian'
            self.metadata['russian_ratio'] = len(russian_chars) / len(self.content)
        else:
            self.metadata['language'] = 'english'
        
        # Check for URLs
        urls = re.findall(r'https?://[^\s]+', self.content)
        self.stats['url_count'] = len(urls)
        self.metadata['urls'] = urls[:10]
        
        # Check for email addresses
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', self.content)
        self.stats['email_count'] = len(emails)
        
        # Word frequency (top 10)
        words = re.findall(r'[\w\u0400-\u04FF]+', content_lower)
        word_freq = Counter(words)
        self.metadata['top_words'] = word_freq.most_common(10)
        
    def _calculate_md5(self) -> str:
        """Calculate MD5 hash of file"""
        try:
            with open(self.path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return 'unknown'
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the file"""
        return {
            'name': self.name,
            'path': str(self.path),
            'size': self.size,
            'size_human': self._human_size(self.size),
            'extension': self.extension,
            'type': self.metadata.get('type', 'unknown'),
            'stats': self.stats,
            'metadata': self.metadata,
            'preview': self._get_preview()
        }
    
    def _human_size(self, size: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _get_preview(self) -> str:
        """Get first 500 characters of content"""
        if self.content:
            return self.content[:500].replace('\n', ' ').replace('\r', ' ')
        return ""


# ==============================================================================
# REPOSITORY ANALYZER
# ==============================================================================

class RepositoryAnalyzer:
    """Analyzes entire repository"""
    
    def __init__(self, repo_path: str = '.'):
        self.repo_path = Path(repo_path)
        self.files = {}
        self.file_analyzers = {}
        self.summary = {}
        
    def scan(self, extensions: List[str] = None) -> Dict[str, FileAnalyzer]:
        """Scan repository for files"""
        if extensions is None:
            extensions = ['.py', '.json', '.html', '.md', '.txt', '.js', '.css']
        
        for file_path in self.repo_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.'):
                ext = file_path.suffix.lower()
                if ext in extensions or not extensions:
                    analyzer = FileAnalyzer(str(file_path))
                    if analyzer.read():
                        analyzer.analyze()
                        self.file_analyzers[analyzer.name] = analyzer
                        self.files[analyzer.name] = analyzer.get_summary()
        
        return self.file_analyzers
    
    def generate_summary(self):
        """Generate comprehensive repository summary"""
        if not self.files:
            self.scan()
        
        total_size = sum(f['size'] for f in self.files.values())
        total_lines = sum(f['stats'].get('line_count', 0) for f in self.files.values())
        total_words = sum(f['stats'].get('word_count', 0) for f in self.files.values())
        
        # Group by type
        by_type = defaultdict(list)
        for name, info in self.files.items():
            file_type = info.get('type', 'other')
            by_type[file_type].append(name)
        
        # Language statistics
        by_language = defaultdict(int)
        for info in self.files.values():
            lang = info.get('metadata', {}).get('language', 'unknown')
            by_language[lang] += 1
        
        # Extension statistics
        by_extension = defaultdict(list)
        for name, info in self.files.items():
            ext = info.get('extension', 'none')
            by_extension[ext].append(name)
        
        self.summary = {
            'total_files': len(self.files),
            'total_size': total_size,
            'total_size_human': self._human_size(total_size),
            'total_lines': total_lines,
            'total_words': total_words,
            'by_type': dict(by_type),
            'by_language': dict(by_language),
            'by_extension': {k: len(v) for k, v in by_extension.items()},
            'largest_file': max(self.files.items(), key=lambda x: x[1]['size']) if self.files else None,
            'smallest_file': min(self.files.items(), key=lambda x: x[1]['size']) if self.files else None,
            'most_lines': max(self.files.items(), key=lambda x: x[1]['stats'].get('line_count', 0)) if self.files else None,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.summary
    
    def _human_size(self, size: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def search(self, query: str, case_sensitive: bool = False) -> Dict[str, List[Tuple[int, str]]]:
        """Search for query across all files"""
        results = {}
        
        if not case_sensitive:
            query = query.lower()
        
        for name, analyzer in self.file_analyzers.items():
            matches = []
            content = analyzer.content
            if not case_sensitive:
                content = content.lower()
            
            for i, line in enumerate(content.splitlines()):
                if query in line:
                    matches.append((i + 1, line.strip()[:200]))
            
            if matches:
                results[name] = matches
        
        return results
    
    def get_file_info(self, filename: str) -> Optional[Dict]:
        """Get detailed information about a specific file"""
        return self.files.get(filename)
    
    def export_summary(self, output_file: str = 'REPO_SUMMARY.json'):
        """Export summary to JSON file"""
        summary = self.generate_summary()
        summary['files'] = self.files
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        return output_file
    
    def generate_report(self) -> str:
        """Generate human-readable report"""
        summary = self.generate_summary()
        
        report = []
        report.append("=" * 80)
        report.append("REPOSITORY ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {summary['timestamp']}")
        report.append(f"Repository: {self.repo_path}")
        report.append("")
        
        report.append("-" * 80)
        report.append("OVERVIEW")
        report.append("-" * 80)
        report.append(f"Total Files: {summary['total_files']}")
        report.append(f"Total Size: {summary['total_size_human']}")
        report.append(f"Total Lines: {summary['total_lines']:,}")
        report.append(f"Total Words: {summary['total_words']:,}")
        report.append("")
        
        report.append("-" * 80)
        report.append("FILE TYPES")
        report.append("-" * 80)
        for file_type, count in summary['by_type'].items():
            report.append(f"  {file_type.capitalize()}: {count} files")
        report.append("")
        
        report.append("-" * 80)
        report.append("LANGUAGES")
        report.append("-" * 80)
        for lang, count in summary['by_language'].items():
            report.append(f"  {lang.capitalize()}: {count} files")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


# ==============================================================================
# WEB SCRAPER (from MEGA_TANK)
# ==============================================================================

class WebScraper:
    """Advanced web scraper with multiple fallback methods"""
    
    def __init__(self):
        self.playwright_available = False
        self.requests_available = False
        self._check_dependencies()
        
    def _check_dependencies(self):
        try:
            import playwright
            self.playwright_available = True
        except ImportError:
            pass
        
        try:
            import requests
            self.requests_available = True
        except ImportError:
            pass
    
    def scrape_url(self, url: str, output_format: str = "txt", output_dir: str = None, 
                   retries: int = 2, aggressive: bool = False) -> Dict[str, Any]:
        """
        Scrape a single URL and save content in specified format
        
        Args:
            url: URL to scrape
            output_format: Format for output (txt, html, md, pdf, docx)
            output_dir: Directory to save output (defaults to current directory)
            retries: Number of retry attempts
            aggressive: Use aggressive anti-blocking measures
            
        Returns:
            Dictionary with scraping results and metadata
        """
        result = {
            "url": url,
            "title": "",
            "status": "failed",
            "format": output_format,
            "file": None,
            "size_bytes": 0,
            "word_count": None,
            "blocked_suspected": False,
            "method": "none",
            "attempts": 0,
            "error": None,
            "elapsed_sec": 0.0,
        }
        
        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, f"UNIVERSAL_OUTPUT_{now_stamp()}")
        os.makedirs(output_dir, exist_ok=True)
        
        t0 = time.time()
        
        # Validate URL
        ok_dns, dns_err = quick_dns_check(url)
        if not ok_dns:
            result["error"] = dns_err
            result["elapsed_sec"] = round(time.time() - t0, 2)
            return result
        
        # Generate safe filename
        safe_name = sanitize_filename(url)
        file_path = os.path.join(output_dir, f"{safe_name}.{output_format}")
        
        # Handle filename conflicts
        counter = 2
        while os.path.exists(file_path):
            file_path = os.path.join(output_dir, f"{safe_name}_{counter}.{output_format}")
            counter += 1
        
        max_attempts = max(1, retries + 1)
        last_error = None
        
        # Try Playwright first
        if self.playwright_available:
            for attempt in range(1, max_attempts + 1):
                result["attempts"] = attempt
                
                try:
                    return self._scrape_with_playwright(
                        url, output_format, file_path, result, attempt, max_attempts, aggressive
                    )
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_attempts:
                        time.sleep(random.uniform(2.0, 4.0))
        
        # Fallback to requests
        if self.requests_available and result["status"] != "ok":
            try:
                return self._scrape_with_requests(
                    url, output_format, file_path, result
                )
            except Exception as e:
                last_error = f"{last_error} | fallback: {e}" if last_error else str(e)
        
        result["error"] = last_error
        result["elapsed_sec"] = round(time.time() - t0, 2)
        return result
    
    def _scrape_with_playwright(self, url: str, output_format: str, file_path: str,
                               result: Dict, attempt: int, max_attempts: int,
                               aggressive: bool) -> Dict[str, Any]:
        """Scrape using Playwright browser automation"""
        from playwright.sync_api import sync_playwright
        
        ua = random_ua()
        locale, tz = random_locale_tz()
        viewport = random.choice(VIEWPORTS)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled',
                    '--lang=en-US,en;q=0.9',
                ],
            )
            
            context = browser.new_context(
                viewport=viewport,
                user_agent=ua,
                extra_http_headers=build_headers(ua),
                locale=locale,
                timezone_id=tz,
                device_scale_factor=1,
                permissions=["notifications"],
            )
            
            context.add_init_script(STEALTH_INIT_SCRIPT)
            page = context.new_page()
            
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=12000)
                except Exception:
                    pass
                
                page.wait_for_timeout(random.randint(400, 900))
                self._autoscroll(page)
                
                # Extract title
                title = ""
                try:
                    title = page.title()
                except Exception:
                    pass
                result["title"] = title
                
                # Check for blocking
                status_code = response.status if response else None
                body_sample = ""
                try:
                    body_sample = page.locator('body').inner_text(timeout=5000)[:2000]
                except Exception:
                    pass
                
                blocked = (status_code in (403, 429, 503)) or looks_blocked(title, body_sample)
                result["blocked_suspected"] = blocked
                
                if blocked:
                    print(f"   ⚠️  Blocking detected (code {status_code}), attempt {attempt}/{max_attempts}")
                
                # Extract content based on format
                if output_format == "pdf":
                    page.pdf(
                        path=file_path,
                        format='A4',
                        print_background=True,
                        margin={'top': '0.5in', 'bottom': '0.5in', 'left': '0.5in', 'right': '0.5in'},
                    )
                    result["word_count"] = None
                elif output_format == "html":
                    content = page.content()
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                elif output_format == "txt":
                    text_content = self._extract_page_text(page)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    result["word_count"] = len(text_content.split())
                    result["_text"] = text_content
                elif output_format == "md":
                    content = self._extract_page_html(page)
                    md_text = self._html_to_markdown(content, url)
                    header = f"# {title or url}\n\nSource: {url}\n\n---\n\n"
                    full_md = header + md_text
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(full_md)
                    result["word_count"] = len(full_md.split())
                    result["_text"] = full_md
                elif output_format == "docx":
                    text_content = self._extract_page_text(page)
                    self._save_as_docx(text_content, title or url, url, file_path)
                    result["word_count"] = len(text_content.split())
                    result["_text"] = text_content
                
                browser.close()
                
                size = os.path.getsize(file_path)
                result["status"] = "ok"
                result["file"] = os.path.basename(file_path)
                result["size_bytes"] = size
                result["method"] = "playwright"
                result["elapsed_sec"] = round(time.time() - result.get("_t0", time.time()), 2)
                
                return result
            
            except Exception as e:
                browser.close()
                raise e
    
    def _scrape_with_requests(self, url: str, output_format: str, file_path: str,
                              result: Dict) -> Dict[str, Any]:
        """Fallback scraping using requests library"""
        import requests
        from bs4 import BeautifulSoup
        
        ua = random_ua()
        headers = build_headers(ua)
        
        resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        
        raw_html = resp.text
        soup = BeautifulSoup(raw_html, "html.parser")
        
        # Clean up soup
        for tag in soup(["script", "style", "noscript", "template", "svg", "iframe",
                        "nav", "header", "footer", "aside"]):
            tag.decompose()
        
        title = soup.title.get_text(strip=True) if soup.title else ""
        result["title"] = title
        
        if output_format == "html":
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(raw_html)
        elif output_format == "txt":
            text_content = soup.get_text("\n", strip=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            result["word_count"] = len(text_content.split())
            result["_text"] = text_content
        elif output_format == "md":
            md_text = self._html_to_markdown(raw_html, url)
            full_md = f"# {title or url}\n\nSource: {url} (requests fallback)\n\n---\n\n" + md_text
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
        result["method"] = "requests-fallback"
        result["elapsed_sec"] = round(time.time() - result.get("_t0", time.time()), 2)
        
        return result
    
    def _autoscroll(self, page, steps: int = 6, pause: float = 0.35):
        """Auto-scroll page to trigger lazy loading"""
        try:
            for _ in range(steps):
                page.mouse.wheel(0, random.randint(500, 900))
                page.wait_for_timeout(int(pause * 1000))
            page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass
    
    def _extract_page_text(self, page) -> str:
        """Extract clean text content from page"""
        selector = "article, main, [role='main'], .article, .post, .entry-content, .post-content, .content"
        cleanup = """
          () => {
            const root = document.querySelector(%s) || document.body || document.documentElement;
            const junk = root.querySelectorAll(
              `script, style, noscript, template, svg, canvas, iframe, nav, header, footer, aside,
               [aria-hidden="true"], [role="navigation"], [role="banner"], [role="contentinfo"],
               .cookie, .cookies, .consent, .popup, .modal, .advert, .ads, .ad, .social-share`
            );
            junk.forEach((node) => node.remove());
            return root.innerText || '';
          }
        """ % json.dumps(selector)
        
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
        
        # Clean up whitespace
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in (text_content or "").splitlines()]
        text_content = re.sub(r"\n{3,}", "\n\n", "\n".join(line for line in lines if line))
        
        # Include iframe content
        frames = page.frames
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
                text_content += "\n--- FRAME CONTENT ---\n" + "\n".join(extra)
        
        return text_content
    
    def _extract_page_html(self, page) -> str:
        """Extract clean HTML content from page"""
        try:
            return page.evaluate("""
                () => {
                  const selector = "article, main, [role='main'], .article, .post, .entry-content, .post-content, .content";
                  const root = document.querySelector(selector) || document.body || document.documentElement;
                  const copy = root.cloneNode(true);
                  copy.querySelectorAll(`script, style, noscript, template, svg, canvas, iframe, nav, header, footer, aside,
                    [aria-hidden="true"], [role="navigation"], [role="banner"], [role="contentinfo"],
                    .cookie, .cookies, .consent, .popup, .modal, .advert, .ads, .ad, .social-share`)
                    .forEach((node) => node.remove());
                  return copy.outerHTML;
                }
            """)
        except Exception:
            return page.content()
    
    def _html_to_markdown(self, html_content: str, page_url: str = "") -> str:
        """Convert HTML to Markdown"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup([
            "script", "style", "noscript", "template", "svg", "iframe",
            "nav", "header", "footer", "aside",
        ]):
            tag.decompose()
        
        try:
            from markdownify import markdownify as md_convert
            body = soup.body or soup
            md = md_convert(str(body), heading_style="ATX", bullets="-")
            md = re.sub(r'\n{3,}', '\n\n', md).strip()
            if md:
                return md
        except Exception:
            pass
        
        # Fallback to manual conversion
        lines = []
        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "a"]):
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
        text = "\n\n".join(lines) if lines else soup.get_text("\n", strip=True)
        return text
    
    def _save_as_docx(self, text_content: str, title: str, url: str, file_path: str):
        """Save content as DOCX file"""
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


# ==============================================================================
# CONTENT PROCESSOR (Combines Scraping and Analysis)
# ==============================================================================

class ContentProcessor:
    """Unified content processor combining scraping and analysis"""
    
    def __init__(self):
        self.scraper = WebScraper()
        self.file_analyzers = {}
        self.processed_urls = {}
        self.processed_files = {}
        
    def process_url(self, url: str, output_format: str = "md", output_dir: str = None,
                    analyze: bool = True) -> Dict[str, Any]:
        """
        Process a URL: scrape, save, and optionally analyze content
        
        Args:
            url: URL to process
            output_format: Format for output
            output_dir: Output directory
            analyze: Whether to analyze the scraped content
            
        Returns:
            Result dictionary with scraping and analysis data
        """
        # Scrape the URL
        scrape_result = self.scraper.scrape_url(
            url, output_format, output_dir
        )
        
        if scrape_result["status"] != "ok":
            return scrape_result
        
        # Store scrape result
        self.processed_urls[url] = scrape_result
        
        # Analyze content if requested
        if analyze and scrape_result.get("_text"):
            content = scrape_result["_text"]
            analysis = self._analyze_text_content(content, url)
            scrape_result["analysis"] = analysis
        
        return scrape_result
    
    def process_urls(self, urls: List[str], output_format: str = "md", output_dir: str = None,
                     analyze: bool = True, concurrency: int = 1) -> Dict[str, Any]:
        """
        Process multiple URLs with optional concurrency
        
        Args:
            urls: List of URLs to process
            output_format: Output format for each URL
            output_dir: Base output directory
            analyze: Whether to analyze content
            concurrency: Number of concurrent workers
            
        Returns:
            Summary of all processed URLs
        """
        if not urls:
            return {"status": "error", "message": "No URLs provided"}
        
        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, f"BATCH_PROCESSING_{now_stamp()}")
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        lock = threading.Lock()
        
        def worker(url):
            try:
                result = self.process_url(url, output_format, output_dir, analyze)
                with lock:
                    results[url] = result
            except Exception as e:
                with lock:
                    results[url] = {"status": "error", "error": str(e), "url": url}
        
        # Use threading for concurrent processing
        threads = []
        for url in urls:
            t = threading.Thread(target=worker, args=(url,))
            threads.append(t)
            t.start()
            
            # Limit concurrency
            if len(threads) >= concurrency:
                for thread in threads:
                    thread.join()
                threads = []
        
        # Wait for remaining threads
        for thread in threads:
            thread.join()
        
        # Generate summary
        summary = self._generate_url_summary(results)
        return summary
    
    def _analyze_text_content(self, content: str, source: str = "") -> Dict[str, Any]:
        """Analyze text content"""
        analysis = {
            "char_count": len(content),
            "word_count": len(content.split()),
            "line_count": len(content.splitlines()),
            "urls": [],
            "emails": [],
            "top_words": [],
            "language": "unknown",
        }
        
        # Check for Russian text
        russian_chars = re.findall(r'[\u0400-\u04FF]', content)
        if russian_chars:
            analysis["language"] = 'russian'
            analysis["russian_ratio"] = len(russian_chars) / len(content)
        else:
            analysis["language"] = 'english'
        
        # Extract URLs
        urls = re.findall(r'https?://[^\s]+', content)
        analysis["urls"] = urls[:10]
        analysis["url_count"] = len(urls)
        
        # Extract emails
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', content)
        analysis["emails"] = emails
        analysis["email_count"] = len(emails)
        
        # Word frequency
        content_lower = content.lower()
        words = re.findall(r'[\w\u0400-\u04FF]+', content_lower)
        word_freq = Counter(words)
        analysis["top_words"] = word_freq.most_common(10)
        
        # Detect document structure
        analysis["has_headers"] = bool(re.search(r'^#{1,6}\s+', content, re.MULTILINE))
        analysis["has_code_blocks"] = bool(re.search(r'```[\s\S]*?```', content))
        analysis["has_lists"] = bool(re.search(r'^\s*[-*+]\s+', content, re.MULTILINE))
        
        return analysis
    
    def _generate_url_summary(self, results: Dict[str, Dict]) -> Dict[str, Any]:
        """Generate summary of URL processing results"""
        total = len(results)
        success = sum(1 for r in results.values() if r.get("status") == "ok")
        failed = total - success
        
        total_size = sum(r.get("size_bytes", 0) for r in results.values())
        total_words = sum(r.get("word_count", 0) or 0 for r in results.values())
        
        # Group by status
        by_status = defaultdict(list)
        for url, result in results.items():
            status = result.get("status", "unknown")
            by_status[status].append(url)
        
        # Group by format
        by_format = defaultdict(list)
        for url, result in results.items():
            fmt = result.get("format", "unknown")
            by_format[fmt].append(url)
        
        # Group by method
        by_method = defaultdict(list)
        for url, result in results.items():
            method = result.get("method", "unknown")
            by_method[method].append(url)
        
        return {
            "total_urls": total,
            "successful": success,
            "failed": failed,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "total_size": total_size,
            "total_size_human": human_size(total_size),
            "total_words": total_words,
            "by_status": dict(by_status),
            "by_format": {k: len(v) for k, v in by_format.items()},
            "by_method": {k: len(v) for k, v in by_method.items()},
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """Process and analyze a local file"""
        analyzer = FileAnalyzer(file_path)
        if analyzer.read():
            analyzer.analyze()
            summary = analyzer.get_summary()
            self.file_analyzers[analyzer.name] = analyzer
            self.processed_files[analyzer.name] = summary
            return summary
        else:
            return {"status": "error", "error": "Failed to read file", "path": file_path}
    
    def process_directory(self, directory: str, extensions: List[str] = None) -> Dict[str, Any]:
        """Process all files in a directory"""
        repo_analyzer = RepositoryAnalyzer(directory)
        if extensions:
            repo_analyzer.scan(extensions)
        else:
            repo_analyzer.scan()
        
        summary = repo_analyzer.generate_summary()
        self.file_analyzers.update(repo_analyzer.file_analyzers)
        self.processed_files.update(repo_analyzer.files)
        
        return summary
    
    def search_content(self, query: str, case_sensitive: bool = False) -> Dict[str, Any]:
        """Search across all processed content"""
        results = {}
        
        # Search in processed URLs
        for url, data in self.processed_urls.items():
            if data.get("_text"):
                content = data["_text"]
                if not case_sensitive:
                    query_lower = query.lower()
                    content = content.lower()
                else:
                    query_lower = query
                
                matches = []
                for i, line in enumerate(content.splitlines()):
                    if query_lower in line:
                        matches.append((i + 1, line.strip()[:200]))
                
                if matches:
                    results[f"URL: {url}"] = matches
        
        # Search in processed files
        repo_analyzer = RepositoryAnalyzer(BASE_DIR)
        repo_analyzer.files = self.processed_files
        repo_analyzer.file_analyzers = self.file_analyzers
        file_results = repo_analyzer.search(query, case_sensitive)
        
        results.update(file_results)
        return results
    
    def export_results(self, output_file: str = "PROCESSING_RESULTS.json") -> str:
        """Export all processing results to JSON"""
        data = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(),
            "processed_urls": self.processed_urls,
            "processed_files": self.processed_files,
            "summary": {
                "url_count": len(self.processed_urls),
                "file_count": len(self.processed_files),
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return output_file


# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    """Main entry point with CLI interface"""
    parser = argparse.ArgumentParser(
        description=f'{APP_NAME} - Universal Smart Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
Examples:
  %(prog)s --urls https://example.com https://example.org
  %(prog)s --url https://example.com --format pdf
  %(prog)s --file ./myfile.py
  %(prog)s --directory ./myproject
  %(prog)s --urls url1 url2 --search "important term"
  %(prog)s --analyze ./ --export results.json
        ''')
    )
    
    # URL processing arguments
    parser.add_argument(
        '--urls', '-u',
        nargs='+',
        default=None,
        help='List of URLs to process'
    )
    
    parser.add_argument(
        '--url',
        type=str,
        default=None,
        help='Single URL to process'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        default='md',
        choices=list(FORMAT_MAP.values()) + list(FORMAT_MAP.keys()),
        help='Output format for URL processing (txt, html, md, pdf, docx)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=None,
        help='Output directory for processed files'
    )
    
    parser.add_argument(
        '--concurrency', '-c',
        type=int,
        default=1,
        help='Number of concurrent workers for URL processing'
    )
    
    # File processing arguments
    parser.add_argument(
        '--file',
        type=str,
        default=None,
        help='Single file to analyze'
    )
    
    parser.add_argument(
        '--directory', '-d',
        type=str,
        default=None,
        help='Directory to analyze'
    )
    
    parser.add_argument(
        '--extensions',
        nargs='+',
        default=None,
        help='File extensions to process (default: all supported)'
    )
    
    # Search and query
    parser.add_argument(
        '--search', '-s',
        type=str,
        default=None,
        help='Search query across processed content'
    )
    
    parser.add_argument(
        '--case-sensitive',
        action='store_true',
        help='Case-sensitive search'
    )
    
    # Export and reporting
    parser.add_argument(
        '--export', '-e',
        type=str,
        default=None,
        help='Export results to JSON file'
    )
    
    parser.add_argument(
        '--report', '-r',
        action='store_true',
        help='Generate human-readable report'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List processed files and URLs'
    )
    
    parser.add_argument(
        '--analyze', '-a',
        action='store_true',
        help='Perform deep analysis on content'
    )
    
    parser.add_argument(
        '--no-stealth',
        action='store_true',
        help='Disable stealth mode (faster but more detectable)'
    )
    
    parser.add_argument(
        '--retries',
        type=int,
        default=2,
        help='Number of retry attempts for failed URLs'
    )
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = ContentProcessor()
    
    # Check dependencies if doing web scraping
    urls_to_process = []
    if args.urls:
        urls_to_process = args.urls
    if args.url:
        urls_to_process.append(args.url)
    
    if urls_to_process:
        # Check if we need scraping dependencies
        installer = AutoInstaller(REQUIRED_PACKAGES["scraping"])
        installer.run("scraping")
    
    # Process URLs
    if urls_to_process:
        print(f"Processing {len(urls_to_process)} URLs...")
        
        # Normalize format
        output_format = args.format.lower()
        if output_format in FORMAT_MAP:
            output_format = FORMAT_MAP[output_format]
        
        result = processor.process_urls(
            urls_to_process,
            output_format=output_format,
            output_dir=args.output_dir,
            analyze=args.analyze,
            concurrency=args.concurrency
        )
        
        print(f"\nResults:")
        print(f"  Successful: {result['successful']}/{result['total_urls']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Total size: {result['total_size_human']}")
        print(f"  Total words: {result['total_words']:,}")
        
        if result['failed'] > 0:
            print(f"\nFailed URLs:")
            for url, data in result['results'].items():
                if data.get('status') != 'ok':
                    print(f"  ❌ {url}: {data.get('error', 'Unknown error')}")
        
        if args.export:
            with open(args.export, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            print(f"\nExported results to: {args.export}")
        else:
            default_export = f"URL_PROCESSING_{now_stamp()}.json"
            with open(default_export, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            print(f"\nExported results to: {default_export}")
    
    # Process files
    if args.file:
        print(f"Processing file: {args.file}")
        result = processor.process_file(args.file)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    if args.directory:
        print(f"Processing directory: {args.directory}")
        result = processor.process_directory(args.directory, args.extensions)
        print(f"Found {result['total_files']} files")
        print(f"Total size: {result['total_size_human']}")
        print(f"Total lines: {result['total_lines']:,}")
        print(f"Total words: {result['total_words']:,}")
    
    # Search
    if args.search:
        print(f"Searching for: '{args.search}'")
        results = processor.search_content(args.search, args.case_sensitive)
        
        if not results:
            print("No matches found.")
        else:
            for source, matches in results.items():
                print(f"\n{source}:")
                for line_num, line_content in matches:
                    print(f"  Line {line_num}: {line_content}")
    
    # List
    if args.list:
        print("Processed URLs:")
        for url in processor.processed_urls.keys():
            print(f"  🌐 {url}")
        
        print("\nProcessed Files:")
        for filename in processor.processed_files.keys():
            print(f"  📄 {filename}")
    
    # Export all
    if args.export and not urls_to_process:
        output_file = args.export
        print(f"Exporting all results to: {output_file}")
        processor.export_results(output_file)
        print("Done!")
    
    # Report
    if args.report:
        print("\n" + "=" * 80)
        print("PROCESSING REPORT")
        print("=" * 80)
        print(f"App: {APP_NAME} v{APP_VERSION}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"\nProcessed URLs: {len(processor.processed_urls)}")
        print(f"Processed Files: {len(processor.processed_files)}")
        print("=" * 80)


if __name__ == '__main__':
    main()
