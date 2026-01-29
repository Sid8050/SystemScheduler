"""
Windows Service Wrapper for Endpoint Security Agent

Allows the agent to run as a Windows service that:
- Starts automatically at boot
- Runs in the background
- Survives user logoff
- Restarts on failure
"""

import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional

# ... (rest of imports)

def set_service_recovery():
    if sys.platform != 'win32':
        return
        
    try:
        cmd = [
            "sc", "failure", "EndpointSecurityAgent",
            "reset=", "0",
            "actions=", "restart/1000/restart/1000/restart/1000"
        ]
        subprocess.run(cmd, check=True, capture_output=True, shell=True)
        print("Service recovery options configured (auto-restart enabled)")
    except Exception as e:
        print(f"Warning: Could not configure service recovery: {e}")


def install_service():
    """Install the Windows service."""
    if sys.platform != 'win32':
        print("Service installation only available on Windows")
        return False
    
    try:
        win32serviceutil.InstallService(
            None,
            EndpointSecurityService._svc_name_,
            EndpointSecurityService._svc_display_name_,
            startType=win32service.SERVICE_AUTO_START,
            description=EndpointSecurityService._svc_description_
        )
        
        set_service_recovery()
        
        print(f"Service '{EndpointSecurityService._svc_display_name_}' installed successfully")
        return True
        
    except Exception as e:
        print(f"Failed to install service: {e}")
        return False


    
    try:
        # Get the path to this script
        module_path = Path(__file__).parent.parent / "main.py"
        
        win32serviceutil.InstallService(
            None,  # Use default class
            EndpointSecurityService._svc_name_,
            EndpointSecurityService._svc_display_name_,
            startType=win32service.SERVICE_AUTO_START,
            description=EndpointSecurityService._svc_description_
        )
        
        print(f"Service '{EndpointSecurityService._svc_display_name_}' installed successfully")
        return True
        
    except Exception as e:
        print(f"Failed to install service: {e}")
        return False


def uninstall_service():
    """Uninstall the Windows service."""
    if sys.platform != 'win32':
        print("Service uninstallation only available on Windows")
        return False
    
    try:
        # Stop service first if running
        try:
            win32serviceutil.StopService(EndpointSecurityService._svc_name_)
        except Exception:
            pass  # Service might not be running
        
        win32serviceutil.RemoveService(EndpointSecurityService._svc_name_)
        print(f"Service '{EndpointSecurityService._svc_display_name_}' uninstalled successfully")
        return True
        
    except Exception as e:
        print(f"Failed to uninstall service: {e}")
        return False


def start_service():
    """Start the Windows service."""
    if sys.platform != 'win32':
        print("Service control only available on Windows")
        return False
    
    try:
        win32serviceutil.StartService(EndpointSecurityService._svc_name_)
        print(f"Service '{EndpointSecurityService._svc_display_name_}' started")
        return True
    except Exception as e:
        print(f"Failed to start service: {e}")
        return False


def stop_service():
    """Stop the Windows service."""
    if sys.platform != 'win32':
        print("Service control only available on Windows")
        return False
    
    try:
        win32serviceutil.StopService(EndpointSecurityService._svc_name_)
        print(f"Service '{EndpointSecurityService._svc_display_name_}' stopped")
        return True
    except Exception as e:
        print(f"Failed to stop service: {e}")
        return False


def get_service_status() -> str:
    """Get current service status."""
    if sys.platform != 'win32':
        return "unknown"
    
    try:
        import win32service
        
        scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        service = win32service.OpenService(scm, EndpointSecurityService._svc_name_, win32service.SERVICE_QUERY_STATUS)
        status = win32service.QueryServiceStatus(service)
        
        win32service.CloseServiceHandle(service)
        win32service.CloseServiceHandle(scm)
        
        state = status[1]
        states = {
            1: "stopped",
            2: "start_pending",
            3: "stop_pending",
            4: "running",
            5: "continue_pending",
            6: "pause_pending",
            7: "paused"
        }
        
        return states.get(state, "unknown")
        
    except Exception:
        return "not_installed"


if __name__ == '__main__':
    if sys.platform == 'win32':
        win32serviceutil.HandleCommandLine(EndpointSecurityService)
    else:
        print("Windows service management only available on Windows")
