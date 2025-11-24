import streamlit as st
import pandas as pd
import time
import os
import logic
import json
from datetime import datetime

import database

# Initialize DB
database.init_db()

# Page Config
st.set_page_config(page_title="JobHunter AI", page_icon="🚀", layout="wide")

# Custom CSS
st.markdown("""
<style>
    /* Remove default padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }
    
    /* Card styling */
    .job-card {
        background: white;
        border: 1px solid #E8E4DD;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .job-header {
        display: flex;
        justify-content: space-between;
        align-items: start;
        margin-bottom: 12px;
    }
    
    .job-title {
        font-size: 1.4em;
        font-weight: 700;
        color: #2C2C2C;
        margin: 0;
    }
    
    .job-org {
        font-size: 1em;
        color: #666;
        margin: 4px 0 0 0;
    }
    
    .score-badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9em;
        white-space: nowrap;
    }
    
    .score-green {
        background: #D4EDDA;
        color: #155724;
    }
    
    .score-orange {
        background: #FFF3CD;
        color: #856404;
    }
    
    .summary-box {
        background: #F7F5F2;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
        font-style: italic;
        color: #4A4A4A;
        line-height: 1.6;
    }
    
    .details-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin: 16px 0;
    }
    
    .detail-box h4 {
        margin: 0 0 10px 0;
        font-size: 1em;
        font-weight: 600;
    }
    
    .detail-box ul {
        margin: 0;
        padding-left: 20px;
    }
    
    .detail-box li {
        margin-bottom: 6px;
        line-height: 1.5;
    }
    
    .apply-button {
        display: block;
        width: 100%;
        padding: 12px;
        background: #A98467;
        color: white;
        text-align: center;
        text-decoration: none;
        border-radius: 8px;
        font-weight: 600;
        margin-top: 16px;
    }
    
    .apply-button:hover {
        background: #8F6E55;
        text-decoration: none;
    }
    
    /* Sidebar profile styling */
    .profile-section {
        background: #F0EBE3;
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
    }
    
    .profile-section h4 {
        margin: 0 0 8px 0;
        color: #2C2C2C;
    }
    
    .skill-tag {
        display: inline-block;
        background: white;
        padding: 4px 12px;
        border-radius: 16px;
        margin: 4px 4px 4px 0;
        font-size: 0.85em;
        border: 1px solid #D4CFC5;
    }
</style>
""", unsafe_allow_html=True)

# Session State for User and Registration Wizard
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'registration_step' not in st.session_state:
    st.session_state['registration_step'] = 0
if 'registration_data' not in st.session_state:
    st.session_state['registration_data'] = {}

