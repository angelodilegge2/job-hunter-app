import os
import json
import requests
import time
import pdfplumber
import smtplib
import io
from bs4 import BeautifulSoup
import openai
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Initialize OpenAI client
# Client will be initialized inside functions to allow env var setting in main.py

def extract_text_from_pdf(pdf_input):
    """Extracts text from a PDF file path or file-like object."""
    text = ""
    try:
        # If input is bytes, wrap in BytesIO
        if isinstance(pdf_input, bytes):
            pdf_input = io.BytesIO(pdf_input)
            
        with pdfplumber.open(pdf_input) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def generate_candidate_profile(cv_text):
    """Uses OpenAI to summarize CV into a structured profile for IOs."""
    print("🧠 Analyzing CV against IO criteria...")
    prompt = f"""
    You are a Recruitment Expert for International Organizations (UN, EU, OECD).
    Analyze this CV.

    CV TEXT:
    {cv_text[:12000]}

    OUTPUT JSON ONLY:
    {{
        "1_essential_qualifications": {{
            "education": "Highest degree",
            "years_experience": "Integer",
            "languages": ["List languages"],
            "sector": "Primary sector"
        }},
        "2_core_tech_stack": ["List HARD skills (e.g. CBA, SCM, Evaluation)"],
        "3_desired_stack": ["List BONUS skills"],
        "4_logistics": {{
            "current_location": "City, Country",
            "mobility": "Relocation preference"
        }},
        "search_keywords": ["List 3-4 keywords for finding relevant jobs"]
    }}
    """
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}], 
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error generating profile: {e}")
        return {"search_keywords": ["Evaluation", "Policy"], "1_essential_qualifications": {"years_experience": 5}}

def fetch_reliefweb(profile):
    print("\n🔍 [ReliefWeb] Connecting...")
    keywords = profile.get('search_keywords', ["Evaluation"])
    # Ensure keywords are strings
    keywords = [str(k) for k in keywords]
    query_string = " OR ".join([f'"{k}"' for k in keywords[:3]])
    appname = "AngeloDiLegge-JobResearch-9k2x5-g1sb1E"
    url = f"https://api.reliefweb.int/v2/jobs?appname={appname}"
    cutoff = datetime.now() - timedelta(days=7)
    try:
        payload = {
            "limit": 50, 
            "preset": "latest", 
            "query": { "value": query_string }, 
            "fields": { "include": ["title", "body", "source", "url", "date"] }
        }
        response = requests.post(url, json=payload)
        if response.status_code != 200: 
            print(f"ReliefWeb Error: {response.status_code}")
            return []
        jobs = []
        for j in response.json().get('data', []):
            date = datetime.fromisoformat(j['fields']['date']['created']).replace(tzinfo=None)
            if date > cutoff:
                soup = BeautifulSoup(j['fields']['body'], "html.parser")
                jobs.append({
                    "title": j['fields']['title'], 
                    "org": j['fields']['source'][0]['name'], 
                    "clean_body": soup.get_text(separator="\n"), 
                    "url": j['fields']['url'], 
                    "source": "ReliefWeb"
                })
        print(f"   ✅ Found {len(jobs)} jobs.")
        return jobs
    except Exception as e:
        print(f"ReliefWeb Exception: {e}")
        return []

