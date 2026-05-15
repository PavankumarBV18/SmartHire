
import shutil
import os

src = r"C:\Users\Nandu M\.gemini\antigravity\brain\0a6c98a6-1994-4c0c-8a04-009237e3935a\favicon_1766920687402.png"
dst_dir = r"C:\Users\Nandu M\OneDrive\Desktop\Resume Creator And ATS\Resume Creator\static"
dst_file = os.path.join(dst_dir, "favicon.png")

print(f"Checking source: {src}")
if os.path.exists(src):
    print("Source exists.")
else:
    print("Source MISSING.")
    exit(1)

print(f"Copying to: {dst_file}")
try:
    shutil.copy2(src, dst_file)
    print("Copy executed.")
    if os.path.exists(dst_file):
        print(f"Success: File size {os.path.getsize(dst_file)} bytes")
    else:
        print("Error: Destination file not found after copy.")
except Exception as e:
    print(f"Exception: {e}")