# --- Login / Register Logic ---
if not st.session_state['user']:
    st.title("🚀 JobHunter AI")
    
    # Not in registration mode - show login
    if st.session_state['registration_step'] == 0:
        st.subheader("🔑 Login")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            col_login, col_register = st.columns(2)
            with col_login:
                if st.button("Login", type="primary", use_container_width=True):
                    user = database.verify_password(email, password)
                    if user:
                        st.session_state['user'] = user
                        # Load Profile
                        profile = database.get_profile(user['id'])
                        if profile:
                            st.session_state['cv_text'] = profile['cv_text']
                            st.session_state['candidate_profile'] = profile['structured_profile']
                            st.session_state['candidate_profile']['search_keywords'] = profile['search_keywords']
                        else:
                            st.session_state['cv_text'] = ""
                            st.session_state['candidate_profile'] = {}
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
            
            with col_register:
                if st.button("Create Account", use_container_width=True):
                    st.session_state['registration_step'] = 1
                    st.session_state['registration_data'] = {}
                    st.rerun()
    
    # Registration Wizard
    elif st.session_state['registration_step'] > 0:
        st.subheader("📝 Create Your Account")
        st.progress(st.session_state['registration_step'] / 3, text=f"Step {st.session_state['registration_step']} of 3")
        
        # Step 1: Account Setup
        if st.session_state['registration_step'] == 1:
            st.markdown("### Step 1: Account Information")
            
            reg_email = st.text_input("Email Address", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
            
            col_back, col_next = st.columns([1, 1])
            with col_back:
                if st.button("Cancel", use_container_width=True):
                    st.session_state['registration_step'] = 0
                    st.session_state['registration_data'] = {}
                    st.rerun()
            
            with col_next:
                if st.button("Next →", type="primary", use_container_width=True):
                    if not reg_email or not reg_password:
                        st.error("Please fill in all fields")
                    elif reg_password != reg_password_confirm:
                        st.error("Passwords do not match")
                    elif database.get_user_by_email(reg_email):
                        st.error("Email already exists. Please login instead.")
                    else:
                        st.session_state['registration_data']['email'] = reg_email
                        st.session_state['registration_data']['password'] = reg_password
                        st.session_state['registration_step'] = 2
                        st.rerun()
        
        # Step 2: The Brain (CV Upload)
        elif st.session_state['registration_step'] == 2:
            st.markdown("### Step 2: Upload Your CV")
            st.caption("We'll analyze your CV to create your personalized job hunting profile")
            
            uploaded_cv = st.file_uploader("Upload CV (PDF)", type="pdf", key="reg_cv_upload")
            
            if uploaded_cv and 'cv_text' not in st.session_state['registration_data']:
                with st.spinner("Extracting and analyzing your CV..."):
                    cv_text = logic.extract_text_from_pdf(uploaded_cv)
                    profile = logic.generate_candidate_profile(cv_text)
                    
                    st.session_state['registration_data']['cv_text'] = cv_text
                    st.session_state['registration_data']['profile'] = profile
                    st.success("✅ CV Analyzed!")
            
            if 'profile' in st.session_state['registration_data']:
                st.markdown("#### 👀 Profile Preview")
                profile = st.session_state['registration_data']['profile']
                
                with st.expander("🔍 Search Keywords", expanded=True):
                    keywords = profile.get('search_keywords', [])
                    st.write(", ".join(keywords))
                
                with st.expander("🛠️ Core Skills"):
                    skills = profile.get('2_core_tech_stack', [])
                    for skill in skills:
                        st.markdown(f"- {skill}")
            
            col_back, col_next = st.columns([1, 1])
            with col_back:
                if st.button("← Back", use_container_width=True):
                    if 'cv_text' in st.session_state['registration_data']:
                        del st.session_state['registration_data']['cv_text']
                    if 'profile' in st.session_state['registration_data']:
                        del st.session_state['registration_data']['profile']
                    st.session_state['registration_step'] = 1
                    st.rerun()
            
            with col_next:
                if st.button("Next →", type="primary", use_container_width=True, disabled='profile' not in st.session_state['registration_data']):
                    st.session_state['registration_step'] = 3
                    st.rerun()
        
        # Step 3: Preferences
        elif st.session_state['registration_step'] == 3:
            st.markdown("### Step 3: Notification Preferences")
            
            default_email = st.session_state['registration_data'].get('email', '')
            target_email = st.text_input(
                "Email for Daily Job Alerts", 
                value=default_email,
                key="reg_target_email",
                help="Where should we send your daily job matches?"
            )
            
            col_back, col_finish = st.columns([1, 1])
            with col_back:
                if st.button("← Back", use_container_width=True):
                    st.session_state['registration_step'] = 2
                    st.rerun()
            
            with col_finish:
                if st.button("🚀 Create Account", type="primary", use_container_width=True):
                    user_id = database.create_user(
                        st.session_state['registration_data']['email'],
                        st.session_state['registration_data']['password'],
                        target_email
                    )
                    
                    if user_id:
                        database.save_profile(
                            user_id,
                            st.session_state['registration_data']['cv_text'],
                            st.session_state['registration_data']['profile'],
                            st.session_state['registration_data']['profile'].get('search_keywords', [])
                        )
                        
                        user = database.get_user_by_email(st.session_state['registration_data']['email'])
                        st.session_state['user'] = user
                        st.session_state['cv_text'] = st.session_state['registration_data']['cv_text']
                        st.session_state['candidate_profile'] = st.session_state['registration_data']['profile']
                        
                        st.session_state['registration_step'] = 0
                        st.session_state['registration_data'] = {}
                        
                        st.success("🎉 Account created! Welcome to JobHunter AI!")
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")
    
    st.stop()

# --- Main App (Logged In) ---

# Startup check for credentials
try:
    if 'OPENAI_API_KEY' not in st.secrets and not os.getenv('OPENAI_API_KEY'):
        st.error("⚠️ OPENAI_API_KEY not configured. Please add it to .streamlit/secrets.toml")
        st.stop()
except:
    if not os.getenv('OPENAI_API_KEY'):
        st.error("⚠️ OPENAI_API_KEY not configured. Please set it as an environment variable.")
        st.stop()

# Sidebar - User Dashboard
with st.sidebar:
    st.markdown("## 👤 My Profile")
    
    # Logout
    if st.button("Logout", use_container_width=True):
        st.session_state['user'] = None
        st.session_state['cv_text'] = ""
        st.session_state['candidate_profile'] = {}
        st.rerun()
    
    st.divider()
    
    # Load or upload CV
    user_profile = database.get_profile(st.session_state['user']['id'])
    
    cv_upload = st.file_uploader("📄 Upload/Update CV", type="pdf")
    
    if cv_upload:
        with st.spinner("Processing CV..."):
            cv_text = logic.extract_text_from_pdf(cv_upload)
            profile = logic.generate_candidate_profile(cv_text)
            
            database.save_profile(
                st.session_state['user']['id'],
                cv_text,
                profile,
                profile.get('search_keywords', [])
            )
            
            st.session_state['cv_text'] = cv_text
            st.session_state['candidate_profile'] = profile
            st.success("✅ CV Updated!")
            st.rerun()
    
    # Display profile if exists
    if user_profile:
        profile_data = user_profile.get('structured_profile', {})
        
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        st.markdown("#### 🛠️ Top Skills")
        skills = profile_data.get('2_core_tech_stack', [])[:6]
        for skill in skills:
            st.markdown(f'<span class="skill-tag">{skill}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        st.markdown("#### 📊 Experience")
        qual = profile_data.get('1_essential_qualifications', {})
        years = qual.get('years_experience', 0)
        sector = qual.get('sector', 'Not specified')
        st.write(f"**{years} years** in {sector}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Target Email
    current_target = st.session_state['user'].get('target_email', '')
    target_email = st.text_input("📧 Alert Email", value=current_target)
    
    if target_email != current_target:
        conn = database.sqlite3.connect(database.DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET target_email = ? WHERE id = ?", 
                  (target_email, st.session_state['user']['id']))
        conn.commit()
        conn.close()
        st.session_state['user']['target_email'] = target_email
    
    st.divider()
    
    # Find Jobs Button
    if st.button("🔍 Find New Jobs", type="primary", use_container_width=True):
        if not user_profile:
            st.warning("Please upload a CV first!")
        else:
            st.session_state['trigger_search'] = True
            st.rerun()

# Main Page - Job Feed
st.title("📰 Daily Intelligence Report")
st.caption(f"Generated on {datetime.now().strftime('%B %d, %Y')}")

st.divider()

# Trigger job search
if st.session_state.get('trigger_search', False):
    st.session_state['trigger_search'] = False
    
    user_profile = database.get_profile(st.session_state['user']['id'])
    candidate_profile = user_profile['structured_profile']
    candidate_profile['search_keywords'] = user_profile['search_keywords']
    
    with st.status("🔍 Scanning Job Boards...", expanded=True) as status:
        start_time = time.time()
        
        def update_status(msg):
            status.write(msg)
        
        jobs = logic.fetch_all_jobs(candidate_profile, status_callback=update_status)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        status.update(label=f"✅ Found {len(jobs)} jobs in {elapsed:.2f}s", state="complete", expanded=False)
    
    # Match jobs
    results = []
    progress_bar = st.progress(0)
    
    for i, job in enumerate(jobs):
        analysis = logic.match_job_to_cv(job['clean_body'], candidate_profile)
        score = analysis.get('score', 0)
        
        if score > 0:  # Only keep jobs with score > 0
            results.append({
                "title": job['title'],
                "org": job['org'],
                "score": score,
                "summary": analysis.get('job_summary', 'N/A'),
                "strengths": analysis.get('strengths', []),
                "gaps": analysis.get('gaps', []),
                "url": job['url'],
                "source": job['source']
            })
        
        progress_bar.progress((i + 1) / len(jobs))
    
    progress_bar.empty()
    st.session_state['job_results'] = sorted(results, key=lambda x: x['score'], reverse=True)

# Display job cards
if 'job_results' in st.session_state and st.session_state['job_results']:
    st.subheader(f"🎯 {len(st.session_state['job_results'])} Matching Opportunities")
    
    for job in st.session_state['job_results']:
        # Determine badge color
        badge_class = "score-green" if job['score'] > 85 else "score-orange"
        
        # Build strengths list
        strengths_html = "".join([f"<li>{s}</li>" for s in job['strengths'][:5]])
        
        # Build gaps list
        gaps_html = "".join([f"<li>{g}</li>" for g in job['gaps'][:5]])
        
        # Create card HTML
        card_html = f"""
        <div class="job-card">
            <div class="job-header">
                <div>
                    <h2 class="job-title">{job['title']}</h2>
                    <p class="job-org">{job['org']}</p>
                </div>
                <div class="score-badge {badge_class}">
                    {job['score']}% Match
                </div>
            </div>
            
            <div class="summary-box">
                {job['summary']}
            </div>
            
            <div class="details-grid">
                <div class="detail-box">
                    <h4>✅ Your Match</h4>
                    <ul>
                        {strengths_html}
                    </ul>
                </div>
                <div class="detail-box">
                    <h4>⚠️ Potential Gaps</h4>
                    <ul>
                        {gaps_html}
                    </ul>
                </div>
            </div>
            
            <a href="{job['url']}" target="_blank" class="apply-button">
                Apply Now →
            </a>
        </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Save button (outside the card)
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("💾 Save", key=f"save_{job['url']}", use_container_width=True):
                saved = database.save_job(
                    st.session_state['user']['id'],
                    job['title'],
                    job['org'],
                    job['score'],
                    job['url']
                )
                if saved:
                    st.toast(f"Saved: {job['title']}")
                else:
                    st.toast("Already saved!")

elif 'job_results' in st.session_state:
    st.info("No matching jobs found. Try adjusting your profile or check back later!")
else:
    st.info("👈 Click 'Find New Jobs' in the sidebar to start your search!")
