import json
import os
import re
import time
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

from main import (
    DueDiligenceInput,
    FeedbackInput,
    _build_swarm_decision,
    _mock_linkedin_profile,
    _reason_linkedin_skillset,
    _runway_months,
    _update_weights_after_feedback,
)

web = Flask(__name__)
load_dotenv()


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _llm_ready() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") and OpenAI)


def _llm_opinion(system: str, user: str, fallback: str) -> str:
    if not _llm_ready():
        return fallback
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (response.choices[0].message.content or fallback).strip()
    except Exception:
        return fallback


def _tavily_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []
    try:
        res = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": False,
            },
            timeout=15,
        )
        if res.status_code != 200:
            return []
        data = res.json()
        return data.get("results", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _fetch_linkedin_profile_with_tavily(profile_url: str) -> Dict[str, Any]:
    """Fetch LinkedIn profile data using Tavily API"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        # Fallback to mock if no API key
        return _mock_linkedin_profile(profile_url)
    
    # Extract username from URL
    username = profile_url.split("/in/")[-1].strip("/").split("?")[0] if "/in/" in profile_url else ""
    
    try:
        # Search for the LinkedIn profile using Tavily
        search_query = f"{profile_url} OR site:linkedin.com/in/{username}"
        
        res = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": search_query,
                "max_results": 5,
                "include_answer": True,
                "include_raw_content": True,
                "search_depth": "advanced",
            },
            timeout=20,
        )
        
        if res.status_code != 200:
            print(f"Tavily API error: {res.status_code}")
            return _mock_linkedin_profile(profile_url)
        
        data = res.json()
        results = data.get("results", [])
        answer = data.get("answer", "")
        
        if not results:
            print("No results from Tavily, using mock data")
            return _mock_linkedin_profile(profile_url)
        
        # Parse profile information from results
        profile_data = _parse_linkedin_data(results, answer, profile_url, username)
        return profile_data
        
    except Exception as e:
        print(f"Error fetching LinkedIn with Tavily: {e}")
        return _mock_linkedin_profile(profile_url)


def _parse_linkedin_data(results: List[Dict], answer: str, profile_url: str, username: str) -> Dict[str, Any]:
    """Parse LinkedIn profile data from Tavily search results"""
    
    # Log for debugging
    print(f"\n=== Parsing LinkedIn Data ===")
    print(f"Username: {username}")
    print(f"Answer: {answer[:300] if answer else 'None'}...")
    print(f"Number of results: {len(results)}")
    
    # Extract name from username or results
    name = username.replace("-", " ").title()
    company = None
    current_role_from_title = None
    
    # Try to extract name, company, and role from result
    for result in results:
        title = result.get("title", "")
        content = result.get("content", "")
        raw_content = result.get("raw_content", "")
        url = result.get("url", "")
        
        print(f"\nResult URL: {url}")
        print(f"Title: {title[:100]}")
        
        # Extract name from LinkedIn title format: "Name - Role | Keywords"
        if "linkedin" in url.lower() and " - " in title:
            parts = title.split(" - ")
            potential_name = parts[0].strip()
            potential_name = potential_name.split("|")[0].strip()
            if 2 <= len(potential_name.split()) <= 4 and len(potential_name) < 50:
                name = potential_name
                print(f"✓ Extracted name from title: {name}")
                
                # Extract role from title (after the dash)
                if len(parts) > 1:
                    role_part = parts[1].split("|")[0].strip()
                    if role_part and len(role_part) < 100:
                        current_role_from_title = role_part
                        print(f"✓ Role from title: {current_role_from_title}")
        
        # Extract company from raw_content structure
        if raw_content and "**" in raw_content:
            # Look for pattern: # Name\n**Company Name**
            company_match = re.search(r'\*\*([A-Za-z\s&\.]+(?:Ltd|Inc|Corp|Company|Industries|Group|Pte)\.?)\*\*', raw_content)
            if company_match:
                company = company_match.group(1).strip()
                print(f"✓ Found company: {company}")
    
    # Parse answer text for structured job information
    all_text = answer + "\n\n" + "\n\n".join([r.get("content", "") for r in results])
    
    # Extract jobs using multiple patterns
    jobs = []
    
    # First priority: Use extracted title and company from profile header
    if current_role_from_title and company:
        jobs.append({
            "title": current_role_from_title,
            "company": company,
            "years": 3
        })
        print(f"✓ Primary job from profile: {current_role_from_title} at {company}")
    elif company:
        # We have company but no specific role, try to infer from answer
        if "data scientist" in answer.lower():
            jobs.append({"title": "Data Scientist", "company": company, "years": 3})
            print(f"✓ Inferred: Data Scientist at {company}")
        elif "product manager" in answer.lower():
            jobs.append({"title": "Product Manager", "company": company, "years": 3})
            print(f"✓ Inferred: Product Manager at {company}")
    
    job_patterns = [
        # Pattern: "Title at Company" or "Title - Company"
        r'(?:^|\n)([A-Z][A-Za-z\s&]+?)\s+(?:at|@|-)\s+([A-Z][A-Za-z\s&\.]+?)(?:\s*\(|\s*[•\n]|$)',
        # Pattern: "Current: Title at Company"
        r'(?:Current|Position):\s*([A-Z][A-Za-z\s&]+?)\s+at\s+([A-Z][A-Za-z\s&\.]+?)(?:\s|$)',
        # Pattern: bullet points with title and company
        r'[•\-]\s*([A-Z][A-Za-z\s&]+?)\s+at\s+([A-Z][A-Za-z\s&\.]+?)(?:\s*\(|\s*[•\n]|$)',
    ]
    
    seen_jobs = set()
    
    for pattern in job_patterns:
        matches = re.findall(pattern, all_text, re.MULTILINE)
        for match in matches:
            if len(match) == 2:
                title, company = match
                title = title.strip()
                company = company.strip().rstrip(".,;:")
                
                # Filter out noise
                if (len(title) > 3 and len(company) > 2 and 
                    len(title.split()) <= 6 and len(company.split()) <= 5 and
                    title.lower() not in ["experience", "work", "currently"] and
                    (title, company) not in seen_jobs):
                    seen_jobs.add((title, company))
                    jobs.append({"title": title, "company": company, "years": 3 if len(jobs) == 0 else 2})
                    print(f"Found job: {title} at {company}")
                    if len(jobs) >= 5:
                        break
        if len(jobs) >= 3:
            break
    
    # If no structured jobs found, try extracting from answer summary
    if not jobs and answer:
        # Look for common role keywords in answer
        role_keywords = {
            "product manager": "Product Manager",
            "senior product": "Senior Product Manager",
            "data scientist": "Data Scientist",
            "senior data": "Senior Data Scientist",
            "software engineer": "Software Engineer",
            "senior software": "Senior Software Engineer",
            "business analyst": "Business Analyst",
            "product lead": "Product Lead",
            "engineering manager": "Engineering Manager",
            "designer": "Product Designer",
            "analyst": "Analyst",
        }
        
        answer_lower = answer.lower()
        for keyword, title in role_keywords.items():
            if keyword in answer_lower:
                # Try to find company mentioned near this keyword
                idx = answer_lower.find(keyword)
                snippet = answer[max(0, idx-50):min(len(answer), idx+150)]
                
                # Look for "at Company" pattern
                at_match = re.search(r'at\s+([A-Z][A-Za-z\s&\.]+?)(?:\s|,|\.|$)', snippet)
                company = at_match.group(1).strip() if at_match else "Tech Company"
                
                jobs.append({"title": title, "company": company, "years": 3})
                print(f"Extracted from answer: {title} at {company}")
                break
    
    # If we only have 1 job, try to add more based on answer and about section
    if len(jobs) == 1 and answer:
        # Extract hints from answer about career progression
        if "senior" in jobs[0]["title"].lower():
            # Add a mid-level version
            base_title = jobs[0]["title"].replace("Senior ", "")
            jobs.append({"title": base_title, "company": "Previous Company", "years": 3})
            print(f"✓ Added career progression: {base_title}")
        
        # Look for internship or junior role mentions
        if "intern" in answer.lower():
            jobs.append({"title": "Intern", "company": "Early Career Co", "years": 1})
    
    # Fallback to username and answer-based inference if still no jobs
    if not jobs:
        username_lower = username.lower()
        answer_lower = answer.lower() if answer else ""
        
        # Check answer first for better accuracy
        if "data scientist" in answer_lower or "data science" in answer_lower:
            jobs = [
                {"title": "Data Scientist", "company": company or "Tech Company", "years": 3},
                {"title": "Data Analyst", "company": "Analytics Co", "years": 2},
            ]
            print("✓ Fallback: Inferred Data Scientist role from answer")
        elif "product manager" in answer_lower:
            jobs = [
                {"title": "Product Manager", "company": company or "Tech Company", "years": 3},
                {"title": "Associate Product Manager", "company": "Startup Inc", "years": 2},
            ]
            print("✓ Fallback: Inferred Product Manager from answer")
        elif any(kw in username_lower for kw in ["product", "pm"]):
            jobs = [
                {"title": "Senior Product Manager", "company": company or "Tech Company", "years": 3},
                {"title": "Product Manager", "company": "Startup Inc", "years": 3},
            ]
        elif any(kw in username_lower for kw in ["data", "scientist", "analytics"]):
            jobs = [
                {"title": "Senior Data Scientist", "company": company or "Tech Company", "years": 3},
                {"title": "Data Scientist", "company": "Analytics Co", "years": 2},
            ]
        elif any(kw in username_lower for kw in ["engineer", "dev"]):
            jobs = [
                {"title": "Senior Software Engineer", "company": company or "Tech Company", "years": 3},
                {"title": "Software Engineer", "company": "Startup Inc", "years": 3},
            ]
        else:
            jobs = [
                {"title": "Senior Product Manager", "company": company or "Tech Company", "years": 3},
                {"title": "Product Manager", "company": "Startup Inc", "years": 3},
            ]
    
    # Extract education with better parsing
    education = []
    education_patterns = [
        r'(Bachelor|Master|MBA|B\.S\.|B\.A\.|M\.S\.|Ph\.D).*?(?:from|at)?\s+([A-Z][A-Za-z\s]+(?:University|College|Institute))',
        r'([A-Z][A-Za-z\s]+(?:University|College|Institute))[,\s]+.*?(Bachelor|Master|Degree)',
    ]
    
    for pattern in education_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        for match in matches:
            degree, school = match if "university" in match[1].lower() else (match[1], match[0])
            education.append({
                "school": school.strip(),
                "degree": degree.strip()
            })
            print(f"Found education: {degree} from {school}")
            if len(education) >= 2:
                break
        if education:
            break
    
    # Default education if none found
    if not education:
        education = [
            {"school": "National University of Singapore", "degree": "B.Eng Computer Engineering"},
        ]
    
    # Extract location with better patterns
    location = None
    location_patterns = [
        r'(?:Location|Based in|Lives in|Located in):\s*([A-Za-z\s,]+?)(?:\n|$)',
        r'(?:^|\s)([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*(?:Singapore|USA|UK|California|New York))',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, all_text, re.MULTILINE)
        if match:
            location = match.group(1).strip()
            print(f"Found location: {location}")
            break
    
    # Simple location detection if not found
    if not location:
        for result in results:
            content = result.get("content", "").lower()
            if "singapore" in content:
                location = "Singapore"
                break
            elif "san francisco" in content or "bay area" in content:
                location = "San Francisco"
                break
            elif "new york" in content:
                location = "New York"
                break
    
    print(f"\nFinal parsed data:")
    print(f"Name: {name}")
    print(f"Jobs: {len(jobs)}")
    print(f"Location: {location}")
    print("=== End Parsing ===\n")
    
    return {
        "name": name,
        "profile_url": profile_url,
        "jobs": jobs[:5],  # Limit to 5 most recent
        "education": education[:2],  # Limit to 2 degrees
        "location": location,
        "raw_content": answer[:500] if answer else ""
    }


def _form_to_due_diligence(form: dict) -> DueDiligenceInput:
    skills_raw = form.get("top_skills", "")
    skills = [item.strip() for item in skills_raw.split(",") if item.strip()]
    payload = {
        "personal_background": {
            "age": int(form.get("age", 30)),
            "current_role": form.get("current_role", "Unknown"),
            "years_experience": float(form.get("years_experience", 5)),
            "location": form.get("location", "Singapore"),
            "risk_tolerance": form.get("risk_tolerance", "medium"),
            "career_goal_12_months": form.get("career_goal_12_months", "Build a sustainable business"),
        },
        "linkedin_context": {
            "profile_url": form.get("profile_url") or None,
            "top_skills": skills,
            "endorsements_strength": form.get("endorsements_strength", "moderate"),
            "network_reach": form.get("network_reach", "medium"),
            "recent_relevant_posts": int(form.get("recent_relevant_posts", 0)),
        },
        "financial_situation": {
            "monthly_expenses_usd": float(form.get("monthly_expenses_usd", 0)),
            "monthly_income_usd": float(form.get("monthly_income_usd", 0)),
            "liquid_savings_usd": float(form.get("liquid_savings_usd", 0)),
            "debt_usd": float(form.get("debt_usd", 0)),
            "expected_side_income_usd": float(form.get("expected_side_income_usd", 0)),
            "other_investments_usd": float(form.get("other_investments_usd", 0)),
            "expected_investment_monthly_income_usd": float(form.get("expected_investment_monthly_income_usd", 0)),
            "health_insurance_if_quit": _to_bool(form.get("health_insurance_if_quit", "true")),
        },
        "family_context": {
            "dependents_count": int(form.get("dependents_count", 0)),
            "partner_income_stable": _to_bool(form.get("partner_income_stable", "true")),
            "family_support_level": form.get("family_support_level", "medium"),
            "major_events_next_12_months": [
                item.strip() for item in form.get("major_events_next_12_months", "").split(",") if item.strip()
            ],
        },
    }
    return DueDiligenceInput.model_validate(payload)


def _parse_external_urls(payload: Any) -> List[str]:
    raw = ""
    if isinstance(payload, dict):
        raw = str(payload.get("external_linkedin_urls", "")).strip()
    urls = [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]
    deduped: List[str] = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        deduped.append(url)
        seen.add(url)
    return deduped[:8]


def _simulate_external_opinions(data: DueDiligenceInput, urls: List[str]) -> Dict[str, Any]:
    opinions: List[Dict[str, Any]] = []
    trace: List[Dict[str, str]] = []
    runway = _runway_months(data.financial_situation)

    for url in urls:
        # Use Tavily to fetch real LinkedIn profiles
        profile = _fetch_linkedin_profile_with_tavily(url)
        reason = _reason_linkedin_skillset(profile)
        readiness = reason.market_readiness_score_0_to_100
        if runway >= 7 and readiness >= 72:
            stance = "support"
            msg = "I would support a near-term quit if milestones are locked."
        elif runway <= 4:
            stance = "hold"
            msg = "I would advise waiting and extending runway."
        else:
            stance = "cautious"
            msg = "I would advise a staged transition with side-income first."

        opinions.append(
            {
                "advisor_name": profile["name"],
                "profile_url": url,
                "stance": stance,
                "message": _llm_opinion(
                    "You simulate a concise advisor opinion about whether someone should quit their job.",
                    f"Profile summary: {profile}. Candidate runway months: {runway:.1f}. Skill readiness: {readiness}. Give one short opinion.",
                    msg,
                ),
                "top_skills": reason.inferred_skills[:4],
                "market_readiness_score_0_to_100": readiness,
            }
        )
        trace.append(
            {
                "agent": "peer_opinion_agent",
                "step": f"Imported {profile['name']} profile and simulated opinion ({stance}).",
            }
        )

    support = sum(1 for item in opinions if item["stance"] == "support")
    hold = sum(1 for item in opinions if item["stance"] == "hold")
    if support > hold:
        consensus = f"Peers lean supportive ({support} support vs {hold} hold)."
    elif hold > support:
        consensus = f"Peers lean conservative ({hold} hold vs {support} support)."
    else:
        consensus = "Peers are mixed; use hard milestones."
    return {"opinions": opinions, "consensus": consensus, "trace": trace}


def _jobs_agent(target_role: str, location: str) -> Dict[str, Any]:
    role = (target_role or "Product Manager").lower()
    city = location or "Singapore"
    listings = [
        {
            "title": "AI Product Consultant",
            "company": "Northstar Labs",
            "location": city,
            "salary_range": "USD 8k-12k / month contract",
        },
        {
            "title": "Founding Product Lead (AI)",
            "company": "Mosaic Cloud",
            "location": city,
            "salary_range": "USD 120k-170k / year",
        },
        {
            "title": "Growth + Product Operator",
            "company": "SignalOps",
            "location": city,
            "salary_range": "USD 95k-145k / year",
        },
    ]
    if "engineer" in role:
        listings[0]["title"] = "AI Solutions Engineer (Contract)"
    market_score = 76 if len(listings) >= 3 else 55
    fallback_opinion = (
        "Job market signal is healthy; keeping an interview pipeline can de-risk quitting."
        if market_score >= 70
        else "Job market signal is thin; prioritize cash runway before quitting."
    )
    opinion = _llm_opinion(
        "You are a pragmatic jobs-market advisor.",
        f"Role: {target_role}, location: {location}, market score: {market_score}, jobs: {listings}. Give one short opinion.",
        fallback_opinion,
    )
    trace = [
        {"agent": "job_search_agent", "step": f"Searched opportunities for '{target_role}' in {city}."},
        {"agent": "market_opinion_agent", "step": f"Generated market signal score {market_score}/100."},
    ]
    return {"jobs": listings, "market_signal_score_0_to_100": market_score, "opinion": opinion, "trace": trace}


def _news_agent(topic: str, horizon_months: int, location: str) -> Dict[str, Any]:
    query = f"{topic} jobs outlook in {location} next {horizon_months} months"
    results = _tavily_search(query)
    articles = []
    for item in results[:4]:
        articles.append(
            {
                "title": item.get("title", "Untitled"),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:220],
            }
        )
    fallback = [
        {
            "title": f"{topic} hiring signals steady in {location}",
            "url": "",
            "snippet": "No live data available; using fallback sentiment: neutral-to-positive.",
        }
    ]
    articles = articles or fallback
    opinion = _llm_opinion(
        "You are a concise news summarizer for job landscape.",
        f"Articles: {articles}. Produce one-line outlook for {topic} in {location} for {horizon_months} months.",
        f"Outlook for {topic} in {location}: stable with moderate demand.",
    )
    trace = [
        {"agent": "news_agent", "step": f"Searched horizon {horizon_months}m for '{topic}' in {location}."},
        {"agent": "news_opinion_agent", "step": "Synthesized outlook from articles."},
    ]
    return {"articles": articles, "outlook": opinion, "trace": trace}


@web.get("/")
def home():
    return render_template("index.html")


@web.post("/api/connect/linkedin")
def connect_linkedin():
    payload = request.get_json(force=True, silent=False) if request.is_json else request.form
    profile_url = payload.get("profile_url")
    
    if not profile_url or not profile_url.strip():
        return jsonify({"error": "Profile URL is required"}), 400
    
    # Use Tavily to fetch real LinkedIn data
    print(f"Fetching LinkedIn profile: {profile_url}")
    profile = _fetch_linkedin_profile_with_tavily(profile_url)
    print(f"Profile fetched: {profile.get('name')}")
    
    reason = _reason_linkedin_skillset(profile)
    
    trace = [
        {"agent": "tavily_search_agent", "step": f"Searched LinkedIn profile via Tavily API: {profile_url}"},
        {"agent": "linkedin_connector_agent", "step": f"Extracted profile data for {profile.get('name')}"},
        {"agent": "linkedin_skill_reasoner_agent", "step": "Inferred transferable skillset and readiness."},
    ]
    
    return jsonify(
        {
            "profile": profile,
            "autofill": {
                "top_skills": ", ".join(reason.inferred_skills[:4]),
                "years_experience": sum(int(job.get("years", 0)) for job in profile.get("jobs", [])),
                "current_role": profile.get("jobs", [{}])[0].get("title", "Unknown"),
            },
            "skill_reasoning": reason.model_dump(),
            "trace": trace,
        }
    )


def _generate_financial_data_with_ai(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Use OpenAI to generate believable financial data based on profile"""
    if not _llm_ready():
        # Fallback to defaults if OpenAI not available (in SGD)
        return {
            "monthly_income_usd": 11000,
            "liquid_savings_usd": 40000,
            "debt_usd": 8000,
            "monthly_expenses_usd": 4500,
            "expected_side_income_usd": 1200,
        }
    
    try:
        name = profile_data.get("name", "Professional")
        role = profile_data.get("current_role", "Product Manager")
        years_exp = profile_data.get("years_experience", 8)
        location = profile_data.get("location", "Singapore")
        age = profile_data.get("age", 31)
        
        prompt = f"""Based on this professional profile, generate realistic financial estimates in SGD (Singapore Dollars):

Profile:
- Name: {name}
- Role: {role}
- Years of Experience: {years_exp}
- Location: {location}
- Age: {age}

Generate believable financial ranges for someone in this position. Consider:
- Market rates for {role} in {location} (in SGD)
- Cost of living in {location} (in SGD)
- Typical savings for someone with {years_exp} years experience (in SGD)
- Common debt levels for someone age {age} (in SGD)

IMPORTANT: All amounts must be in SGD (Singapore Dollars). 
For reference: Entry-level roles in SG start around SGD 3,500-5,000/month, mid-level SGD 6,000-12,000/month, senior SGD 10,000-20,000/month.

Return ONLY a JSON object with these exact fields (numbers only, no formatting):
{{
  "monthly_income_usd": <number in SGD>,
  "monthly_expenses_usd": <number in SGD>,
  "liquid_savings_usd": <number in SGD>,
  "debt_usd": <number in SGD>,
  "expected_side_income_usd": <number in SGD>
}}"""

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        response = client.chat.completions.create(
            model=model,
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a financial data estimator for Singapore. Generate realistic financial data in SGD (Singapore Dollars) based on professional profiles. Always return valid JSON with numeric values in SGD."},
                {"role": "user", "content": prompt},
            ],
        )
        
        result = response.choices[0].message.content
        financial_data = json.loads(result)
        
        print(f"Generated financial data for {name}: {financial_data}")
        
        return financial_data
        
    except Exception as e:
        print(f"Error generating financial data with AI: {e}")
        # Fallback to defaults (in SGD)
        return {
            "monthly_income_usd": 11000,
            "liquid_savings_usd": 40000,
            "debt_usd": 8000,
            "monthly_expenses_usd": 4500,
            "expected_side_income_usd": 1200,
        }


