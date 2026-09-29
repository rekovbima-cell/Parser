# Berlin's AI - Universal Web Scraper

## 📁 Structure

```
.
├── FINAL_PROGRAM/                    # ✅ FINAL VERSION - Use this!
│   ├── UNIVERSAL_FINAL_PROGRAM.py   # Main program (v4.1 - Checked)
│   └── __init__.py
│
├── ORIGINAL_FILES/                  # Original versions (backup)
│   ├── UNIVERSAL_SMART_PROCESSOR.py
│   └── UNIVERSAL_SMART_PROCESSOR_ORIGINAL.py
│
└── ARCHIVE/                         # Archive - Old versions
    └── MEGA_TANK_v3_0/              # First development version
        ├── 00-bad-tank.html
        ├── 01-MEGA_TANK_2026 .py
        ├── 02-Architecture...
        ├── 03-Architecture...
        ├── 04-finish-result...
        ├── 05-chat-full-qwen.json
        ├── START.bat
        └── START.sh
```

---

## 🎯 Quick Start

### 1. Use FINAL PROGRAM (Recommended)
```bash
cd FINAL_PROGRAM
python UNIVERSAL_FINAL_PROGRAM.py --url https://example.com
```

### 2. Or use original version
```bash
python ORIGINAL_FILES/UNIVERSAL_SMART_PROCESSOR.py --urls url1 url2
```

---

## 📊 What's What

| Folder | Version | Status | Description |
|--------|---------|--------|-------------|
| **FINAL_PROGRAM/** | v4.1 | ✅ **RECOMMENDED** | Final checked version, all bugs fixed |
| ORIGINAL_FILES/ | v1.0 | 📋 Backup | Original working versions |
| ARCHIVE/ | v3.0 | 🗃️ Archive | First development, for reference only |

---

## 🚀 Features (FINAL_PROGRAM)

- ✅ Scrape ANY websites (including .gov, protected)
- ✅ Support all formats: TXT, HTML, Markdown, DOCX
- ✅ Auto-proxy simulation (all in code, no external keys)
- ✅ Process URL lists from files or input
- ✅ Bypass blocking detection
- ✅ Caching system (7 days)
- ✅ Logging to file and console
- ✅ Duplicate URL detection
- ✅ Error handling
- ✅ Multi-threading support

---

## 💡 Usage Examples

```bash
# Single URL
python FINAL_PROGRAM/UNIVERSAL_FINAL_PROGRAM.py --url https://example.com

# Multiple URLs
python FINAL_PROGRAM/UNIVERSAL_FINAL_PROGRAM.py --urls https://example.com https://example.org

# From file
python FINAL_PROGRAM/UNIVERSAL_FINAL_PROGRAM.py --file urls.txt

# With format
python FINAL_PROGRAM/UNIVERSAL_FINAL_PROGRAM.py --url https://example.com --format md

# With output directory
python FINAL_PROGRAM/UNIVERSAL_FINAL_PROGRAM.py --url https://example.com --output MY_FOLDER

# Install dependencies
python FINAL_PROGRAM/UNIVERSAL_FINAL_PROGRAM.py --install

# Clear cache
python FINAL_PROGRAM/UNIVERSAL_FINAL_PROGRAM.py --clear-cache
```

---

## 📝 Notes

- **FINAL_PROGRAM/** - This is the main working directory. Use this!
- **ORIGINAL_FILES/** - Backup of original versions. Don't use unless needed.
- **ARCHIVE/** - Old development files. For reference only. Don't use for production.

---

## 🔧 Requirements

```bash
pip install requests beautifulsoup4 python-docx markdownify
```

---

## 📞 Support

For questions or issues, check the FINAL_PROGRAM first. It has all the latest fixes and improvements.
