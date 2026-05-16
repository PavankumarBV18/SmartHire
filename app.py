"""
Smart ATS Checker - Advanced Resume Analysis System
A Flask-based web application that uses Groq Llama 3 AI to analyze resumes
and provide ATS scoring, job matching, and improvement suggestions.

"""

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for, make_response
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime
import fitz  # PyMuPDF
from groq import Groq
from dotenv import load_dotenv
import re
import io
import time
import threading
from functools import wraps
from reportlab.lib.pagesizes import letter
from itertools import zip_longest

from services.job_matcher import add_user, match_jobs, load_users
from services.email_sender import send_job_alert_email
from services.save_resume import save_resume, get_resumes_by_user, get_resume_by_id, delete_user_resume, load_saved_resumes
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

# Custom Colors
teal = colors.HexColor('#008080')
# Load environment variables
load_dotenv(override=True)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('SECRET_KEY') or os.urandom(24).hex() # Fallback to random if not set
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Vercel Compatibility: Use /tmp for writable directories
IS_VERCEL = os.getenv('VERCEL') == '1'
BASE_DIR = '/tmp' if IS_VERCEL else os.getcwd()

app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['ANALYSIS_FOLDER'] = os.path.join(BASE_DIR, 'analysis_data')
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Configure Groq AI
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
client = None

ai_init_error = None

if GROQ_API_KEY and GROQ_API_KEY.strip():
    try:
        client = Groq(api_key=GROQ_API_KEY)
        print("Groq Client Successfully Initialized.")
    except Exception as e:
        ai_init_error = str(e)
        print(f"CRITICAL: Failed to initialize Groq client: {e}")
else:
    ai_init_error = "GROQ_API_KEY not found in environment variables."
    print(f"CRITICAL: {ai_init_error}")

# Ensure directories exist (handle potential OS errors in serverless)
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['ANALYSIS_FOLDER'], exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create directories: {e}")

@app.context_processor
def inject_ai_status():
    return dict(ai_ready=(client is not None))



# ============================================================================
# UNIFIED AI HELPER
# ============================================================================

def get_ai_completion(prompt, system_message="You are a helpful assistant.", temperature=0.1, max_tokens=4096, is_json=False):
    """Helper to call Groq AI"""
    if client:
        try:
            extra_params = {}
            if is_json:
                extra_params["response_format"] = {"type": "json_object"}
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=25.0,
                **extra_params
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Groq API Error: {e}")
            raise e

    raise Exception("Groq AI provider is not available.")


# In-memory storage for analysis results (use database in production)

analysis_storage = {}

def get_writable_path(filename):
    """Helper to get writable path for serverless environments"""
    if IS_VERCEL:
        # If it's a relative path in root, move to /tmp
        if not os.path.isabs(filename):
            # Check if it belongs to a folder we've already redirected
            if filename.startswith('uploads'):
                return os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(filename))
            if filename.startswith('analysis_data'):
                return os.path.join(app.config['ANALYSIS_FOLDER'], os.path.basename(filename))
            return os.path.join('/tmp', filename)
    return filename

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_current_user():
    email = session.get('user')
    if not email: return None
    from services.job_matcher import load_users
    users = load_users()
    for u in users:
        if u.get('email') == email:
            return u
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            from flask import flash
            flash("Please login to continue.", "info")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def premium_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            from flask import flash
            flash("Please login to continue.", "info")
            return redirect(url_for('login'))
        user = get_current_user()
        if session.get('user') == 'smarthire72@gmail.com':
            return f(*args, **kwargs)
        if user and (user.get('role') == 'admin' or user.get('plan') == 'premium'):
            return f(*args, **kwargs)
        return render_template('premium_locked.html')
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user') or session.get('role') != 'admin':
            from flask import flash
            flash("Admin access required.", "error")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function




@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    import traceback
    print(f"DEBUG: 500 Error: {error}")
    traceback.print_exc()
    return render_template('500.html'), 500

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "vercel": IS_VERCEL,
        "groq_ready": client is not None,
        "ai_error": ai_init_error,
        "timestamp": datetime.now().isoformat()
    })




@app.route('/subscription')
@login_required
def subscription():
    user = get_current_user()
    return render_template('subscription.html', user=user)

@app.route('/upgrade', methods=['POST'])
def upgrade():
    if not session.get('user'):
        return redirect(url_for('login'))
        
    email = session.get('user')
    plan_type = request.form.get('plan_type', 'monthly')
    
    try:
        from services.job_matcher import load_users, save_users
        from datetime import datetime, timedelta
        users = load_users()
        for u in users:
            if u.get('email') == email:
                # Calculate end date
                days = 30 if plan_type == 'monthly' else 365
                end_date = datetime.now() + timedelta(days=days)
                
                u['plan'] = 'premium'
                u['plan_type'] = plan_type
                u['subscription_end'] = end_date.strftime("%Y-%m-%d")
                
                session['plan'] = 'premium'
                session['subscription_end'] = u['subscription_end']
                
                save_users(users)
                from flask import flash
                flash(f"Successfully upgraded to {plan_type.capitalize()} Premium Plan! Valid until {u['subscription_end']}", "success")
                return redirect(url_for('subscription'))
    except Exception as e:
        print(f"Upgrade error: {e}")
        from flask import flash
        flash("System error during upgrade.", "error")
        
    return redirect(url_for('subscription'))

@app.route('/premium-locked')
def premium_locked():
    return render_template('premium_locked.html')


def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def extract_text_from_pdf(pdf_path):
    """
    Extract text content from PDF file using PyMuPDF
    Returns: Extracted text as string
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return "" # Return empty string instead of crashing, let validation handle it

def clean_json_response(text):
    """Clean and parse JSON response from AI"""
    try:
        # Find the first '{' and last '}'
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            return json.loads(json_str)
        
        # Fallback for standard markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        return json.loads(text.strip())
    except Exception as e:
        print(f"JSON Parse Error. Raw text: {text}")
        # Try one more time with simple cleanup
        try:
             return json.loads(text.replace("```json", "").replace("```", "").strip())
        except:
             raise Exception(f"Failed to parse AI response: {str(e)}")


def analyze_with_groq(resume_text, job_description=None):
    """
    Analyze resume using Groq (Llama 3)
    Returns: Structured analysis results as dictionary
    """
    try:
        if not client:
            raise Exception("Groq client not initialized. Check API Key.")

        prompt = f"""
You are an expert ATS (Applicant Tracking System) analyzer and career coach. Analyze the following resume and provide a comprehensive evaluation.

RESUME TEXT:
{resume_text}

{"JOB DESCRIPTION: " + job_description if job_description else "No specific job description provided."}

Provide a detailed analysis in valid JSON format with the following structure:
{{
    "ats_score": <number between 0-100>,
    "candidate_summary": {{
        "name": "<extracted name or 'Not found'>",
        "email": "<extracted email or 'Not found'>",
        "phone": "<extracted phone or 'Not found'>",
        "experience_years": "<estimated years>",
        "current_role": "<current or most recent role>",
        "overview": "<2-3 sentence professional summary>"
    }},
    "resume_strength": {{
        "score": <number between 0-100>,
        "formatting_score": <number between 0-100>,
        "content_quality": "<assessment of content quality>",
        "formatting_assessment": "<assessment of formatting and structure>",
        "formatting_issues": ["<e.g. Tables detected>", "<e.g. Icons used instead of text>", "<e.g. Non-standard font usage>"],
        "keyword_density": "<percentage or assessment>",
        "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
        "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"]
    }},
    "job_match": {{
        "score": <number between 0-100>,
        "hard_skills_match": <number between 0-100>,
        "soft_skills_match": <number between 0-100>,
        "keyword_coverage": <number between 0-100>,
        "matching_skills": ["<skill 1>", "<skill 2>", "<skill 3>"],
        "missing_skills": ["<skill 1>", "<skill 2>", "<skill 3>"],
        "relevance_assessment": "<detailed assessment of how well resume matches job>"
    }},
    "skill_analysis": {{
        "technical_skills": ["<skill 1>", "<skill 2>", "<skill 3>"],
        "soft_skills": ["<skill 1>", "<skill 2>", "<skill 3>"],
        "certifications": ["<cert 1>", "<cert 2>"],
        "skill_gaps": [
            {{
                "skill": "<missing skill 1>",
                "impact": "High/Critical",
                "learning_resources": ["<Resource 1: e.g. Coursera>", "<Resource 2: e.g. YouTube>", "<Resource 3: e.g. Documentation>"]
            }}
        ],
        "recommended_skills": ["<skill to add 1>", "<skill to add 2>"]
    }},
    "grammar_feedback": {{
        "score": <number between 0-100>,
        "issues_found": <number of issues>,
        "common_errors": ["<error 1>", "<error 2>"],
        "suggestions": ["<suggestion 1>", "<suggestion 2>"]
    }},
    "ai_suggestions": {{
        "immediate_improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
        "section_improvements": {{
            "summary": "<how to improve summary section>",
            "experience": "<how to improve experience section>",
            "skills": "<how to improve skills section>",
            "education": "<how to improve education section>"
        }},
        "keyword_recommendations": ["<keyword 1>", "<keyword 2>", "<keyword 3>"],
        "formatting_tips": ["<tip 1>", "<tip 2>", "<tip 3>"]
    }},
    "enhanced_sections": {{
        "improved_summary": "<AI-generated improved professional summary>",
        "improved_experience": "<AI-generated improved experience bullet points>",
        "action_verbs": ["<verb 1>", "<verb 2>", "<verb 3>"]
    }},
    "predicted_roles": [
        {{"role": "<role 1>", "match": <number 0-100>}},
        {{"role": "<role 2>", "match": <number 0-100>}},
        {{"role": "<role 3>", "match": <number 0-100>}}
    ],
    "interview_probability": <number 0-100>,
    "missing_sections": ["<e.g. Skills, Education, Projects>"],
    "security_scan": {{
        "issues": ["<e.g. Home address exposed>", "<e.g. Age or marital status included>"],
        "is_safe": <false if any personal info leaked, else true>
    }},
    "comparison": {{
        "your_resume": {{
            "pros": ["<pro 1>", "<pro 2>"],
            "cons": ["<con 1>", "<con 2>"]
        }},
        "ideal_resume": {{
            "should_have": ["<element 1>", "<element 2>"],
            "best_practices": ["<practice 1>", "<practice 2>"]
        }}
    }}
}}

