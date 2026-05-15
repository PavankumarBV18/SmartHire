
import os
try:
    src = r"C:\Users\Nandu M\.gemini\antigravity\brain\0a6c98a6-1994-4c0c-8a04-009237e3935a\favicon_1766920687402.png"
    dst = r"static\favicon.png"
    print(f"Reading {src}...")
    with open(src, 'rb') as f:
        data = f.read()
    print(f"Read {len(data)} bytes.")
    print(f"Writing to {dst}...")
    with open(dst, 'wb') as f:
        f.write(data)
    print("Write success.")
except Exception as e:
    print(f"FATAL ERROR: {e}")
