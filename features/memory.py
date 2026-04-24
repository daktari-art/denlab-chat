"""
Hierarchical Memory System for DenLab Chat.
Three-tier memory: Working (current conversation), Episodic (past summaries), Semantic (extracted knowledge).
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from dataclasses import dataclass, field

# Import from centralized config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import MemoryConfig, Constants


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class MemoryEntry:
    """Single memory entry in working memory."""
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime
    importance: float = 0.5
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntry":
        return cls(
            content=data["content"],
            role=data["role"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            importance=data.get("importance", 0.5)
        )


@dataclass
class EpisodicEntry:
    """Summarized conversation episode."""
    summary: str
    timestamp: datetime
    message_count: int
    topics: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
            "message_count": self.message_count,
            "topics": self.topics
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EpisodicEntry":
        return cls(
            summary=data["summary"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_count=data["message_count"],
            topics=data.get("topics", [])
        )


# ============================================================================
# SIMPLE EMBEDDING (No external dependencies)
# ============================================================================

class SimpleEmbedding:
    """Simple embedding generator without external libraries."""
    
    @staticmethod
    def generate(text: str, dimensions: int = 64) -> List[float]:
        """Generate a simple deterministic embedding from text."""
        # Use hash-based embedding for reproducibility
        words = text.lower().split()
        vec = [0.0] * dimensions
        
        for i, word in enumerate(words[:200]):  # Limit to 200 words
            # Create hash for the word
            hash_val = hash(word + str(i)) % (dimensions * 100)
            idx = abs(hash_val) % dimensions
            vec[idx] += 1.0 / (len(words) + 1)
        
        # Normalize
        magnitude = sum(v * v for v in vec) ** 0.5
        if magnitude > 0:
            vec = [v / magnitude for v in vec]
        
        return vec
    
    @staticmethod
    def similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot / (mag1 * mag2)


# ============================================================================
# HIERARCHICAL MEMORY
# ============================================================================

class HierarchicalMemory:
    """
    Three-tier memory system:
    - Working: Current conversation (max 15 messages)
    - Episodic: Summarized past conversations (max 50 entries)
    - Semantic: Extracted knowledge key-value store
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.persist_dir = Path(MemoryConfig.MEMORY_DIR) / user_id
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory tiers
        self.working: List[MemoryEntry] = []
        self.episodic: List[EpisodicEntry] = []
        self.semantic: Dict[str, Any] = {}
        
        # Embedding utility
        self._embedder = SimpleEmbedding()
        
        # Load existing memory
        self._load()
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def add(self, content: str, role: str, importance: float = 0.5):
        """Add a message to working memory."""
        entry = MemoryEntry(
            content=content,
            role=role,
            timestamp=datetime.now(),
            importance=importance
        )
        self.working.append(entry)
        
        # Auto-consolidate when working memory is full
        if len(self.working) > MemoryConfig.MAX_WORKING_MESSAGES:
            self._consolidate()
        
        self._save()
    
    def retrieve_relevant(self, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant memories based on query."""
        results = []
        query_embed = self._embedder.generate(query)
        
        # 1. Working memory (highest priority - exact matches)
        for entry in reversed(self.working[-10:]):
            relevance = self._calculate_relevance(entry, query, query_embed)
            if relevance > 0.2:
                results.append({
                    "type": "working",
                    "role": entry.role,
                    "content": entry.content[:1000],
                    "timestamp": entry.timestamp.isoformat(),
                    "relevance": relevance
                })
        
        # 2. Episodic memory
        for ep in self.episodic[-10:]:
            # Check topic match
            topic_match = any(topic in query.lower() for topic in ep.topics)
            # Check content match
            content_match = any(word in ep.summary.lower() for word in query.lower().split()[:5])
            
            if topic_match or content_match:
                results.append({
                    "type": "episodic",
                    "content": ep.summary[:500],
                    "timestamp": ep.timestamp.isoformat(),
                    "topics": ep.topics,
                    "relevance": 0.6 if topic_match else 0.4
                })
        
        # 3. Semantic memory
        for key, value in list(self.semantic.items())[-20:]:
            if key in query.lower() or query.lower() in key:
                results.append({
                    "type": "semantic",
                    "key": key,
                    "content": str(value)[:500],
                    "relevance": 0.8
                })
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def get_context(self, query: str, max_tokens: int = 1000) -> str:
        """Get formatted context string for LLM."""
        memories = self.retrieve_relevant(query, limit=3)
        if not memories:
            return ""
        
        context_parts = ["## Relevant Conversation Memory\n"]
        
        for mem in memories:
            if mem["type"] == "working":
                context_parts.append(f"[Previous {mem['role']}]: {mem['content'][:300]}\n")
            elif mem["type"] == "episodic":
                context_parts.append(f"[Past Conversation]: {mem['content'][:300]}\n")
            elif mem["type"] == "semantic":
                context_parts.append(f"[Known Fact - {mem['key']}]: {mem['content'][:200]}\n")
        
        result = "\n".join(context_parts)
        
        # Truncate if too long
        if len(result) > max_tokens:
            result = result[:max_tokens] + "...\n[Memory truncated]"
        
        return result
    
    def store_knowledge(self, key: str, value: Any):
        """Store extracted knowledge in semantic memory."""
        self.semantic[key.lower()] = value
        self._prune_semantic()
        self._save()
    
    def get_knowledge(self, key: str) -> Optional[Any]:
        """Retrieve stored knowledge."""
        return self.semantic.get(key.lower())
    
    def clear_working(self):
        """Clear working memory (start fresh conversation)."""
        self.working = []
        self._save()
    
    def clear_all(self):
        """Clear all memory tiers."""
        self.working = []
        self.episodic = []
        self.semantic = {}
        self._save()
    
    def get_stats(self) -> Dict[str, int]:
        """Get memory statistics."""
        return {
            "working_messages": len(self.working),
            "episodic_entries": len(self.episodic),
            "semantic_facts": len(self.semantic)
        }
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _calculate_relevance(self, entry: MemoryEntry, query: str, query_embed: List[float]) -> float:
        """Calculate relevance score between memory entry and query."""
        score = 0.0
        
        # Exact word match (weight: 0.5)
        query_words = set(query.lower().split())
        entry_words = set(entry.content.lower().split())
        common = query_words.intersection(entry_words)
        if common:
            score += 0.3 * len(common) / max(len(query_words), 1)
        
        # Semantic similarity (weight: 0.4)
        if entry.embedding:
            sim = self._embedder.similarity(query_embed, entry.embedding)
            score += 0.4 * sim
        
        # Recency boost (weight: 0.1)
        age_hours = (datetime.now() - entry.timestamp).total_seconds() / 3600
        recency_boost = max(0, 1.0 - age_hours / 48)  # Fades over 48 hours
        score += 0.1 * recency_boost
        
        # Importance multiplier
        score *= (0.5 + entry.importance)
        
        return min(score, 1.0)
    
    def _consolidate(self):
        """Summarize working memory to episodic."""
        if len(self.working) < 5:
            return
        
        # Extract key points for summary
        points = []
        topics = set()
        
        for entry in self.working[-15:]:
            if entry.role == "user" and len(entry.content) > 30:
                points.append(f"• {entry.content[:200]}")
            
            # Extract potential topics
            words = entry.content.lower().split()
            for word in words:
                if len(word) > 4 and word not in Constants.AGENT_TYPES:
                    topics.add(word)
        
        summary = "\n".join(points[:5]) if points else "Conversation with no key points extracted"
        
        # Create episodic entry
        episodic = EpisodicEntry(
            summary=summary[:500],
            timestamp=datetime.now(),
            message_count=len(self.working),
            topics=list(topics)[:5]
        )
        
        self.episodic.append(episodic)
        
        # Prune episodic memory if too large
        if len(self.episodic) > MemoryConfig.MAX_EPISODIC_ENTRIES:
            self.episodic = self.episodic[-MemoryConfig.MAX_EPISODIC_ENTRIES:]
        
        # Keep only last 5 messages in working memory
        self.working = self.working[-5:]
    
    def _prune_semantic(self):
        """Prune semantic memory to reasonable size."""
        if len(self.semantic) > 200:
            # Remove oldest 50 entries (approximate - dict doesn't preserve order in older Python)
            keys = list(self.semantic.keys())
            for key in keys[:50]:
                del self.semantic[key]
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text."""
        return self._embedder.generate(text)
    
    # ========================================================================
    # Persistence
    # ========================================================================
    
    def _save(self):
        """Save memory to disk."""
        data = {
            "user_id": self.user_id,
            "working": [e.to_dict() for e in self.working],
            "episodic": [e.to_dict() for e in self.episodic],
            "semantic": self.semantic,
            "version": "2.0",
            "updated_at": datetime.now().isoformat()
        }
        
        try:
            with open(self.persist_dir / "memory.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving memory for {self.user_id}: {e}")
    
    def _load(self):
        """Load memory from disk."""
        memory_file = self.persist_dir / "memory.json"
        
        if not memory_file.exists():
            return
        
        try:
            with open(memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.working = [MemoryEntry.from_dict(e) for e in data.get("working", [])]
            self.episodic = [EpisodicEntry.from_dict(e) for e in data.get("episodic", [])]
            self.semantic = data.get("semantic", {})
            
        except Exception as e:
            print(f"Error loading memory for {self.user_id}: {e}")
            # Initialize fresh if corrupted
            self.working = []
            self.episodic = []
            self.semantic = {}


# ============================================================================
# MEMORY MANAGER (Singleton)
# ============================================================================

_memory_instances: Dict[str, HierarchicalMemory] = {}


def get_memory(user_id: str) -> HierarchicalMemory:
    """Get or create memory for a user."""
    if user_id not in _memory_instances:
        _memory_instances[user_id] = HierarchicalMemory(user_id)
    return _memory_instances[user_id]


def clear_memory(user_id: str):
    """Clear memory for a user."""
    if user_id in _memory_instances:
        _memory_instances[user_id].clear_all()
        del _memory_instances[user_id]


def get_all_memory_stats() -> Dict[str, Dict[str, int]]:
    """Get memory stats for all users."""
    return {uid: mem.get_stats() for uid, mem in _memory_instances.items()}