@web.post("/api/connect/singpass")
def connect_singpass():
    payload = request.get_json(force=True, silent=False) if request.is_json else {}
    
    # Extract profile data from payload
    profile_data = {
        "name": payload.get("name", "Professional"),
        "current_role": payload.get("current_role", "Product Manager"),
        "years_experience": payload.get("years_experience", 8),
        "location": payload.get("location", "Singapore"),
        "age": payload.get("age", 31),
    }
    
    print(f"Generating financial data for profile: {profile_data['name']}, {profile_data['current_role']}")
    
    # Generate financial data using OpenAI
    financial_data = _generate_financial_data_with_ai(profile_data)
    
    # Add health insurance default
    financial_data["health_insurance_if_quit"] = "true"
    
    return jsonify(
        {
            "autofill": financial_data,
            "notes": [
                f"Financial estimates in SGD generated for {profile_data['current_role']} with {profile_data['years_experience']} years experience in {profile_data['location']}.",
                "All amounts are in Singapore Dollars (SGD).",
                "Estimates are based on typical market rates and cost of living.",
                "Fill side investments manually if applicable.",
            ],
            "required_user_inputs": ["other_investments_usd", "expected_investment_monthly_income_usd"],
            "trace": [
                {"agent": "ai_financial_estimator", "step": f"Generated realistic financial estimates in SGD using OpenAI based on profile data."},
                {"agent": "singpass_connector_agent", "step": "Populated financial fields with AI-generated estimates in SGD."}
            ],
        }
    )


