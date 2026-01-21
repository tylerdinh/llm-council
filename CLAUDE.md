# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a 4-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovations are:
1. Stage 2 collaboration through tool-based messaging (inspired by chorus-text)
2. Anonymized peer review in Stage 3 to prevent models from playing favorites

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MEMBERS` (dict of member configs with unique identities)
- Each member has: name, model, personality, traits, and role
- Similar structure to chorus-text's `AGENTS` configuration
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`openrouter.py`**
- `query_model()`: Single async model query with optional system_prompt and tools parameters
- Supports tool calling via the `tools` parameter
- `query_members_parallel()`: Parallel queries to all council members
- Builds unique system prompts for each member based on their personality/traits
- Returns dict mapping member_id to response
- Graceful degradation: returns None on failure, continues with successful responses

**`tools.py`**
- `ToolExecutor`: Executes tools called by council members during collaboration
- `send_message`: Allows members to communicate with each other
- `TOOLS`: List of tool definitions in OpenAI function calling format
- Inspired by chorus-text's multi-agent messaging system

**`council.py`** - The Core Logic
- `stage1_collect_responses()`: Parallel queries to all council members with their unique personalities
- Returns list with member_id, member_name, model, role, and response
- `stage2_collaboration()`: **NEW** - Members exchange messages using tool calls
  - Max 2 rounds of collaboration by default
  - Tool executor processes `send_message` calls
  - Returns collaboration log with all exchanges and tool calls
- `stage3_collect_rankings()`:
- `stage3_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_member` mapping (maps to member_name, not model)
  - Prompts members to evaluate and rank (with strict format requirements)
  - Returns tuple: (rankings_list, label_to_member_dict)
  - Each ranking includes member_id, member_name, model, raw text and `parsed_ranking` list
- `stage4_synthesize_final()`: Chairman synthesizes from all responses + collaboration + rankings
- Shows member names and roles in context to chairman
- Includes collaboration summary in chairman's context
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section, handles both numbered lists and plain format
- `calculate_aggregate_rankings()`: Computes average rank position across all peer evaluations

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3, stage4}`
- Note: metadata (label_to_model, aggregate_rankings) is NOT persisted to storage, only returned via API

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- POST `/api/conversations/{id}/message` returns metadata in addition to stages
- POST `/api/conversations/{id}/message/stream` streams all 4 stages with SSE
- Metadata includes: label_to_member mapping and aggregate_rankings

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding

**`components/Stage1.jsx`**
- Tab view of individual member responses
- Shows member name and role
- ReactMarkdown rendering with markdown-content wrapper

**`components/Stage2.jsx`**
- **NEW**: Displays collaboration exchanges between council members
- Shows messages sent between members using tool calls
- Round-based view with tabs for multiple collaboration rounds
- Displays both member responses and inter-member messages
- Shows tool usage (send_message calls)

**`components/Stage3.jsx`** (formerly Stage2.jsx)
- **Critical Feature**: Tab view showing RAW evaluation text from each member
- De-anonymization happens CLIENT-SIDE for display (members receive anonymous labels)
- Shows member names in evaluations and rankings
- Shows "Extracted Ranking" below each evaluation so users can validate parsing
- Aggregate rankings shown with average position and vote count
- Explanatory text clarifies that boldface member names are for readability only

**`components/Stage4.jsx`** (formerly Stage3.jsx)
- Final synthesized answer from chairman
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Stage 2 Collaboration (NEW)
Inspired by chorus-text's multi-agent system:
- Council members can send messages to each other via `send_message` tool
- Messages are queued and delivered to recipients
- Each member maintains conversation history including received messages
- Members get 2 rounds of collaboration by default
- Tool calls are logged and displayed to users for transparency
- This allows members to critique, question, and build on each other's ideas

### Stage 3 Prompt Format
The Stage 2 prompt is very specific to ensure parseable output:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

### De-anonymization Strategy
- Members receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "Alice", "Response B": "Bob", ...}`
- Frontend displays member names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Council Member Configuration
- Each member has unique name, personality, traits, and role
- Members receive personalized system prompts based on their configuration
- Similar to chorus-text's agent-based approach
- Allows different perspectives and thinking styles in deliberation
- All members can use the same or different underlying models

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Members are configured as a dict in `backend/config.py` with each member having:
- `name`: Display name (e.g., "Alice")
- `model`: Model identifier (e.g., "qwen/qwen3-1.7b")
- `personality`: Description of thinking style
- `traits`: List of personality traits
- `role`: Member's role in deliberation

Chairman can be same or different from council member models. The current default is Gemini as chairman per user preference.

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Streaming responses instead of batch loading
- Export conversations to markdown/PDF
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling

## Testing Notes

Use `test_openrouter.py` to verify API connectivity and test different model identifiers before adding to council. The script tests both streaming and non-streaming modes.

## Data Flow Summary

```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display with tabs + validation UI
```

The entire flow is async/parallel where possible to minimize latency.
