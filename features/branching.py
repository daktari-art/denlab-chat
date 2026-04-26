# features/branching.py
"""Allow branching conversations from any point."""
import json
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class ConversationBranch:
    """A branch point in a conversation."""
    
    def __init__(self, branch_id: str, name: str, parent_conv_id: str, branch_point_msg_id: str):
        self.id = branch_id
        self.name = name
        self.parent_conv_id = parent_conv_id
        self.branch_point_msg_id = branch_point_msg_id
        self.created_at = datetime.now()
        self.messages: List[Dict] = []

class BranchManager:
    """Manage conversation branching."""
    
    def __init__(self, data_dir: str = "data/branches"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.branches: Dict[str, ConversationBranch] = {}
        self._load()
    
    def create_branch(self, parent_conv_id: str, branch_point_msg_id: str, 
                      name: str, messages_up_to: List[Dict]) -> str:
        """Create a new branch from a message."""
        branch_id = str(uuid.uuid4())[:8]
        
        branch = ConversationBranch(
            branch_id=branch_id,
            name=name,
            parent_conv_id=parent_conv_id,
            branch_point_msg_id=branch_point_msg_id
        )
        branch.messages = messages_up_to.copy()
        
        self.branches[branch_id] = branch
        self._save()
        
        return branch_id
    
    def add_message(self, branch_id: str, message: Dict):
        """Add a message to a branch."""
        if branch_id in self.branches:
            self.branches[branch_id].messages.append(message)
            self._save()
    
    def get_branch(self, branch_id: str) -> Optional[ConversationBranch]:
        """Get a branch by ID."""
        return self.branches.get(branch_id)
    
    def get_branches_for_conv(self, conv_id: str) -> List[ConversationBranch]:
        """Get all branches from a conversation."""
        return [b for b in self.branches.values() if b.parent_conv_id == conv_id]
    
    def delete_branch(self, branch_id: str):
        """Delete a branch."""
        if branch_id in self.branches:
            del self.branches[branch_id]
            self._save()
    
    def _save(self):
        """Save branches to disk."""
        data = {}
        for bid, branch in self.branches.items():
            data[bid] = {
                "id": branch.id,
                "name": branch.name,
                "parent_conv_id": branch.parent_conv_id,
                "branch_point_msg_id": branch.branch_point_msg_id,
                "created_at": branch.created_at.isoformat(),
                "messages": branch.messages
            }
        with open(self.data_dir / "branches.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def _load(self):
        """Load branches from disk."""
        branch_file = self.data_dir / "branches.json"
        if branch_file.exists():
            try:
                with open(branch_file) as f:
                    data = json.load(f)
                    for bid, entry in data.items():
                        branch = ConversationBranch(
                            branch_id=entry["id"],
                            name=entry["name"],
                            parent_conv_id=entry["parent_conv_id"],
                            branch_point_msg_id=entry["branch_point_msg_id"]
                        )
                        branch.created_at = datetime.fromisoformat(entry["created_at"])
                        branch.messages = entry["messages"]
                        self.branches[bid] = branch
            except Exception:
                pass


# Singleton
_branch_manager = None

def get_branch_manager() -> BranchManager:
    global _branch_manager
    if _branch_manager is None:
        _branch_manager = BranchManager()
    return _branch_manager