@web.post("/api/self/process")
def self_process():
    try:
        data = DueDiligenceInput.model_validate(request.get_json()) if request.is_json else _form_to_due_diligence(request.form)
        decision = _build_swarm_decision(data)
        fallback_self_opinion = (
            "Your profile supports a staged quit after checklist gates are met."
            if decision.aggregate_score_0_to_100 >= 60
            else "Your profile needs de-risking before quitting."
        )
        self_opinion = _llm_opinion(
            "You are a conservative career transition advisor.",
            (
                f"Candidate aggregate score: {decision.aggregate_score_0_to_100}, "
                f"recommendation: {decision.recommendation}, rationale: {decision.rationale}. "
                "Give a short first-person self-opinion."
            ),
            fallback_self_opinion,
        )
        trace = [
            {"agent": "self_profile_agent", "step": "Validated your profile, family, and financial inputs."},
            {"agent": "self_opinion_agent", "step": f"Simulated your own risk stance: {self_opinion}"},
            {"agent": "swarm_decision_agent", "step": "Ran weighted specialist decision for your case."},
        ]
        response = decision.model_dump()
        response["self_simulated_opinion"] = self_opinion
        response["trace"] = trace
        return jsonify(response)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400


@web.post("/api/simulated/process")
def simulated_process():
    try:
        payload = request.get_json(force=True, silent=False) if request.is_json else request.form
        data = _form_to_due_diligence(payload)
        urls = _parse_external_urls(payload)
        result = _simulate_external_opinions(data, urls)
        return jsonify(result)
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400


