#!/usr/bin/env python3
import subprocess
import sys
import os

def run_command(cmd, description):
    print(f"[FIX] {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {description} failed:")
        print(result.stderr)
        return False
    print(f"[SUCCESS] {description} completed")
    return True

def main():
    print("[FIX] Fixing permissions and service configuration")
    
    # Stop service first
    run_command("sudo systemctl stop crystall-budget", "Stopping service")
    
    # Fix permissions on virtual environment
    run_command("chmod -R 755 venv/", "Setting venv permissions")
    run_command("chmod +x venv/bin/python", "Making Python executable")
    run_command("chmod +x app.py", "Making app.py executable")
    
    # Update systemd service with absolute paths and proper configuration
    user = os.getenv("USER", "root")
    working_dir = os.getcwd()
    
    service_content = f"""[Unit]
Description=CrystallBudget Flask API
After=network.target

[Service]
Type=simple
User={user}
Group={user}
WorkingDirectory={working_dir}
Environment=PATH={working_dir}/venv/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=-{working_dir}/.env
ExecStart={working_dir}/venv/bin/python {working_dir}/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    
    with open("crystall-budget.service", "w") as f:
        f.write(service_content)
    
    # Reinstall service
    run_command("sudo cp crystall-budget.service /etc/systemd/system/", "Installing updated service")
    run_command("sudo systemctl daemon-reload", "Reloading systemd")
    
    # Start service
    run_command("sudo systemctl start crystall-budget", "Starting service")
    run_command("sudo systemctl status crystall-budget --no-pager", "Checking service status")
    
    print("[FIX] Permissions and service configuration fixed!")

if __name__ == "__main__":
    main()