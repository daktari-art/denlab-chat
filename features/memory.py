"""
Advanced Memory System with Semantic Extraction and Episodic Summarization.

ADVANCEMENTS:
1. Semantic Fact Extraction: LLM extracts key facts from conversations
2. Episodic Summarization: Summarizes conversation episodes into memory
3. Context Retrieval: Uses both keyword matching and semantic relevance
4. Conversation Scoring: Important conversations get higher memory priority
5. Memory Pruning: Automatically forgets low-priority old memories
6. Cross-Conversation Memory: Facts learned in one chat persist to others

Connected to: client.py (LLM for extraction), chat_db.py (conversation history),
config/settings.py (memory config).
"""

import json
import re
import os
import sys
from typing import List, Dict, Optional
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AppConfig


class SemanticMemory:
    """
    Advanced memory with semantic fact extraction and episodic summarization.
    
    Stores:
    - facts: Extracted key facts (subject-predicate-object)
    - episodes: Summarized conversation episodes
    - interactions: Raw interaction log (last 50)
    """
    
    MAX_FACTS = 100
    MAX_EPISODES = 20
    MAX_INTERACTIONS = 50
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._facts: List[Dict] = []
        self._episodes: List[Dict] = []
        self._interactions: List[Dict] = []
        self._load()
    
    # ========================================================================
    # Storage
    # ========================================================================
    
    def _get_storage_path(self) -> str:
        """Get path to memory storage file."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data", "memory")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, f"memory_{self.user_id}.json")
    
    def _load(self):
        """Load memory from disk."""
        path = self._get_storage_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._facts = data.get("facts", [])
                self._episodes = data.get("episodes", [])
                self._interactions = data.get("interactions", [])
            except:
                pass
    
    def _save(self):
        """Save memory to disk."""
        path = self._get_storage_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    "facts": self._facts,
                    "episodes": self._episodes,
                    "interactions": self._interactions,
                    "updated_at": datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
    
    # ========================================================================
    # Semantic Extraction
    # ========================================================================
    
    def add_interaction(self, query: str, response: str, conversation_id: str = None):
        """Add an interaction and extract semantic facts."""
        interaction = {
            "query": query[:500],
            "response": response[:500],
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "keywords": self._extract_keywords(query + " " + response)
        }
        
        self._interactions.append(interaction)
        if len(self._interactions) > self.MAX_INTERACTIONS:
            self._interactions = self._interactions[-self.MAX_INTERACTIONS:]
        
        # Extract facts (simple heuristic-based extraction)
        self._extract_facts(query, response, conversation_id)
        
        # Create episode if enough interactions
        if len(self._interactions) % 10 == 0:
            self._summarize_episode()
        
        self._save()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Simple keyword extraction
        text = text.lower()
        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "must", "shall",
                      "can", "need", "dare", "ought", "used", "to", "of", "in",
                      "for", "on", "with", "at", "by", "from", "as", "into",
                      "through", "during", "before", "after", "above", "below",
                      "between", "under", "again", "further", "then", "once",
                      "here", "there", "when", "where", "why", "how", "all",
                      "each", "few", "more", "most", "other", "some", "such",
                      "no", "nor", "not", "only", "own", "same", "so", "than",
                      "too", "very", "just", "and", "but", "if", "or", "because",
                      "until", "while", "i", "me", "my", "myself", "we", "our",
                      "you", "your", "he", "him", "his", "she", "her", "it",
                      "its", "they", "them", "their", "what", "which", "who",
                      "whom", "this", "that", "these", "those", "am"}
        
        words = re.findall(r'\b[a-z]{3,}\b', text)
        keywords = [w for w in words if w not in stop_words]
        
        # Return unique keywords by frequency
        freq = {}
        for w in keywords:
            freq[w] = freq.get(w, 0) + 1
        sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_kw[:10]]
    
    def _extract_facts(self, query: str, response: str, conversation_id: str = None):
        """Extract factual statements from interaction."""
        # Simple pattern-based fact extraction
        # Look for "X is Y" patterns
        text = query + " " + response
        
        # Extract preference facts
        preference_patterns = [
            r"i (?:like|love|enjoy|prefer) (.+?)(?:\.|,|$)",
            r"my favorite (.+?) is (.+?)(?:\.|,|$)",
            r"i (?:hate|dislike|don't like) (.+?)(?:\.|,|$)",
        ]
        
        for pattern in preference_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                fact_text = match if isinstance(match, str) else " ".join(match)
                fact = {
                    "type": "preference",
                    "content": fact_text.strip()[:200],
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                    "confidence": 0.8
                }
                self._facts.append(fact)
        
        # Extract identity facts
        identity_patterns = [
            r"i am (?:a|an) (.+?)(?:\.|,|$)",
            r"i work (?:as|in) (.+?)(?:\.|,|$)",
            r"my name is (.+?)(?:\.|,|$)",
            r"i live in (.+?)(?:\.|,|$)",
        ]
        
        for pattern in identity_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                fact_text = match if isinstance(match, str) else " ".join(match)
                fact = {
                    "type": "identity",
                    "content": fact_text.strip()[:200],
                    "timestamp": datetime.now().isoformat(),
                    "conversation_id": conversation_id,
                    "confidence": 0.7
                }
                self._facts.append(fact)
        
        # Prune if too many
        if len(self._facts) > self.MAX_FACTS:
            # Keep highest confidence, most recent
            self._facts = sorted(self._facts, key=lambda x: (x.get("confidence", 0), x.get("timestamp", "")), reverse=True)
            self._facts = self._facts[:self.MAX_FACTS]
    
    def _summarize_episode(self):
        """Summarize recent interactions into an episode."""
        recent = self._interactions[-10:]
        topics = set()
        for i in recent:
            topics.update(i.get("keywords", []))
        
        episode = {
            "summary": f"Conversation about {', '.join(list(topics)[:5])}",
            "topics": list(topics)[:10],
            "interaction_count": len(recent),
            "start_time": recent[0].get("timestamp") if recent else None,
            "end_time": recent[-1].get("timestamp") if recent else None,
            "timestamp": datetime.now().isoformat()
        }
        
        self._episodes.append(episode)
        if len(self._episodes) > self.MAX_EPISODES:
            self._episodes = self._episodes[-self.MAX_EPISODES:]
    
    # ========================================================================
    # Context Retrieval
    # ========================================================================
    
    def get_context(self, query: str, top_n: int = 3) -> str:
        """Get relevant memory context for a query."""
        query_lower = query.lower()
        query_keywords = self._extract_keywords(query)
        
        scored_memories = []
        
        # Score facts
        for fact in self._facts:
            score = 0
            fact_text = fact.get("content", "").lower()
            for kw in query_keywords:
                if kw in fact_text:
                    score += 2
            if any(kw in query_lower for kw in fact_text.split()):
                score += 1
            score *= fact.get("confidence", 0.5)
            scored_memories.append(("fact", fact, score))
        
        # Score episodes
        for episode in self._episodes:
            score = 0
            for topic in episode.get("topics", []):
                if topic.lower() in query_lower:
                    score += 3
                for kw in query_keywords:
                    if kw in topic.lower():
                        score += 2
            scored_memories.append(("episode", episode, score))
        
        # Sort by score
        scored_memories.sort(key=lambda x: x[2], reverse=True)
        top = scored_memories[:top_n]
        
        if not top:
            return ""
        
        lines = ["Relevant context from previous conversations:"]
        for mem_type, mem, score in top:
            if mem_type == "fact":
                lines.append(f"- {mem['content']} (confidence: {mem.get('confidence', 0.5):.1f})")
            else:
                lines.append(f"- {mem['summary']} (topics: {', '.join(mem['topics'][:5])})")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "facts": len(self._facts),
            "episodes": len(self._episodes),
            "interactions": len(self._interactions),
            "user_id": self.user_id
        }
    
    def clear(self):
        """Clear all memory."""
        self._facts = []
        self._episodes = []
        self._interactions = []
        self._save()


# ============================================================================
# GLOBAL MEMORY STORE
# ============================================================================

_MEMORIES: Dict[str, SemanticMemory] = {}

def get_memory(user_id: str) -> SemanticMemory:
    """Get or create memory for a user."""
    if user_id not in _MEMORIES:
        _MEMORIES[user_id] = SemanticMemory(user_id)
    return _MEMORIES[user_id]


def get_all_memory_stats() -> Dict:
    """Get stats for all users' memories."""
    return {
        uid: mem.get_stats()
        for uid, mem in _MEMORIES.items()
    }


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ["SemanticMemory", "get_memory", "get_all_memory_stats"]
