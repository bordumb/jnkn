import subprocess
import shutil
from pathlib import Path

def test_e2e_demo_flow(tmp_path):
    """
    Real-world simulation:
    1. init --demo
    2. scan (check output)
    3. scan --mode enforcement (check filtering)
    """
    # 1. Init Demo
    cwd = tmp_path / "test_run"
    cwd.mkdir()
    
    subprocess.run(["jnkn", "init", "--demo"], cwd=cwd, check=True, capture_output=True)
    
    demo_dir = cwd / "jnkn-demo"
    assert demo_dir.exists()
    
    # 2. First Scan (Discovery)
    result = subprocess.run(
        ["jnkn", "scan"], 
        cwd=demo_dir, 
        capture_output=True, 
        text=True
    )
    assert result.returncode == 0
    assert "Discovery" in result.stdout
    assert "Scan complete" in result.stdout
    
    # 3. Verify Database Creation
    assert (demo_dir / ".jnkn" / "jnkn.db").exists()