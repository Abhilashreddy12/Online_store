"""
Memory Module
-------------
Handles conversation memory for the chatbot using LangChain memory components.
"""

import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Simple conversation memory that maintains context across messages.
    Stores last N turns of conversation per session.
    """
    
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._sessions: Dict[str, List[Dict]] = defaultdict(list)
        self._context: Dict[str, Dict] = defaultdict(dict)  # Store extracted context like filters, last products
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history"""
        message = {
            'role': role,
            'content': content,
            'metadata': metadata or {}
        }
        
        self._sessions[session_id].append(message)
        
        # Keep only last N turns (2 messages per turn = user + assistant)
        max_messages = self.max_turns * 2
        if len(self._sessions[session_id]) > max_messages:
            self._sessions[session_id] = self._sessions[session_id][-max_messages:]
    
    def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        return self._sessions.get(session_id, [])
    
    def get_formatted_history(self, session_id: str) -> str:
        """Get conversation history as formatted string for LLM context"""
        history = self.get_history(session_id)
        if not history:
            return ""
        
        formatted = []
        for msg in history[-6:]:  # Last 3 turns
            role = "Customer" if msg['role'] == 'user' else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)
    
    def set_context(self, session_id: str, key: str, value: Any):
        """Store context data for a session (e.g., last search filters, product IDs)"""
        self._context[session_id][key] = value
    
    def get_context(self, session_id: str, key: str, default: Any = None) -> Any:
        """Get context data for a session"""
        return self._context[session_id].get(key, default)
    
    def update_context(self, session_id: str, updates: Dict):
        """Update multiple context values"""
        self._context[session_id].update(updates)
    
    def get_all_context(self, session_id: str) -> Dict:
        """Get all context for a session"""
        return dict(self._context.get(session_id, {}))
    
    def clear_session(self, session_id: str):
        """Clear conversation history and context for a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._context:
            del self._context[session_id]
    
    def get_last_products(self, session_id: str) -> List[int]:
        """Get the last shown product IDs"""
        return self.get_context(session_id, 'last_products', [])
    
    def set_last_products(self, session_id: str, product_ids: List[int]):
        """Store the last shown product IDs"""
        self.set_context(session_id, 'last_products', product_ids)
    
    def get_last_filters(self, session_id: str) -> Dict:
        """Get the last used search filters"""
        return self.get_context(session_id, 'last_filters', {})
    
    def set_last_filters(self, session_id: str, filters: Dict):
        """Store the last used search filters"""
        self.set_context(session_id, 'last_filters', filters)


# Global memory instance
_memory = None


def get_memory() -> ConversationMemory:
    """Get the global conversation memory instance"""
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory


def get_langchain_memory(session_id: str):
    """
    Get conversation history as langchain_core messages.
    """
    try:
        from langchain_core.messages import HumanMessage, AIMessage

        messages = []
        existing = get_memory().get_history(session_id)
        for msg in existing[-10:]:
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            else:
                messages.append(AIMessage(content=msg['content']))
        return messages
    except ImportError:
        logger.warning("langchain_core not installed")
        return []
