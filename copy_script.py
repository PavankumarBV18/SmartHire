import shutil
import os

src = r"C:\Users\Nandu M\.gemini\antigravity\brain\0a6c98a6-1994-4c0c-8a04-009237e3935a\title_banner_1766919239049.png"
dst = r"C:\Users\Nandu M\OneDrive\Desktop\Resume Creator And ATS\Resume Creator\static\title_banner.png"

try:
    print(f"Copying from {src} to {dst}")
    if not os.path.exists(src):
        print("Source does not exist!")
    else:
        shutil.copy2(src, dst)
        print("Copy success!")
except Exception as e:
    print(f"Error: {e}")
