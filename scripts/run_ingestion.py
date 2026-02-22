"""
scripts/run_ingestion.py — CLI to run the full ingestion pipeline.
(Stub — will be fully implemented in Phase 2)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

print("🔄 [Stub] Ingestion pipeline will be implemented in Phase 2.")
print("   Steps that will run:")
print("   1. Fetch job postings from RemoteOK API")
print("   2. Normalize and clean job data")
print("   3. Filter by AI-generated role keywords")
print("   4. Qualify leads via LLM")
print("   5. Save leads to DB")
