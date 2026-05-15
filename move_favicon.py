
import shutil
import os
import sys

src = r"C:\Users\Nandu M\.gemini\antigravity\brain\0a6c98a6-1994-4c0c-8a04-009237e3935a\favicon_1766920687402.png"
dst = r"C:\Users\Nandu M\OneDrive\Desktop\Resume Creator And ATS\Resume Creator\static\favicon.png"

print(f"Attempting to copy from {src} to {dst}")

if not os.path.exists(src):
    print("Error: Source file does not exist.")
    sys.exit(1)

try:
    shutil.copy2(src, dst)
    if os.path.exists(dst):
        print("Success: File copied successfully.")
    else:
        print("Error: Destination file not found after copy.")
        sys.exit(1)
except Exception as e:
    print(f"Error: Exception during copy: {e}")
    sys.exit(1)
