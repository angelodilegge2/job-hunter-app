import streamlit as st
import pandas as pd
import time
import os
import logic
import json

import database

# Initialize DB
database.init_db()

# Page Config
st.set_page_config(page_title="JobHunter AI", page_icon="🚀", layout="wide")

# Session State for User and Registration Wizard
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'registration_step' not in st.session_state:
    st.session_state['registration_step'] = 0  # 0 = not registering, 1-3 = wizard steps
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
            
            # Process CV if uploaded and not yet processed
            if uploaded_cv and 'cv_text' not in st.session_state['registration_data']:
                with st.spinner("Extracting and analyzing your CV..."):
                    cv_text = logic.extract_text_from_pdf(uploaded_cv)
                    profile = logic.generate_candidate_profile(cv_text)
                    
                    st.session_state['registration_data']['cv_text'] = cv_text
                    st.session_state['registration_data']['profile'] = profile
                    st.success("✅ CV Analyzed!")
            
            # Display profile preview if available
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
                
                with st.expander("🎯 Desired Skills"):
                    desired = profile.get('3_desired_stack', [])
                    for skill in desired:
                        st.markdown(f"- {skill}")
            
            col_back, col_next = st.columns([1, 1])
            with col_back:
                if st.button("← Back", use_container_width=True):
                    # Clear CV data when going back
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
                    # Create user
                    user_id = database.create_user(
                        st.session_state['registration_data']['email'],
                        st.session_state['registration_data']['password'],
                        target_email
                    )
                    
                    if user_id:
                        # Save profile
                        database.save_profile(
                            user_id,
                            st.session_state['registration_data']['cv_text'],
                            st.session_state['registration_data']['profile'],
                            st.session_state['registration_data']['profile'].get('search_keywords', [])
                        )
                        
                        # Auto-login
                        user = database.get_user_by_email(st.session_state['registration_data']['email'])
                        st.session_state['user'] = user
                        
                        # Load profile into session
                        st.session_state['cv_text'] = st.session_state['registration_data']['cv_text']
                        st.session_state['candidate_profile'] = st.session_state['registration_data']['profile']
                        
                        # Clear registration state
                        st.session_state['registration_step'] = 0
                        st.session_state['registration_data'] = {}
                        
                        st.success("🎉 Account created! Welcome to JobHunter AI!")
                        st.rerun()
                    else:
                        st.error("Failed to create account. Please try again.")
    
    st.stop() # Stop execution if not logged in

# --- Main App Logic (Logged In) ---

# Startup check for credentials
try:
    if 'OPENAI_API_KEY' not in st.secrets and not os.getenv('OPENAI_API_KEY'):
        st.error("⚠️ OPENAI_API_KEY not configured. Please add it to .streamlit/secrets.toml")
        st.stop()
except:
    if not os.getenv('OPENAI_API_KEY'):
        st.error("⚠️ OPENAI_API_KEY not configured. Please set it as an environment variable.")
        st.stop()

# Title & Logout
col_title, col_logout = st.columns([8, 1])
with col_title:
    st.title(f"🚀 JobHunter AI")
    st.caption(f"Logged in as: {st.session_state['user']['email']}")
with col_logout:
    if st.button("Logout"):
        st.session_state['user'] = None
        st.session_state['cv_text'] = ""
        st.session_state['candidate_profile'] = {}
        st.rerun()

# Sidebar - Profile Summary
with st.sidebar:
    st.header("👤 Your Profile")
    
    # Load profile from DB
    user_profile = database.get_profile(st.session_state['user']['id'])
    
    if user_profile:
        # Search Keywords
        st.subheader("🔍 Search Keywords")
        keywords = user_profile.get('search_keywords', [])
        if keywords:
            st.write(", ".join(keywords))
        else:
            st.caption("No keywords set")
        
        # Core Skills
        st.subheader("🛠️ Core Skills")
        profile_data = user_profile.get('structured_profile', {})
        skills = profile_data.get('2_core_tech_stack', [])
        if skills:
            for skill in skills[:5]:  # Show top 5
                st.markdown(f"- {skill}")
            if len(skills) > 5:
                st.caption(f"...and {len(skills) - 5} more")
        else:
            st.caption("No skills listed")
        
        # Target Email
        st.subheader("📧 Alert Email")
        st.write(st.session_state['user'].get('target_email', 'Not set'))
    else:
        st.info("No profile data. Upload a CV in Settings.")

# Main Area - 3 Tabs
tab1, tab2, tab3 = st.tabs(["🔍 Live Search", "💾 My Saved Jobs", "⚙️ Settings"])

