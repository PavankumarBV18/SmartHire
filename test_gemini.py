import google.generativeai as genai
import os
from google.api_core import exceptions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. SETUP: Replace with your actual API key
# Ideally, store this in an environment variable
API_KEY = os.getenv('GEMINI_API_KEY')

if not API_KEY or API_KEY == "your-google-gemini-api-key-here" or API_KEY == "put your gemini api key here from google ai studio go to ky section and create one":
    print("Error: API Key not found or default value used. Please check your .env file.")
    exit()

print(f"Using API Key: {API_KEY[:5]}... (masked)")

genai.configure(api_key=API_KEY)

def generate_content_safe(prompt):
    # Use a stable model version
    model = genai.GenerativeModel('gemini-1.5-flash')

    try:
        print(f"Sending request for: '{prompt}'...")
        
        # Set unsafe filtering to allow more content (optional, use with care)
        # This helps if your valid requests are getting blocked falsely
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]

        response = model.generate_content(
            prompt,
            safety_settings=safety_settings
        )

        # 2. CHECK: Did the API return a candidate but block it due to safety?
        if response.prompt_feedback.block_reason:
            return f"Error: Blocked by safety filters. Reason: {response.prompt_feedback.block_reason}"

        # 3. CHECK: Does the text actually exist?
        # Sometimes the response is valid but empty
        if not response.parts:
            return "Error: The model returned an empty response (possible internal error)."

        return response.text

    # 4. EXCEPTION HANDLING: Catch specific API errors
    except exceptions.InvalidArgument as e:
        return f"Error: Invalid Argument (Check model name or prompt format). Details: {e}"
    except exceptions.ResourceExhausted as e:
        return f"Error: Quota Exceeded (Rate limit hit). Details: {e}"
    except exceptions.Unauthenticated as e:
        return f"Error: API Key Invalid or Unauthenticated. Details: {e}"
    except Exception as e:
        # Catch-all for other Python errors
        return f"Critical Error: {e}"

# --- Test the Code ---
prompt_text = "Explain quantum computing in one sentence."
result = generate_content_safe(prompt_text)

print("-" * 30)
print("FINAL RESULT:")
print(result)
print("-" * 30)
