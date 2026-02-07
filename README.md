# AgentField Hackathon: Swarm Quit-Job Intelligence

This project now has:
- AgentField reasoners for due diligence + swarm coordination
- Feedback loop that reweights specialist agents
- Flask frontend for a live demo

## What the swarm does

Specialist agents:
- `finance_risk_agent`
- `career_market_agent`
- `family_stability_agent`
- `linkedin_positioning_agent`

Coordinator output:
- weighted aggregate decision
- quit window
- rationale and red flags
- action plan
- similar historical cases

Memory:
- stored in `/Users/lorky/Documents/New project 3/swarm_memory.json`
- feedback updates weights so future decisions are influenced by real outcomes

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run AgentField backend

Terminal A:
```bash
af server
```

Terminal B:
```bash
source .venv/bin/activate
python main.py
```

## AgentField reasoners

### Import profile
```bash
curl -X POST "http://localhost:8080/api/v1/execute/quit-job-due-diligence-agent.import_from_singpass" \
  -H "Content-Type: application/json" \
  -d @sample_singpass_import.json
```

### Swarm recommendation
```bash
curl -X POST "http://localhost:8080/api/v1/execute/quit-job-due-diligence-agent.recommend_with_memory" \
  -H "Content-Type: application/json" \
  -d @sample_input.json
```

### Submit outcome feedback
```bash
curl -X POST "http://localhost:8080/api/v1/execute/quit-job-due-diligence-agent.submit_feedback" \
  -H "Content-Type: application/json" \
  -d @sample_feedback.json
```

## Run Flask demo frontend

```bash
source .venv/bin/activate
python frontend.py
```

Open:
- [http://127.0.0.1:5050](http://127.0.0.1:5050)

Frontend tabs:
1. `Your Details`: connect your own LinkedIn + Singpass, then run own-agent opinion process.
2. `Simulated Opinions`: paste other people's LinkedIn URLs (boss/coworker) and simulate their opinion.
3. `Jobs Agent`: run a job-search agent and market opinion process.
4. `Agentic Swarm`: orchestrate self + peers + jobs into one final swarm opinion with trace.

Manual side-investment inputs:
- `other_investments_usd`
- `expected_investment_monthly_income_usd`

## Notes

- This is decision support, not financial/legal advice.
- For a hackathon demo, this local JSON memory loop is enough to show collective learning.