def fetch_smartrecruiters(profile):
    targets = ["OECD", "CERN", "TheGlobalFund", "Euroclear", "ReliefInternational", "InternationalSOS", "JobsForHumanity", "OxfamAmerica2", "PlanInternational", "Dalberg"]
    print(f"\n🔍 [SmartRecruiters] Scanning {len(targets)} Orgs...")
    all_jobs = []
    cutoff = datetime.now() - timedelta(days=30)
    for org in targets:
        try:
            response = requests.get(f"https://api.smartrecruiters.com/v1/companies/{org}/postings")
            if response.status_code != 200: continue
            for j in response.json().get('content', []):
                date_str = j.get('releasedDate')
                if date_str and datetime.fromisoformat(date_str[:19]) > cutoff:
                    if any(k in j['name'] for k in ['Policy', 'Evaluat', 'Regul', 'Analyst', 'Data', 'Program']):
                        detail = requests.get(f"https://api.smartrecruiters.com/v1/companies/{org}/postings/{j['id']}").json()
                        full_text = j['name'] + "\n"
                        if 'jobAd' in detail:
                            for key in detail['jobAd']['sections']: 
                                full_text += detail['jobAd']['sections'][key].get('text', '') + "\n"
                        all_jobs.append({
                            "title": j['name'], 
                            "org": org, 
                            "clean_body": full_text, 
                            "url": f"https://jobs.smartrecruiters.com/{org}/{j['id']}", 
                            "source": "SmartRecruiters"
                        })
                        time.sleep(0.1)
        except: continue
    print(f"   ✅ Found {len(all_jobs)} jobs.")
    return all_jobs

def fetch_greenhouse(profile):
    targets = ["worldresourcesinstitute", "path", "dataorg", "interamerican", "educate", "onecampaign"]
    print(f"\n🔍 [Greenhouse] Scanning {len(targets)} Orgs...")
    all_jobs = []
    for org in targets:
        try:
            response = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs?content=true")
            if response.status_code != 200: continue
            for j in response.json().get('jobs', []):
                if any(k in j['title'] for k in ["Director", "Senior", "Head", "Evaluation", "Policy", "Regulatory"]):
                    soup = BeautifulSoup(j['content'], "html.parser")
                    all_jobs.append({
                        "title": j['title'], 
                        "org": org.title(), 
                        "clean_body": soup.get_text(separator="\n"), 
                        "url": j['absolute_url'], 
                        "source": "Greenhouse"
                    })
            time.sleep(0.1)
        except: continue
    print(f"   ✅ Found {len(all_jobs)} jobs.")
    return all_jobs

def fetch_lever(profile):
    targets = ["climatepolicyinitiative", "vitalstrategies", "dimagi", "givedirectly", "openai", "anthropic"]
    print(f"\n🔍 [Lever] Scanning {len(targets)} Orgs...")
    all_jobs = []
    for org in targets:
        try:
            response = requests.get(f"https://api.lever.co/v0/postings/{org}")
            if response.status_code != 200: continue
            for j in response.json():
                if any(k in j['text'] for k in ["Director", "Senior", "Head", "Evaluation", "Policy"]):
                    all_jobs.append({
                        "title": j['text'], 
                        "org": org.title(), 
                        "clean_body": j.get('descriptionPlain', j['text']), 
                        "url": j['hostedUrl'], 
                        "source": "Lever"
                    })
            time.sleep(0.1)
        except: continue
    print(f"   ✅ Found {len(all_jobs)} jobs.")
    return all_jobs

def fetch_remoteok(profile):
    print("\n🔍 [Remote OK] Connecting...")
    try:
        response = requests.get("https://remoteok.com/api", headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200: return []
        jobs = []
        for j in response.json()[1:]:
            if any(k in j.get('position', '').lower() for k in ["data", "policy", "manager"]):
                jobs.append({
                    "title": j['position'], 
                    "org": j.get('company', 'Unknown'), 
                    "clean_body": j.get('description', ''), 
                    "url": j.get('url', ''), 
                    "source": "Remote OK"
                })
                if len(jobs) >= 10: break
        print(f"   ✅ Found {len(jobs)} jobs.")
        return jobs
    except: return []

def fetch_all_jobs(profile, status_callback=None):
    all_jobs = []
    
    sources = [
        ("ReliefWeb", fetch_reliefweb),
        ("SmartRecruiters", fetch_smartrecruiters),
        ("Greenhouse", fetch_greenhouse),
        ("Lever", fetch_lever),
        ("Remote OK", fetch_remoteok)
    ]
    
    for name, fetcher in sources:
        if status_callback:
            status_callback(f"Searching {name}...")
        
        jobs = fetcher(profile)
        count = len(jobs)
        all_jobs.extend(jobs)
        
        if status_callback:
            status_callback(f"✅ Found {count} jobs from {name}")
            
    return all_jobs

def match_job_to_cv(job_text, candidate_profile):
    prompt = f"""
    Act as a Forensic Career Analyst. Compare this Candidate vs this Job.
    CANDIDATE PROFILE: {json.dumps(candidate_profile)}
    JOB DESCRIPTION: {job_text[:6000]}
    INSTRUCTIONS:
    1. Analyze Requirements (Hard Skills, Languages, Sector).
    2. Cross-reference with Candidate.
    3. Scoring: 100 (Perfect), 85-95 (Strong Skill/Wrong Sector), 60-80 (Good Skill/Missing Context), <50 (Irrelevant).
    OUTPUT JSON ONLY:
    {{
        "score": <int>,
        "job_summary": "<2-sentence summary>",
        "strengths": ["Strength 1", "Strength 2", "Strength 3"],
        "gaps": ["Gap 1 (Critical)", "Gap 2", "Gap 3"]
    }}
    """
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}], 
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error matching job: {e}")
        return {"score": 0, "job_summary": "Error", "strengths": [], "gaps": []}

