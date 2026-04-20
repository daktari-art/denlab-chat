"""Sandboxed code execution."""
import subprocess
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Any

class CodeExecutor:
    """Execute Python code safely."""
    
    ALLOWED_MODULES = {
        'math', 'random', 'datetime', 'json', 're', 'statistics',
        'itertools', 'collections', 'functools', 'typing', 'string',
        'hashlib', 'base64', 'urllib.parse'
    }
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
    
    def execute(self, code: str) -> Dict[str, Any]:
        """Execute code in sandbox."""
        # Security check
        if not self._security_check(code):
            return {"error": "Security violation: disallowed import or dangerous syntax"}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "script.py"
            script.write_text(code)
            
            try:
                result = subprocess.run(
                    ["python3", str(script)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmpdir
                )
                
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "success": result.returncode == 0
                }
            except subprocess.TimeoutExpired:
                return {"error": f"Execution timed out after {self.timeout}s"}
            except Exception as e:
                return {"error": str(e)}
    
    def _security_check(self, code: str) -> bool:
        """Basic security validation."""
        import ast
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base = alias.name.split('.')[0]
                        if base not in self.ALLOWED_MODULES:
                            return False
                elif isinstance(node, ast.ImportFrom):
                    base = (node.module or '').split('.')[0]
                    if base not in self.ALLOWED_MODULES:
                        return False
                elif isinstance(node, ast.Call):
                    # Check for dangerous builtins
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec', 'compile', '__import__']:
                            return False
            return True
        except SyntaxError:
            return False

_executor = CodeExecutor()

def execute_code(code: str) -> str:
    """Execute Python code and return results."""
    result = _executor.execute(code)
    return json.dumps(result, indent=2)
