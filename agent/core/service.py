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

# Windows service imports
if sys.platform == 'win32':
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
else:
    # Mock classes for development on non-Windows
    class win32serviceutil:
        class ServiceFramework:
            pass
        @staticmethod
        def HandleCommandLine(cls): pass
        @staticmethod
        def InstallService(*args, **kwargs): pass
        @staticmethod
        def RemoveService(*args, **kwargs): pass
        @staticmethod
        def StartService(*args, **kwargs): pass
        @staticmethod
        def StopService(*args, **kwargs): pass
    
    class win32service:
        SERVICE_WIN32_OWN_PROCESS = 0x10
        SERVICE_AUTO_START = 2
        SERVICE_DEMAND_START = 3
        SERVICE_STOP_PENDING = 3
        SERVICE_STOPPED = 1
        SERVICE_RUNNING = 4
    
    class win32event:
        @staticmethod
        def CreateEvent(*args): return None
        @staticmethod
        def SetEvent(h): pass
        @staticmethod
        def WaitForSingleObject(h, t): return 0
        WAIT_OBJECT_0 = 0
    
    class servicemanager:
        @staticmethod
        def LogMsg(*args): pass
        @staticmethod
        def LogErrorMsg(msg): print(f"ERROR: {msg}")
        @staticmethod
        def LogInfoMsg(msg): print(f"INFO: {msg}")
        EVENTLOG_INFORMATION_TYPE = 4
        EVENTLOG_ERROR_TYPE = 1
        PYS_SERVICE_STARTED = 1
        PYS_SERVICE_STOPPED = 2


class EndpointSecurityService(win32serviceutil.ServiceFramework):
    """
    Windows Service implementation for Endpoint Security Agent.
    """
    
    _svc_name_ = "EndpointSecurityAgent"
    _svc_display_name_ = "Endpoint Security Agent"
    _svc_description_ = "Monitors and protects endpoint data, controls USB devices, and manages network access"
    
    def __init__(self, args):
        if sys.platform == 'win32':
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        else:
            self.stop_event = None
        
        self.is_running = False
        self.agent = None
    
    def SvcStop(self):
        """Handle service stop request."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        if sys.platform == 'win32':
            win32event.SetEvent(self.stop_event)
        
        self.is_running = False
        
        # Stop agent
        if self.agent:
            try:
                self.agent.stop()
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error stopping agent: {e}")
        
        servicemanager.LogInfoMsg("Endpoint Security Agent service stopped")
    
    def SvcDoRun(self):
        """Main service entry point."""
        project_root = str(Path(__file__).parent.parent.parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.is_running = True
        self.main()
    
    def main(self):
        """Main service loop."""
        try:
            project_root = str(Path(__file__).parent.parent.parent)
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from agent.main import EndpointSecurityAgent
            
            # Create and start agent
            self.agent = EndpointSecurityAgent()
            self.agent.start()
            
            servicemanager.LogInfoMsg("Endpoint Security Agent started successfully")
            
            # Wait for stop signal
            while self.is_running:
                if sys.platform == 'win32':
                    # Check for stop event
                    result = win32event.WaitForSingleObject(self.stop_event, 5000)
                    if result == win32event.WAIT_OBJECT_0:
                        break
                else:
                    time.sleep(5)
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {e}")
            raise


def set_service_recovery():
    """Configure service to restart automatically on failure."""
    if sys.platform != 'win32':
        return
        
    try:
        # Use 'sc' command to set failure recovery actions
        cmd = [
            "sc", "failure", "EndpointSecurityAgent",
            "reset=", "0",
            "actions=", "restart/1000/restart/1000/restart/1000"
        ]
        subprocess.run(cmd, check=True, capture_output=True, shell=True)
        print("Service recovery options configured (auto-restart enabled)")
    except Exception as e:
        print(f"Warning: Could not configure service recovery: {e}")


def configure_service_path():
    if sys.platform != 'win32':
        return
        
    try:
        import winreg
        project_root = str(Path(__file__).parent.parent.parent.absolute())
        svc_name = EndpointSecurityService._svc_name_
        
        param_key_path = f"SYSTEM\\CurrentControlSet\\Services\\{svc_name}\\Parameters"
        winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, param_key_path)
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, param_key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "PythonPath", 0, winreg.REG_SZ, project_root)
            
        svc_key_path = f"SYSTEM\\CurrentControlSet\\Services\\{svc_name}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, svc_key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "Environment", 0, winreg.REG_MULTI_SZ, [f"PYTHONPATH={project_root}"])
            
        print(f"Service Environment and Path configured: {project_root}")
    except Exception as e:
        print(f"Warning: Could not configure service Registry: {e}")


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
