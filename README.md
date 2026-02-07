# AgentField Hackathon: Swarm Quit-Job Intelligence

This project now has:
- AgentField reasoners for due diligence + swarm coordination
- Feedback loop that reweights specialist agents
- Flask frontend for a live demo
- Optional OpenAI opinions (if `OPENAI_API_KEY` set)
- Optional Tavily news search (if `TAVILY_API_KEY` set)

## What the swarm does

Specialist agents:
- `finance_risk_agent`
- `career_market_agent`
- `family_stability_agent`
- `linkedin_positioning_agent`
- `peer_opinion_agent`
- `job_search_agent`
- `news_agent`
- `knowledge_synth_agent`

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

LLM and news (optional) in `.env`:
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-4o-mini`
- `TAVILY_API_KEY=...`

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
- http://127.0.0.1:5050

Frontend flow:
1. `Your Details`: connect LinkedIn + Singpass, run own-agent opinion.
2. `Simulated Personas`: paste LinkedIn URLs for boss/coworker opinions.
3. `Jobs + News Agents`: job search and news horizon (Tavily) with opinion.
4. `Agentic Swarm + Memory`: merges self + peers + jobs + news; memory in `swarm_memory.json`.

Manual side-investment inputs:
- `other_investments_usd`
- `expected_investment_monthly_income_usd`

## Notes

- This is decision support, not financial/legal advice.
- For a hackathon demo, this local JSON memory loop is enough to show collective learning.