Provide only valid JSON, no additional text or explanation. 
IMPORTANT: Ensure valid JSON output.
"""

        content = get_ai_completion(
            prompt=prompt,
            system_message="You are a helpful assistant that outputs only valid JSON.",
            temperature=0.1,
            max_tokens=4096,
            is_json=True
        )
        return clean_json_response(content)

    except Exception as e:
        raise Exception(f"AI analysis failed: {str(e)}")




def generate_enhanced_pdf(analysis_data, original_text):
    """Generate an AI-enhanced resume PDF"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title = Paragraph("<b>AI-Enhanced Resume: Upgrade your resume.</b>", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))

        # Candidate Information
        try:
            if 'candidate_summary' in analysis_data:
                candidate = analysis_data['candidate_summary']
                if isinstance(candidate, dict):
                    name = str(candidate.get('name', 'N/A'))
                    email = str(candidate.get('email', 'N/A'))
                    phone = str(candidate.get('phone', 'N/A'))
                    
                    story.append(Paragraph(f"<b>Name:</b> {name}", styles['Normal']))
                    story.append(Paragraph(f"<b>Email:</b> {email}", styles['Normal']))
                    story.append(Paragraph(f"<b>Phone:</b> {phone}", styles['Normal']))
                    story.append(Spacer(1, 12))
        except Exception as e:
            print(f"Error adding candidate info: {e}")

        # Improved Professional Summary
        story.append(Paragraph("<b>Professional Summary</b>", styles['Heading2']))
        try:
            summary_added = False
            if 'enhanced_sections' in analysis_data:
                enhanced = analysis_data['enhanced_sections']
                if isinstance(enhanced, dict) and 'improved_summary' in enhanced:
                    summary_text = str(enhanced['improved_summary'])
                    if summary_text and summary_text != 'None':
                        story.append(Paragraph(summary_text, styles['BodyText']))
                        summary_added = True
            
            if not summary_added and 'candidate_summary' in analysis_data:
                candidate = analysis_data['candidate_summary']
                if isinstance(candidate, dict) and 'overview' in candidate:
                    summary_text = str(candidate['overview'])
                    if summary_text and summary_text != 'None':
                        story.append(Paragraph(summary_text, styles['BodyText']))
                        summary_added = True
            
            if not summary_added:
                story.append(Paragraph("Professional with demonstrated experience in the field.", styles['BodyText']))
        except Exception as e:
            print(f"Error adding summary: {e}")
            story.append(Paragraph("Professional with demonstrated experience in the field.", styles['BodyText']))
        
        story.append(Spacer(1, 12))

        # Key Skills
        story.append(Paragraph("<b>Key Skills</b>", styles['Heading2']))
        try:
            if 'skill_analysis' in analysis_data:
                skills = analysis_data['skill_analysis']
                
                if isinstance(skills, dict):
                    # Technical Skills
                    if 'technical_skills' in skills:
                        tech_skills_list = skills['technical_skills']
                        if isinstance(tech_skills_list, list) and tech_skills_list:
                            tech_skills = ', '.join([str(s) for s in tech_skills_list[:10]])
                            story.append(Paragraph(f"<b>Technical:</b> {tech_skills}", styles['Normal']))
                    
                    # Soft Skills
                    if 'soft_skills' in skills:
                        soft_skills_list = skills['soft_skills']
                        if isinstance(soft_skills_list, list) and soft_skills_list:
                            soft_skills = ', '.join([str(s) for s in soft_skills_list[:10]])
                            story.append(Paragraph(f"<b>Soft Skills:</b> {soft_skills}", styles['Normal']))
        except Exception as e:
            print(f"Error adding skills: {e}")
        
        story.append(Spacer(1, 12))

        # Enhanced Experience Section
        story.append(Paragraph("<b>Professional Experience</b>", styles['Heading2']))
        try:
            exp_added = False
            if 'enhanced_sections' in analysis_data:
                enhanced = analysis_data['enhanced_sections']
                if isinstance(enhanced, dict) and 'improved_experience' in enhanced:
                    exp_text = enhanced['improved_experience']
                    if isinstance(exp_text, str) and exp_text and exp_text != 'None':
                        # Split by newlines and create paragraphs
                        exp_lines = exp_text.split('\n')
                        for line in exp_lines[:20]:  # Limit to 20 lines
                            if line.strip():
                                story.append(Paragraph(line.strip(), styles['BodyText']))
                        exp_added = True
            
            if not exp_added and original_text:
                # Use original text (first 1500 chars)
                original_preview = str(original_text)[:1500] if len(str(original_text)) > 1500 else str(original_text)
                # Clean the text
                original_preview = original_preview.replace('\n\n', '<br/><br/>').replace('\n', ' ')
                story.append(Paragraph(original_preview, styles['BodyText']))
        except Exception as e:
            print(f"Error adding experience: {e}")
            story.append(Paragraph("Experienced professional with a strong background.", styles['BodyText']))
        
        story.append(Spacer(1, 12))

        # AI Recommendations
        story.append(Paragraph("<b>AI Recommendations</b>", styles['Heading2']))
        try:
            if 'ai_suggestions' in analysis_data:
                suggestions = analysis_data['ai_suggestions']
                if isinstance(suggestions, dict) and 'immediate_improvements' in suggestions:
                    improvements = suggestions['immediate_improvements']
                    if isinstance(improvements, list):
                        for i, improvement in enumerate(improvements[:5], 1):
                            improvement_text = str(improvement)
                            story.append(Paragraph(f"{i}. {improvement_text}", styles['Normal']))
        except Exception as e:
            print(f"Error adding recommendations: {e}")
        
        story.append(Spacer(1, 24))

        # Footer
        story.append(Paragraph("<i>Generated by ATS Checker - AI-Powered Resume Analyzer</i>", styles['Normal']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    except Exception as e:
        print(f"PDF generation error details: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f"PDF generation failed: {str(e)}")


def generate_custom_resume(resume_text, target_job_description):
    """
    Generate a tailored resume using Groq (Llama 3)
    """
    try:
        if not client:
             raise Exception("Groq client not initialized")

        print("[DEBUG] Calling Groq API for resume generation...")
        prompt = f"""
        You are an expert professional resume writer specialized in ATS (Applicant Tracking System) optimization. I will provide a candidate's existing resume content and a target Job Description.
        Your task is to REWRITE and TAILOR the resume to specifically target this job description.

        CORE INSTRUCTIONS:
        1. ANALYZE the Job Description to identify key skills, keywords, and requirements.
        2. REWRITE the candidate's professional summary to align with these requirements, highlighting their most relevant experience.
        3. TAILOR the bullet points in the Experience section. Use strong action verbs and emphasize results that matter for the target role.
        4. REORDER skills to prioritize those mentioned in the JD.

        RULES:
        - Use ONLY facts from the existing resume. Do NOT invent experiences or skills not present in the source text.
        - You MAY rephrase, summarize, or expand on existing points to better match the JD's language.
        - Use STANDARD SECTION HEADINGS: "Professional Summary", "Experience", "Education", "Skills", "Projects".
        - NO tables, NO columns, NO graphics. Plain text structure is essential.

        EXISTING RESUME:
        {resume_text}

        TARGET JOB DESCRIPTION:
        {target_job_description}

        Output a comprehensive JSON object for the new resume with this structure:
        {{
            "personal_info": {{
                "name": "...",
                "contact_info": "..."
            }},
            "summary": "...",
            "skills": {{
                "technical": ["..."],
                "soft": ["..."]
            }},
            "experience": [
                {{
                    "title": "...",
                    "company": "...",
                    "dates": "...",
                    "bullets": ["...", "..."]
                }}
            ],
            "education": [
                {{
                    "degree": "...",
                    "school": "...",
                    "dates": "..."
                }}
            ],
            "projects": [
                {{
                    "name": "...",
                    "description": "...",
                    "technologies": "..."
                }}
            ]
        }}
        Provide only valid JSON.
        """
        print("[DEBUG] Calling AI for resume generation...")
        content = get_ai_completion(
            prompt=prompt,
            system_message="You are a resume expert that outputs valid JSON.",
            temperature=0.5,
            max_tokens=4096,
            is_json=True
        )
        print("[DEBUG] AI response received.")
        return clean_json_response(content)

    except Exception as e:
        print(f"Resume Gen Error: {e}")
        raise Exception(f"Resume generation failed: {str(e)}")


def analyze_job_description_with_ai(job_description):
    """
    Analyze job description using Groq
    """
    try:
        if not client: raise Exception("Groq client not initialized")
        
        prompt = f"""
You are an expert HR Specialist and Technical Recruiter. Analyze the following Job Description to extract structured information.

JOB DESCRIPTION:
{job_description}

Provide a comprehensive analysis in valid JSON format with the following structure:
{{
    "job_title": "<extracted title or 'Unknown'>",
    "summary": "<brief 2-sentence summary of the role>",
    "skills": {{
        "technical": ["<skill 1>", "<skill 2>", "..."],
        "soft": ["<skill 1>", "<skill 2>", "..."]
    }},
    "qualifications": ["<qualification 1>", "<qualification 2>", "..."],
    "responsibilities": ["<responsibility 1>", "<responsibility 2>", "..."],
    "keywords": [
        {{"keyword": "<keyword 1>", "importance": "High"}},
        {{"keyword": "<keyword 2>", "importance": "Medium"}}
    ],
    "culture_fit_clues": ["<clue 1>", "<clue 2>"]
}}
Provide only valid JSON.
"""
        content = get_ai_completion(
            prompt=prompt,
            system_message="You are a helpful assistant that outputs only valid JSON.",
            temperature=0.1,
            max_tokens=2048,
            is_json=True
        )
        return clean_json_response(content)
    except Exception as e:
        print(f"JD Analysis Error: {e}")
        raise Exception(f"JD Analysis failed: {str(e)}")



def rewrite_resume_section(text, improvement_type="Professional"):
    """
    Rewrite resume text based on selected style using Groq
    """
    try:
        if not client: raise Exception("Groq client not initialized")

        prompt = f"""
You are an expert professional resume editor. Rewrite the following text to make it more impactful.

TEXT TO IMPROVE:
{text}

IMPROVEMENT STYLE: {improvement_type}

Specific Instructions for {improvement_type}:
- Professional: Use strong action verbs, formal tone, and precise language.
- Creative: Use engaging language, slightly more vivid descriptors, but keep it professional.
- ATS-Friendly: Focus on standard keywords, simple formatting, and clarity.
- Concise: Shorten sentences, remove fluff, get straight to the point.
- Action-Oriented: Start every bullet/sentence with a powerful action verb.

Provide the improved text. Do not include explanations, just the rewritten content.
"""
        return get_ai_completion(
            prompt=prompt,
            system_message="You are a helpful editor.",
            temperature=0.3,
            max_tokens=1024,
            is_json=False
        )
    except Exception as e:
        raise Exception(f"Content rewrite failed: {str(e)}")



def generate_two_column_pdf(resume_data, accent_color=teal):
    """Generate a Two-Column Modern PDF Resume with Pagination Fix and Full Bleed"""
    try:
        buffer = io.BytesIO()
        # Full Bleed: Set all margins to 0
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0, leftMargin=0, topMargin=0, bottomMargin=0)
        styles = getSampleStyleSheet()
        
        # Dimensions
        page_width, page_height = letter
        sidebar_width = 180  # Optimized sidebar
        main_width = page_width - sidebar_width
        
        # Custom Styles
        # Increase padding in styles since we lost page margins
        style_left_header = ParagraphStyle('LeftHeader', parent=styles['Heading3'], textColor=colors.white, spaceAfter=8)
        style_left_text = ParagraphStyle('LeftText', parent=styles['Normal'], textColor=colors.white, fontSize=9, leading=12)
        style_right_header = ParagraphStyle('RightHeader', parent=styles['Heading3'], textColor=accent_color, spaceAfter=8, borderPadding=0)
        style_right_text = ParagraphStyle('RightText', parent=styles['BodyText'], fontSize=10, leading=14)
        style_name = ParagraphStyle('Name', parent=styles['Title'], textColor=accent_color, alignment=0, spaceAfter=10, fontSize=24)
        
        # --- LEFT COLUMN CHUNKS ---
        left_chunks = []
        
        # Add a top spacer for margin simulation
        left_chunks.append([Spacer(1, 15)]) 
        
        # 1. Contact Info
        if 'personal_info' in resume_data:
            info = resume_data['personal_info']
            if 'contact_info' in info:
                chunk = []
                chunk.append(Paragraph("<b>CONTACT</b>", style_left_header))
                contacts = info['contact_info'].replace(' | ', '\n').replace(', ', '\n').replace(' • ', '\n').split('\n')
                for contact in contacts:
                    chunk.append(Paragraph(contact, style_left_text))
                chunk.append(Spacer(1, 15))
                left_chunks.append(chunk)

        # 2. Skills
        if 'skills' in resume_data:
            chunk = []
            chunk.append(Paragraph("<b>SKILLS</b>", style_left_header))
            skills = resume_data['skills']
            if isinstance(skills, dict):
                if 'technical' in skills:
                    chunk.append(Paragraph("<b>Technical:</b>", style_left_text))
                    for skill in skills['technical']:
                        chunk.append(Paragraph(f"• {skill}", style_left_text))
                    chunk.append(Spacer(1, 5))
                if 'soft' in skills:
                    chunk.append(Paragraph("<b>Soft:</b>", style_left_text))
                    for skill in skills['soft']:
                         chunk.append(Paragraph(f"• {skill}", style_left_text))
            elif isinstance(skills, list):
                for skill in skills:
                    chunk.append(Paragraph(f"• {skill}", style_left_text))
            chunk.append(Spacer(1, 15))
            left_chunks.append(chunk)

        # 3. Education
        if 'education' in resume_data:
            chunk = []
            chunk.append(Paragraph("<b>EDUCATION</b>", style_left_header))
            for edu in resume_data['education']:
                school = edu.get('school', '')
                degree = edu.get('degree', '')
                dates = edu.get('dates', '')
                chunk.append(Paragraph(f"<b>{school}</b>", style_left_text))
                chunk.append(Paragraph(degree, style_left_text))
                chunk.append(Paragraph(dates, style_left_text))
                chunk.append(Spacer(1, 8))
            left_chunks.append(chunk)
        
        # --- RIGHT COLUMN CHUNKS ---
        right_chunks = []
        
        # Add a top spacer for margin simulation
        right_chunks.append([Spacer(1, 15)])
        
        # 1. Name
        if 'personal_info' in resume_data:
             name = resume_data['personal_info'].get('name', 'Candidate')
             right_chunks.append([Paragraph(name.upper(), style_name)])
        
        # 2. Summary
        if 'summary' in resume_data:
            chunk = []
            chunk.append(Paragraph("PROFESSIONAL SUMMARY", style_right_header))
            chunk.append(Paragraph(resume_data['summary'], style_right_text))
            chunk.append(Spacer(1, 12))
            right_chunks.append(chunk)
            
        # 3. Experience (One chunk per job to allow splitting)
        if 'experience' in resume_data:
            # Header
            right_chunks.append([Paragraph("EXPERIENCE", style_right_header)])
            
            for job in resume_data['experience']:
                chunk = []
                title = job.get('title', '')
                company = job.get('company', '')
                dates = job.get('dates', '')
                chunk.append(Paragraph(f"<b>{title}</b> | {company}", style_right_text))
                chunk.append(Paragraph(f"<i>{dates}</i>", style_right_text))
                for bullet in job.get('bullets', []):
                     chunk.append(Paragraph(f"• {bullet}", style_right_text))
                chunk.append(Spacer(1, 8))
                right_chunks.append(chunk)

        # 4. Projects (One chunk per project)
        if 'projects' in resume_data:
             right_chunks.append([Paragraph("PROJECTS", style_right_header)])
             for proj in resume_data['projects']:
                 chunk = []
                 name = proj.get('name', '')
                 desc = proj.get('description', '')
                 tech = proj.get('technologies', '')
                 chunk.append(Paragraph(f"<b>{name}</b> ({tech})", style_right_text))
                 chunk.append(Paragraph(desc, style_right_text))
                 chunk.append(Spacer(1, 8))
                 right_chunks.append(chunk)

        # --- BUILD MULTI-ROW TABLE ---
        table_data = []
        
        # Pair up chunks using zip_longest
        for left, right in zip_longest(left_chunks, right_chunks, fillvalue=[]):
            # Check for None inputs from zip_longest if lists are unequal length
            # zip_longest fills with the fillvalue (empty list)
            table_data.append([left if left is not None else [], right if right is not None else []])
            
        col_widths = [sidebar_width, main_width] 
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (0,-1), colors.Color(0.2, 0.2, 0.2)), # Dark Sidebar for Left Col
            # Padding simulates page margins
            ('LEFTPADDING', (0,0), (-1,-1), 20), # Sidebar content padding
            ('RIGHTPADDING', (0,0), (0,-1), 10), # Sidebar right padding
            ('LEFTPADDING', (1,0), (-1,-1), 20), # Main content padding
            ('RIGHTPADDING', (1,0), (-1,-1), 20), # Main content right padding
            ('TOPPADDING', (0,0), (-1,-1), 0), # Reduce row gaps
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        
        doc.build([t])
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Two Column PDF Error: {e}")
        # Build traceback
        import traceback
        traceback.print_exc()
        raise Exception(f"Two column PDF generation failed: {str(e)}")

def generate_zety_pdf(resume_data):
    """Generate a Zety-style PDF (Dark Sidebar)"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        
        # Colors
        dark_navy = colors.Color(0.17, 0.24, 0.31) # #2c3e50
        white = colors.white
        
        # Styles
        style_sidebar_header = ParagraphStyle('SidebarHead', parent=styles['Heading3'], textColor=white, spaceAfter=6, fontSize=11)
        style_sidebar_text = ParagraphStyle('SidebarText', parent=styles['Normal'], textColor=white, fontSize=9, leading=12)
        style_main_header = ParagraphStyle('MainHead', parent=styles['Heading2'], textColor=dark_navy, spaceAfter=8, borderPadding=0, spaceBefore=12)
        style_main_text = ParagraphStyle('MainText', parent=styles['BodyText'], fontSize=10, leading=14)
        style_name = ParagraphStyle('Name', parent=styles['Title'], textColor=dark_navy, alignment=0, spaceAfter=4, fontSize=26)
        style_role = ParagraphStyle('Role', parent=styles['Normal'], textColor=colors.gray, alignment=0, spaceAfter=12, fontSize=12)

        # --- LEFT (SIDEBAR) ---
        left_chunks = []
        
        # Contact
        if 'personal_info' in resume_data:
            info = resume_data['personal_info']
            if 'contact_info' in info:
                chunk = []
                chunk.append(Paragraph("<b>CONTACT</b>", style_sidebar_header))
                contacts = info['contact_info'].replace(' | ', '\n').replace(', ', '\n').replace(' • ', '\n').split('\n')
                for contact in contacts:
                    chunk.append(Paragraph(contact.strip(), style_sidebar_text))
                chunk.append(Spacer(1, 15))
                left_chunks.append(chunk)

        # Skills
        if 'skills' in resume_data:
            chunk = []
            chunk.append(Paragraph("<b>SKILLS</b>", style_sidebar_header))
            skills = resume_data['skills']
            if isinstance(skills, dict):
                 all_skills = skills.get('technical', []) + skills.get('soft', [])
            elif isinstance(skills, list):
                 all_skills = skills
            else:
                 all_skills = []
            
            for skill in all_skills[:12]: # Limit to prevent overflow
                chunk.append(Paragraph(f"• {skill}", style_sidebar_text))
            left_chunks.append(chunk)

        # --- RIGHT (MAIN) ---
        right_chunks = []
        
        # Header (Name position)
        if 'personal_info' in resume_data:
             info = resume_data['personal_info']
             name = info.get('name', 'Candidate')
             # We can add role if we had it, but resume_data structure matches what we have
             right_chunks.append([Paragraph(f"<b>{name.upper()}</b>", style_name)])

        # Summary
        if 'summary' in resume_data:
             chunk = []
             chunk.append(Paragraph("Summary", style_main_header))
             chunk.append(Paragraph(resume_data['summary'], style_main_text))
             right_chunks.append(chunk)

        # Experience
        if 'experience' in resume_data:
            chunk = []
            chunk.append(Paragraph("Experience", style_main_header))
            for job in resume_data['experience']:
                title = job.get('title', '')
                company = job.get('company', '')
                dates = job.get('dates', '')
                chunk.append(Paragraph(f"<b>{title}</b>", style_main_text))
                chunk.append(Paragraph(f"{company} | {dates}", style_main_text))
                for bullet in job.get('bullets', []):
                    chunk.append(Paragraph(f"• {bullet}", style_main_text))
                chunk.append(Spacer(1, 8))
            right_chunks.append(chunk)

        # Education
        if 'education' in resume_data:
            chunk = []
            chunk.append(Paragraph("Education", style_main_header))
            for edu in resume_data['education']:
                school = edu.get('school', '')
                degree = edu.get('degree', '')
                dates = edu.get('dates', '')
                chunk.append(Paragraph(f"<b>{degree}</b>", style_main_text))
                chunk.append(Paragraph(f"{school}, {dates}", style_main_text))
                chunk.append(Spacer(1, 8))
            right_chunks.append(chunk)

        # Build Table
        table_data = []
        for left, right in zip_longest(left_chunks, right_chunks, fillvalue=[]):
            table_data.append([left, right])
            
        t = Table(table_data, colWidths=[160, 360]) # Standardized widths to fit 552pt safe area
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND', (0,0), (0,-1), dark_navy), # Dark Sidebar
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        
        doc.build([t])
        buffer.seek(0)
        return buffer
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Zety PDF failed: {str(e)}")

def generate_harrison_pdf(resume_data):
    """Generate a Harrison-style PDF (Yellow Header)"""
    try:
        buffer = io.BytesIO()
        # Top margin bigger to accommodate header
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=140, leftMargin=40, rightMargin=40, bottomMargin=30)
        styles = getSampleStyleSheet()
        
        # Colors
        yellow = colors.Color(1, 0.88, 0.2) # #ffdf32 (approx Harrison yellow)
        black = colors.black
        
        # Styles
        style_section_head = ParagraphStyle('SecHead', parent=styles['Heading2'], textColor=black, 
                                          borderWidth=0, borderPadding=0, spaceAfter=8, spaceBefore=4,
                                          fontName='Helvetica-Bold', fontSize=10, textTransform='uppercase')
        
        # Section line/box (We will simulate with a drawing or just simple underline)
        # Harrison uses bold black lines.
        
        style_text = ParagraphStyle('Text', parent=styles['BodyText'], fontSize=10, leading=14, spaceAfter=4)
        style_bold = ParagraphStyle('BoldText', parent=styles['BodyText'], fontSize=10, leading=14, fontName='Helvetica-Bold')

        story = []
        
        # Helper for header drawing
        def draw_header(canvas, doc):
            canvas.saveState()
            # Draw Yellow Header Background
            canvas.setFillColor(yellow)
            canvas.rect(0, letter[1]-130, letter[0], 130, stroke=0, fill=1)
            
            # Draw Name
            canvas.setFillColor(black)
            canvas.setFont("Helvetica-Bold", 32)
            if 'personal_info' in resume_data:
                name = resume_data['personal_info'].get('name', 'NAME').upper()
                canvas.drawString(40, letter[1]-60, name)
                
                # Draw Role/Title (Mockup if not in data, or use contact)
                # resume_data doesn't stricly have 'role', we can use first job title or just leave empty
                contacts = resume_data['personal_info'].get('contact_info', '')
                canvas.setFont("Helvetica", 10)
                canvas.drawString(40, letter[1]-85, contacts)
                
            canvas.restoreState()

        # Content - Single Column
        
        # Summary
        if 'summary' in resume_data:
            # We can use a Drawing Flowable for the thick black line, or just a Paragraph
            story.append(Paragraph("<b>PROFILE</b>", style_section_head))
            # Draw line?
            story.append(Paragraph(resume_data['summary'], style_text))
            story.append(Spacer(1, 15))
            
        # Experience
        if 'experience' in resume_data:
            story.append(Paragraph("<b>EMPLOYMENT HISTORY</b>", style_section_head))
            for job in resume_data['experience']:
                title = job.get('title', '')
                company = job.get('company', '')
                dates = job.get('dates', '')
                
                story.append(Paragraph(f"{title}, {company}", style_bold))
                story.append(Paragraph(dates.upper(), ParagraphStyle('Date', parent=style_text, fontSize=8, textColor=colors.gray)))
                
                for bullet in job.get('bullets', []):
                    story.append(Paragraph(f"• {bullet}", style_text))
                story.append(Spacer(1, 10))

        # Education
        if 'education' in resume_data:
            story.append(Paragraph("<b>EDUCATION</b>", style_section_head))
            for edu in resume_data['education']:
                school = edu.get('school', '')
                degree = edu.get('degree', '')
                dates = edu.get('dates', '')
                story.append(Paragraph(f"{degree}, {school}", style_bold))
                story.append(Paragraph(dates, style_text))
                story.append(Spacer(1, 5))

        # Skills
        if 'skills' in resume_data:
            story.append(Paragraph("<b>SKILLS</b>", style_section_head))
            skills = resume_data['skills']
            if isinstance(skills, dict):
                 tech = ", ".join(skills.get('technical', []))
                 soft = ", ".join(skills.get('soft', []))
                 if tech: story.append(Paragraph(f"<b>Technical:</b> {tech}", style_text))
                 if soft: story.append(Paragraph(f"<b>Soft:</b> {soft}", style_text))
            elif isinstance(skills, list):
                 story.append(Paragraph(", ".join(skills), style_text))

        doc.build(story, onFirstPage=draw_header, onLaterPages=draw_header)
        buffer.seek(0)
        return buffer
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Harrison PDF failed: {str(e)}")

def generate_elegant_pdf(resume_data):
    """Generate an 'Elegant' PDF (Gray Header, Bordered)"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        # Colors
        gray_bg = colors.Color(0.95, 0.96, 0.97) # #f3f4f6
        dark_text = colors.Color(0.1, 0.1, 0.1)
        border_color = colors.Color(0.8, 0.8, 0.8)
        
        # Styles
        style_header_name = ParagraphStyle('HeadName', parent=styles['Title'], fontSize=24, alignment=1, textColor=dark_text, spaceAfter=4, fontName='Helvetica-Bold')
        style_header_title = ParagraphStyle('HeadTitle', parent=styles['Normal'], fontSize=12, alignment=1, textColor=colors.gray, spaceAfter=12, textTransform='uppercase', letterSpacing=1)
        style_header_contact = ParagraphStyle('HeadContact', parent=styles['Normal'], fontSize=9, alignment=1, textColor=dark_text)
        
        style_section = ParagraphStyle('Sec', parent=styles['Heading3'], fontSize=10, textColor=dark_text, 
                                     borderWidth=0, borderPadding=0, spaceAfter=8, spaceBefore=0, 
                                     fontName='Helvetica-Bold', textTransform='uppercase')
        
        style_item_title = ParagraphStyle('ItemTitle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', leading=12)
        style_item_sub = ParagraphStyle('ItemSub', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Oblique', textColor=colors.gray, leading=12)
        style_text = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=13)
        
        story = []
        
        # --- HEADER SECTION (Gray Box) ---
        header_content = []
        if 'personal_info' in resume_data:
            info = resume_data['personal_info']
            name = info.get('name', 'CANDIDATE NAME').upper()
            contact = info.get('contact_info', '')
            
            header_content.append(Paragraph(name, style_header_name))
            header_content.append(Paragraph(contact, style_header_contact))
            
        header_table = Table([[header_content]], colWidths=[532]) # Full width (612 - 80 margin)
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), gray_bg),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 20),
            ('BOTTOMPADDING', (0,0), (-1,-1), 20),
            ('BOX', (0,0), (-1,-1), 0.5, border_color), # Thin border
        ]))
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        # --- BODY CONTENT ---
        left_chunks = []
        
        # Education (Left)
        if 'education' in resume_data:
            chunk = []
            chunk.append(Paragraph("EDUCATION", style_section))
            chunk.append(Spacer(1, 4))
            for edu in resume_data['education']:
                degree = edu.get('degree', '')
                school = edu.get('school', '')
                dates = edu.get('dates', '')
                chunk.append(Paragraph(degree, style_item_title))
                chunk.append(Paragraph(school, style_item_sub))
                chunk.append(Paragraph(dates, style_text))
                chunk.append(Spacer(1, 8))
            left_chunks.append(chunk)

        # Skills (Left)
        if 'skills' in resume_data:
            chunk = []
            chunk.append(Paragraph("SKILLS", style_section))
            chunk.append(Spacer(1, 4))
            skills = resume_data['skills']
            if isinstance(skills, dict):
                 tech = ", ".join(skills.get('technical', []))
                 soft = ", ".join(skills.get('soft', []))
                 if tech: 
                     chunk.append(Paragraph("Technical", style_item_title))
                     chunk.append(Paragraph(tech, style_text))
                     chunk.append(Spacer(1, 4))
                 if soft: 
                     chunk.append(Paragraph("Soft Skills", style_item_title))
                     chunk.append(Paragraph(soft, style_text))
            elif isinstance(skills, list):
                 chunk.append(Paragraph(", ".join(skills), style_text))
            left_chunks.append(chunk)
            
        right_chunks = []
        
        # Summary (Right)
        if 'summary' in resume_data:
            chunk = []
            chunk.append(Paragraph("PROFESSIONAL SUMMARY", style_section))
            chunk.append(Spacer(1, 4))
            chunk.append(Paragraph(resume_data['summary'], style_text))
            chunk.append(Spacer(1, 15))
            right_chunks.append(chunk)
            
        # Experience (Right)
        if 'experience' in resume_data and resume_data['experience']:
            # Header
            right_chunks.append([Paragraph("WORK EXPERIENCE", style_section), Spacer(1, 4)])
            
            for job in resume_data['experience']:
                chunk = []
                title = job.get('title', '')
                company = job.get('company', '')
                dates = job.get('dates', '')
                
                chunk.append(Paragraph(title, style_item_title))
                chunk.append(Paragraph(f"{company} | {dates}", style_item_sub))
                
                for bullet in job.get('bullets', []):
                    chunk.append(Paragraph(f"• {bullet}", style_text))
                chunk.append(Spacer(1, 10))
                right_chunks.append(chunk)

        # Projects (Right)
        if 'projects' in resume_data and resume_data['projects']:
             right_chunks.append([Paragraph("PROJECTS", style_section), Spacer(1, 4)])
             for proj in resume_data['projects']:
                 chunk = []
                 name = proj.get('name', '')
                 desc = proj.get('description', '')
                 tech = proj.get('technologies', '')
                 chunk.append(Paragraph(name, style_item_title))
                 chunk.append(Paragraph(f"({tech})", style_item_sub))
                 chunk.append(Paragraph(desc, style_text))
                 chunk.append(Spacer(1, 8))
                 right_chunks.append(chunk)

        # Assemble Two-Column Body
        body_data = []
        for left, right in zip_longest(left_chunks, right_chunks, fillvalue=[]):
            body_data.append([left, right])
            
        body_table = Table(body_data, colWidths=[170, 340])
        body_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (0,-1), 15), # Padding between columns
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LINEAFTER', (0,0), (0,-1), 0.5, border_color),
        ]))
        
        story.append(body_table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise Exception(f"Elegant PDF failed: {str(e)}")

def generate_brand_new_pdf(resume_data, template_name='classic'):
    """Generate a PDF from the structured resume data"""
    
    # Route to Specific Template Functions
    if template_name == 'modern':
        return generate_two_column_pdf(resume_data, accent_color=teal)
    elif template_name == 'zety':
        return generate_zety_pdf(resume_data)
    elif template_name == 'harrison':
        return generate_harrison_pdf(resume_data)
    elif template_name == 'elegant':
        return generate_elegant_pdf(resume_data)
        
    # Define styles based on other templates (Classic / Creative)
    if template_name == 'creative':
        accent_color = colors.purple
        title_alignment = 0 # Left
    else: # Classic
        accent_color = colors.Color(0.145, 0.388, 0.922) # #2563eb
        title_alignment = 0 # Left

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        story = []

        # Heading Style
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            textColor=accent_color,
            fontSize=14,
            borderPadding=2,
            borderColor=accent_color,
            borderWidth=0,
            borderBottomWidth=0.5,
            spaceAfter=6,
            spaceBefore=12,
            alignment=title_alignment
        )
        
        # Title Style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            alignment=title_alignment,
            spaceAfter=12
        )

        # Header
        if 'personal_info' in resume_data:
            info = resume_data['personal_info']
            name = info.get('name', '')
            contact = info.get('contact_info', '')
            
            # Standard Font (Helvetica) for ATS
            story.append(Paragraph(f"<b>{name}</b>", title_style))
            story.append(Paragraph(contact, styles['Normal']))

        # Summary
        if 'summary' in resume_data:
            story.append(Paragraph("<b>Professional Summary</b>", heading_style)) 
            story.append(Paragraph(resume_data['summary'], styles['BodyText']))
        
        # Skills
        if 'skills' in resume_data:
            story.append(Paragraph("<b>Skills</b>", heading_style)) 
            skills = resume_data['skills']
            if isinstance(skills, dict):
                tech = ", ".join(skills.get('technical', []))
                soft = ", ".join(skills.get('soft', []))
                # Simple list format is best for ATS
                if tech: story.append(Paragraph(f"<b>Technical:</b> {tech}", styles['Normal']))
                if soft: story.append(Paragraph(f"<b>Soft:</b> {soft}", styles['Normal']))
            elif isinstance(skills, list):
                story.append(Paragraph(", ".join(skills), styles['Normal']))

        # Experience
        if 'experience' in resume_data and resume_data['experience']:
            story.append(Paragraph("<b>Experience</b>", heading_style))
            for job in resume_data['experience']:
                title = job.get('title', '')
                company = job.get('company', '')
                dates = job.get('dates', '')
                # Clean format: Title at Company | Dates
                # We can also color the Title
                header = f"<b><font color={accent_color}>{title}</font></b> at {company} | {dates}"
                story.append(Paragraph(header, styles['Normal']))
                for bullet in job.get('bullets', []):
                    story.append(Paragraph(f"• {bullet}", styles['BodyText']))
        
        # Education
        if 'education' in resume_data and resume_data['education']:
            story.append(Paragraph("<b>Education</b>", heading_style))
            for edu in resume_data['education']:
                 degree = edu.get('degree', '')
                 school = edu.get('school', '')
                 dates = edu.get('dates', '')
                 cgpa = edu.get('cgpa', '')
                 
                 edu_text = f"{degree}, {school} - {dates}"
                 if cgpa:
                     edu_text += f" | CGPA/Percentage: {cgpa}"
                     
                 story.append(Paragraph(edu_text, styles['Normal']))
            story.append(Spacer(1, 12))

        # Certifications
        if 'certifications' in resume_data and resume_data['certifications']:
            story.append(Paragraph("<b>Certifications</b>", heading_style))
            for cert in resume_data['certifications']:
                 story.append(Paragraph(f"• {cert}", styles['Normal']))
            story.append(Spacer(1, 12))
            
        # Achievements
        if 'achievements' in resume_data and resume_data['achievements']:
            story.append(Paragraph("<b>Achievements</b>", heading_style))
            for ach in resume_data['achievements']:
                 story.append(Paragraph(f"• {ach}", styles['Normal']))
            story.append(Spacer(1, 12))

        # Projects
        if 'projects' in resume_data and resume_data['projects']:
            story.append(Paragraph("<b>Projects</b>", heading_style)) 
            for proj in resume_data['projects']:
                 name = proj.get('name', '')
                 desc = proj.get('description', '')
                 tech = proj.get('technologies', '')
                 story.append(Paragraph(f"<b><font color={accent_color}>{name}</font></b> ({tech})", styles['Normal']))
                 story.append(Paragraph(desc, styles['BodyText']))
                 
        # Languages
        if 'languages' in resume_data and resume_data['languages']:
            story.append(Paragraph("<b>Languages Known</b>", heading_style))
            story.append(Paragraph(", ".join(resume_data['languages']), styles['Normal']))
            story.append(Spacer(1, 12))
            
        # Hobbies
        if 'hobbies' in resume_data and resume_data['hobbies']:
            story.append(Paragraph("<b>Hobbies & Interests</b>", heading_style))
            story.append(Paragraph(", ".join(resume_data['hobbies']), styles['Normal']))
            story.append(Spacer(1, 12))
        
        doc.build(story)
            
        buffer.seek(0)
        return buffer
    except Exception as e:
        raise Exception(f"New PDF generation failed: {str(e)}")


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            from services.job_matcher import load_users
            from werkzeug.security import check_password_hash
            users = load_users()
            for u in users:
                if u.get('email') == email:
                    stored_password = u.get('password')
                    # Support both plaintext and hashed passwords
                    is_valid = False
                    if stored_password.startswith('scrypt:') or stored_password.startswith('pbkdf2:'):
                        is_valid = check_password_hash(stored_password, password)
                    else:
                        is_valid = (stored_password == password)
                        
                    if is_valid:
                        session['user'] = email
                        session['role'] = u.get('role', 'user')
                        session['plan'] = u.get('plan', 'free')
                        session['plan_type'] = u.get('plan_type')
                        session['subscription_end'] = u.get('subscription_end')

                        if u.get('email') == 'smarthire72@gmail.com' or u.get('role') == 'admin':
                             session['role'] = 'admin'
                             session['plan'] = 'premium'

                        session['just_logged_in'] = True
                        return redirect('/dashboard')
            return render_template('login.html', error='Invalid credentials')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template('login.html', error='System error loading credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name', '')
        phone = request.form.get('phone', '')
        education = request.form.get('education', '')
        skills_raw = request.form.get('skills', '')
        skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
        
        try:
            from services.job_matcher import load_users, save_users
            from werkzeug.security import generate_password_hash
            users = load_users()
            
            # Check if exists
            for u in users:
                if u.get('email') == email:
                    return render_template('register.html', error='User already exists. Please login.')
            
            hashed_password = generate_password_hash(password)
            users.append({
                "email": email, 
                "password": hashed_password,
                "full_name": full_name,
                "phone": phone,
                "education": education,
                "skills": skills,
                "role": "user",
                "plan": "free"
            })
            
            save_users(users)
                
            from flask import flash
            flash('Registration successful! Please sign in.', 'success')
            return redirect('/login')
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template('register.html', error='System error during registration')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect('/login'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.after_request
def add_header(response):
    protected_endpoints = ['admin_job_alert', 'add_job', 'delete_job_route', 'edit_job_route', 'show_dashboard']
    if request.endpoint in protected_endpoints:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response




@app.route("/add-job", methods=["POST"])
@admin_required
def add_job_post():
    if not session.get("user"):
        return redirect("/login")
    
    title = request.form.get("title", "Untitled Job")
    company = request.form.get("company", "Unknown")
    skills_raw = request.form.get("skills", "")
    skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
    description = request.form.get("description", "")
    location = request.form.get("location", "")
    apply_link = request.form.get("apply_link", "")
    
    from services.job_matcher import add_job_and_notify
    try:
        add_job_and_notify(title, company, skills, description, location, apply_link)
        from flask import flash
        flash("Job Alert successfully created and notifications triggered!", "success")
    except Exception as e:
        from flask import flash
        flash(f"Failed to create job alert: {str(e)}", "error")
        
    return redirect("/admin-dashboard")

@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():
        
    from services.job_matcher import load_users, load_jobs
    from services.save_resume import load_saved_resumes
    
    users = load_users()
    jobs = load_jobs()
    history = load_saved_resumes()
    
    total_users = len([u for u in users if u.get('role') != 'admin'])
    premium_users = len([u for u in users if u.get('plan') == 'premium' and u.get('role') != 'admin'])
    total_resumes = len(history)
    total_jobs = len(jobs)
    total_alerts = total_jobs * max(1, total_users // 2)

    feedback = []
    if os.path.exists('feedback.json'):
        try:
            with open('feedback.json', 'r') as f:
                feedback = json.load(f)
        except:
            pass
            
    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        premium_users=premium_users,
        total_resumes=total_resumes,
        total_jobs=total_jobs,
        total_alerts=total_alerts,
        jobs=jobs,
        enumerated_jobs=list(enumerate(jobs)),
        users=users,
        history=history
    )

@app.route("/admin-job-alert")
def admin_job_alert_compat():
    return redirect("/admin-dashboard")

@app.route("/send-alert", methods=['POST', 'GET'])
def send_alert():
    if not session.get("user"):
        return redirect("/login")
    return redirect("/admin-dashboard")

@app.route("/delete-job/<int:index>", methods=['POST'])
def delete_job_route(index):
    if not session.get("user"):
        return redirect("/login")
    from services.job_matcher import delete_job
    try:
        if delete_job(index):
            from flask import flash
            flash("Job Alert successfully deleted.", "success")
        else:
            from flask import flash
            flash("Job not found.", "error")
    except Exception as e:
        from flask import flash
        flash(f"Error deleting job: {e}", "error")
    return redirect("/admin-dashboard")

@app.route("/edit-job/<int:index>", methods=['GET', 'POST'])
def edit_job_route(index):
    if not session.get("user"):
        return redirect("/login")
        
    from services.job_matcher import load_jobs, update_job_and_notify
    jobs = load_jobs()
    
    if index < 0 or index >= len(jobs):
        from flask import flash
        flash("Job not found.", "error")
        return redirect("/admin-job-alert")
        
    job = jobs[index]
    
    if request.method == 'POST':
        title = request.form.get("title", job.get("title"))
        company = request.form.get("company", job.get("company"))
        skills_raw = request.form.get("skills", "")
        skills = [s.strip() for s in skills_raw.split(',') if s.strip()] if skills_raw else job.get("skills", [])
        description = request.form.get("description", job.get("description", ""))
        location = request.form.get("location", job.get("location", ""))
        apply_link = request.form.get("apply_link", job.get("apply_link", ""))
        
        try:
            update_job_and_notify(index, title, company, skills, description, location, apply_link)
            from flask import flash
            flash("Job Alert successfully updated and notifications re-triggered!", "success")
            return redirect("/admin-dashboard")
        except Exception as e:
            from flask import flash
            flash(f"Error updating job: {e}", "error")
            
    return render_template('admin_dashboard.html', jobs=jobs, enumerated_jobs=list(enumerate(jobs)), edit_job=job, edit_index=index)

@app.route('/')
def index():
    """Selection Screen / Landing Redirect"""
    if session.get('user'):
        if session.get('role') == 'admin':
            return redirect('/admin-dashboard')
        return redirect('/dashboard')
    return render_template('selection.html')

@app.route('/admin-key-verify', methods=['GET', 'POST'])
def admin_key_verify():
    if request.method == 'POST':
        key = request.form.get('admin_key')
        if key == "123456789":
            session['admin_key_verified'] = True
            return redirect('/admin-signup')
        else:
            return render_template('admin_key_verify.html', error='Invalid Admin Key')
    return render_template('admin_key_verify.html')

@app.route('/admin-signup', methods=['GET', 'POST'])
def admin_signup():
    if not session.get('admin_key_verified'):
        return redirect('/admin-key-verify')
        
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        from services.job_matcher import load_users, save_users
        from werkzeug.security import generate_password_hash
        
        users = load_users()
        if any(u.get('email') == email for u in users):
            return render_template('admin_register.html', error='Email already registered')
            
        new_admin = {
            'full_name': full_name,
            'email': email,
            'password': generate_password_hash(password),
            'role': 'admin',
            'plan': 'premium' # Admins are always premium
        }
        users.append(new_admin)
        save_users(users)
        
        session.pop('admin_key_verified', None)
        return redirect('/admin-login')
        
    return render_template('admin_register.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        from services.job_matcher import load_users
        from werkzeug.security import check_password_hash
        
        users = load_users()
        for u in users:
            if u.get('email') == email and u.get('role') == 'admin':
                if check_password_hash(u.get('password'), password):
                    session['user'] = email
                    session['role'] = 'admin'
                    session['plan'] = 'premium'
                    session['plan_type'] = u.get('plan_type', 'yearly')
                    session['subscription_end'] = u.get('subscription_end', 'Never')
                    session['just_logged_in'] = True
                    return redirect('/admin-dashboard')
        
        return render_template('admin_login.html', error='Invalid Email or Password')
        
    return render_template('admin_login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """User Central Dashboard"""
    return render_template('user_dashboard.html')

@app.route('/home')
def home():
    """Landing Page"""
    if session.get('user'):
        return redirect('/dashboard')
    return render_template('index.html')


@app.route('/status')
def system_status():
    """Check system status"""
    status = {
        'groq_initialized': client is not None,
        'key_configured': GROQ_API_KEY is not None and len(GROQ_API_KEY) > 0,
        'key_preview': f"{GROQ_API_KEY[:7]}...{GROQ_API_KEY[-4:]}" if GROQ_API_KEY else "Missing",
        'timestamp': datetime.now().isoformat()
    }
    return jsonify(status)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_resume():
    """Manual Resume Creation"""
    if request.method == 'POST':
        try:
            phone_val = request.form.get('phone', '').strip()
            import re
            if phone_val and not re.match(r'^(?:\+91\s?)?[6789]\d{9}$', phone_val):
                return "Invalid Phone Number. Must be a valid Indian phone number.", 400

            # Logic to extract form data and create JSON
            data = {
                'personal_info': {
                    'name': request.form.get('name'),
                    'email': request.form.get('email'),
                    'phone': phone_val,
                    'contact_info': f"{request.form.get('email')} | {phone_val} | {request.form.get('links', '')}"
                },
                'summary': request.form.get('summary'),
                'skills': {
                    'technical': [s.strip() for s in request.form.get('technical_skills', '').split(',') if s.strip()],
                    'soft': [s.strip() for s in request.form.get('soft_skills', '').split(',') if s.strip()]
                },
                'experience': [],
                'education': [],
                'projects': [],
                'hobbies': [h.strip() for h in request.form.get('hobbies', '').split(',') if h.strip()],
                'certifications': [c.strip() for c in request.form.get('certifications', '').split('\n') if c.strip()],
                'achievements': [a.strip() for a in request.form.get('achievements', '').split('\n') if a.strip()],
                'languages': [l.strip() for l in request.form.get('languages', '').split(',') if l.strip()]
            }

            # Extract dynamic lists
            titles = request.form.getlist('exp_title[]')
            companies = request.form.getlist('exp_company[]')
            dates = request.form.getlist('exp_dates[]')
            descs = request.form.getlist('exp_desc[]')
            
            for i in range(len(titles)):
                title_val = titles[i].strip() if i < len(titles) else ''
                company_val = companies[i].strip() if i < len(companies) else ''
                if title_val or company_val:
                    desc_val = descs[i] if i < len(descs) else ''
                    date_val = dates[i] if i < len(dates) else ''
                    data['experience'].append({
                        'title': title_val,
                        'company': company_val,
                        'dates': date_val,
                        'bullets': [b.strip() for b in desc_val.split('\n') if b.strip()]
                    })

            degrees = request.form.getlist('edu_degree[]')
            schools = request.form.getlist('edu_school[]')
            edates = request.form.getlist('edu_dates[]')
            cgpas = request.form.getlist('edu_cgpa[]')

            for i in range(len(degrees)):
                deg_val = degrees[i].strip() if i < len(degrees) else ''
                if deg_val:
                    cgpa_val = cgpas[i] if i < len(cgpas) else ''
                    school_val = schools[i] if i < len(schools) else ''
                    edates_val = edates[i] if i < len(edates) else ''
                    data['education'].append({
                        'degree': deg_val,
                        'school': school_val,
                        'dates': edates_val,
                        'cgpa': cgpa_val
                    })

            pnames = request.form.getlist('proj_name[]')
            ptech = request.form.getlist('proj_tech[]')
            pdesc = request.form.getlist('proj_desc[]')

            for i in range(len(pnames)):
                pname_val = pnames[i].strip() if i < len(pnames) else ''
                if pname_val:
                    ptech_val = ptech[i] if i < len(ptech) else ''
                    pdesc_val = pdesc[i] if i < len(pdesc) else ''
                    data['projects'].append({
                        'name': pname_val,
                        'technologies': ptech_val,
                        'description': pdesc_val
                    })

            # Generate PDF
            # Process Job Alerts for extracted email and skills
            try:
                email_val = data.get('personal_info', {}).get('email')
                skills_tech = data.get('skills', {}).get('technical', [])
                skills_soft = data.get('skills', {}).get('soft', [])
                all_skills = skills_tech + skills_soft
                
                if email_val and '@' in email_val:
                    add_user(email_val, all_skills)
                    matched_results = match_jobs(all_skills)
                    for result in matched_results:
                        threading.Thread(target=send_job_alert_email, args=(email_val, result["job"], result["matched_skills"]), daemon=True).start()
            except Exception as e:
                print(f"Error processing job alerts: {e}")

            template = request.form.get('template', 'modern')
            pdf_buffer = generate_brand_new_pdf(data, template_name=template)
            
            # Save generated PDF locally to be previewable via history
            resume_filename = f"gen_resume_{data['personal_info'].get('name', 'User')}_{uuid.uuid4().hex[:8]}.pdf"
            resume_filepath = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
            with open(resume_filepath, 'wb') as f:
                f.write(pdf_buffer.getvalue())

            if email_val and '@' in email_val:
                try:
                    save_resume(
                        email=email_val, 
                        resume_name=f"{data['personal_info'].get('name', 'My')} Resume - {template.title()}",
                        skills=all_skills,
                        ats_score=None,
                        file_path=resume_filepath
                    )
                except Exception as e:
                    print(f"Error saving to history: {e}")
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"Resume_{data['personal_info']['name']}_{template}.pdf"
            )

        except Exception as e:
            print(f"Create Resume Error: {e}")
            return f"Error creating resume: {str(e)}", 500

    return render_template('create.html')


@app.route('/upload-home', methods=['GET', 'POST'])
@login_required
def upload_home():
    """Handle Resume Generation (Home Page)"""
    if request.method == 'POST':
        try:
            # File validation
            if 'resume' not in request.files:
                return jsonify({'error': 'No resume file uploaded'}), 400
            file = request.files['resume']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type'}), 400
            
            print(f"[DEBUG] Processing new resume generation request: {file.filename}")
            
            job_description = request.form.get('job_description', '').strip()
            if not job_description:
                return jsonify({'error': 'Job description is required'}), 400

            # Get ATS Mode preference
            ats_mode = request.form.get('ats_mode') == 'on' # Checkbox sends 'on' if checked

            # Save and extract
            filename = secure_filename(file.filename)
            unique_filename = f"gen_{uuid.uuid4()}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            try:
                resume_text = extract_text_from_pdf(filepath)
            except Exception as e:
                return jsonify({'error': 'Failed to read PDF'}), 500
            
            # Generate
            print("[DEBUG] Starting AI generation...")
            generated_data = generate_custom_resume(resume_text, job_description)
            print("[DEBUG] AI generation successful.")
            
            # Process Job Alerts
            try:
                candidate_email = ""
                # try to extract email from contact info
                contact_info = generated_data.get('personal_info', {}).get('contact_info', '')
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_info)
                if email_match:
                    candidate_email = email_match.group(0)
                
                if candidate_email:
                    skills_dict = generated_data.get('skills', {})
                    all_skills = skills_dict.get('technical', []) + skills_dict.get('soft', [])
                    add_user(candidate_email, all_skills)
                    matched_results = match_jobs(all_skills)
                    for result in matched_results:
                        threading.Thread(target=send_job_alert_email, args=(candidate_email, result["job"], result["matched_skills"]), daemon=True).start()
                    
                    # Save to History
                    save_resume(
                        email=candidate_email,
                        resume_name=f"Generated - {filename}",
                        skills=all_skills,
                        ats_score=None,
                        file_path=filepath
                    )
            except Exception as e:
                print(f"Error processing job alerts or history: {e}")

            # Save generated data
            
            gen_id = str(uuid.uuid4())
            gen_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"gen_{gen_id}.json")
            with open(gen_file, 'w') as f:
                json.dump(generated_data, f)
            
            return jsonify({
                'success': True,
                'redirect': url_for('show_generated_resume', gen_id=gen_id)
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return render_template('upload_home.html')


@app.route('/tips')
@login_required
def tips():
    """Resume tips and best practices page"""
    return render_template('tips.html')


@app.route('/clear-session')
def clear_session():
    """Clear current session and analysis data"""
    # Clean up uploaded files and analysis data
    if 'current_analysis_id' in session:
        analysis_id = session['current_analysis_id']
        analysis_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"{analysis_id}.json")
        
        # Load and delete associated files
        try:
            with open(analysis_file, 'r') as f:
                analysis = json.load(f)
            filepath = analysis.get('filepath')
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            os.remove(analysis_file)
        except:
            pass
    
    session.clear()
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return render_template('500.html'), 500


@app.errorhandler(413)
def too_large(e):
    """Handle file too large errors"""
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413


# ============================================================================


# ============================================================================
# CLEANUP TASK (Optional - runs periodically)
# ============================================================================

# ============================================================================
# JOB ALERT SCHEDULER
# ============================================================================

def run_daily_job_alerts():
    """Send daily job alerts to all users"""
    users = load_users()
    for user in users:
        email = user.get("email")
        skills = user.get("skills", [])
        if email and skills:
            matched_results = match_jobs(skills)
            for result in matched_results:
                send_job_alert_email(email, result["job"], result["matched_skills"])

def start_job_scheduler():
    """
    Note: Standard background scheduling does not work on Vercel Serverless.
    This function is kept for local development only.
    """
    try:
        import schedule
        schedule.every().day.at("10:00").do(run_daily_job_alerts)
        def run_scheduler_loop():
            while True:
                schedule.run_pending()
                time.sleep(60)
                
        thread = threading.Thread(target=run_scheduler_loop, daemon=True)
        thread.start()
    except ImportError:
        print("Schedule library not found. Skipping background scheduler.")

def cleanup_old_files():
    """Remove uploaded files and analysis data older than 1 hour"""
    try:
        current_time = datetime.now().timestamp()
        
        from services.save_resume import load_saved_resumes
        resumes = load_saved_resumes()
        protected_basenames = {os.path.basename(r.get("file_path", "")) for r in resumes if r.get("file_path")}
        
        # Clean uploads folder
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.isfile(filepath):
                if filename in protected_basenames:
                    continue
                file_time = os.path.getmtime(filepath)
                # Delete files older than 1 hour
                if current_time - file_time > 3600:
                    os.remove(filepath)
        
        # Clean analysis data folder
        for filename in os.listdir(app.config['ANALYSIS_FOLDER']):
            filepath = os.path.join(app.config['ANALYSIS_FOLDER'], filename)
            if os.path.isfile(filepath):
                file_time = os.path.getmtime(filepath)
                # Delete files older than 1 hour
                if current_time - file_time > 3600:
                    os.remove(filepath)
    except Exception as e:
        print(f"Cleanup error: {e}")



@app.route('/api/add_job', methods=['POST'])
def add_job_route():
    from services.job_matcher import add_job_and_notify
    try:
        data = request.json
        if not data or not data.get('title') or not data.get('skills'):
            return jsonify({'error': 'Missing title or skills'}), 400
        job = add_job_and_notify(
            data.get('title'),
            data.get('company', 'Unknown'),
            data.get('skills')
        )
        return jsonify({'success': True, 'job': job})
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/generated-resume/<gen_id>')
@login_required
def show_generated_resume(gen_id):
    """View generated resume"""
    gen_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"gen_{gen_id}.json")
    try:
        with open(gen_file, 'r') as f:
            data = json.load(f)
        return render_template('generated_resume.html', resume=data, gen_id=gen_id)
    except FileNotFoundError:
        return redirect(url_for('upload_home'))

