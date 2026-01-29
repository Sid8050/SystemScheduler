import time
import uuid
import socket
import httpx
import argparse
from datetime import datetime

class MockAgent:
    def __init__(self, dashboard_url="http://localhost:8000/api/v1", hostname=None):
        self.dashboard_url = dashboard_url
        self.hostname = hostname or socket.gethostname()
        self.machine_id = str(uuid.uuid4())
        self.api_key = f"mock-key-{self.machine_id[:8]}"
        self.agent_version = "1.0.0-mock"
        self.os_version = "Linux Mock"
        self.ip_address = "127.0.0.1"
        self.running = False

    def register(self):
        print(f"[*] Registering mock agent {self.hostname} ({self.machine_id})...")
        payload = {
            "machine_id": self.machine_id,
            "hostname": self.hostname,
            "agent_version": self.agent_version,
            "os_version": self.os_version,
            "ip_address": self.ip_address
        }
        try:
            with httpx.Client() as client:
                response = client.post(f"{self.dashboard_url}/endpoints/register", json=payload)
                if response.status_code in (200, 201):
                    data = response.data if hasattr(response, 'data') else response.json()
                    self.api_key = data.get('api_key')
                    print(f"[+] Successfully registered! API Key: {self.api_key}")
                    return True
                else:
                    print(f"[-] Registration failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            print(f"[-] Error during registration: {e}")
            return False

    def send_heartbeat(self):
        print(f"[*] Sending heartbeat for {self.machine_id}...")
        payload = {
            "status": "online",
            "stats": {
                "files_backed_up": 10,
                "backup_size": 1024 * 1024 * 5,
                "usb_events": 0,
                "network_blocks": 2,
                "sensitive_data": 1
            }
        }
        headers = {"X-API-Key": self.api_key}
        try:
            with httpx.Client() as client:
                response = client.post(f"{self.dashboard_url}/agent/heartbeat", json=payload, headers=headers)
                if response.status_code == 200:
                    print(f"[+] Heartbeat success! Config: {response.json().get('config', {})}")
                else:
                    print(f"[-] Heartbeat failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[-] Error during heartbeat: {e}")

    def send_event(self, event_type="DLP_DETECTION", severity="info", message="Sensitive data found in mock scan"):
        print(f"[*] Sending event: {event_type} ({severity})...")
        payload = {
            "events": [{
                "event_type": event_type,
                "severity": severity,
                "message": message,
                "details": {"file": "/tmp/mock_sensitive.txt", "pattern": "SSN"},
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
        headers = {"X-API-Key": self.api_key}
        try:
            with httpx.Client() as client:
                response = client.post(f"{self.dashboard_url}/agent/events", json=payload, headers=headers)
                if response.status_code in (200, 201):
                    print(f"[+] Event sent successfully!")
                else:
                    print(f"[-] Event failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[-] Error sending event: {e}")

    def start(self, interval=30):
        if not self.register():
            return
        
        self.running = True
        print(f"[*] Mock Agent started. Sending heartbeat every {interval}s. Ctrl+C to stop.")
        
        # Send one initial event
        self.send_event()
        
        try:
            while self.running:
                self.send_heartbeat()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[*] Stopping mock agent...")
            self.running = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Endpoint Security Agent")
    parser.add_argument("--url", default="http://localhost:8000/api/v1", help="Dashboard API URL")
    parser.add_argument("--interval", type=int, default=30, help="Heartbeat interval in seconds")
    args = parser.parse_args()

    agent = MockAgent(dashboard_url=args.url)
    agent.start(interval=args.interval)
