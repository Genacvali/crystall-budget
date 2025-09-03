#!/usr/bin/env python3
import os
import subprocess
import sys

def run_command(cmd, description):
    print(f"[DEPLOY] {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {description} failed:")
        print(result.stderr)
        sys.exit(1)
    print(f"[SUCCESS] {description} completed")

def main():
    print("[DEPLOY] Starting CrystallBudget deployment")
    
    # Check if virtual environment exists
    if not os.path.exists("venv"):
        print("[DEPLOY] Creating virtual environment...")
        run_command("python3 -m venv venv", "Virtual environment creation")
    
    # Activate virtual environment and install dependencies
    run_command("./venv/bin/pip install -r requirements.txt", "Installing Python dependencies")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("[DEPLOY] Creating .env file from template...")
        run_command("cp .env.example .env", "Creating environment file")
        print("[WARNING] Please edit .env file with your database credentials and JWT secret")
    
    # Create systemd service
    service_content = """[Unit]
Description=CrystallBudget Flask API
After=network.target

[Service]
Type=simple
User={}
WorkingDirectory={}
Environment=PATH={}:$PATH
ExecStart={} app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
""".format(
        os.getenv("USER"),
        os.getcwd(),
        os.path.join(os.getcwd(), "venv/bin"),
        os.path.join(os.getcwd(), "venv/bin/python")
    )
    
    with open("crystall-budget.service", "w") as f:
        f.write(service_content)
    
    print("[DEPLOY] Created systemd service file")
    
    # Install systemd service
    run_command("sudo cp crystall-budget.service /etc/systemd/system/", "Installing systemd service")
    run_command("sudo systemctl daemon-reload", "Reloading systemd")
    run_command("sudo systemctl enable crystall-budget", "Enabling service")
    
    print("[DEPLOY] Deployment completed successfully!")
    print("[INFO] Service commands:")
    print("  Start: sudo systemctl start crystall-budget")
    print("  Stop:  sudo systemctl stop crystall-budget")
    print("  Status: sudo systemctl status crystall-budget")
    print("  Logs: sudo journalctl -u crystall-budget -f")

if __name__ == "__main__":
    main()