def send_visual_email(job_results, email_user, email_pass, target_email):
    valid_matches = [r for r in job_results if r['Score'] > 50]
    if not valid_matches: 
        print("📭 No matches to email.")
        return
    
    sorted_jobs = sorted(valid_matches, key=lambda x: x['Score'], reverse=True)
    html_content = f"""<html><body style="font-family: Helvetica, Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; border: 1px solid #ddd;">
    <h2 style="color: #2c3e50; border-bottom: 2px solid #0056b3; padding-bottom: 10px;">🚀 Daily Job Intelligence</h2>
    <p>Found <strong>{len(sorted_jobs)}</strong> opportunities matching your profile.</p>"""

    for i, job in enumerate(sorted_jobs):
        bg_color = "#27ae60" if job['Score'] >= 80 else "#e67e22"
        strengths = "".join([f"<li style='margin-bottom: 4px; color: #27ae60;'>✅ <span style='color:#333'>{s}</span></li>" for s in job['strengths']])
        gaps = "".join([f"<li style='margin-bottom: 4px; color: #c0392b;'>⚠️ <span style='color:#333'>{g}</span></li>" for g in job['gaps']])
        html_content += f"""
        <div style="margin-top: 30px; border: 1px solid #eee; border-radius: 8px; padding: 20px;">
            <div style="display: flex; justify-content: space-between;">
                <h3 style="margin: 0; font-size: 18px;"><a href="{job['URL']}" style="text-decoration: none; color: #0056b3;">{i+1}. {job['Job Title']}</a></h3>
                <span style="background-color: {bg_color}; color: white; padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 12px;">{job['Score']}/100</span>
            </div>
            <p style="color: #777; font-size: 14px; margin-top: 5px;">{job['Organization']} | {job['source']}</p>
            <div style="background-color: #f0f7ff; border-left: 4px solid #0056b3; padding: 10px; font-style: italic; color: #555; font-size: 14px; margin: 15px 0;">"{job['Summary']}"</div>
            <div style="font-size: 14px;"><strong>Strengths:</strong><ul style="padding-left: 20px; margin-top: 5px;">{strengths}</ul></div>
            <div style="font-size: 14px; margin-top: 10px;"><strong>Gaps / Risks:</strong><ul style="padding-left: 20px; margin-top: 5px;">{gaps}</ul></div>
            <div style="text-align: right; margin-top: 15px;"><a href="{job['URL']}" style="background-color: #0056b3; color: white; text-decoration: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; font-size: 14px;">Apply Now</a></div>
        </div>"""
    
    html_content += "</div></body></html>"
    
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = target_email
    msg['Subject'] = f"🔥 Job Report: {len(sorted_jobs)} Matches Found"
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        print("\n✅ Email sent!")
    except Exception as e: 
        print(f"\n❌ Email Failed: {e}")
