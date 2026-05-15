import os
import re

filepath = r'app.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """@app.route('/login', methods=['GET', 'POST'])
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
                        if u.get('role') == 'admin':
                            return redirect('/admin-job-alert')
                        return redirect('/')
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
    return render_template('register.html')"""

pattern = r'@app\.route\(\'/login\', methods=\[\'GET\', \'POST\'\]\).*?return render_template\(\'register\.html\'\)'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated login/register in app.py')
