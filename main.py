import json
import os
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentfield import AIConfig, Agent
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).parent
SWARM_MEMORY_PATH = BASE_DIR / "swarm_memory.json"


class PersonalBackground(BaseModel):
    age: int = Field(..., ge=18, le=90)
    current_role: str
    years_experience: float = Field(..., ge=0)
    location: str
    risk_tolerance: str = Field(..., description="low, medium, or high")
    career_goal_12_months: str


class LinkedInContext(BaseModel):
    profile_url: Optional[str] = None
    top_skills: List[str] = Field(default_factory=list)
    endorsements_strength: str = Field(..., description="weak, moderate, or strong")
    network_reach: str = Field(..., description="small, medium, or large")
    recent_relevant_posts: int = Field(..., ge=0)


class FinancialSituation(BaseModel):
    monthly_expenses_usd: float = Field(..., ge=0)
    monthly_income_usd: float = Field(..., ge=0)
    liquid_savings_usd: float = Field(..., ge=0)
    debt_usd: float = Field(..., ge=0)
    expected_side_income_usd: float = Field(..., ge=0)
    other_investments_usd: float = Field(default=0, ge=0)
    expected_investment_monthly_income_usd: float = Field(default=0, ge=0)
    health_insurance_if_quit: bool


class FamilyContext(BaseModel):
    dependents_count: int = Field(..., ge=0)
    partner_income_stable: bool
    family_support_level: str = Field(..., description="low, medium, or high")
    major_events_next_12_months: List[str] = Field(default_factory=list)


class DueDiligenceInput(BaseModel):
    personal_background: PersonalBackground
    linkedin_context: LinkedInContext
    financial_situation: FinancialSituation
    family_context: FamilyContext


class RiskSummary(BaseModel):
    runway_months: float
    readiness_score_0_to_100: int
    recommendation: str


class ActionPlan(BaseModel):
    next_30_days: List[str]
    before_quitting: List[str]
    first_90_days_after_quit: List[str]


class DueDiligenceRecommendation(BaseModel):
    risk_summary: RiskSummary
    recommended_quit_window: str
    rationale: List[str]
    action_plan: ActionPlan
    red_flags: List[str]


class SingpassImportInput(BaseModel):
    singpass_profile: Dict[str, Any]
    linkedin_context: Optional[LinkedInContext] = None
    financial_overrides: Optional[FinancialSituation] = None
    family_overrides: Optional[FamilyContext] = None
    personal_overrides: Optional[PersonalBackground] = None


class SingpassImportOutput(BaseModel):
    due_diligence_input: DueDiligenceInput
    missing_information: List[str]
    notes: List[str]


class SpecialistAssessment(BaseModel):
    agent: str
    score_0_to_100: int
    confidence_0_to_1: float
    verdict: str
    reasons: List[str]


class SimilarCase(BaseModel):
    case_id: str
    similarity_0_to_1: float
    recommendation: str
    was_successful: Optional[bool] = None


class SwarmDecision(BaseModel):
    case_id: str
    aggregate_score_0_to_100: int
    aggregate_confidence_0_to_1: float
    recommendation: str
    recommended_quit_window: str
    rationale: List[str]
    specialists: List[SpecialistAssessment]
    action_plan: ActionPlan
    red_flags: List[str]
    used_agent_weights: Dict[str, float]
    similar_cases: List[SimilarCase]


class FeedbackInput(BaseModel):
    case_id: str
    did_user_quit: bool
    was_successful: bool
    months_after_quit: Optional[int] = Field(default=None, ge=0)
    stress_score_1_to_10: Optional[int] = Field(default=None, ge=1, le=10)
    income_delta_usd: Optional[float] = None
    notes: Optional[str] = None


class FeedbackResult(BaseModel):
    case_id: str
    status: str
    updated_agent_weights: Dict[str, float]
    message: str


class LinkedInSkillReasoning(BaseModel):
    inferred_skills: List[str]
    confidence_0_to_1: float
    market_readiness_score_0_to_100: int
    narrative: str
    recommended_focus_areas: List[str]


