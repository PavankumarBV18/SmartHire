# ==================== requirements.txt ====================

Flask==3.0.0
Werkzeug==3.0.1
python-dotenv==1.0.0
PyMuPDF==1.23.8
groq==0.5.0
reportlab==4.0.7

# ==================== .env (EXAMPLE) ====================

# Create this file in the root directory and add your actual API keys

# DO NOT commit this file to version control (GitHub/GitLab)!

SECRET_KEY=your-super-secret-key-change-this-in-production
GROQ_API_KEY=your-groq-api-key-here

# ==================== .gitignore ====================

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# Flask
instance/
.webassets-cache

# Environment variables
.env
.env.local

# Uploads & Data
uploads/
analysis_data/
*.pdf
*.json

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# ==================== README.md ====================

# Resume Creator And ATS - Advanced AI Resume Platform

**Resume Creator And ATS** is a cutting-edge, Flask-based web application designed to revolutionize the job application process. By leveraging the power of **Groq AI (Llama 3)**, it offers a comprehensive suite of tools for resume analysis, ATS (Applicant Tracking System) scoring, content enhancement, and automated resume generation.

This project is designed to provide "pin-to-pin" assistance—from the moment you upload an existing resume to the moment you download a polished, job-ready PDF.

## 🌟 Comprehensive Features

### 🧠 Core Intelligence (Groq AI Powered)
-   **Deep Resume Analysis**: Utilizes **Llama 3 70b** (via Groq) to dissect every section of your resume.
-   **ATS Compatibility Scoring**: Generates a precise **0-100 score** simulating real-world ATS algorithms used by Fortune 500 companies.
-   **Contextual Job Matching**: Compares your resume against a specific **Job Description (JD)** to calculate a "Match Score" and identify gaps.
-   **Smart Gap Analysis**: Automatically detects missing **Hard Skills**, **Soft Skills**, and **Keywords** critical for the targeted role.

### 🛠️ Resume Building & Generation
-   **Tailored Resume Creation**: The "Create" feature allows you to generate a **brand new resume** that is specifically written to target a provided Job Description, using your existing profile data.
-   **PDF Generation Engine**: Built-in **ReportLab** integration creates clean, professional, and ATS-friendly PDF documents from scratch.
-   **Formatting Standardization**: Ensures consistent fonts, margins, and layout structures that pass ATS parsers easily.

### 📝 Content Enhancement Tools
-   **AI Section Rewriter**: Instantly rewrite weak sections (e.g., "Professional Summary" or "Experience") with a single click.
-   **Tone Modes**: Choose between different writing styles:
    -   *Professional*: Formal and corporate-ready.
    -   *Creative*: Engaging and modern.
    -   *Action-Oriented*: Focuses on results and strong verbs.
-   **Grammar & Quality Check**: Identifies passive voice, spelling errors, and vague descriptions.

### 💬 Interactive Assistance
-   **AI Career Chatbot**: A dedicated "Chat" widget available on every page to answer career questions (e.g., "How do I explain a career gap?", "What skills are trending for Data Science?").
-   **Detailed Dashboard**: A visual hub displaying charts (Charts.js) for your scores, skill breakdowns, and improvement progress.

## 📋 Prerequisites

Before running the application, ensure your system meets these requirements:

