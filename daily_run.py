import os
import logic
import sys

def main():
    print("🚀 Starting Daily Job Hunter...")

    # 1. Load Credentials
    openai_key = os.getenv("OPENAI_API_KEY")
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    target_email = os.getenv("TARGET_EMAIL")

    if not all([openai_key, email_user, email_pass, target_email]):
        print("❌ Missing environment variables! Ensure OPENAI_API_KEY, EMAIL_USER, EMAIL_PASS, and TARGET_EMAIL are set.")
        sys.exit(1)

    # 2. Load CV
    cv_path = "cv.pdf"
    if not os.path.exists(cv_path):
        print(f"❌ CV file not found at {cv_path}. Please ensure cv.pdf is in the root directory.")
        sys.exit(1)

    print(f"📄 Loading CV from {cv_path}...")
    cv_text = logic.extract_text_from_pdf(cv_path)
    
    if not cv_text:
        print("❌ Failed to extract text from CV.")
        sys.exit(1)

    # 3. Generate Profile
    print("🧠 Generating Candidate Profile...")
    profile = logic.generate_candidate_profile(cv_text)
    print(f"   Keywords: {profile.get('search_keywords')}")

    # 4. Fetch Jobs
    print("🔍 Fetching Jobs...")
    jobs = logic.fetch_all_jobs(profile, status_callback=print)
    
    if not jobs:
        print("📭 No jobs found today.")
        return

    # 5. Match Jobs
    print(f"🤖 Matching {len(jobs)} jobs...")
    results = []
    for job in jobs:
        analysis = logic.match_job_to_cv(job['clean_body'], profile)
        analysis['URL'] = job['url']
        analysis['Job Title'] = job['title']
        analysis['Organization'] = job['org']
        analysis['source'] = job['source']
        analysis['Score'] = analysis.get('score', 0)
        analysis['Summary'] = analysis.get('job_summary', 'N/A')
        results.append(analysis)

    # 6. Send Email
    print("📧 Sending Email Report...")
    logic.send_visual_email(results, email_user, email_pass, target_email)
    print("✅ Daily run complete!")

if __name__ == "__main__":
    main()
