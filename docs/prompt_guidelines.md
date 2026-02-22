# Prompt Guidelines

All prompts live in `app/ai_engine/prompt_templates.py` as LangChain `ChatPromptTemplate` objects.

---

## 1. Keyword Generation Prompt

**Purpose:** Given a product description, generate job role keywords that indicate a potential customer company.

**Template variables:** `{product_description}`

**Expected output:** JSON array of role strings
```json
["cto", "vp engineering", "head of engineering", "engineering manager", "director of engineering"]
```

**Tuning tips:**
- Keep `product_description` concise (1–3 sentences).
- If keywords are too broad, add context like industry or company size.
- Keywords are matched case-insensitively against job titles.

---

## 2. Lead Qualification Prompt

**Purpose:** Determine if a job posting signals that the company is a good fit for the product.

**Template variables:**
- `{product_description}` — What the product does
- `{job_title}` — Title of the job posting
- `{job_description}` — Plain-text description (truncated to ~2000 chars)

**Expected output:** JSON object
```json
{
  "is_qualified": true,
  "relevance_score": 78,
  "reason": "The company is scaling its engineering team rapidly...",
  "target_contact_role": "VP of Engineering",
  "company_pain_points": ["slow code reviews", "engineering hiring velocity"]
}
```

**Tuning tips:**
- Adjust `MIN_RELEVANCE_SCORE` in `.env` (default: 60) to raise/lower the bar.
- To target different buyer personas, update the product description.
- The `reason` field is passed directly into the email draft — make the prompt produce specific, actionable reasons.

---

## 3. Email Draft Prompt

**Purpose:** Write a personalized cold outreach email given company context.

**Template variables:**
- `{product_description}`
- `{company_name}`
- `{job_title}`
- `{contact_role}` — Who to address (e.g. VP of Engineering)
- `{company_pain_points}` — JSON list from qualification step
- `{reason}` — Why this company was qualified

**Expected output:** JSON object
```json
{
  "subject": "Quick question about your engineering hiring at Acme",
  "body": "Hi [Name],\n\nI noticed you're hiring an Engineering Manager..."
}
```

**Tuning tips:**
- Keep emails under 150 words — brevity gets replies.
- Do not add placeholders like `[First Name]` unless you have contact info.
- The `body` should end with a single soft CTA (e.g. "Worth a quick chat?").
- To change tone (formal ↔ casual), update the `TONE` constant in the prompt template.

---

## Robustness

All three prompts are wrapped in `parse_json_safely()` which:
1. Strips markdown code fences (` ```json ... ``` `)
2. Extracts the first `{...}` or `[...]` block via regex
3. Falls back to a safe default if parsing fails

`qualify_lead` and `draft_email` chains return safe fallback values on failure — they never crash the pipeline.
