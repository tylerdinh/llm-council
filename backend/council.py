"""4-stage LLM Council orchestration."""

import json
from typing import List, Dict, Any, Tuple
from .openrouter import query_members_parallel, query_model
from .config import COUNCIL_MEMBERS, CHAIRMAN_MODEL
from .tools import ToolExecutor, TOOLS


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council members.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'member_id', 'member_name', 'model' and 'response' keys
    """
    # Instruct models to keep responses brief
    prompt = f"{user_query}\n\nIMPORTANT: Keep your response to ONE paragraph only (4 sentences). Be concise and direct."
    messages = [{"role": "user", "content": prompt}]

    # Query all members in parallel
    responses = await query_members_parallel(COUNCIL_MEMBERS, messages)

    # Format results with member information
    stage1_results = []
    for member_id, response in responses.items():
        if response is not None:
            member_config = COUNCIL_MEMBERS[member_id]
            content = response.get('content', '') if isinstance(response, dict) else str(response)
            stage1_results.append({
                "member_id": member_id,
                "member_name": member_config['name'],
                "model": member_config['model'],
                "role": member_config['role'],
                "response": content
            })

    return stage1_results


async def stage2_collaboration(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    max_rounds: int = 2
) -> List[Dict[str, Any]]:
    """
    Stage 2: Council members collaborate through message passing.
    
    Members can send messages to each other to discuss, critique, and refine their initial responses.
    
    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        max_rounds: Maximum number of collaboration rounds
        
    Returns:
        List of collaboration exchanges with member messages and tool calls
    """
    from .openrouter import query_model
    
    message_queue = []
    tool_executor = ToolExecutor(message_queue)
    collaboration_log = []
    
    # Build system prompt for collaboration
    def build_collab_system_prompt(member_config: Dict[str, Any]) -> str:
        traits_str = ", ".join(member_config.get("traits", []))
        return f"""You are {member_config['name']}, a council member in a multi-model deliberation system.

Role: {member_config['role']}
Personality: {member_config['personality']}
Traits: {traits_str}

You are now in the COLLABORATION stage. You've seen everyone's initial responses to the user's question.
Your goal is to engage with other council members to refine and improve the collective understanding.

Use the send_message tool to:
- Share insights or critiques about other members' responses
- Ask clarifying questions
- Build on ideas you find compelling
- Point out potential issues or gaps

Be constructive and stay in character. Limit your messages to 2-3 sentences each."""
    
    # Track conversation history for each member
    member_histories = {member_id: [] for member_id in COUNCIL_MEMBERS.keys()}
    
    # Show each member all the Stage 1 responses
    all_responses_text = "\n\n".join([
        f"{result['member_name']} ({result['role']}):\n{result['response']}"
        for result in stage1_results
    ])
    
    initial_context = f"""Original Question: {user_query}

Here are all the initial responses from the council:

{all_responses_text}

