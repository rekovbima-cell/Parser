# -*- coding: utf-8 -*-
import json, os
base = 'ARCHIVE/MEGA_TANK_v3_0'
out = 'SPLIT'
os.makedirs(out + '/chat', exist_ok=True)
os.makedirs(out + '/doc', exist_ok=True)

# --- Qwen chat: one file per message, split in 38k parts ---
with open(base + '/05-chat-full-qwen.json', encoding='utf-8') as f:
    chat = json.load(f)
msgs = chat.get('chat', {}).get('history', {}).get('messages', {})
index = []
n = 0
for mid, m in msgs.items():
    if not isinstance(m, dict):
        continue
    role = m.get('role', '?')
    content = m.get('content') or ''
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    n += 1
    prefix = out + '/chat/' + ('%04d_%s' % (n, role))
    size = 38000
    parts = [content[i:i+size] for i in range(0, len(content), size)] or ['']
    for p, chunk in enumerate(parts):
        with open('%s.part%d' % (prefix, p), 'w', encoding='utf-8') as fh:
            fh.write(chunk)
    index.append('#%04d [%s] len=%d parts=%d id=%s' % (n, role, len(content), len(parts), mid))
with open(out + '/chat/INDEX.txt', 'w', encoding='utf-8') as fh:
    fh.write(chr(10).join(index))
print('CHAT MESSAGES: %d' % n)

# --- docs: 38k parts ---
for fn in sorted(os.listdir(base)):
    if fn.endswith('.json'):
        continue
    src = os.path.join(base, fn)
    if not os.path.isfile(src):
        continue
    with open(src, encoding='utf-8', errors='replace') as f:
        txt = f.read()
    tag = fn.split(' ')[0][:6]
    size = 38000
    parts = [txt[i:i+size] for i in range(0, len(txt), size)]
    for p, chunk in enumerate(parts):
        with open('%s/doc/%s.part%d' % (out, tag, p), 'w', encoding='utf-8') as fh:
            fh.write(chunk)
    with open(out + '/doc/' + tag + '.INDEX.txt', 'w', encoding='utf-8') as fh:
        fh.write('%s = %s | total_len=%d parts=%d' % (tag, fn, len(txt), len(parts)) + chr(10))
print('DOCS SPLIT DONE')