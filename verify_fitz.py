import sys
print(f"Python Executable: {sys.executable}")
try:
    import fitz
    print("FITZ IMPORT SUCCESS")
    print(f"Fitz file: {fitz.__file__}")
except ImportError as e:
    print(f"FITZ IMPORT FAILED: {e}")
except Exception as e:
    print(f"ERROR: {e}")
