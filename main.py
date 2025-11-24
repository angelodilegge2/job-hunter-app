import os
import logic
from getpass import getpass

def main():
    print("🔐 SECURE SETUP")
    print("------------------------------------------------")
    
    # Load credentials
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        openai_key = getpass("Paste OpenAI Key: ")
        os.environ["OPENAI_API_KEY"] = openai_key
        # Re-initialize client in logic if needed, but logic.py initializes at module level.
        # Since we set env var here, we might need to reload or just set it.
        # logic.client.api_key = openai_key # If using global client
    
    email_user = os.getenv("EMAIL_USER")
    if not email_user:
        email_user = input("Your Gmail Address: ")
    
    email_pass = os.getenv("EMAIL_PASS")
    if not email_pass:
        email_pass = getpass("Gmail App Password (16 chars): ")
        
    target_email = os.getenv("TARGET_EMAIL")
    if not target_email:
        target_email = input("Target Email: ")

    print("\n📂 Please provide path to your CV (PDF)...")
    cv_path = input("CV Path (or press Enter to use default profile): ").strip()
    
    my_profile = {"search_keywords": ["Evaluation", "Policy"]}
    
    if cv_path and os.path.exists(cv_path):
        cv_text = logic.extract_text_from_pdf(cv_path)
        if cv_text:
            my_profile = logic.generate_candidate_profile(cv_text)
            print("✅ CV Profiled.")
        else:
            print("⚠️ Could not extract text from CV. Using default profile.")
    else:
        print("⚠️ No CV provided or file not found. Using default profile.")

    # Fetch Jobs
    jobs = logic.fetch_all_jobs(my_profile)
    
    # Match and Report
    results = []
    print(f"\n🤖 Analyzing {len(jobs)} jobs...")
    for job in jobs:
        print(f"   👉 {job['title'][:40]}...", end="")
        analysis = logic.match_job_to_cv(job['clean_body'], my_profile)
        score = analysis.get('score', 0)
        print(f" Score: {score}")
        results.append({
            "Job Title": job['title'], 
            "Organization": job['org'], 
            "Score": score,
            "Summary": analysis.get('job_summary', 'N/A'), 
            "strengths": analysis.get('strengths', []),
            "gaps": analysis.get('gaps', []), 
            "URL": job['url'], 
            "source": job['source']
        })
        
    # Send Email
    if results:
        logic.send_visual_email(results, email_user, email_pass, target_email)
    else:
        print("No results to report.")

if __name__ == "__main__":
    main()