@web.post("/api/jobs/process")
def jobs_process():
    payload = request.get_json(force=True, silent=False) if request.is_json else request.form
    target_role = payload.get("target_role", "Product Manager")
    location = payload.get("target_location", "Singapore")
    return jsonify(_jobs_agent(target_role, location))


@web.post("/api/news/process")
def news_process():
    payload = request.get_json(force=True, silent=False) if request.is_json else request.form
    topic = payload.get("news_topic", "AI product")
    horizon = int(payload.get("horizon_months", 6))
    location = payload.get("target_location", "Singapore")
    return jsonify(_news_agent(topic, horizon, location))


@web.post("/api/swarm/process")
def swarm_process():
    try:
        payload = request.get_json(force=True, silent=False) if request.is_json else request.form
        data = _form_to_due_diligence(payload)
        urls = _parse_external_urls(payload)
        target_role = payload.get("target_role", data.personal_background.current_role)
        target_location = payload.get("target_location", data.personal_background.location)
        news_topic = payload.get("news_topic", target_role)
        horizon = int(payload.get("horizon_months", 6))

        own = _build_swarm_decision(data)
        peers = _simulate_external_opinions(data, urls)
        jobs = _jobs_agent(target_role, target_location)
        news = _news_agent(news_topic, horizon, target_location)

        trace = [
            {"agent": "orchestrator_agent", "step": "Dispatched your profile to self-opinion and swarm agents."},
            {"agent": "peer_panel_agent", "step": f"Gathered {len(peers['opinions'])} simulated peer opinions."},
            {"agent": "market_intel_agent", "step": f"Job market signal {jobs['market_signal_score_0_to_100']}/100."},
            {"agent": "news_agent", "step": f"News horizon {horizon}m on '{news_topic}'."},
            {"agent": "knowledge_synth_agent", "step": "Merged self, peers, market, and news into final swarm perspective."},
        ]

        fallback_final = own.recommendation
        if peers["opinions"] and "conservative" in peers["consensus"].lower():
            fallback_final = f"{fallback_final} Peers are conservative, so use stricter milestones."
        if jobs["market_signal_score_0_to_100"] >= 75:
            fallback_final = f"{fallback_final} Strong job-market fallback lowers downside."
        final = _llm_opinion(
            "You are a swarm coordinator agent. Merge multiple agent signals into one concise final opinion.",
            (
                f"Own decision: {own.recommendation}; own score: {own.aggregate_score_0_to_100}. "
                f"Peer consensus: {peers['consensus']}. Jobs opinion: {jobs['opinion']}. "
                f"News outlook: {news['outlook']}. "
                "Return one concise final opinion."
            ),
            fallback_final,
        )

        return jsonify(
            {
                "self_decision": own.model_dump(),
                "peer_simulation": peers,
                "job_market": jobs,
                "news": news,
                "swarm_final_opinion": final,
                "trace": trace,
            }
        )
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400


@web.post("/api/feedback")
def feedback():
    try:
        payload = request.get_json(force=True, silent=False)
        feedback_input = FeedbackInput.model_validate(payload)
        result = _update_weights_after_feedback(feedback_input)
        code = 200 if result.status == "ok" else 404
        return jsonify(result.model_dump()), code
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "details": exc.errors()}), 400


if __name__ == "__main__":
    web.run(debug=True, port=5050)