# Tab 1: Live Search
with tab1:
    st.header("Live Job Search")
    
    if st.button("🔍 Run Scan Now", type="primary"):
        user_profile = database.get_profile(st.session_state['user']['id'])
        
        if not user_profile or not user_profile.get('search_keywords'):
            st.warning("Please set up your profile in Settings first.")
        else:
            # Use stored profile for search
            candidate_profile = user_profile['structured_profile']
            candidate_profile['search_keywords'] = user_profile['search_keywords']
            
            with st.status("🔍 Scanning Job Boards...", expanded=True) as status:
                start_time = time.time()
                
                def update_status(msg):
                    status.write(msg)
                
                # Fetch Jobs
                jobs = logic.fetch_all_jobs(candidate_profile, status_callback=update_status)
                
                end_time = time.time()
                elapsed = end_time - start_time
                
                status.update(label=f"✅ Search Complete! Found {len(jobs)} jobs in {elapsed:.2f} seconds.", state="complete", expanded=False)
                
                st.info(f"⏱️ Search took {elapsed:.2f} seconds. Analyzing matches...")
                
                # Match Jobs
                results = []
                progress_bar = st.progress(0)
                
                for i, job in enumerate(jobs):
                    analysis = logic.match_job_to_cv(job['clean_body'], candidate_profile)
                    score = analysis.get('score', 0)
                    
                    results.append({
                        "Job Title": job['title'],
                        "Organization": job['org'],
                        "Score": score,
                        "Summary": analysis.get('job_summary', 'N/A'),
                        "Strengths": analysis.get('strengths', []),
                        "Gaps": analysis.get('gaps', []),
                        "URL": job['url'],
                        "Source": job['source']
                    })
                    progress_bar.progress((i + 1) / len(jobs))
                
                if results:
                    st.session_state['last_results'] = results
                else:
                    st.warning("No jobs found to analyze.")

    # Display Results
    if 'last_results' in st.session_state:
        results = st.session_state['last_results']
        
        st.subheader(f"📊 Found {len(results)} Jobs")
        
        sorted_results = sorted(results, key=lambda x: x['Score'], reverse=True)
        
        for job in sorted_results:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"### [{job['Job Title']}]({job['URL']})")
                    st.markdown(f"**{job['Organization']}** | Score: **{job['Score']}** | Source: {job['Source']}")
                    
                    with st.expander("Details"):
                        st.write(job['Summary'])
                        st.markdown("**Strengths:**")
                        for s in job['Strengths']:
                            st.markdown(f"- ✅ {s}")
                        st.markdown("**Gaps:**")
                        for g in job['Gaps']:
                            st.markdown(f"- ⚠️ {g}")
                with col2:
                    if st.button("💾 Save", key=f"save_{job['URL']}"):
                        saved = database.save_job(
                            st.session_state['user']['id'], 
                            job['Job Title'], 
                            job['Organization'], 
                            job['Score'], 
                            job['URL']
                        )
                        if saved:
                            st.toast(f"Saved: {job['Job Title']}")
                        else:
                            st.toast("Already saved!")
                st.divider()

# Tab 2: My Saved Jobs
with tab2:
    st.header("💾 My Saved Jobs")
    
    saved_jobs = database.get_saved_jobs(st.session_state['user']['id'])
    
    if saved_jobs:
        df_saved = pd.DataFrame(saved_jobs)
        st.dataframe(
            df_saved[["title", "company", "score", "date_added", "url"]],
            use_container_width=True,
            column_config={
                "url": st.column_config.LinkColumn("Link"),
                "title": "Job Title",
                "company": "Company",
                "score": "Score",
                "date_added": "Date Added"
            }
        )
    else:
        st.info("No saved jobs yet. Run a search and save jobs you like!")

# Tab 3: Settings
with tab3:
    st.header("⚙️ Settings")
    
    # Section 1: Update Target Email
    st.subheader("📧 Notification Email")
    current_email = st.session_state['user'].get('target_email', '')
    new_target_email = st.text_input("Email for daily job alerts", value=current_email)
    
    if st.button("Update Email"):
        # Update user in database
        conn = database.sqlite3.connect(database.DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET target_email = ? WHERE id = ?", 
                  (new_target_email, st.session_state['user']['id']))
        conn.commit()
        conn.close()
        
        # Update session state
        st.session_state['user']['target_email'] = new_target_email
        st.success("✅ Email updated!")
    
    st.divider()
    
    # Section 2: Re-upload CV
    st.subheader("📄 Update Your CV")
    st.caption("Upload a new CV to refresh your profile")
    
    cv_file = st.file_uploader("Upload CV (PDF)", type="pdf", key="settings_cv_upload")
    
    if cv_file:
        with st.spinner("Processing your CV..."):
            # Extract and analyze
            cv_text = logic.extract_text_from_pdf(cv_file)
            profile = logic.generate_candidate_profile(cv_text)
            
            # Save to database
            database.save_profile(
                st.session_state['user']['id'],
                cv_text,
                profile,
                profile.get('search_keywords', [])
            )
            
            st.success("✅ CV updated! Your profile has been refreshed.")
            st.info("💡 Your search keywords and skills have been updated based on the new CV.")
            st.rerun()