@app.route('/download-generated-pdf/<gen_id>')
def download_generated_pdf(gen_id):
    """Download generated resume as PDF"""
    gen_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"gen_{gen_id}.json")
    try:
        template = request.args.get('template', 'classic')
        with open(gen_file, 'r') as f:
            data = json.load(f)
        # Use saved accent color if available
        pdf_buffer = generate_brand_new_pdf(data, template_name=template)
        
        # Cleanup if needed? No, we don't want to delete before download
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Resume_{data.get("personal_info", {}).get("name", "Generated")}_{template}.pdf'
        )
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/download-enhanced-resume/<analysis_id>')
def download_enhanced_resume(analysis_id):
    """Download AI-enhanced resume PDF"""
    analysis_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"ats_{analysis_id}.json")
    try:
        with open(analysis_file, 'r') as f:
            data = json.load(f)
        
        # Try to get original text
        original_text = ""
        if 'filepath' in data:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], data['filepath'])
            if os.path.exists(filepath):
                try:
                    original_text = extract_text_from_pdf(filepath)
                except:
                    pass
        
        pdf_buffer = generate_enhanced_pdf(data, original_text)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='Enhanced_Resume.pdf'
        )
    except Exception as e:
        # Improved error visibility
        print(f"Download Error: {e}")
        return f"Error generating PDF: {str(e)}", 500


