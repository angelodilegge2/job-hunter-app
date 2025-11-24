import logic
import os

# Mock OpenAI key for test if not present (it won't work for real calls but checks import)
if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY not set. OpenAI calls will fail.")

print("Testing imports...")
try:
    import requests
    import bs4
    import pdfplumber
    import openai
    print("Imports successful.")
except ImportError as e:
    print(f"Import failed: {e}")

print("\nTesting fetch_reliefweb_jobs...")
jobs = logic.fetch_reliefweb_jobs()
print(f"Fetched {len(jobs)} jobs from ReliefWeb.")
if jobs:
    print(f"Sample job: {jobs[0]['title']}")

print("\nTesting fetch_all_jobs (empty targets)...")
all_jobs = logic.fetch_all_jobs()
print(f"Fetched {len(all_jobs)} total jobs.")
