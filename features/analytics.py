# features/analytics.py
"""Usage analytics and insights dashboard."""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import streamlit as st

class Analytics:
    """Track and analyze tool usage."""
    
    def __init__(self, data_dir="data/analytics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, event_type: str, data: dict):
        """Log an event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        
        log_file = self.data_dir / f"{datetime.now().strftime('%Y%m')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_stats(self, days: int = 7) -> dict:
        """Get statistics for last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        events = []
        
        for log_file in self.data_dir.glob("*.jsonl"):
            with open(log_file) as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if datetime.fromisoformat(event["timestamp"]) > cutoff:
                            events.append(event)
                    except:
                        continue
        
        if not events:
            return {}
        
        # Tool usage stats
        tool_calls = [e for e in events if e.get("type") == "tool_call"]
        tool_stats = defaultdict(lambda: {"count": 0, "avg_duration": 0, "failures": 0})
        
        for tc in tool_calls:
            tool = tc.get("tool", "unknown")
            tool_stats[tool]["count"] += 1
            tool_stats[tool]["avg_duration"] += tc.get("duration_ms", 0)
            if not tc.get("success", True):
                tool_stats[tool]["failures"] += 1
        
        for tool in tool_stats:
            if tool_stats[tool]["count"] > 0:
                tool_stats[tool]["avg_duration"] /= tool_stats[tool]["count"]
                tool_stats[tool]["success_rate"] = 1 - (tool_stats[tool]["failures"] / tool_stats[tool]["count"])
        
        # Model usage
        model_usage = defaultdict(int)
        for e in events:
            if e.get("model"):
                model_usage[e["model"]] += 1
        
        return {
            "total_events": len(events),
            "tool_calls": len(tool_calls),
            "tool_stats": dict(tool_stats),
            "model_usage": dict(model_usage),
            "period_days": days
        }
    
    def render_dashboard(self):
        """Render analytics dashboard in Streamlit."""
        stats = self.get_stats(7)
        
        if not stats:
            st.info("No analytics data available yet. Start using the app to see stats.")
            return
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Events", stats["total_events"])
        with col2:
            st.metric("Tool Calls", stats["tool_calls"])
        with col3:
            st.metric("Period", f"{stats['period_days']} days")
        
        if stats["tool_stats"]:
            st.subheader("Tool Usage")
            tool_data = []
            for tool, data in stats["tool_stats"].items():
                tool_data.append({
                    "Tool": tool,
                    "Calls": data["count"],
                    "Avg Duration (ms)": int(data["avg_duration"]),
                    "Success Rate": f"{data['success_rate']:.1%}"
                })
            st.dataframe(pd.DataFrame(tool_data))
        
        if stats["model_usage"]:
            st.subheader("Model Usage")
            model_data = [{"Model": m, "Calls": c} for m, c in stats["model_usage"].items()]
            st.dataframe(pd.DataFrame(model_data))


_analytics = None

def get_analytics() -> Analytics:
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics
