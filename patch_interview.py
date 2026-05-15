import os
import re

filepath = r'app.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """@app.route('/interview-questions', methods=['GET', 'POST'])
def interview_questions():
    \"\"\"AI Interview Question Generator\"\"\"
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
            is_premium = user and (user.get('role') == 'admin' or user.get('plan') == 'premium')
            if not is_premium and num_questions > 2:
                num_questions = 2 # Enforce limit for free users
                
            if not client:
                 return jsonify({'error': 'Groq client not initialized'}), 500"""

pattern = r'@app\.route\(\'/interview-questions\', methods=\[\'GET\', \'POST\'\]\)\ndef interview_questions\(\):\n\s*\"\"\"AI Interview Question Generator\"\"\"\n\s*if request\.method == \'POST\':\n\s*try:[\s\S]*?if not client:\n\s*return jsonify\(\{\'error\': \'Groq client not initialized\'\}\), 500'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated interview_questions in app.py')
