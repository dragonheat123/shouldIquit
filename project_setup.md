# Project Setup Guide - Should I Quit?

## Overview

**Should I Quit?** is a multi-agent swarm intelligence system that helps professionals make informed career exit decisions. Built with Python, AgentField, and Flask, it uses specialized agents to analyze financial, career, family, and market factors to provide data-driven recommendations.

### Key Technologies
- **Backend**: AgentField (agent orchestration framework)
- **Web Framework**: Flask 3.0+
- **Data Validation**: Pydantic 2.0+
- **Optional APIs**: OpenAI (LLM opinions), Tavily (news search)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

### Required
- **Python 3.x** (Python 3.8 or higher recommended)
- **pip** (Python package installer)
- **AgentField CLI** - The control plane for agent orchestration
  
  **IMPORTANT**: You need BOTH the Python SDK AND the CLI tool:
  
  1. Python SDK (installed via requirements.txt):
     ```bash
     pip install agentfield  # This is just the Python library
     ```
  
  2. AgentField CLI tool (separate installation required):
     ```bash
     curl -sSf https://agentfield.ai/get | sh
     source ~/.zshrc  # or source ~/.bashrc on Linux
     ```
  
  Verify CLI installation:
  ```bash
  af --version  # Should show AgentField version
  ```

### Optional (for enhanced features)
- **OpenAI API Key** - For AI-generated opinions
- **Tavily API Key** - For news horizon scanning

---

## Installation Steps

### 1. Clone the Repository (if not already done)

```bash
git clone <repository-url>
cd shouldIquit
```

### 2. Create Virtual Environment

Create and activate a Python virtual environment to isolate dependencies:

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` prefix in your terminal prompt indicating the virtual environment is active.

### 3. Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

This will install:
- `agentfield` - Agent orchestration framework
- `pydantic>=2.0.0` - Data validation
- `python-dotenv>=1.0.0` - Environment variable management
- `flask>=3.0.0` - Web framework
- `openai>=1.40.0` - OpenAI API client (optional)
- `requests>=2.31.0` - HTTP client for Tavily API

### 4. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```bash
# Required: AgentField server URL
AGENTFIELD_SERVER=http://localhost:8080

# Optional: AgentField model configuration
AF_MODEL=openai/gpt-4o-mini

# Optional: OpenAI API (enables LLM-generated opinions)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Optional: Tavily API (enables news search)
TAVILY_API_KEY=your-tavily-api-key-here
```

**Important Notes:**
- `AGENTFIELD_SERVER` is required and defaults to `http://localhost:8080`
- OpenAI and Tavily API keys are optional but unlock additional features
- Without API keys, the system will still work with local agent reasoning

---

## Running the Application

The application consists of three components that need to run simultaneously:

### Step 1: Start AgentField Server

Open a terminal window and run:

```bash
af server
```

This starts the AgentField server on **port 8080**. Keep this terminal running.

**Expected output:**
```
AgentField server running on http://localhost:8080
```

### Step 2: Start Main Agent Application

Open a **second terminal window**, activate the virtual environment, and run:

```bash
source .venv/bin/activate  # On macOS/Linux
# or .venv\Scripts\activate on Windows

python main.py
```

This registers the agent with the AgentField server and keeps the agent system running.

**Expected output:**
```
Agent 'quit-job-due-diligence-agent' registered successfully
```

### Step 3: Start Flask Frontend

Open a **third terminal window**, activate the virtual environment, and run:

```bash
source .venv/bin/activate  # On macOS/Linux
# or .venv\Scripts\activate on Windows

python frontend.py
```

The Flask frontend will start on **port 5050**.

**Expected output:**
```
 * Running on http://127.0.0.1:5050
```

### Step 4: Access the Application

Open your web browser and navigate to:

```
http://localhost:5050
```

---

## Application Architecture

### Components

1. **AgentField Server** (Port 8080)
   - Orchestrates agent communication
   - Manages agent registry and execution

2. **Main Agent System** (`main.py`)
   - 8 specialized agents working in swarm mode:
     - `finance_risk_agent` - Financial runway analysis
     - `career_market_agent` - Market readiness assessment
     - `family_stability_agent` - Family/household risk analysis
     - `linkedin_positioning_agent` - LinkedIn profile strength
     - `peer_opinion_agent` - Simulated peer opinions
     - `job_search_agent` - Job market analysis
     - `news_agent` - News horizon scanning
     - `knowledge_synth_agent` - Final synthesis

3. **Flask Frontend** (Port 5050)
   - User interface for data input
   - API endpoints for agent communication
   - Real-time results display

### Data Storage

- **Local JSON File**: `swarm_memory.json`
  - Auto-created on first run
  - Stores agent weights, case history, and scorecards
  - Gitignored (not committed to repository)
  - Enables feedback loop and learning

---

## API Endpoints

### AgentField API (Port 8080)

```bash
# Import from Singpass
POST /api/v1/execute/quit-job-due-diligence-agent.import_from_singpass

# Get recommendation with memory
POST /api/v1/execute/quit-job-due-diligence-agent.recommend_with_memory

# Submit feedback
POST /api/v1/execute/quit-job-due-diligence-agent.submit_feedback

# Coordinate swarm
POST /api/v1/execute/quit-job-due-diligence-agent.coordinate_swarm

# Get quit plan
POST /api/v1/execute/quit-job-due-diligence-agent.recommend_quit_plan
```

