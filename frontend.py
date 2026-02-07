import time
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError

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


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


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
        profile = _mock_linkedin_profile(url)
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
                "message": msg,
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
    opinion = (
        "Job market signal is healthy; keeping an interview pipeline can de-risk quitting."
        if market_score >= 70
        else "Job market signal is thin; prioritize cash runway before quitting."
    )
    trace = [
        {"agent": "job_search_agent", "step": f"Searched opportunities for '{target_role}' in {city}."},
        {"agent": "market_opinion_agent", "step": f"Generated market signal score {market_score}/100."},
    ]
    return {"jobs": listings, "market_signal_score_0_to_100": market_score, "opinion": opinion, "trace": trace}


@web.get("/")
def home():
    return render_template("index.html")


@web.post("/api/connect/linkedin")
def connect_linkedin():
    payload = request.get_json(force=True, silent=False) if request.is_json else request.form
    profile_url = payload.get("profile_url")
    time.sleep(1.3)
    profile = _mock_linkedin_profile(profile_url)
    reason = _reason_linkedin_skillset(profile)
    return jsonify(
        {
            "profile": profile,
            "autofill": {
                "top_skills": ", ".join(reason.inferred_skills[:4]),
                "years_experience": sum(int(job.get("years", 0)) for job in profile.get("jobs", [])),
                "current_role": profile.get("jobs", [{}])[0].get("title", "Unknown"),
            },
            "skill_reasoning": reason.model_dump(),
            "trace": [
                {"agent": "linkedin_connector_agent", "step": "Pulled profile jobs and education."},
                {"agent": "linkedin_skill_reasoner_agent", "step": "Inferred transferable skillset and readiness."},
            ],
        }
    )


@web.post("/api/connect/singpass")
def connect_singpass():
    time.sleep(1.2)
    return jsonify(
        {
            "autofill": {
                "monthly_income_usd": 8900,
                "liquid_savings_usd": 28000,
                "debt_usd": 4800,
                "monthly_expenses_usd": 3600,
                "health_insurance_if_quit": "true",
            },
            "notes": [
                "Income, savings, and debt imported from Singpass/Myinfo demo payload.",
                "Fill side investments manually.",
            ],
            "required_user_inputs": ["other_investments_usd", "expected_investment_monthly_income_usd"],
            "trace": [{"agent": "singpass_connector_agent", "step": "Pulled personal finance snapshot."}],
        }
    )


@web.post("/api/self/process")
def self_process():
    try:
        data = DueDiligenceInput.model_validate(request.get_json()) if request.is_json else _form_to_due_diligence(request.form)
        decision = _build_swarm_decision(data)
        self_opinion = (
            "Your profile supports a staged quit after checklist gates are met."
            if decision.aggregate_score_0_to_100 >= 60
            else "Your profile needs de-risking before quitting."
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


@web.post("/api/swarm/process")
def swarm_process():
    try:
        payload = request.get_json(force=True, silent=False) if request.is_json else request.form
        data = _form_to_due_diligence(payload)
        urls = _parse_external_urls(payload)
        target_role = payload.get("target_role", data.personal_background.current_role)
        target_location = payload.get("target_location", data.personal_background.location)

        own = _build_swarm_decision(data)
        peers = _simulate_external_opinions(data, urls)
        jobs = _jobs_agent(target_role, target_location)

        trace = [
            {"agent": "orchestrator_agent", "step": "Dispatched your profile to self-opinion and swarm agents."},
            {"agent": "peer_panel_agent", "step": f"Gathered {len(peers['opinions'])} simulated peer opinions."},
            {"agent": "market_intel_agent", "step": f"Generated job market signal {jobs['market_signal_score_0_to_100']}/100."},
            {"agent": "knowledge_synth_agent", "step": "Merged self, peers, and market into final swarm perspective."},
        ]

        final = own.recommendation
        if peers["opinions"] and "conservative" in peers["consensus"].lower():
            final = f"{final} Peers are conservative, so use stricter milestones."
        if jobs["market_signal_score_0_to_100"] >= 75:
            final = f"{final} Strong job-market fallback lowers downside."

        return jsonify(
            {
                "self_decision": own.model_dump(),
                "peer_simulation": peers,
                "job_market": jobs,
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
