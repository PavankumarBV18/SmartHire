import os
import re

filepath = r'app.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """@app.route("/admin-job-alert")
def admin_job_alert():
    if not session.get("user"):
        return redirect("/login")
    user = get_current_user()
    if not user or user.get('role') != 'admin':
        return redirect('/')
    try:
        from services.job_matcher import load_jobs, load_users
        jobs = load_jobs()
        users = load_users()
        total_users = len(users)
        premium_users = len([u for u in users if u.get('plan') == 'premium'])
    except Exception as e:
        jobs = []
        users = []
        total_users = 0
        premium_users = 0

    # Load feedback
    feedback_data = []
    if os.path.exists('feedback.json'):
        try:
            with open('feedback.json', 'r') as f:
                import json
                raw_feedback = json.load(f)
                
            from datetime import datetime
            for fb in raw_feedback:
                try:
                    dt = datetime.fromisoformat(fb.get('timestamp', ''))
                    fb['formatted_time'] = dt.strftime('%B %d, %Y - %I:%M %p')
                except:
                    fb['formatted_time'] = fb.get('timestamp', 'Unknown Time')
            feedback_data = raw_feedback
        except:
            pass

    # Load system resume history
    try:
        from services.save_resume import load_saved_resumes
        system_resumes = load_saved_resumes()
        system_resumes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except Exception:
        system_resumes = []

    response = make_response(render_template('admin_dashboard.html', 
                                          jobs=jobs, 
                                          enumerated_jobs=list(enumerate(jobs)), 
                                          feedback=feedback_data, 
                                          history=system_resumes,
                                          users=users,
                                          total_users=total_users,
                                          premium_users=premium_users))
    return response"""

# Find the admin_job_alert function
pattern = r'@app\.route\("/admin-job-alert"\)\ndef admin_job_alert\(\):.*?return response'
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated admin-job-alert in app.py')
