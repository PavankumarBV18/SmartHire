import os
import sys

def check_dependencies():
    print("--- Checking Dependencies ---")
    missing = []
    try:
        import flask
        print("✔ Flask installed")
    except ImportError:
        missing.append("flask")
    
    try:
        import groq
        print("✔ Groq installed")
    except ImportError:
        missing.append("groq")
        
    try:
        import fitz
        print("✔ PyMuPDF (fitz) installed")
    except ImportError:
        missing.append("PyMuPDF")
        
    try:
        import reportlab
        print("✔ ReportLab installed")
    except ImportError:
        missing.append("reportlab")
        
    if missing:
        print(f"❌ MISSING DEPENDENCIES: {', '.join(missing)}")
        print("Please run: pip install " + " ".join(missing))
        return False
    return True

def check_env():
    print("\n--- Checking Integretions ---")
    from dotenv import load_dotenv
    load_dotenv()
    
    key = os.getenv('GROQ_API_KEY')
    if not key:
        print("❌ GROQ_API_KEY not found in environment variables.")
        return False
        
    if key.startswith('gsk_'):
        print(f"✔ API Key found (starts with gsk_...)")
    else:
        print(f"⚠ API Key found but format looks unusual: {key[:4]}...")
        
    try:
        from groq import Groq
        client = Groq(api_key=key)
        print("✔ Groq Client initialized")
        
        # Test connection
        print("Testing API connection...")
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
                model="llama-3.3-70b-versatile",
            )
            print("✔ API Connection Successful")
            return True
        except Exception as e:
            print(f"❌ API Connection Failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Client Initialization Failed: {e}")
        return False

if __name__ == "__main__":
    deps_ok = check_dependencies()
    if deps_ok:
        check_env()
