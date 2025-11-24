import logic
import os
from unittest.mock import MagicMock, patch

# Mock OpenAI
with patch('openai.OpenAI') as MockClient:
    mock_instance = MockClient.return_value
    mock_instance.chat.completions.create.return_value.choices[0].message.content = '{"score": 85, "job_summary": "Good match", "strengths": ["Python"], "gaps": ["None"]}'

    # Mock requests
    with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
        # Mock ReliefWeb response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": [{
                "fields": {
                    "title": "Test Job",
                    "source": [{"name": "Test Org"}],
                    "body": "<p>Test Description</p>",
                    "url": "http://example.com",
                    "date": {"created": "2025-11-20T12:00:00+00:00"}
                }
            }]
        }
        
        # Mock other fetchers to return empty or simple data
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [] # Default empty for others

        print("Testing fetch_all_jobs...")
        profile = {"search_keywords": ["Test"]}
        jobs = logic.fetch_all_jobs(profile)
        print(f"Fetched {len(jobs)} jobs.")
        
        if jobs:
            print("Testing match_job_to_cv...")
            match = logic.match_job_to_cv(jobs[0]['clean_body'], profile)
            print(f"Match score: {match.get('score')}")

print("Test complete.")
