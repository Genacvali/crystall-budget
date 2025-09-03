#!/usr/bin/env python3
import subprocess
import os

def run_command(cmd, description):
    print(f"[FIX] {description}...")
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0

def main():
    print("[FIX] Final fix for service")
    
    # Stop service
    run_command("sudo systemctl stop crystall-budget", "Stopping service")
    
    # Check if venv exists and recreate if needed
    if os.path.exists("venv"):
        print("[FIX] Removing old venv...")
        run_command("rm -rf venv", "Removing old venv")
    
    # Create fresh venv
    run_command("python3 -m venv venv", "Creating new venv")
    
    # Install requirements
    run_command("./venv/bin/pip install -r requirements.txt", "Installing requirements")
    
    # Check what we have
    print("[CHECK] Checking files:")
    run_command("ls -la venv/bin/python*", "Python executables")
    run_command("ls -la app.py", "App file")
    
    # Try to run app manually first
    print("[TEST] Testing app manually:")
    run_command("./venv/bin/python app.py &", "Testing app")
    run_command("sleep 2 && pkill -f app.py", "Stopping test")
    
    # Create simple systemd service
    service_content = f"""[Unit]
Description=CrystallBudget Flask API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={os.getcwd()}
ExecStart=/bin/bash -c 'cd {os.getcwd()} && ./venv/bin/python app.py'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    
    with open("crystall-budget.service", "w") as f:
        f.write(service_content)
    
    # Install service
    run_command("sudo cp crystall-budget.service /etc/systemd/system/", "Installing service")
    run_command("sudo systemctl daemon-reload", "Reloading systemd")
    run_command("sudo systemctl enable crystall-budget", "Enabling service")
    run_command("sudo systemctl start crystall-budget", "Starting service")
    
    # Check status
    print("[FINAL] Checking final status:")
    run_command("sleep 3 && sudo systemctl status crystall-budget", "Final status check")

if __name__ == "__main__":
    main()