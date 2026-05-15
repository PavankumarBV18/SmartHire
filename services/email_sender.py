import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
import time
import logging

# Configure explicitly visible logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EmailSender")

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def send_job_alert_email(to_email, job, matched_skills):
    logger.info(f"Initializing email sequence for receiver: {to_email}")
    
    if not job or not to_email:
        logger.error("Missing job data or email address. Aborting.")
        return False
        
    if not is_valid_email(to_email):
        logger.error(f"Invalid email address format provided: {to_email}. Aborting.")
        return False
        
    sender_email = os.getenv("SMTP_EMAIL", "smarthire72@gmail.com")
    sender_password = os.getenv("SMTP_PASSWORD", "")
    
    if not sender_password or sender_password == "your_password":
        logger.error(f"SMTP_PASSWORD is not configured in .env. Cannot send to {to_email}. Aborting.")
        return False
    
    subject = f"Job Match Alert: {job.get('title', 'Position')}"

    match_status = ""
    if len(matched_skills) >= 2:
        match_status = "Strong Match Found"
    elif len(matched_skills) >= 1:
        match_status = "Partial Match Found"
    else:
        logger.info(f"No matched skills for {to_email}. Condition not met, skipping email.")
        return False
        
    matched_skills_str = "\n".join([f"• {skill}" for skill in matched_skills])
    
    body = f"""Hello,

{match_status}

Job Title: {job.get('title', 'Unknown')}  
Company Name: {job.get('company', 'Unknown')}  

Matched Skills:
{matched_skills_str}

Apply Link: {job.get('apply_link', '#')}

Best Regards,  
SmartHire Team"""

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting to connect to SMTP server (Attempt {attempt}/{max_retries})...")
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.set_debuglevel(0) # Keep off unless deep tracing needed
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            logger.info(f"[SUCCESS] Job alert email successfully delivered to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error(f"[ERROR] SMTP Authentication failed for {sender_email}. Your App Password may be incorrect.")
            return False # No need to retry if it's an auth error
            
        except smtplib.SMTPException as smtp_e:
            logger.warning(f"SMTP error on attempt {attempt}: {smtp_e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error(f"[ERROR] Failed to send email to {to_email} after {max_retries} attempts.")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Unexpected failure sending email to {to_email}. Error type: {type(e).__name__}, Message: {e}")
            return False