### Flask Frontend API (Port 5050)

```bash
GET  /                        # Home page
POST /api/connect/linkedin    # LinkedIn profile connection
POST /api/connect/singpass    # Singpass financial import
POST /api/self/process        # Own-agent opinion
POST /api/simulated/process   # Simulated peer opinions
POST /api/jobs/process        # Job market analysis
POST /api/news/process        # News horizon search
POST /api/swarm/process       # Full swarm decision
POST /api/feedback            # Submit outcome feedback
```

---

## Testing the Setup

### 1. Test OpenAI API Connection (Optional)

If you configured OpenAI API key, test the connection:

```bash
python test_llm.py
```

**Expected output:**
```
Testing OpenAI API connection...
✓ OpenAI API is working correctly
Model: gpt-4o-mini
```

### 2. Test AgentField Connection

Use curl to test if agents are registered:

```bash
curl http://localhost:8080/api/v1/agents
```

You should see the registered agent in the response.

### 3. Test Sample Input

Use the provided sample files to test the system:

```bash
curl -X POST http://localhost:8080/api/v1/execute/quit-job-due-diligence-agent.coordinate_swarm \
  -H "Content-Type: application/json" \
  -d @sample_input.json
```

---

## Project Structure

```
shouldIquit/
├── main.py                      # Main agent application
├── frontend.py                  # Flask web server
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .env                         # Environment variables (gitignored)
├── .gitignore                   # Git ignore rules
├── README.md                    # Project documentation
├── project_setup.md             # This setup guide
├── test_llm.py                  # OpenAI API test script
├── swarm_memory.json            # Local memory (auto-created, gitignored)
├── templates/
│   └── index.html               # Frontend HTML
├── static/
│   ├── app.js                   # Frontend JavaScript
│   └── styles.css               # Frontend styling
├── sample_input.json            # Example due diligence input
├── sample_singpass_import.json  # Example Singpass import
└── sample_feedback.json         # Example feedback submission
```

---

## Common Issues & Troubleshooting

### Issue: "[Errno 61] Connect call failed" or "AgentField server unavailable"
**Symptoms**: 
```
❌ Failed to connect to memory events: [Errno 61] Connect call failed
⚠️ AgentField server unavailable - running in degraded mode
```

**Root Cause**: The AgentField server is not running on port 8080

**Solution**: 
1. First, verify the AgentField CLI is installed:
   ```bash
   af --version
   ```
   
   If not found, install it:
   ```bash
   curl -sSf https://agentfield.ai/get | sh
   source ~/.zshrc  # Reload shell configuration
   ```

2. Start the AgentField server in a separate terminal:
   ```bash
   af server
   ```
   
3. Wait for the message: "AgentField server running on http://localhost:8080"

4. Then run `python main.py` - it should now connect successfully

### Issue: "Module not found" errors
**Solution**: 
1. Ensure virtual environment is activated: `source .venv/bin/activate`
2. Reinstall dependencies: `pip install -r requirements.txt`

### Issue: "Port already in use"
**Solution**: 
- AgentField (8080): Check if another process is using port 8080
- Flask (5050): Change port in `frontend.py` if needed

### Issue: OpenAI API errors
**Solution**: 
1. Verify your API key in `.env` file
2. Test with `python test_llm.py`
3. The system will work without OpenAI, just won't have LLM opinions

### Issue: `swarm_memory.json` not found
**Solution**: This file is auto-created on first run. If there are permission issues, create it manually:
```bash
echo '{"agent_weights": {}, "case_history": [], "agent_scorecard": {}}' > swarm_memory.json
```

---

## Development Workflow

### Making Changes

1. **Backend Changes** (`main.py`):
   - Stop `main.py` (Ctrl+C)
   - Make changes
   - Restart: `python main.py`

2. **Frontend Changes** (`frontend.py`, `templates/`, `static/`):
   - Stop `frontend.py` (Ctrl+C)
   - Make changes
   - Restart: `python frontend.py`

3. **AgentField Server**:
   - Usually doesn't need restarting unless upgrading AgentField

### Adding New Dependencies

```bash
pip install <package-name>
pip freeze > requirements.txt
```

---

## Stopping the Application

To shut down the application:

1. Stop Flask frontend: `Ctrl+C` in frontend terminal
2. Stop main agent: `Ctrl+C` in main.py terminal
3. Stop AgentField server: `Ctrl+C` in server terminal
4. Deactivate virtual environment: `deactivate`

---

## Next Steps

1. **Explore the UI**: Open http://localhost:5050 and try the career assessment
2. **Review Sample Files**: Check `sample_*.json` for example payloads
3. **Read the README**: See `README.md` for detailed feature documentation
4. **Customize Agents**: Modify agent logic in `main.py` to adjust recommendations

---

## Additional Resources

- **AgentField Documentation**: https://github.com/agentfield/agentfield
- **Flask Documentation**: https://flask.palletsprojects.com/
- **Pydantic Documentation**: https://docs.pydantic.dev/

---

## Support & Feedback

This is a hackathon project demonstrating swarm intelligence for career decisions. For questions or contributions, please refer to the repository's issue tracker.

---

**Last Updated**: February 7, 2026
