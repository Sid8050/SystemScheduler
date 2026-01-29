import time
import subprocess
import sys
import os
from pathlib import Path

def is_service_running(service_name="EndpointSecurityAgent"):
    try:
        output = subprocess.check_output(f'sc query "{service_name}"', shell=True).decode()
        return "RUNNING" in output
    except Exception:
        return False

def start_service(service_name="EndpointSecurityAgent"):
    try:
        subprocess.run(f'sc start "{service_name}"', shell=True, check=True)
        return True
    except Exception:
        return False

def guardian_loop():
    """Monitor the main service and ensure it stays running."""
    service_name = "EndpointSecurityAgent"
    
    while True:
        try:
            if not is_service_running(service_name):
                start_service(service_name)
        except Exception:
            pass
        # Check every 10 seconds
        time.sleep(10)

if __name__ == "__main__":
    # Run as a detached background process
    if os.name == 'nt':
        guardian_loop()
