"""
scripts/run_outreach.py — CLI to run the email outreach pipeline.
(Stub — will be fully implemented in Phase 5)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

print("📧 [Stub] Outreach pipeline will be implemented in Phase 5.")
print("   Steps that will run:")
print("   1. Fetch qualified leads from DB")
print("   2. Generate personalized email via LLM")
print("   3. Send via Gmail SMTP (or print if DRY_RUN=true)")
print("   4. Log delivery status in DB")
