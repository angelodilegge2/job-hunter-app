import database
import os

# Reset DB for testing
if os.path.exists("jobs.db"):
    os.remove("jobs.db")

print("🚀 Initializing DB...")
database.init_db()

print("\n👤 Testing User Creation...")
user_id = database.create_user("test@example.com", "password123", "target@example.com")
if user_id:
    print(f"✅ User created with ID: {user_id}")
else:
    print("❌ Failed to create user")

print("\n🔐 Testing Login...")
user = database.verify_password("test@example.com", "password123")
if user:
    print(f"✅ Login successful for: {user['email']}")
else:
    print("❌ Login failed")

print("\n📄 Testing Profile Save/Load...")
profile_data = {"skills": ["Python", "AI"]}
keywords = ["Python", "Developer"]
database.save_profile(user_id, "Raw CV Text", profile_data, keywords)
loaded_profile = database.get_profile(user_id)

if loaded_profile and loaded_profile['structured_profile'] == profile_data:
    print("✅ Profile saved and loaded correctly")
else:
    print(f"❌ Profile mismatch: {loaded_profile}")

print("\n💾 Testing Job Save...")
saved = database.save_job(user_id, "AI Engineer", "Google", 95, "http://google.com/jobs/1")
if saved:
    print("✅ Job saved")
else:
    print("❌ Failed to save job")

jobs = database.get_saved_jobs(user_id)
if len(jobs) == 1 and jobs[0]['title'] == "AI Engineer":
    print("✅ Job retrieved correctly")
else:
    print(f"❌ Job retrieval failed: {jobs}")

print("\n🚫 Testing Isolation (User 2)...")
user2_id = database.create_user("user2@example.com", "pass", "u2@ex.com")
jobs2 = database.get_saved_jobs(user2_id)
if len(jobs2) == 0:
    print("✅ User 2 sees 0 jobs (Isolation working)")
else:
    print(f"❌ Isolation failed, User 2 sees: {jobs2}")