-   **Operating System**: Windows 10/11, macOS, or Linux.
-   **Python**: Version 3.8 or higher.
-   **Groq API Key**: A valid API key from [Groq Cloud](https://console.groq.com/).
-   **Package Manager**: `pip` (standard with Python).

## 🚀 Step-by-Step Installation Guide

### Step 1: Clone the Repository
Download the project code to your local machine.

```bash
# Using Git
git clone <repository-url>
cd "Resume Creator And ATS"

# OR Download the ZIP file and extract it
```

### Step 2: Set Up Virtual Environment
Isolate the project dependencies to avoid conflicts.

```bash
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
Install all required Python libraries (Flask, Groq, PyMuPDF, etc.) listed in `requirements.txt`.

```bash
pip install -r requirements.txt
```

### Step 4: Configure API Keys
The application requires API keys to function.

1.  Create a new file named `.env` in the root folder.
2.  Add your keys (refer to the example at the top of this file):

```ini
SECRET_KEY=any_random_string_for_security
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
```

### Step 5: Initialize Directories
Manually create the necessary folders if they don't exist (though the app attempts to create them automatically).

```bash
mkdir uploads
mkdir analysis_data
mkdir static
mkdir templates
```

## 🏃 Running the Application

### Development Server
This is the standard way to run the app for testing and local use.

```bash
python app.py
```

-   **Status**: The terminal will show `Running on http://0.0.0.0:5001`.
-   **Access**: Open your web browser and go to **`http://localhost:5001`**.

*Note: Port 5001 is used to prevent conflicts with other services like AirPlay on macOS.*

### Production Deployment (Gunicorn)
For deploying to a live server (e.g., Heroku, DigitalOcean, Render).

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

## 📁 Detailed Project Structure

```text
Resume Creator/
├── app.py                 # THE CORE: Main Flask server logic, AI integration, and routing.
├── requirements.txt       # LIST: All Python libraries needed.
├── .env                   # CONFIG: Hidden file for API keys.
├── .gitignore            # GIT: Specifies files to ignore (like venv/).
├── README.md             # DOCS: This documentation file.
├── analysis_data/         # DATA: Stores JSON results of resume analyses.
├── uploads/               # TEMP: Stores uploaded PDF resumes temporarily.
├── templates/             # FRONTEND (HTML):
│   ├── base.html         # Layout template (Header, Footer, Nav).
│   ├── index.html        # Home page & Upload form.
│   ├── dashboard.html    # Analytics dashboard view.
│   ├── generated_resume.html # View for newly created resumes.
│   ├── tips.html         # Static career advice page.
│   ├── 404.html          # Custom "Page Not Found" error.
│   └── 500.html          # Custom "Server Error" page.
└── static/                # ASSETS:
    ├── style.css         # Styling (if not using Tailwind CDN).
    └── scripts.js        # Frontend interactions.
```

## 🎯 Detailed Usage Guide

### Scenario 1: Analyzing an Existing Resume
1.  Navigate to the **Home Page**.
2.  **Upload**: Click the upload area and select your current Resume (PDF).
3.  **Job Description**: Paste the text of the job you want to apply for.
4.  **Analyze**: Click the button.
5.  **Result**: You will be redirected to the **Dashboard** to see your Score, Missing Skills, and matching analysis.

### Scenario 2: Improving Content
1.  From the **Dashboard**, look at the "AI Suggestions" tab.
2.  Find a suggestion you like (e.g., "Rewrite Summary").
3.  Click the **"Enhance"** button.
4.  The system will use **Groq AI** to generate a stronger version of that text.

### Scenario 3: Creating a Tailored Resume
1.  Upload your "Master Resume" (contains all your history).
2.  Input the specific **Job Description**.
3.  Select **"Generate New"**.
4.  The system will smartly Pick & Choose the most relevant experiences and rephrase them.
5.  Download the result as a new **PDF**.

## 🔧 Configuration & Tuning

### Application Settings (`app.py`)
You can modify these variables directly in the Python code if needed:

-   `MAX_CONTENT_LENGTH`: Limits file uploads (Default: `16MB`).
-   `ALLOWED_EXTENSIONS`: Limits file types (Default: `{'pdf'}`).
-   `app.config['UPLOAD_FOLDER']`: Where files are saved.

### AI Model Settings
The app is currently configured to use **Llama-3.3-70b-versatile**.
-   This can be changed in the `analyze_with_groq` function in `app.py` if you wish to use a different model supported by Groq.

## 🐛 Troubleshooting Guide

### 1. Error: `Groq client not initialized`
-   **Cause**: The `GROQ_API_KEY` is missing or incorrect in `.env`.
-   **Fix**: Check the `.env` file for typos. Ensure there are no spaces around the `=`.

### 2. Error: `ModuleNotFoundError`
-   **Cause**: Dependencies are not installed.
-   **Fix**: Run `pip install -r requirements.txt`.

### 3. Application won't start (Port 5001 in use)
-   **Cause**: Another program is using port 5001.
-   **Fix**:
    -   **Windows**: `netstat -ano | findstr :5001` then `taskkill /PID <PID> /F`
    -   **Mac/Linux**: `lsof -ti:5001 | xargs kill -9`

### 4. PDF Text Extraction Issues
-   **Cause**: The PDF might be an image scan (not selectable text).
-   **Fix**: Use a PDF that has selectable text. OCR features are not currently enabled.

## 🔒 Security & Privacy Notes

-   **Data Retention**: Uploaded PDF files are temporary and cleaned up automatically (see `cleanup_old_files` in `app.py`).
-   **API Security**: Your API keys are stored in environment variables, not code.
-   **HTTPS**: For production use, always enable HTTPS (SSL) to encrypt resume data during upload.

## 📊 API Limits (Groq)

-   **Model**: Llama 3 70b Versatile.
-   **Rate Limits**: Refer to the Groq console for your specific tier limits (Tokens per minute / Requests per day).
-   **Cost**: Groq offers very competitive pricing and generous free tiers for developers.

## 🤝 Contributing

This project was built as a **Final Year College Project**. We welcome forkers and contributors!

1.  **Fork** the repository.
2.  Create a **Feature Branch** (`git checkout -b feature/NewFeature`).
3.  **Commit** your changes (`git commit -m 'Add NewFeature'`).
4.  **Push** to the branch (`git push origin feature/NewFeature`).
5.  Open a **Pull Request**.

## 👨‍💻 Development Team

**ATS Checker Team**
-   **Project Goal**: To democratize access to high-quality resume reviews.
-   **Tech Context**: Built using modern Python web standards and State-of-the-Art LLMs.

## 🙏 Acknowledgments

-   **Groq Inc.**: For providing high-speed inference for Llama 3.
-   **Meta AI**: For the Llama 3 model weights.
-   **Open Source Community**: For Flask, PyMuPDF, and ReportLab.

---
**Made with ❤️ for better career opportunities**
#   S m a r t H i r e  
 