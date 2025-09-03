#!/usr/bin/env python3
import subprocess
import sys
import os

def run_command(cmd, description):
    print(f"[MANAGE] {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {description} failed:")
        print(result.stderr)
        return False
    print(f"[SUCCESS] {description} completed")
    if result.stdout.strip():
        print(result.stdout)
    return True

def start_service():
    print("[MANAGE] Starting CrystallBudget service...")
    if run_command("sudo systemctl start crystall-budget", "Starting service"):
        run_command("sudo systemctl status crystall-budget --no-pager", "Service status")

def stop_service():
    print("[MANAGE] Stopping CrystallBudget service...")
    run_command("sudo systemctl stop crystall-budget", "Stopping service")

def restart_service():
    print("[MANAGE] Restarting CrystallBudget service...")
    if run_command("sudo systemctl restart crystall-budget", "Restarting service"):
        run_command("sudo systemctl status crystall-budget --no-pager", "Service status")

def status_service():
    print("[MANAGE] Checking service status...")
    run_command("sudo systemctl status crystall-budget --no-pager", "Service status")

def logs_service():
    print("[MANAGE] Showing service logs...")
    run_command("sudo journalctl -u crystall-budget -n 50", "Recent logs")

def logs_follow():
    print("[MANAGE] Following service logs (Ctrl+C to stop)...")
    subprocess.run("sudo journalctl -u crystall-budget -f", shell=True)

def dev_start():
    print("[MANAGE] Starting development server...")
    if not os.path.exists("venv"):
        print("[ERROR] Virtual environment not found. Run ./deploy.py first.")
        sys.exit(1)
    
    if not os.path.exists(".env"):
        print("[ERROR] .env file not found. Run ./deploy.py first.")
        sys.exit(1)
    
    print("[INFO] Starting Flask development server on http://127.0.0.1:4000")
    subprocess.run("./venv/bin/python app.py", shell=True)

def show_help():
    print("CrystallBudget Management Script")
    print("Usage: ./manage.py [command]")
    print()
    print("Commands:")
    print("  start     - Start the service")
    print("  stop      - Stop the service")
    print("  restart   - Restart the service")
    print("  status    - Show service status")
    print("  logs      - Show recent logs")
    print("  follow    - Follow logs in real-time")
    print("  dev       - Start development server")
    print("  help      - Show this help")

def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        start_service()
    elif command == "stop":
        stop_service()
    elif command == "restart":
        restart_service()
    elif command == "status":
        status_service()
    elif command == "logs":
        logs_service()
    elif command == "follow":
        logs_follow()
    elif command == "dev":
        dev_start()
    elif command == "help":
        show_help()
    else:
        print(f"[ERROR] Unknown command: {command}")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()