# LLM Council

![llmcouncil](header.jpg)

A collaborative AI deliberation system where multiple LLMs with distinct personalities work together to answer questions.

## How It Works

When you submit a query, the council goes through 4 stages:

1. **Stage 1: Individual Responses**. Each council member (with unique personalities and roles) independently responds to your question. Members have distinct traits like "analytical", "creative", or "diplomatic" that influence their perspectives.

2. **Stage 2: Collaboration**. Council members engage in multi-round discussions using tool-based messaging. They can send messages to each other to critique, question, and build on ideas. This allows for real-time deliberation and refinement.

3. **Stage 3: Peer Review**. Each member evaluates all initial responses (anonymized as "Response A, B, C, etc.") to prevent bias. They rank the responses based on accuracy and insight, with results aggregated into "street cred" rankings.

4. **Stage 4: Final Synthesis**. The Chairman synthesizes all responses, collaboration exchanges, and peer rankings into a comprehensive final answer that represents the council's collective wisdom.

## Features

- **Multi-Agent Collaboration**: Council members communicate via tool-based messaging to refine their thinking
- **Unique Personalities**: Each member has distinct traits, roles, and perspectives
- **Anonymized Peer Review**: Prevents bias by hiding identities during evaluation
- **Aggregate Rankings**: "Street cred" system shows which responses the council collectively values
- **Streaming UI**: Watch each stage unfold in real-time as the council deliberates
- **Local Storage**: All conversations saved as JSON for easy inspection and portability

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for project management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure Local LLM Server

This project uses a **local Qwen API server** (LM Studio or similar) instead of OpenRouter. 

1. Install [LM Studio](https://lmstudio.ai/) or run your own OpenAI-compatible API server
2. Load a model (e.g., Qwen 3 1.7B or any other model)
3. Start the local server (default: http://127.0.0.1:1234/v1)

**Note:** The default configuration in `backend/config.py` uses Qwen 3 1.7B for all members and the chairman. You can modify this to use different models or different API endpoints.

### 3. Configure Council Members (Optional)

Edit `backend/config.py` to customize council members:

```python
COUNCIL_MEMBERS = {
    "alice": {
        "name": "Alice",
        "model": "qwen/qwen3-1.7b",
        "personality": "analytical and methodical",
        "traits": ["logical", "detail-oriented", "skeptical"],
        "role": "Analyst - breaks down problems systematically"
    },
    "bob": {
        "name": "Bob",
        "model": "qwen/qwen3-1.7b",
        "personality": "creative and enthusiastic",
        "traits": ["imaginative", "optimistic", "spontaneous"],
        "role": "Innovator - generates creative solutions"
    },
    # Add more members...
}

CHAIRMAN_MODEL = "qwen/qwen3-1.7b"
QWEN_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
```

## Running the Application

**Start the local LLM server**
Default: http://127.0.0.1:1234/v1

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

**Note:** The backend runs on port 8001 (not 8000) to avoid conflicts with other applications.

## Project Structure

```
llm-council/
├── backend/
│   ├── config.py          # Council member configurations & settings
│   ├── council.py         # 4-stage orchestration logic
│   ├── openrouter.py      # Local Qwen API client
│   ├── tools.py           # Tool execution (send_message, etc.)
│   ├── storage.py         # JSON-based conversation storage
│   └── main.py            # FastAPI server
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Stage1.jsx # Individual responses tab view
│       │   ├── Stage2.jsx # Collaboration exchanges
│       │   ├── Stage3.jsx # Peer rankings & aggregate scores
│       │   └── Stage4.jsx # Final synthesized answer
│       ├── App.jsx        # Main app orchestration
│       └── api.js         # Backend API client
├── data/
│   └── conversations/     # Stored conversations (JSON)
└── CLAUDE.md             # Technical architecture documentation
```

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, Local Qwen API
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript
- **AI Orchestration:** Multi-agent collaboration with tool calling

## Inspiration

This extension to Karpathy's original project was inspired from:
- **[Chorus](https://www.youtube.com/watch?v=8CoBHyIiHMM&feature=youtu.be)**: The final project I made during the Fall 2025 semester for CSE 2004, Web Development, at Washington University in St. Louis
- **[Vending-Bench](https://arxiv.org/pdf/2502.15840)**: The original inspiration for me to create multi-agent systems with AI (with tool calling)
