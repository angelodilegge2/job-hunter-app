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

# Title
st.title("🚀 JobHunter AI")

# Sidebar - API Key & File Upload
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check for API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = st.text_input("Enter OpenAI API Key", type="password")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            st.success("API Key saved!")
    else:
        st.success("API Key loaded from environment")

    st.divider()
    
    st.header("📄 CV Upload")
    uploaded_file = st.file_uploader("Upload your CV (PDF)", type="pdf")
    
    # Initialize session state
    if 'cv_text' not in st.session_state:
        st.session_state['cv_text'] = ""
    if 'candidate_profile' not in st.session_state:
        st.session_state['candidate_profile'] = {}
    
    if uploaded_file is not None:
        # Only extract if we haven't already or if it's a new file (simplified check)
        # For now, just extract when uploaded
        if not st.session_state['cv_text']:
            with st.spinner("Extracting text..."):
                st.session_state['cv_text'] = logic.extract_text_from_pdf(uploaded_file)

    # Editable CV Text
    if st.session_state['cv_text']:
        st.subheader("📝 Editable CV Text")
        st.session_state['cv_text'] = st.text_area(
            "Modify text before analysis:", 
            value=st.session_state['cv_text'], 
            height=300
        )
        
        if st.button("🔄 Analyze / Re-Analyze Profile"):
            with st.spinner("Analyzing CV..."):
                st.session_state['candidate_profile'] = logic.generate_candidate_profile(st.session_state['cv_text'])
                st.success("Profile Updated!")

    # Editable Profile Data
    if st.session_state['candidate_profile']:
        st.divider()
        st.header("👤 Profile Context")
        
        # Search Keywords
        current_keywords = st.session_state['candidate_profile'].get('search_keywords', [])
        keywords_str = ", ".join(current_keywords)
        new_keywords_str = st.text_input("🔍 Search Keywords (comma separated)", value=keywords_str)
        st.session_state['candidate_profile']['search_keywords'] = [k.strip() for k in new_keywords_str.split(",") if k.strip()]
        
        st.subheader("🧬 Match Context")
        
        # 1. Essential Qualifications
        with st.expander("🎓 Essential Qualifications", expanded=True):
            qual = st.session_state['candidate_profile'].get('1_essential_qualifications', {})
            
            new_edu = st.text_input("Education", value=qual.get('education', ''))
            new_exp = st.number_input("Years of Experience", value=int(qual.get('years_experience', 0)), min_value=0)
            new_sector = st.text_input("Sector", value=qual.get('sector', ''))
            
            langs = qual.get('languages', [])
            langs_str = ", ".join(langs) if isinstance(langs, list) else str(langs)
            new_langs_str = st.text_input("Languages (comma separated)", value=langs_str)
            
            # Update state
            st.session_state['candidate_profile']['1_essential_qualifications'] = {
                "education": new_edu,
                "years_experience": new_exp,
                "sector": new_sector,
                "languages": [l.strip() for l in new_langs_str.split(",") if l.strip()]
            }

        # 2. Tech Stack
        with st.expander("🛠️ Skills & Tech Stack"):
            core = st.session_state['candidate_profile'].get('2_core_tech_stack', [])
            core_str = ", ".join(core) if isinstance(core, list) else str(core)
            new_core_str = st.text_area("Core Tech Stack (comma separated)", value=core_str)
            st.session_state['candidate_profile']['2_core_tech_stack'] = [s.strip() for s in new_core_str.split(",") if s.strip()]
            
            desired = st.session_state['candidate_profile'].get('3_desired_stack', [])
            desired_str = ", ".join(desired) if isinstance(desired, list) else str(desired)
            new_desired_str = st.text_area("Desired Stack (comma separated)", value=desired_str)
            st.session_state['candidate_profile']['3_desired_stack'] = [s.strip() for s in new_desired_str.split(",") if s.strip()]

        # 3. Logistics
        with st.expander("🌍 Logistics"):
            logistics = st.session_state['candidate_profile'].get('4_logistics', {})
            
            new_loc = st.text_input("Current Location", value=logistics.get('current_location', ''))
            new_mob = st.text_input("Mobility", value=logistics.get('mobility', ''))
            
            st.session_state['candidate_profile']['4_logistics'] = {
                "current_location": new_loc,
                "mobility": new_mob
            }

# Main Area Tabs
tab1, tab2 = st.tabs(["🔍 Search Jobs", "💾 My Saved Jobs"])

with tab1:
    if st.button("🔍 Scan for Jobs", type="primary"):
        candidate_profile = st.session_state.get('candidate_profile', {})
        if not candidate_profile:
            st.warning("Please upload a CV and analyze it first.")
        else:
            with st.status("🔍 Scanning Job Boards...", expanded=True) as status:
                start_time = time.time()
                
                # Define callback for status updates
                def update_status(msg):
                    status.write(msg)
                
                # Fetch Jobs with callback
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
                    # Store results in session state to persist across reruns (like saving)
                    st.session_state['last_results'] = results
                else:
                    st.warning("No jobs found to analyze.")

    # Display Results from Session State
    if 'last_results' in st.session_state:
        results = st.session_state['last_results']
        
        st.subheader("📊 Results")
        
        # Display as list with Save buttons
        # Sorting by score
        sorted_results = sorted(results, key=lambda x: x['Score'], reverse=True)
        
        for job in sorted_results:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"### [{job['Job Title']}]({job['URL']})")
                    st.markdown(f"**{job['Organization']}** | Score: **{job['Score']}**")
                    st.caption(f"Source: {job['Source']}")
                    with st.expander("Details"):
                        st.write(job['Summary'])
                        st.write(job['Summary'])
                        st.markdown("**Strengths:**")
                        for s in job['Strengths']:
                            st.markdown(f"- ✅ {s}")
                        st.markdown("**Gaps:**")
                        for g in job['Gaps']:
                            st.markdown(f"- ⚠️ {g}")
                with col2:
                    if st.button("💾 Save", key=f"save_{job['URL']}"):
                        saved = database.save_job(job['Job Title'], job['Organization'], job['Score'], job['URL'])
                        if saved:
                            st.toast(f"Saved: {job['Job Title']}")
                        else:
                            st.toast("Already saved!")
                st.divider()

with tab2:
    st.header("💾 My Saved Jobs")
    saved_jobs = database.get_saved_jobs()
    
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
        st.info("No saved jobs yet.")

# Cleanup temp file - No longer needed
# if os.path.exists("temp_cv.pdf"):
#    os.remove("temp_cv.pdf")
