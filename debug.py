#!/usr/bin/env python3
import subprocess
import os

def run_command(cmd, description, show_output=True):
    print(f"[DEBUG] {description}")
    print(f"[CMD] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
    print(f"[RESULT] Exit code: {result.returncode}")
    print("-" * 50)
    return result.returncode == 0

def main():
    print("[DEBUG] Debugging service issues")
    
    # Check if service file exists
    print("[DEBUG] Checking service file...")
    if os.path.exists("crystall-budget.service"):
        with open("crystall-budget.service", "r") as f:
            print(f.read())
    else:
        print("Service file not found!")
    
    print("-" * 50)
    
    # Check systemctl commands directly
    run_command("sudo systemctl status crystall-budget", "Direct systemctl status")
    run_command("sudo journalctl -u crystall-budget -n 20", "Recent logs")
    run_command("ls -la venv/bin/python", "Check Python executable")
    run_command("ls -la app.py", "Check app.py")
    run_command("whoami", "Current user")
    run_command("pwd", "Current directory")

if __name__ == "__main__":
    main()