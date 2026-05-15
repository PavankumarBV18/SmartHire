import json
import os
import uuid
from datetime import datetime

RESUMES_FILE = "saved_resumes.json"

def load_saved_resumes():
    if not os.path.exists(RESUMES_FILE):
        return []
    try:
        with open(RESUMES_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_resumes_data(data):
    with open(RESUMES_FILE, "w") as f:
        json.dump(data, f, indent=4)

def save_resume(email, resume_name, skills, ats_score, file_path):
    if not email:
        return None
        
    resumes = load_saved_resumes()
    
    # Check for duplicate
    for r in resumes:
        if r.get("email") == email and r.get("file_path") == file_path:
            return r # Already exists
            
    resume_id = str(uuid.uuid4())
    new_resume = {
        "id": resume_id,
        "email": email,
        "resume_name": resume_name,
        "skills": [s for s in skills if isinstance(s, str)],
        "ats_score": ats_score,
        "file_path": file_path,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    resumes.append(new_resume)
    save_resumes_data(resumes)
    return new_resume

def get_resumes_by_user(email):
    resumes = load_saved_resumes()
    return [r for r in resumes if r.get("email", "").lower() == email.lower()]

def delete_user_resume(email, resume_id):
    resumes = load_saved_resumes()
    filtered = []
    deleted = False
    for r in resumes:
        if r.get("id") == resume_id and r.get("email", "").lower() == email.lower():
            deleted = True
            # Optional: remove file from disk
            file_path = r.get("file_path")
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        else:
            filtered.append(r)
            
    if deleted:
        save_resumes_data(filtered)
    return deleted

def get_resume_by_id(resume_id):
    resumes = load_saved_resumes()
    for r in resumes:
        if r.get("id") == resume_id:
            return r
    return None
