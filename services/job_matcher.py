import json
import os

def load_jobs(filepath="jobs.json"):
    if not os.path.exists(filepath):
        # Default jobs if file doesn't exist
        default_jobs = [
            {"title": "Python Developer", "company": "ABC Company", "skills": ["Python", "Django", "SQL"]},
            {"title": "Data Analyst", "company": "Tech Corp", "skills": ["SQL", "Python", "Excel"]},
            {"title": "Frontend Developer", "company": "Web Solutions", "skills": ["HTML", "CSS", "JavaScript"]}
        ]
        with open(filepath, "w") as f:
            json.dump(default_jobs, f, indent=4)
        return default_jobs
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_jobs(jobs, filepath="jobs.json"):
    with open(filepath, "w") as f:
        json.dump(jobs, f, indent=4)

def add_job_and_notify(title, company, skills, description="", location="", apply_link="", filepath="jobs.json"):
    jobs = load_jobs(filepath)
    new_job = {"title": title, "company": company, "skills": skills, "description": description, "location": location, "apply_link": apply_link}
    jobs.append(new_job)
    save_jobs(jobs, filepath)
    
    # Notify users
    from services.email_sender import send_job_alert_email
    import threading
    import logging
    
    logger = logging.getLogger("JobMatcher")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    users = load_users()
    for user in users:
        email = user.get("email")
        user_skills = user.get("skills", [])
        if email and user_skills:
            matched = match_skills(user_skills, new_job["skills"])
            if len(matched) >= 1:
                logger.info(f"Triggering email for {email}. Found {len(matched)} match(es): {', '.join(matched)}")
                threading.Thread(target=send_job_alert_email, args=(email, new_job, matched), daemon=True).start()
    return new_job

def update_job_and_notify(index, title, company, skills, description="", location="", apply_link="", filepath="jobs.json"):
    jobs = load_jobs(filepath)
    if index < 0 or index >= len(jobs):
        raise ValueError("Invalid job index")
        
    updated_job = {"title": title, "company": company, "skills": skills, "description": description, "location": location, "apply_link": apply_link}
    jobs[index] = updated_job
    save_jobs(jobs, filepath)
    
    # Notify users
    from services.email_sender import send_job_alert_email
    import threading
    import logging
    
    logger = logging.getLogger("JobMatcher")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    users = load_users()
    for user in users:
        email = user.get("email")
        user_skills = user.get("skills", [])
        if email and user_skills:
            matched = match_skills(user_skills, updated_job["skills"])
            if len(matched) >= 1:
                logger.info(f"Triggering email for {email} (UPDATED JOB). Found {len(matched)} match(es): {', '.join(matched)}")
                threading.Thread(target=send_job_alert_email, args=(email, updated_job, matched), daemon=True).start()
    return updated_job

def delete_job(index, filepath="jobs.json"):
    jobs = load_jobs(filepath)
    if 0 <= index < len(jobs):
        del jobs[index]
        save_jobs(jobs, filepath)
        return True
    return False

def match_skills(user_skills, job_skills):
    matches = []

    for skill in user_skills:
        if isinstance(skill, str) and skill.strip().lower() in [j.strip().lower() for j in job_skills if isinstance(j, str)]:
            matches.append(skill)

    return list(set(matches))

def match_jobs(user_skills):
    if not user_skills:
        return []
    
    jobs = load_jobs()
    matched_results = []
    
    for job in jobs:
        matched = match_skills(user_skills, job.get("skills", []))
        if len(matched) >= 1:
            matched_results.append({
                "job": job,
                "matched_skills": matched
            })
            
    return matched_results

def load_users(filepath="users.json"):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_users(users, filepath="users.json"):
    with open(filepath, "w") as f:
        json.dump(users, f, indent=4)

def add_user(email, skills, filepath="users.json"):
    if not email:
        return None
        
    users = load_users(filepath)
    # Ensure skills is a list of strings
    safe_skills = [s for s in skills if isinstance(s, str)]
    
    # Check for duplicate
    for user in users:
        if user.get("email") == email:
            existing_skills = user.get("skills", [])
            new_skills = list(set(existing_skills + safe_skills))
            user["skills"] = new_skills
            save_users(users, filepath)
            return user
            
    new_user = {
        "email": email, 
        "skills": safe_skills,
        "full_name": email.split('@')[0],
        "password": "default123",
        "phone": "",
        "education": "",
        "role": "user",
        "plan": "free"
    }
    users.append(new_user)
    save_users(users, filepath)
    return new_user
