"""
app/ai_engine/prompt_templates.py — All LangChain prompt templates for the AI engine.

Three prompt chains:
  1. KEYWORD_GENERATION  — product description → list of buyer-signal role keywords
  2. LEAD_QUALIFICATION  — job posting + product → structured qualification JSON
  3. EMAIL_DRAFT         — lead context → personalized cold outreach email
"""

from langchain_core.prompts import ChatPromptTemplate


# ── 1. Keyword Generation ─────────────────────────────────────────────────────

KEYWORD_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are an expert B2B sales strategist. Your job is to identify "
            "which job roles at a company would most likely be the decision-maker "
            "or buyer for a given product."
        ),
    ),
    (
        "human",
        """Given the product description below, generate a list of job role keywords.
These keywords will be used to search and filter job postings to find companies who are potential customers.

PRODUCT DESCRIPTION:
{product_description}

INSTRUCTIONS:
- List 15–25 specific job role keywords or phrases (lowercase)
- Focus on roles that would FEEL the pain your product solves or have BUDGET authority
- Include both seniority levels (e.g. "head of engineering", "engineering manager")
- Be specific — avoid generic terms like "manager" or "developer" alone
- Return ONLY a valid JSON array of strings, nothing else

Example output format:
["cto", "vp engineering", "head of engineering", "engineering manager", "director of engineering"]
""",
    ),
])


# ── 2. Lead Qualification ─────────────────────────────────────────────────────

LEAD_QUALIFICATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are an expert B2B lead qualification analyst. "
            "You analyze job postings and company context to identify potential customers "
            "for a given product. Be analytical, concise, and realistic in your scoring."
        ),
    ),
    (
        "human",
        """Analyze whether this company is a potential customer for our product.

PRODUCT DESCRIPTION:
{product_description}

JOB POSTING:
Company: {company_name}
Job Title: {job_title}
Location: {location}
Description:
{job_description}

INSTRUCTIONS:
Determine if this company is likely to need and buy our product based on the job posting context.
Consider: company size signals, tech stack, team structure, growth stage, and the job role's pain points.

Return ONLY a valid JSON object with exactly these fields:
{{
  "is_qualified": true or false,
  "relevance_score": <integer 0-100>,
  "reason": "<1-2 sentence explanation of why they are or aren't a good lead>",
  "target_contact_role": "<ideal job title to reach out to at this company>",
  "company_pain_points": ["<pain point 1>", "<pain point 2>", "<pain point 3>"]
}}

Scoring guide:
- 80-100: Strong signal — company clearly needs this product
- 60-79:  Good lead — reasonable fit with potential
- 40-59:  Weak lead — marginal fit, include if score threshold allows
- 0-39:   Not qualified — poor fit, set is_qualified to false
""",
    ),
])


# ── 3. Email Draft ────────────────────────────────────────────────────────────

EMAIL_DRAFT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are an expert cold outreach copywriter specializing in B2B SaaS. "
            "You write short, personalized, and compelling cold emails that get replies. "
            "Never use hollow phrases like 'I hope this email finds you well' or 'synergy'. "
            "Write like a real person, not a marketing bot."
        ),
    ),
    (
        "human",
        """Write a personalized cold outreach email for the following lead.

OUR PRODUCT:
{product_description}

LEAD CONTEXT:
Company: {company_name}
Job Title Seen: {job_title}
Target Contact Role: {contact_role}
Why They're A Good Fit: {reason}
Company Pain Points: {pain_points}

REQUIREMENTS:
- Subject line: short, specific, no clickbait (max 8 words)
- Email body: 4-6 sentences max, conversational tone
- Mention ONE specific pain point relevant to them
- End with a soft, low-pressure CTA (e.g., "Worth a quick call?")
- Do NOT use the recipient's name (we don't have it)
- Do NOT use placeholder text like [Name] or [Company]

Return ONLY a valid JSON object with exactly these two fields:
{{
  "subject": "<email subject line>",
  "body": "<email body as plain text, use \\n for line breaks>"
}}
""",
    ),
])
