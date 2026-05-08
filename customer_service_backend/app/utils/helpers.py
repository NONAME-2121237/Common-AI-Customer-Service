import json
import re
from typing import List, Dict, Any, Optional

def format_history(messages: List[Dict[str, Any]], limit: Optional[int] = None) -> str:
    if limit:
        messages = messages[-limit:]
    
    formatted = []
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        formatted.append(f"{role}: {content}")
    
    return '\n'.join(formatted)

def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    
    if text.startswith('{'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, text)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None

def sanitize_text(text: str) -> str:
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    return text

def truncate_text(text: str, max_length: int = 2000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'
