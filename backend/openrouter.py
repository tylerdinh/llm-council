"""Local Qwen client for making LLM requests."""

import httpx
from typing import List, Dict, Any, Optional
from .config import QWEN_API_URL, MAX_TOKENS


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    system_prompt: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via local Qwen API.

    Args:
        model: Model identifier (e.g., "qwen/qwen3-1.7b")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        system_prompt: Optional system prompt to prepend
        tools: Optional list of tool definitions for function calling

    Returns:
        Response dict with 'content', optional 'reasoning_details', and optional 'tool_calls', or None if failed
    """

    headers = {
        "Content-Type": "application/json",
    }

    # Prepend system prompt if provided
    final_messages = messages
    if system_prompt:
        final_messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": model,
        "messages": final_messages,
        "max_tokens": MAX_TOKENS,
    }
    
    # Add tools if provided
    if tools:
        payload["tools"] = tools

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                QWEN_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details'),
                'tool_calls': message.get('tool_calls', [])
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_members_parallel(
    members: Dict[str, Dict[str, Any]],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple council members in parallel.

    Args:
        members: Dict of member configs (from COUNCIL_MEMBERS)
        messages: List of message dicts to send to each member

    Returns:
        Dict mapping member_id to response dict (or None if failed)
    """
    import asyncio

    # Build system prompts for each member
    def build_system_prompt(member_config: Dict[str, Any]) -> str:
        """Build system prompt from member configuration."""
        traits_str = ", ".join(member_config.get("traits", []))
        return f"""You are {member_config['name']}, a council member in a multi-model deliberation system.

Role: {member_config['role']}
Personality: {member_config['personality']}
Traits: {traits_str}

You collaborate with other models to answer questions. Stay in character and leverage your unique perspective."""

    # Create tasks for all members with their system prompts
    tasks = []
    member_ids = []
    for member_id, member_config in members.items():
        system_prompt = build_system_prompt(member_config)
        task = query_model(member_config['model'], messages, system_prompt=system_prompt)
        tasks.append(task)
        member_ids.append(member_id)

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map member IDs to their responses
    return {member_id: response for member_id, response in zip(member_ids, responses)}
