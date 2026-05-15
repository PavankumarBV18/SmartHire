import os
from dotenv import load_dotenv
from services.email_sender import send_job_alert_email

load_dotenv()

print(f"SMTP_EMAIL: {os.getenv('SMTP_EMAIL')}")
# Do not print password
job = {
    "title": "Test Job Title",
    "company": "Test Company",
    "apply_link": "http://example.com"
}
matched_skills = ["Python", "Flask"]

print("Attempting to send email...")
result = send_job_alert_email("makamabhi16@gmail.com", job, matched_skills)
print(f"Result: {result}")