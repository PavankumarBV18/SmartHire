
import shutil
import os
import time

# Source path where the agent creates the file
src_dir = r"C:\Users\Nandu M\.gemini\antigravity\brain\0a6c98a6-1994-4c0c-8a04-009237e3935a"
# Destination path
dst_file = r"C:\Users\Nandu M\OneDrive\Desktop\Resume Creator And ATS\Resume Creator\static\classic_bg.png"

print("Searching for generated classic_bg file...")

found_src = None
# Find the most recent file matching the pattern
for i in range(10):
    files = [f for f in os.listdir(src_dir) if "classic_bg" in f and f.endswith(".png")]
    if files:
        # Sort by modification time, newest first
        files.sort(key=lambda x: os.path.getmtime(os.path.join(src_dir, x)), reverse=True)
        found_src = os.path.join(src_dir, files[0])
        print(f"Found source: {found_src}")
        break
    time.sleep(2)

if not found_src:
    print("Error: Could not find generated background image.")
    exit(1)

print(f"Copying to {dst_file}...")
try:
    with open(found_src, 'rb') as f_src:
        data = f_src.read()
    with open(dst_file, 'wb') as f_dst:
        f_dst.write(data)
    print("Success: File written.")
except Exception as e:
    print(f"Error copying file: {e}")