Review these responses and decide if you want to engage with other council members. You can use the send_message tool to communicate with them."""
    
    for round_num in range(max_rounds):
        # Each member gets a chance to send messages
        for member_id, member_config in COUNCIL_MEMBERS.items():
            system_prompt = build_collab_system_prompt(member_config)
            
            # Build messages for this member
            if round_num == 0:
                # First round: present the initial responses
                messages = [{"role": "user", "content": initial_context}]
            else:
                # Subsequent rounds: continue the conversation
                messages = [{"role": "user", "content": "Continue the discussion if you have more to contribute."}]
            
            # Add any messages this member received
            if member_histories[member_id]:
                messages.extend(member_histories[member_id])
            
            # Query the model with tools
            response = await query_model(
                member_config['model'],
                messages,
                system_prompt=system_prompt,
                tools=TOOLS
            )
            
            if response is None:
                continue
            
            # Log the response
            log_entry = {
                "round": round_num + 1,
                "member_id": member_id,
                "member_name": member_config['name'],
                "content": response.get('content', ''),
                "tool_calls": []
            }
            
            # Process tool calls
            tool_calls = response.get('tool_calls', [])
            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call['function']['name']
                    try:
                        args = json.loads(tool_call['function']['arguments'])
                    except json.JSONDecodeError:
                        args = {}
                    
                    # Execute the tool
                    result = tool_executor.execute(member_config['name'], tool_name, args)
                    
                    # Log the tool call
                    log_entry['tool_calls'].append({
                        "tool": tool_name,
                        "arguments": args,
                        "result": result
                    })
                    
                    # Add tool result to member's history
                    member_histories[member_id].append({
                        "role": "assistant",
                        "content": response.get('content', ''),
                        "tool_calls": tool_calls
                    })
                    member_histories[member_id].append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": result
                    })
            
            collaboration_log.append(log_entry)
        
        # Deliver messages from the queue
        while message_queue:
            msg = message_queue.pop(0)
            recipient_id = None
            
            # Find the recipient's member_id
            for mid, mconfig in COUNCIL_MEMBERS.items():
                if mconfig['name'] == msg['to']:
                    recipient_id = mid
                    break
            
            if recipient_id:
                # Add message to recipient's history
                member_histories[recipient_id].append({
                    "role": "user",
                    "content": f"Message from {msg['from']}: {msg['message']}"
                })
                
                # Log the delivered message
                collaboration_log.append({
                    "round": round_num + 1,
                    "type": "message_delivery",
                    "from": msg['from'],
                    "to": msg['to'],
                    "message": msg['message']
                })
    
    return collaboration_log


async def stage3_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 3: Each member ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_member mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to member name
    label_to_member = {
        f"Response {label}": result['member_name']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Keep your evaluation concise - use ONE brief paragraph per response (2-3 sentences each).

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council members in parallel
    responses = await query_members_parallel(COUNCIL_MEMBERS, messages)

    # Format results with member information
    stage3_results = []
    for member_id, response in responses.items():
        if response is not None:
            member_config = COUNCIL_MEMBERS[member_id]
            full_text = response.get('content', '') if isinstance(response, dict) else str(response)
            parsed = parse_ranking_from_text(full_text)
            stage3_results.append({
                "member_id": member_id,
                "member_name": member_config['name'],
                "model": member_config['model'],
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage3_results, label_to_member


async def stage4_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    stage3_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 4: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual member responses from Stage 1
        stage2_results: Collaboration exchanges from Stage 2
        stage3_results: Rankings from Stage 3

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"{result['member_name']} ({result['role']}):\n{result['response']}"
        for result in stage1_results
    ])
    
    # Build Stage 2 collaboration summary
    stage2_text = ""
    if stage2_results:
        stage2_messages = []
        for entry in stage2_results:
            if entry.get('type') == 'message_delivery':
                stage2_messages.append(f"{entry['from']} → {entry['to']}: {entry['message']}")
            elif entry.get('content'):
                stage2_messages.append(f"{entry['member_name']}: {entry['content']}")
        
        if stage2_messages:
            stage2_text = f"\n\nSTAGE 2 - Collaboration:\n" + "\n".join(stage2_messages)

    stage3_text = "\n\n".join([
        f"{result['member_name']}'s Evaluation:\n{result['ranking']}"
        for result in stage3_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models with different personalities and roles have provided responses to a user's question, collaborated through discussion, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Initial Responses:
{stage1_text}
{stage2_text}

STAGE 3 - Peer Rankings:
{stage3_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The collaborative discussion and refinements made
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

IMPORTANT: Keep your final answer to 2-3 paragraphs maximum. Be clear, concise, and well-reasoned.

Provide your final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [match.group() for m in numbered_matches if (match := re.search(r'Response [A-Z]', m)) is not None]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage3_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage3_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage3_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, List, Dict, Dict]:
    """
    Run the complete 4-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_results, stage4_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collaboration
    stage2_results = await stage2_collaboration(user_query, stage1_results, max_rounds=2)

    # Stage 3: Collect rankings
    stage3_results, label_to_model = await stage3_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage3_results, label_to_model)

    # Stage 4: Synthesize final answer
    stage4_result = await stage4_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        stage3_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_results, stage4_result, metadata
