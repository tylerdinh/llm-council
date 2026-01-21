"""Configuration for the LLM Council."""

# Council members - dict of member configs with unique identities
# Each member has a name, model, and optional personality/traits
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
    "charlie": {
        "name": "Charlie",
        "model": "qwen/qwen3-1.7b",
        "personality": "diplomatic and balanced",
        "traits": ["empathetic", "fair-minded", "collaborative"],
        "role": "Coordinator - synthesizes different perspectives"
    }
}

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "qwen/qwen3-1.7b"


# Local Qwen API endpoint
QWEN_API_URL = "http://127.0.0.1:1234/v1/chat/completions"

# Maximum tokens for model responses
MAX_TOKENS = 700  # Approximately one paragraph

# Data directory for conversation storage
DATA_DIR = "data/conversations"
