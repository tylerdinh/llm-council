"""Tool execution for council member interactions."""

import json
from typing import Dict, Any, List


class ToolExecutor:
    """Executes tools called by council members."""
    
    def __init__(self, message_queue: List):
        self.message_queue = message_queue
    
    def execute(self, member_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return result."""
        try:
            if tool_name == "send_message":
                return self._send_message(member_name, arguments)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
    
    def _send_message(self, from_member: str, args: Dict) -> str:
        """Send message to another council member."""
        to_member = args.get("to_member")
        message = args.get("message")
        
        if not all([to_member, message]):
            return json.dumps({"error": "Missing required fields: to_member, message"})
        
        msg = {
            "from": from_member,
            "to": to_member,
            "message": message
        }
        self.message_queue.append(msg)
        
        return json.dumps({
            "status": "sent",
            "from": from_member,
            "to": to_member
        })


# Tool definitions available to all council members
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a message to another council member to share insights or ask for their perspective",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_member": {
                        "type": "string",
                        "description": "Name of the council member to send message to (e.g., 'Alice', 'Bob', 'Charlie')"
                    },
                    "message": {
                        "type": "string",
                        "description": "The message content - share an insight, ask a question, or build on their response"
                    }
                },
                "required": ["to_member", "message"]
            }
        }
    }
]