def _default_memory() -> Dict[str, Any]:
    return {
        "agent_weights": {
            "finance_risk_agent": 1.0,
            "career_market_agent": 1.0,
            "family_stability_agent": 1.0,
            "linkedin_positioning_agent": 1.0,
        },
        "agent_scorecard": {},
        "cases": [],
    }


def _load_swarm_memory() -> Dict[str, Any]:
    if not SWARM_MEMORY_PATH.exists():
        return _default_memory()
    try:
        with SWARM_MEMORY_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        default = _default_memory()
        default.update(data)
        return default
    except (json.JSONDecodeError, OSError):
        return _default_memory()


def _save_swarm_memory(memory: Dict[str, Any]) -> None:
    with SWARM_MEMORY_PATH.open("w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2)


def _extract_value(obj: Any) -> Any:
    if isinstance(obj, dict) and "value" in obj:
        return obj["value"]
    return obj


def _get_any(profile: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in profile:
            value = _extract_value(profile[key])
            if value not in (None, "", []):
                return value
    return None


def _calc_age_from_dob(dob: Optional[str]) -> Optional[int]:
    if not dob:
        return None
    try:
        born = datetime.strptime(dob[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _build_location(profile: Dict[str, Any]) -> Optional[str]:
    regadd = profile.get("regadd")
    if not isinstance(regadd, dict):
        return _get_any(profile, ["address", "residential_address"])
    parts = [
        _extract_value(regadd.get("block")),
        _extract_value(regadd.get("street")),
        _extract_value(regadd.get("building")),
        _extract_value(regadd.get("postal")),
    ]
    cleaned = [str(p).strip() for p in parts if p not in (None, "")]
    return ", ".join(cleaned) if cleaned else None


def _from_singpass(payload: SingpassImportInput) -> SingpassImportOutput:
    profile = payload.singpass_profile
    missing: List[str] = []
    notes: List[str] = []

    full_name = _get_any(profile, ["name", "fullname", "uinfin"])
    age = _calc_age_from_dob(_get_any(profile, ["dob", "date_of_birth"])) or 30
    location = _build_location(profile) or "Singapore"

    annual_income_raw = _get_any(profile, ["annualincome", "assessableincome"])
    monthly_income = 0.0
    if annual_income_raw is not None:
        try:
            monthly_income = float(annual_income_raw) / 12.0
            notes.append("Monthly income estimated from annual Singpass/Myinfo income.")
        except (TypeError, ValueError):
            missing.append("financial_situation.monthly_income_usd")
    else:
        missing.append("financial_situation.monthly_income_usd")

    dependents_raw = _get_any(profile, ["dependants", "dependents_count", "children_count"])
    dependents_count = 0
    if dependents_raw is not None:
        try:
            dependents_count = int(dependents_raw)
        except (TypeError, ValueError):
            missing.append("family_context.dependents_count")

    personal = PersonalBackground(
        age=age,
        current_role="Unknown - update manually",
        years_experience=5,
        location=location,
        risk_tolerance="medium",
        career_goal_12_months="Update with your career objective",
    )
    linkedin = payload.linkedin_context or LinkedInContext(
        profile_url=None,
        top_skills=[],
        endorsements_strength="moderate",
        network_reach="medium",
        recent_relevant_posts=0,
    )
    finances = payload.financial_overrides or FinancialSituation(
        monthly_expenses_usd=3000,
        monthly_income_usd=monthly_income,
        liquid_savings_usd=0,
        debt_usd=0,
        expected_side_income_usd=0,
        other_investments_usd=0,
        expected_investment_monthly_income_usd=0,
        health_insurance_if_quit=True,
    )
    family = payload.family_overrides or FamilyContext(
        dependents_count=dependents_count,
        partner_income_stable=True,
        family_support_level="medium",
        major_events_next_12_months=[],
    )

    if full_name:
        notes.append(f"Imported profile for: {full_name}")
    else:
        notes.append("No full name found in Singpass payload.")
    if not linkedin.top_skills:
        missing.append("linkedin_context.top_skills")
    if finances.monthly_expenses_usd <= 0:
        missing.append("financial_situation.monthly_expenses_usd")
    if finances.liquid_savings_usd <= 0:
        missing.append("financial_situation.liquid_savings_usd")
    if personal.current_role.startswith("Unknown"):
        missing.append("personal_background.current_role")
    if personal.career_goal_12_months.startswith("Update"):
        missing.append("personal_background.career_goal_12_months")

    due_diligence_input = DueDiligenceInput(
        personal_background=payload.personal_overrides or personal,
        linkedin_context=linkedin,
        financial_situation=finances,
        family_context=family,
    )

    return SingpassImportOutput(
        due_diligence_input=due_diligence_input,
        missing_information=sorted(set(missing)),
        notes=notes,
    )


def _net_burn(fin: FinancialSituation) -> float:
    monthly_offsets = fin.expected_side_income_usd + fin.expected_investment_monthly_income_usd
    return max(fin.monthly_expenses_usd - monthly_offsets, 1.0)


def _runway_months(fin: FinancialSituation) -> float:
    return fin.liquid_savings_usd / _net_burn(fin)


def _specialist_finance(data: DueDiligenceInput) -> SpecialistAssessment:
    fin = data.financial_situation
    runway = _runway_months(fin)
    score = 35
    reasons = [f"Runway is {runway:.1f} months."]
    if runway >= 12:
        score += 35
        reasons.append("Runway exceeds 12 months.")
    elif runway >= 6:
        score += 20
        reasons.append("Runway is above 6 months.")
    elif runway >= 4:
        score += 10
        reasons.append("Runway is borderline safe.")
    else:
        score -= 15
        reasons.append("Runway is high risk (<4 months).")

    if fin.debt_usd > fin.monthly_expenses_usd * 12:
        score -= 10
        reasons.append("Debt load is heavy against expense profile.")
    if fin.other_investments_usd >= fin.monthly_expenses_usd * 8:
        score += 7
        reasons.append("Investment portfolio provides additional safety buffer.")
    if not fin.health_insurance_if_quit:
        score -= 12
        reasons.append("No health insurance continuity after quitting.")

    score = max(0, min(100, score))
    verdict = "go" if score >= 72 else ("wait" if score >= 50 else "hold")
    confidence = 0.82
    return SpecialistAssessment(
        agent="finance_risk_agent",
        score_0_to_100=score,
        confidence_0_to_1=confidence,
        verdict=verdict,
        reasons=reasons,
    )


def _specialist_market(data: DueDiligenceInput) -> SpecialistAssessment:
    link = data.linkedin_context
    score = 30 + min(len(link.top_skills), 8) * 4
    reasons = [f"Detected {len(link.top_skills)} core skills on LinkedIn context."]

    if link.network_reach == "large":
        score += 20
        reasons.append("Large network improves opportunity discovery.")
    elif link.network_reach == "medium":
        score += 10
    else:
        score -= 5
        reasons.append("Small network may slow initial traction.")

    if link.endorsements_strength == "strong":
        score += 12
    elif link.endorsements_strength == "weak":
        score -= 8
        reasons.append("Weak endorsements reduce social proof.")

    if link.recent_relevant_posts >= 6:
        score += 8
    elif link.recent_relevant_posts == 0:
        score -= 7
        reasons.append("No recent proof-of-work content.")

    score = max(0, min(100, score))
    verdict = "go" if score >= 70 else ("wait" if score >= 48 else "hold")
    return SpecialistAssessment(
        agent="career_market_agent",
        score_0_to_100=score,
        confidence_0_to_1=0.74,
        verdict=verdict,
        reasons=reasons,
    )


def _specialist_family(data: DueDiligenceInput) -> SpecialistAssessment:
    family = data.family_context
    fin = data.financial_situation
    runway = _runway_months(fin)
    score = 55
    reasons = []

    if family.dependents_count >= 2:
        score -= 15
        reasons.append("2+ dependents increase household risk tolerance requirements.")
    elif family.dependents_count == 1:
        score -= 8
        reasons.append("Single dependent requires stronger safety margin.")
    else:
        score += 5

    if family.partner_income_stable:
        score += 12
        reasons.append("Partner income adds household resilience.")
    else:
        score -= 10
        reasons.append("No stable partner income buffer.")

    if family.family_support_level == "high":
        score += 8
    elif family.family_support_level == "low":
        score -= 8
        reasons.append("Low family support can raise execution pressure.")

    if runway < 6 and family.dependents_count > 0:
        score -= 12
        reasons.append("Runway below 6 months with dependents is a red-zone setup.")

    score = max(0, min(100, score))
    verdict = "go" if score >= 72 else ("wait" if score >= 52 else "hold")
    return SpecialistAssessment(
        agent="family_stability_agent",
        score_0_to_100=score,
        confidence_0_to_1=0.79,
        verdict=verdict,
        reasons=reasons if reasons else ["Household context is manageable for transition."],
    )


def _specialist_linkedin(data: DueDiligenceInput) -> SpecialistAssessment:
    link = data.linkedin_context
    score = 25 + min(len(link.top_skills), 10) * 5
    reasons = ["LinkedIn positioning influences inbound lead generation for transition runway."]

    if link.recent_relevant_posts >= 8:
        score += 15
        reasons.append("Strong recent posting cadence.")
    elif link.recent_relevant_posts < 2:
        score -= 8
        reasons.append("Low posting cadence weakens discovery momentum.")

    if link.endorsements_strength == "strong":
        score += 10
    elif link.endorsements_strength == "weak":
        score -= 10

    if link.network_reach == "large":
        score += 10
    elif link.network_reach == "small":
        score -= 6

    score = max(0, min(100, score))
    verdict = "go" if score >= 68 else ("wait" if score >= 45 else "hold")
    return SpecialistAssessment(
        agent="linkedin_positioning_agent",
        score_0_to_100=score,
        confidence_0_to_1=0.7,
        verdict=verdict,
        reasons=reasons,
    )


def _case_features(data: DueDiligenceInput) -> Dict[str, Any]:
    runway = _runway_months(data.financial_situation)
    return {
        "runway_bucket": "high" if runway >= 8 else ("medium" if runway >= 5 else "low"),
        "dependents_count": data.family_context.dependents_count,
        "risk_tolerance": data.personal_background.risk_tolerance,
        "skills_count": len(data.linkedin_context.top_skills),
    }


def _feature_similarity(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    score = 0.0
    if left.get("runway_bucket") == right.get("runway_bucket"):
        score += 0.35
    if left.get("risk_tolerance") == right.get("risk_tolerance"):
        score += 0.2
    diff_dep = abs(int(left.get("dependents_count", 0)) - int(right.get("dependents_count", 0)))
    score += max(0.0, 0.25 - (diff_dep * 0.08))
    diff_skills = abs(int(left.get("skills_count", 0)) - int(right.get("skills_count", 0)))
    score += max(0.0, 0.2 - (diff_skills * 0.04))
    return max(0.0, min(1.0, score))


def _retrieve_similar_cases(data: DueDiligenceInput, memory: Dict[str, Any], top_n: int = 4) -> List[SimilarCase]:
    current = _case_features(data)
    scored: List[SimilarCase] = []
    for case in memory.get("cases", []):
        sim = _feature_similarity(current, case.get("features", {}))
        if sim < 0.35:
            continue
        feedback = case.get("feedback", {})
        scored.append(
            SimilarCase(
                case_id=case.get("case_id", "unknown"),
                similarity_0_to_1=round(sim, 2),
                recommendation=case.get("recommendation", "N/A"),
                was_successful=feedback.get("was_successful"),
            )
        )
    scored.sort(key=lambda x: x.similarity_0_to_1, reverse=True)
    return scored[:top_n]


def _build_action_plan(data: DueDiligenceInput, agg_score: int) -> ActionPlan:
    runway = _runway_months(data.financial_situation)
    dependents = data.family_context.dependents_count
    family_cadence = "weekly" if dependents > 0 else "bi-weekly"

    before = [
        "Lock at least 3 months of paid pipeline (freelance, consulting, pilots).",
        "Build monthly cash dashboard and cap burn with a hard stop threshold.",
    ]
    if runway < 6:
        before.insert(0, "Increase liquid runway to at least 6 months before resigning.")
    if not data.financial_situation.health_insurance_if_quit:
        before.append("Secure health insurance continuity plan before giving notice.")

    post = [
        "Run a weekly operating review: leads, closes, revenue, burn, and stress.",
        "Protect deep work blocks and test paid offers before scaling build effort.",
        f"Review household stress and finances on a {family_cadence} cadence.",
    ]
    if agg_score < 55:
        post.append("Keep a reversible fallback path: part-time role or contract buffer.")

    return ActionPlan(
        next_30_days=[
            "Complete 10+ customer interviews and verify willingness to pay.",
            "Publish 2 proof-of-work posts weekly to strengthen inbound demand.",
            "Define a quit/no-quit gate with objective metrics (runway, pipeline, health).",
        ],
        before_quitting=before,
        first_90_days_after_quit=post,
    )


def _decision_from_score(score: int) -> Dict[str, str]:
    if score >= 75:
        return {
            "recommendation": "Proceed with a near-term quit once checklist gates are met.",
            "window": "1 to 3 months",
        }
    if score >= 58:
        return {
            "recommendation": "Delay quitting and de-risk execution first.",
            "window": "3 to 6 months",
        }
    return {
        "recommendation": "Do not quit yet; build financial and demand stability.",
        "window": "6 to 12+ months",
    }


def _mock_linkedin_profile(profile_url: Optional[str]) -> Dict[str, Any]:
    slug = "candidate"
    if profile_url:
        match = re.search(r"/in/([^/?#]+)", profile_url)
        if match:
            slug = match.group(1).replace("-", " ")
    display_name = " ".join(word.capitalize() for word in slug.split()) or "Candidate"

    # Slightly varied mock jobs to feel more realistic
    base_jobs = [
        ("Senior Product Manager", "Atlas Fintech", 3),
        ("Product Manager", "Nimbus SaaS", 3),
        ("Business Analyst", "Vertex Systems", 2),
    ]
    if any(token in slug.lower() for token in ["data", "analytics", "ds"]):
        base_jobs = [
            ("Senior Data Scientist", "SignalAI", 3),
            ("Data Scientist", "CloudMetrics", 2),
            ("Data Analyst", "BrightInsight", 2),
        ]
    if any(token in slug.lower() for token in ["eng", "engineer", "dev"]):
        base_jobs = [
            ("Senior Software Engineer", "Gridforge", 3),
            ("Software Engineer", "Orbit Labs", 3),
            ("Junior Engineer", "Bluewave Tech", 2),
        ]

    jobs = [{"title": t, "company": c, "years": y} for t, c, y in base_jobs]
    education = [
        {"school": "National University of Singapore", "degree": "B.Eng Computer Engineering"},
        {"school": "SMU", "degree": "Data Analytics Certificate"},
    ]
    return {"name": display_name, "profile_url": profile_url, "jobs": jobs, "education": education}


def _reason_linkedin_skillset(profile: Dict[str, Any]) -> LinkedInSkillReasoning:
    skill_map = {
        "product": "Product Strategy",
        "manager": "Stakeholder Management",
        "analyst": "Data Analysis",
        "data": "Analytics",
        "engineering": "Technical Fluency",
        "fintech": "Domain Expertise (Fintech)",
        "startup": "0-to-1 Execution",
        "saas": "B2B SaaS GTM",
    }
    tokens: List[str] = []
    for job in profile.get("jobs", []):
        tokens.extend(str(job.get("title", "")).lower().split())
        tokens.extend(str(job.get("company", "")).lower().split())
    for edu in profile.get("education", []):
        tokens.extend(str(edu.get("degree", "")).lower().split())

    inferred: List[str] = []
    for token in tokens:
        if token in skill_map and skill_map[token] not in inferred:
            inferred.append(skill_map[token])
    inferred = inferred[:7] if inferred else ["Generalist Problem Solving"]

    readiness = min(90, 45 + len(inferred) * 6)
    focus = [
        "Publish case-study posts that show measurable business outcomes.",
        "Package one clear paid offer aligned to top inferred skills.",
        "Collect 3 testimonials from previous collaborators or managers.",
    ]
    return LinkedInSkillReasoning(
        inferred_skills=inferred,
        confidence_0_to_1=0.79,
        market_readiness_score_0_to_100=readiness,
        narrative=(
            f"{profile.get('name', 'Candidate')} shows a transferable mix of product, analytics, and execution "
            "skills suitable for a transition into independent work."
        ),
        recommended_focus_areas=focus,
    )


def _build_swarm_decision(data: DueDiligenceInput, case_id: Optional[str] = None) -> SwarmDecision:
    memory = _load_swarm_memory()
    weights = memory.get("agent_weights", _default_memory()["agent_weights"])
    specialists = [
        _specialist_finance(data),
        _specialist_market(data),
        _specialist_family(data),
        _specialist_linkedin(data),
    ]

    total_weight = sum(weights.get(spec.agent, 1.0) for spec in specialists) or 1.0
    weighted_score = sum(spec.score_0_to_100 * weights.get(spec.agent, 1.0) for spec in specialists) / total_weight
    weighted_conf = sum(spec.confidence_0_to_1 * weights.get(spec.agent, 1.0) for spec in specialists) / total_weight

    similar_cases = _retrieve_similar_cases(data, memory)
    success_labels = [c.was_successful for c in similar_cases if c.was_successful is not None]
    success_rate = (sum(1 for s in success_labels if s) / len(success_labels)) if success_labels else None
    score_shift = 0
    if success_rate is not None and len(success_labels) >= 2:
        if success_rate >= 0.7:
            score_shift = 4
        elif success_rate <= 0.4:
            score_shift = -4

    aggregate_score = int(max(0, min(100, round(weighted_score + score_shift))))
    aggregate_conf = round(max(0.0, min(1.0, weighted_conf)), 2)
    decision = _decision_from_score(aggregate_score)

    red_flags: List[str] = []
    if _runway_months(data.financial_situation) < 4:
        red_flags.append("Runway below 4 months.")
    if data.family_context.dependents_count > 0 and not data.family_context.partner_income_stable:
        red_flags.append("Dependents with unstable partner income.")
    if not data.financial_situation.health_insurance_if_quit:
        red_flags.append("No health insurance continuity.")
    if len(data.linkedin_context.top_skills) < 3:
        red_flags.append("Weak LinkedIn skills proof for market transition.")

    rationale = [
        f"Weighted swarm score: {aggregate_score}/100 at confidence {aggregate_conf}.",
        "Coordinator combined specialist votes using historical performance weights.",
    ]
    if success_rate is not None:
        rationale.append(
            f"Similar-case success rate is {round(success_rate * 100)}%, shifting score by {score_shift}."
        )

    case_id_value = case_id or str(uuid.uuid4())
    action_plan = _build_action_plan(data, aggregate_score)

    case_record = {
        "case_id": case_id_value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": _case_features(data),
        "specialists": [spec.model_dump() for spec in specialists],
        "recommendation": decision["recommendation"],
        "aggregate_score": aggregate_score,
        "aggregate_confidence": aggregate_conf,
        "input": data.model_dump(),
    }
    memory.setdefault("cases", []).append(case_record)
    _save_swarm_memory(memory)

    return SwarmDecision(
        case_id=case_id_value,
        aggregate_score_0_to_100=aggregate_score,
        aggregate_confidence_0_to_1=aggregate_conf,
        recommendation=decision["recommendation"],
        recommended_quit_window=decision["window"],
        rationale=rationale,
        specialists=specialists,
        action_plan=action_plan,
        red_flags=red_flags,
        used_agent_weights={k: round(v, 3) for k, v in weights.items()},
        similar_cases=similar_cases,
    )


def _score_readiness(data: DueDiligenceInput) -> DueDiligenceRecommendation:
    swarm = _build_swarm_decision(data)
    return DueDiligenceRecommendation(
        risk_summary=RiskSummary(
            runway_months=round(_runway_months(data.financial_situation), 2),
            readiness_score_0_to_100=swarm.aggregate_score_0_to_100,
            recommendation=swarm.recommendation,
        ),
        recommended_quit_window=swarm.recommended_quit_window,
        rationale=swarm.rationale,
        action_plan=swarm.action_plan,
        red_flags=swarm.red_flags,
    )


def _update_weights_after_feedback(feedback: FeedbackInput) -> FeedbackResult:
    memory = _load_swarm_memory()
    cases = memory.get("cases", [])
    target_case = next((case for case in cases if case.get("case_id") == feedback.case_id), None)
    if not target_case:
        return FeedbackResult(
            case_id=feedback.case_id,
            status="error",
            updated_agent_weights={},
            message="Case not found in swarm memory.",
        )

    target_case["feedback"] = feedback.model_dump()
    weights = memory.setdefault("agent_weights", _default_memory()["agent_weights"])
    scorecard = memory.setdefault("agent_scorecard", {})

    if feedback.did_user_quit:
        for spec in target_case.get("specialists", []):
            agent = spec.get("agent")
            verdict = spec.get("verdict", "wait")
            predicted_go = verdict == "go"
            correct = (feedback.was_successful and predicted_go) or (
                (not feedback.was_successful) and (not predicted_go)
            )
            old_weight = float(weights.get(agent, 1.0))
            delta = 0.08 if correct else -0.08
            weights[agent] = round(max(0.4, min(2.5, old_weight * (1.0 + delta))), 4)

            current = scorecard.setdefault(agent, {"correct": 0, "total": 0})
            current["total"] += 1
            if correct:
                current["correct"] += 1

    _save_swarm_memory(memory)
    return FeedbackResult(
        case_id=feedback.case_id,
        status="ok",
        updated_agent_weights={k: round(v, 3) for k, v in weights.items()},
        message="Feedback stored and swarm weights updated.",
    )


def _ai_ready() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )


agent_kwargs = dict(
    node_id="quit-job-due-diligence-agent",
    version="0.2.0",
    dev_mode=True,
    agentfield_server=os.getenv("AGENTFIELD_SERVER", "http://localhost:8080"),
)

if _ai_ready():
    agent_kwargs["ai_config"] = AIConfig(model=os.getenv("AF_MODEL", "openai/gpt-4o-mini"), temperature=0.2)

app = Agent(**agent_kwargs)


@app.reasoner
async def import_from_singpass(payload: dict) -> SingpassImportOutput:
    data = SingpassImportInput.model_validate(payload)
    return _from_singpass(data)


@app.reasoner
async def coordinate_swarm(payload: dict) -> SwarmDecision:
    data = DueDiligenceInput.model_validate(payload)
    return _build_swarm_decision(data)


@app.reasoner
async def recommend_with_memory(payload: dict) -> SwarmDecision:
    data = DueDiligenceInput.model_validate(payload)
    return _build_swarm_decision(data)


@app.reasoner
async def submit_feedback(payload: dict) -> FeedbackResult:
    data = FeedbackInput.model_validate(payload)
    return _update_weights_after_feedback(data)


@app.reasoner
async def recommend_quit_plan(payload: dict) -> DueDiligenceRecommendation:
    data = DueDiligenceInput.model_validate(payload)

    if not _ai_ready():
        return _score_readiness(data)

    swarm = _build_swarm_decision(data)
    system_prompt = (
        "You are a pragmatic career transition advisor. "
        "Refine the swarm recommendation conservatively. "
        "Output only JSON matching the schema."
    )
    user_prompt = (
        "Use this profile and swarm context to produce final recommendation.\n\n"
        f"Input profile:\n{json.dumps(payload, indent=2)}\n\n"
        f"Swarm decision:\n{json.dumps(swarm.model_dump(), indent=2)}\n"
    )

    return await app.ai(
        system=system_prompt,
        user=user_prompt,
        schema=DueDiligenceRecommendation,
    )


if __name__ == "__main__":
    app.run()