@app.route('/analyze-jd', methods=['GET', 'POST'])
@login_required
def analyze_jd():
    """Handle Job Description Analysis"""
    if request.method == 'POST':
        try:
            job_description = request.form.get('job_description', '').strip()
            if not job_description:
                return jsonify({'error': 'Job description is required'}), 400

            # Analyze JD
            analysis_result = analyze_job_description_with_ai(job_description)
            
            # Save analysis
            jd_id = str(uuid.uuid4())
            jd_file = get_writable_path(os.path.join(app.config['ANALYSIS_FOLDER'], f"jd_{jd_id}.json"))
            with open(jd_file, 'w') as f:
                json.dump(analysis_result, f)
            
            return jsonify({
                'success': True,
                'redirect': url_for('show_jd_result', jd_id=jd_id)
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return render_template('analyze_jd.html')

@app.route('/jd-result/<jd_id>')
@login_required
def show_jd_result(jd_id):
    """View JD analysis result"""
    jd_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"jd_{jd_id}.json")
    try:
        with open(jd_file, 'r') as f:
            data = json.load(f)
        return render_template('jd_analysis_result.html', analysis=data)
    except FileNotFoundError:
        return redirect(url_for('analyze_jd'))

@app.route('/enhance-content', methods=['GET', 'POST'])
@login_required
def enhance_content():
    """Handle Content Enhancement"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            text = data.get('content', '').strip()
            style = data.get('style', 'Professional')

            if not text:
                return jsonify({'error': 'Content is required'}), 400

            improved_content = rewrite_resume_section(text, style)
            
            return jsonify({
                'success': True,
                'original': text,
                'improved': improved_content
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return render_template('enhance_content.html')


@app.route('/rewrite-section', methods=['POST'])
@login_required
def rewrite_section_route():
    """Handle AI Rewrite for Dashboard"""
    try:
        data = request.get_json()
        section = data.get('section', '')
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'No content provided'}), 400

        # Rewrite the content
        improved_content = rewrite_resume_section(content, improvement_type="Professional")
        
        return jsonify({
            'success': True,
            'improved_content': improved_content
        })

    except Exception as e:
        print(f"Rewrite Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/market-demand', methods=['GET', 'POST'])
@premium_required
def market_demand():
    """Market Demand Skill Analyzer"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            role = data.get('role', '').strip()
            
            if not role:
                return jsonify({'error': 'Please provide a job role.'}), 400

            if not client:
                return jsonify({'error': 'AI services are currently offline.'}), 500

            prompt = f"""
            You are a leading Market Research Analyst specialized in the Global Tech Job Market. 
            Analyze the market demand for the following job role and identify trending skills.
            
            JOB ROLE: {role}
            
            Provide a detailed analysis in valid JSON format with this structure:
            {{
                "role": "{role}",
                "trending_technical_skills": ["<skill 1>", "<skill 2>", "..."],
                "trending_soft_skills": ["<skill 1>", "<skill 2>", "..."],
                "emerging_technologies": ["<tech 1>", "<tech 2>"],
                "top_certifications": ["<cert 1>", "<cert 2>"],
                "market_outlook": "<brief 2-sentence outlook on demand for this role>",
                "salary_range_estimate": "<estimated range (e.g. $80k - $120k)>"
            }}
            Provide ONLY valid JSON.
            """
            
            response_text = get_ai_completion(
                prompt=prompt,
                system_message="You are a market analyst that outputs valid JSON.",
                temperature=0.7,
                max_tokens=1024,
                is_json=True
            )
            
            analysis = clean_json_response(response_text)
            return jsonify({'success': True, 'analysis': analysis})


        except Exception as e:
            print(f"Market Demand Error: {e}")
            return jsonify({'error': str(e)}), 500

    return render_template('market_demand.html')

def generate_summary_ai(skills, experience):
    """
    Generate a professional resume summary from skills and experience
    """
    try:
        prompt = f"""
You are an expert resume writer. Generate a concise, high-impact professional summary (3-4 sentences) based on the following skills and experience.

SKILLS: {skills}
EXPERIENCE: {experience}

Guidelines:
- Start with a strong professional title (e.g., "Results-driven Software Engineer").
- Highlight the most critical technical skills.
- Emphasize impact and value delivery.
- Use an active, professional tone.

Provide only the summary text, no introduction or conclusion.
"""
        return get_ai_completion(
            prompt=prompt,
            system_message="You are a professional resume writer.",
            temperature=0.7,
            max_tokens=512,
            is_json=False
        )


    except Exception as e:
        raise Exception(f"Summary generation failed: {str(e)}")

@app.route('/generate-summary', methods=['POST'])
@premium_required
def generate_summary_route():
    """Handle Summary Generation Request"""
    try:
        data = request.get_json()
        skills = data.get('skills', '').strip()
        experience = data.get('experience', '').strip()

        if not skills and not experience:
            return jsonify({'error': 'Please provide skills or experience context.'}), 400

        summary = generate_summary_ai(skills, experience)
        
        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        print(f"Summary Gen Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-resume', methods=['POST'])
@login_required
def analyze_resume():
    """Handle Resume Analysis (ATS Checker)"""
    try:
        # File validation
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file uploaded'}), 400
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        job_description = request.form.get('job_description', '').strip()
        # JD is optional for pure ATS check, but better if provided
        
        # Save and extract
        filename = secure_filename(file.filename)
        unique_filename = f"ats_{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        try:
            resume_text = extract_text_from_pdf(filepath)
        except Exception as e:
            return jsonify({'error': 'Failed to read PDF'}), 500
        
        # Analyze
        analysis_result = analyze_with_groq(resume_text, job_description)
        
        # Process Job Alerts
        try:
            candidate = analysis_result.get('candidate_summary', {})
            email_val = candidate.get('email') if isinstance(candidate, dict) else None
            
            if email_val and '@' in email_val and email_val.lower() != 'not found':
                skills_dict = analysis_result.get('skill_analysis', {})
                tech_s = skills_dict.get('technical_skills', []) if isinstance(skills_dict, dict) else []
                soft_s = skills_dict.get('soft_skills', []) if isinstance(skills_dict, dict) else []
                all_skills = (tech_s if isinstance(tech_s, list) else []) + (soft_s if isinstance(soft_s, list) else [])
                
                add_user(email_val, all_skills)
                matched_results = match_jobs(all_skills)
                for result in matched_results:
                    threading.Thread(target=send_job_alert_email, args=(email_val, result["job"], result["matched_skills"]), daemon=True).start()
                
                # Save to history
                save_resume(
                    email=email_val,
                    resume_name=f"ATS Analysis - {filename}",
                    skills=all_skills,
                    ats_score=analysis_result.get('ats_score'),
                    file_path=filepath
                )
        except Exception as e:
            print(f"Error handling job alerts or history: {e}")

        # Add metadata
        analysis_result['filename'] = filename
        analysis_result['filepath'] = unique_filename
        analysis_result['timestamp'] = datetime.now().isoformat()
        
        # Save analysis
        analysis_id = str(uuid.uuid4())
        analysis_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"ats_{analysis_id}.json")
        with open(analysis_file, 'w') as f:
            json.dump(analysis_result, f)
            
        return jsonify({
            'success': True,
            'redirect': url_for('show_dashboard', analysis_id=analysis_id)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard/<analysis_id>')
@login_required
def show_dashboard(analysis_id):
    """View Analysis Dashboard"""
    analysis_file = os.path.join(app.config['ANALYSIS_FOLDER'], f"ats_{analysis_id}.json")
    try:
        with open(analysis_file, 'r') as f:
            data = json.load(f)
        return render_template(
            'dashboard.html', 
            analysis=data, 
            filename=data.get('filename', 'Resume.pdf'),
            timestamp=data.get('timestamp', ''),
            analysis_id=analysis_id
        )
    except FileNotFoundError:
        return redirect(url_for('index'))

# ============================================================================
# SKILL SUGGESTION & RESUME COMPARISON ROUTES
# ============================================================================

@app.route('/suggest-skills', methods=['GET', 'POST'])
@premium_required
def suggest_skills():
    """AI Skill Suggestion Engine Route"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            role = data.get('role', '').strip()
            industry = data.get('industry', '').strip()
            
            if not role:
                return jsonify({'error': 'Please provide a job role.'}), 400

            if not client:
                return jsonify({'error': 'Groq client not initialized'}), 500

            prompt = f"""
            You are a leading AI Career Expert. Suggest 5 to 10 highly relevant skills based on the following:
            Job Role: {role}
            Industry: {industry}
            
            Provide only valid JSON in this exact structure:
            {{
                "skills": ["<skill 1>", "<skill 2>", "..."]
            }}
            """
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a skill suggestion API that outputs valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"},
                timeout=25.0
            )
            
            analysis = clean_json_response(completion.choices[0].message.content)
            return jsonify({'success': True, 'skills': analysis.get('skills', [])})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('suggest_skills.html')


@app.route('/compare-resumes', methods=['GET', 'POST'])
@premium_required
def compare_resumes():
    """Resume Version Comparison Route"""
    if request.method == 'POST':
        try:
            if 'old_resume' not in request.files or 'new_resume' not in request.files:
                return jsonify({'error': 'Please provide both an old and new resume file.'}), 400
                
            old_file = request.files['old_resume']
            new_file = request.files['new_resume']
            
            if not allowed_file(old_file.filename) or not allowed_file(new_file.filename):
                return jsonify({'error': 'Invalid file type. Only PDF is accepted.'}), 400

            # Save and parse both
            old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(old_file.filename))
            new_filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(new_file.filename))
            
            old_file.save(old_filepath)
            new_file.save(new_filepath)
            
            old_text = extract_text_from_pdf(old_filepath)
            new_text = extract_text_from_pdf(new_filepath)
            
            if not client:
                return jsonify({'error': 'AI services are currently offline.'}), 500

            prompt = f"""
            You are an expert Resume Reviewer. Compare the "Old Resume" with the "New Resume".
            Identify 3 to 5 key improvements in the New Resume. 
            Focus on things like:
            - Better keywords
            - Improved clarity
            - Higher ATS score readiness (formatting, structure, strong verbs)
            - Impact metrics added
            
            Old Resume Text:
            {old_text[:3000]}
            
            New Resume Text:
            {new_text[:3000]}
            
            Output valid JSON in this exact structure:
            {{
                "winner": "Old Resume" or "New Resume",
                "reasoning": "Resume has...",
                "comparison": [
                    "Better keywords including X and Y",
                    "Improved clarity in the summary section",
                    "Higher ATS score readiness due to strong action verbs"
                ]
            }}
            """
            
            response_text = get_ai_completion(
                prompt=prompt,
                system_message="You are a resume analysis API that outputs valid JSON.",
                temperature=0.5,
                max_tokens=800,
                is_json=True
            )
            
            analysis = clean_json_response(response_text)

            return jsonify({
                'success': True, 
                'comparison': analysis.get('comparison', []),
                'winner': analysis.get('winner', 'Unknown'),
                'reasoning': analysis.get('reasoning', '')
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    return render_template('compare_resumes.html')


# ============================================================================
# SAVED RESUMES ROUTES
# ============================================================================

@app.route('/saved-resumes', methods=['GET'])
@login_required
def saved_resumes():
    email = session.get('user')
    resumes = get_resumes_by_user(email)
    
    # Optional sorting by date descending
    resumes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return render_template('saved_resumes.html', resumes=resumes)

@app.route('/view-resume/<resume_id>', methods=['GET'])
def view_resume_pdf(resume_id):
    resume = get_resume_by_id(resume_id)
    if not resume:
        return "Resume not found", 404
    file_path = resume.get('file_path')
    if not os.path.exists(file_path):
        return "File not found on server", 404
    return send_file(file_path, mimetype='application/pdf')

@app.route('/download-resume/<resume_id>', methods=['GET'])
def download_resume_pdf(resume_id):
    resume = get_resume_by_id(resume_id)
    if not resume:
        return "Resume not found", 404
    file_path = resume.get('file_path')
    if not os.path.exists(file_path):
        return "File not found on server", 404
    return send_file(file_path, mimetype='application/pdf', as_attachment=True, download_name=os.path.basename(file_path))

@app.route('/delete-resume/<resume_id>', methods=['POST'])
def delete_resume(resume_id):
    email = request.form.get('email', '').strip()
    if delete_user_resume(email, resume_id):
        return redirect(url_for('saved_resumes', email=email))
    return "Error deleting resume", 400

# ============================================================================
# INTERVIEW QUESTIONS ROUTE
# ============================================================================

@app.route('/interview-questions', methods=['GET', 'POST'])
@login_required
def interview_questions():
    """AI Interview Question Generator"""
    if request.method == 'POST':
        try:
            experience_level = 'Fresher'
            num_questions = 5
            resume_text = ""
            
            if request.content_type and 'multipart/form-data' in request.content_type:
                experience_level = request.form.get('experience_level', 'Fresher')
                num_questions = int(request.form.get('num_questions', 5))
                
                if 'resume_file' not in request.files:
                    return jsonify({'error': 'No resume file uploaded.'}), 400
                    
                file = request.files['resume_file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected.'}), 400
                    
                if not allowed_file(file.filename):
                    return jsonify({'error': 'Invalid file type. Only PDF is allowed.'}), 400
                    
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                unique_filename = f"temp_int_{uuid.uuid4()}_{filename}"
                filepath_temp = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath_temp)
                resume_text = extract_text_from_pdf(filepath_temp)
                try:
                    os.remove(filepath_temp)
                except:
                    pass
            else:
                data = request.get_json()
                resume_id = data.get('resume_id')
                experience_level = data.get('experience_level', 'Fresher')
                num_questions = int(data.get('num_questions', 5))
                
                if not resume_id:
                    return jsonify({'error': 'Please select a resume.'}), 400
                    
                resume = get_resume_by_id(resume_id)
                if not resume:
                    return jsonify({'error': 'Resume not found.'}), 404
                    
                file_path = resume.get('file_path')
                if not os.path.exists(file_path):
                     return jsonify({'error': 'Resume file missing on server.'}), 404
                     
                resume_text = extract_text_from_pdf(file_path)
            
            user = get_current_user()
            is_premium = session.get('user') == 'smarthire72@gmail.com' or (user and (user.get('role') == 'admin' or user.get('plan') == 'premium'))
            if not is_premium and num_questions > 2:
                num_questions = 2 # Enforce limit for free users
                
            if not client:
                 return jsonify({'error': 'AI services are currently offline.'}), 500
                 
            prompt = f"""
            You are an expert HR Manager and Technical Interviewer. 
            Based on the following resume text, generate interview questions.
            
            RESUME TEXT (Partial):
            {resume_text[:4000]}
            
            Target Experience Level: {experience_level}
            Number of questions requested per category: {num_questions}
            
            Generate {num_questions} Technical Questions (based on their specific technical skills, tools, and projects mentioned) 
            and {num_questions} HR/Behavioral Questions (based on their experience, role, or general career goals).
            
            Ensure the questions are relevant, clear, and professional.
            
            Output strictly valid JSON with this exact structure:
            {{
                "technical_questions": ["question 1", "question 2", ...],
                "hr_questions": ["question 1", "question 2", ...]
            }}
            Provide only the valid JSON.
            """
            
            response_text = get_ai_completion(
                prompt=prompt,
                system_message="You are an interview question generator that outputs only valid JSON.",
                temperature=0.7,
                max_tokens=1500,
                is_json=True
            )
            
            result = clean_json_response(response_text)
            return jsonify({'success': True, 'questions': result})

            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    # Fetch all resumes so user can choose
    resumes = load_saved_resumes()
    resumes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return render_template('interview_questions.html', resumes=resumes)

# ============================================================================
# ROADMAP ROUTE
# ============================================================================

@app.route('/roadmap', methods=['GET'])
@premium_required
def career_roadmap():
    """Render the Career Growth Roadmap page"""
    return render_template('career_roadmap.html')

@app.route('/generate-roadmap', methods=['POST'])
@premium_required
def generate_roadmap():
    """API endpoint to generate AI career roadmap"""
    try:
        data = request.get_json()
        role = data.get('role', '').strip()
        
        if not role:
            return jsonify({'error': 'Target Job Role is required.'}), 400
            
        if not client:
            return jsonify({'error': 'AI services are currently offline.'}), 500
            
        prompt = f"""
        You are an elite Career Coach. The user wants a step-by-step roadmap to become a "{role}".
        Generate a strictly mapped 4 to 6 step roadmap focusing on real-world actions (e.g., learn specific tech, build specific types of projects, apply for internships/roles, networking, etc.).

        Constraint: Output ONLY valid JSON in this exact structure:
        {{
            "roadmap": [
                {{
                    "title": "Step 1: Foundational... (or whatever is appropriate)",
                    "timeframe": "1-3 months",
                    "description": "What to do precisely in this step.",
                    "actions": ["Learn Python and SQL", "Complete introductory data science course"]
                }},
                {{
                   "title": "Step 2: ...",
                   "timeframe": "X months",
                   "description": "...",
                   "actions": ["..."]
                }}
            ]
        }}
        """
        
        response_text = get_ai_completion(
            prompt=prompt,
            system_message="You are a career map generator that outputs valid JSON.",
            temperature=0.5,
            max_tokens=1500,
            is_json=True
        )
        
        analysis = clean_json_response(response_text)
        return jsonify({'success': True, 'roadmap': analysis.get('roadmap', [])})

        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    # Run cleanup on startup
    cleanup_old_files()
    
    # Start job alert scheduler
    start_job_scheduler()
    
    # Start Flask application
    # For production, use a proper WSGI server like Gunicorn
    print("Starting app on port 5001...")
    app.run(debug=True, host='0.0.0.0', port=5001)