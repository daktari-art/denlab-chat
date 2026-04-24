# features/memory.py
"""Hierarchical memory system with summarization and vector retrieval."""
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class MemoryEntry:
    content: str
    role: str
    timestamp: datetime
    importance: float = 0.5
    embedding: Optional[np.ndarray] = None

class HierarchicalMemory:
    """Three-tier memory: working, episodic, semantic."""
    
    def __init__(self, user_id: str, persist_dir: str = "data/memories"):
        self.user_id = user_id
        self.persist_dir = Path(persist_dir) / user_id
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.working: List[MemoryEntry] = []  # Current conversation
        self.episodic: List[Dict] = []  # Summarized past conversations
        self.semantic: Dict[str, Any] = {}  # Extracted knowledge
        
        self._load()
    
    def add(self, content: str, role: str, importance: float = 0.5):
        """Add to working memory."""
        entry = MemoryEntry(
            content=content,
            role=role,
            timestamp=datetime.now(),
            importance=importance
        )
        self.working.append(entry)
        self._save()
        
        # Auto-consolidate when working memory is full
        if len(self.working) > 15:
            self._consolidate()
    
    def _consolidate(self):
        """Summarize working memory to episodic."""
        if len(self.working) < 5:
            return
        
        # Extract key points
        summary = self._extract_key_points()
        
        self.episodic.append({
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(self.working),
            "topics": self._extract_topics()
        })
        
        # Keep only last 5 messages in working memory
        self.working = self.working[-5:]
        self._save()
    
    def _extract_key_points(self) -> str:
        """Extract key points from working memory."""
        points = []
        for entry in self.working[-10:]:
            if entry.role == "user" and len(entry.content) > 20:
                points.append(f"- {entry.content[:100]}")
        return "\n".join(points) if points else "No key points extracted"
    
    def _extract_topics(self) -> List[str]:
        """Simple topic extraction."""
        all_text = " ".join([e.content for e in self.working])
        words = all_text.lower().split()
        
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'to', 'for', 'of', 'in', 'on', 'at'}
        words = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Get most common words as topics
        from collections import Counter
        topics = [w for w, _ in Counter(words).most_common(5)]
        return topics
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant memories."""
        results = []
        query_lower = query.lower()
        
        # Working memory (highest priority)
        for entry in reversed(self.working[-5:]):
            if any(word in query_lower for word in entry.content.lower().split()[:5]):
                results.append({
                    "type": "working",
                    "content": entry.content[:500],
                    "role": entry.role,
                    "relevance": 0.9
                })
        
        # Episodic memory
        for ep in self.episodic[-5:]:
            if any(word in query_lower for word in ep["summary"].lower().split()[:10]):
                results.append({
                    "type": "episodic",
                    "content": ep["summary"],
                    "relevance": 0.7
                })
        
        # Semantic memory (keywords)
        for key, value in list(self.semantic.items())[-10:]:
            if key in query_lower:
                results.append({
                    "type": "semantic",
                    "content": str(value)[:500],
                    "relevance": 0.8
                })
        
        return sorted(results, key=lambda x: x["relevance"], reverse=True)[:limit]
    
    def store_knowledge(self, key: str, value: Any):
        """Store extracted knowledge in semantic memory."""
        self.semantic[key.lower()] = value
        self._save()
    
    def get_context(self, query: str, max_tokens: int = 1000) -> str:
        """Get context string for LLM."""
        memories = self.retrieve_relevant(query, limit=3)
        if not memories:
            return ""
        
        context_parts = ["## Relevant Memories\n"]
        for mem in memories:
            context_parts.append(f"[{mem['type'].upper()}] {mem['content']}\n")
        
        return "\n".join(context_parts)[:max_tokens]
    
    def clear_working(self):
        """Clear working memory for new session."""
        self.working = []
        self._save()
    
    def _save(self):
        """Save memory to disk."""
        data = {
            "working": [(e.content, e.role, e.timestamp.isoformat(), e.importance) for e in self.working],
            "episodic": self.episodic,
            "semantic": self.semantic
        }
        with open(self.persist_dir / "memory.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def _load(self):
        """Load memory from disk."""
        memory_file = self.persist_dir / "memory.json"
        if memory_file.exists():
            try:
                with open(memory_file) as f:
                    data = json.load(f)
                
                self.working = [
                    MemoryEntry(content=c, role=r, timestamp=datetime.fromisoformat(t), importance=imp)
                    for c, r, t, imp in data.get("working", [])
                ]
                self.episodic = data.get("episodic", [])
                self.semantic = data.get("semantic", {})
            except Exception:
                pass


# Memory manager singleton
_memory_instances: Dict[str, HierarchicalMemory] = {}

def get_memory(user_id: str) -> HierarchicalMemory:
    """Get or create memory for a user."""
    if user_id not in _memory_instances:
        _memory_instances[user_id] = HierarchicalMemory(user_id)
    return _memory_instances[user_id]
