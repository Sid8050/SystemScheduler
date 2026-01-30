"""
Data Loss Prevention Guard

Prevents unauthorized file uploads by:
1. Blocking file picker dialogs (Open/Save dialogs)
2. Blocking drag & drop operations
3. Allowing only approved files through a secure gateway
"""

import os
import sys
import subprocess
import shutil
import time
import threading
from typing import List, Optional
from agent.core.logger import Logger
from agent.utils.registry import get_registry_manager

# Windows imports (conditional)
if sys.platform == 'win32':
    try:
        import win32gui
        import win32con
        import win32process
        import psutil
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False


class DataLossGuard:
    """
    Surgical DLP Guard that blocks file upload actions without blocking websites.
    """

    # File dialog class names to detect
    DIALOG_CLASSES = {
        "#32770",           # Standard Windows dialog
        "DirectUIHWND",     # Modern Windows dialogs
        "DUIViewWndClassName",
    }

    # File dialog title keywords
    DIALOG_TITLES = [
        "open", "save", "save as", "select file", "select files",
        "upload", "choose file", "open file", "attach", "browse",
        "file upload", "add files", "choose files", "select a file",
        "insert file", "attach file", "attach files"
    ]

    # Our own processes that should be allowed to use file dialogs
    WHITELISTED_PROCESSES = [
        "request_ui",           # Our upload request UI
        "endpoint security",    # Our agent
        "uploadrequest",
    ]

    def __init__(self, logger: Logger, block_all: bool = False, whitelist: List[str] = None):
        self.logger = logger
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        self._running = False
        self._thread = None
        self._win_thread = None
        self._registry_manager = get_registry_manager()
        self._approved_files = {}
        self._is_temporarily_unlocked = False
        self._unlock_expiry = 0
        self._gateway_dir = os.path.join(
            os.environ.get("Public", "C:\\Users\\Public"),
            "SecureUploadGateway"
        )
        self._blocked_count = 0
        self._our_pid = os.getpid()  # Our own process ID

    def _apply_upload_block(self, block: bool):
        """Apply or remove upload blocking via registry."""
        if not self._registry_manager:
            self.logger.warning("[DLP] No registry manager available")
            return False

        try:
            # Block = True means we want to PREVENT uploads (allowed=False)
            result = self._registry_manager.set_browser_upload_policy(allowed=not block)

            action = "BLOCKED" if block else "ALLOWED"
            self.logger.info(f"[DLP] File picker/upload is now {action}")

            # Force policy refresh
            if sys.platform == 'win32':
                try:
                    subprocess.run(['gpupdate', '/force'],
                                   capture_output=True, timeout=30,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass

            return result
        except Exception as e:
            self.logger.error(f"[DLP] Failed to apply upload block: {e}")
            return False

    def _is_file_dialog(self, hwnd) -> bool:
        """Check if a window handle is a file dialog that should be blocked."""
        if not HAS_WIN32:
            return False

        try:
            # Get window properties
            class_name = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd).lower()

            # Get the process that owns this window
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # NEVER block our own process's dialogs
            if pid == self._our_pid:
                return False

            # Check if it's one of our whitelisted processes
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name().lower()
                cmdline = ' '.join(proc.cmdline()).lower()

                # Skip our own tools
                for whitelist_term in self.WHITELISTED_PROCESSES:
                    if whitelist_term in proc_name or whitelist_term in cmdline:
                        return False

                # Skip if it's python running our scripts
                if 'python' in proc_name:
                    if 'request_ui' in cmdline or 'agent' in cmdline:
                        return False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Check class name
            if class_name in self.DIALOG_CLASSES:
                # #32770 can be many dialogs, check title too
                if class_name == "#32770":
                    # Must have a file-related title
                    if any(t in title for t in self.DIALOG_TITLES):
                        return True
                    # Or has typical file dialog child windows
                    def check_children(child_hwnd, found):
                        try:
                            child_class = win32gui.GetClassName(child_hwnd)
                            if child_class in ("SysListView32", "ComboBoxEx32", "ToolbarWindow32"):
                                found.append(True)
                        except:
                            pass
                        return True

                    found = []
                    try:
                        win32gui.EnumChildWindows(hwnd, check_children, found)
                    except:
                        pass
                    if len(found) >= 2:
                        return True
                else:
                    return True

            # Check title keywords for browser-owned windows
            if any(t in title for t in self.DIALOG_TITLES):
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name().lower()
                    browser_names = ['chrome', 'msedge', 'firefox', 'brave', 'opera', 'browser']
                    if any(b in proc_name for b in browser_names):
                        return True
                except:
                    pass

            return False
        except Exception:
            return False

    def _close_window(self, hwnd, title: str):
        """Close a window handle."""
        if not HAS_WIN32:
            return

        try:
            self._blocked_count += 1
            self.logger.warning(f"[DLP] BLOCKED file dialog #{self._blocked_count}: '{title}'")

            # Try multiple methods to close
            # Method 1: Post WM_CLOSE
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

            # Method 2: If still exists after small delay, try harder
            time.sleep(0.05)
            if win32gui.IsWindow(hwnd):
                # Send ESC key to cancel
                win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_ESCAPE, 0)
                win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_ESCAPE, 0)

        except Exception as e:
            self.logger.error(f"[DLP] Error closing window: {e}")

    def _window_monitor_loop(self):
        """Active window monitoring to close unauthorized file picker dialogs."""
        if not HAS_WIN32:
            self.logger.warning("[DLP] win32gui not available, window monitoring disabled")
            return

        self.logger.info("[DLP] Window monitor started")

        while self._running:
            try:
                # Check unlock expiry
                if self._is_temporarily_unlocked and time.time() > self._unlock_expiry:
                    self.logger.info("[DLP] Temporary unlock expired, relocking")
                    self._is_temporarily_unlocked = False
                    self._apply_upload_block(True)

                # Only block if enabled and not temporarily unlocked
                if self.block_all and not self._is_temporarily_unlocked:
                    dialogs_to_close = []

                    def enum_callback(hwnd, _):
                        if not win32gui.IsWindowVisible(hwnd):
                            return True
                        if self._is_file_dialog(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            dialogs_to_close.append((hwnd, title))
                        return True

                    try:
                        win32gui.EnumWindows(enum_callback, None)
                    except Exception:
                        pass

                    # Close all detected file dialogs
                    for hwnd, title in dialogs_to_close:
                        self._close_window(hwnd, title)

            except Exception as e:
                self.logger.error(f"[DLP] Window monitor error: {e}")

            # Check frequently for responsive blocking
            time.sleep(0.1)

    def _monitor_loop(self):
        """Background monitor thread for periodic tasks."""
        while self._running:
            try:
                # Log status periodically
                if self.block_all:
                    self.logger.debug(f"[DLP] Guard active - {self._blocked_count} dialogs blocked so far")
            except Exception:
                pass
            time.sleep(30)

    def start_guard(self):
        """Start the DLP monitoring."""
        if self._running:
            return

        self._running = True
        self.logger.info(f"[DLP] Starting guard - Block mode: {self.block_all}")

        # Apply initial policy
        if self.block_all:
            self._apply_upload_block(True)
            self.logger.warning("[DLP] Upload blocking is ENABLED - file pickers will be blocked")

        # Start background monitor
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        # Start window monitor on Windows
        if sys.platform == 'win32' and HAS_WIN32:
            self._win_thread = threading.Thread(target=self._window_monitor_loop, daemon=True)
            self._win_thread.start()
            self.logger.info("[DLP] Window monitor thread started")
        else:
            self.logger.warning("[DLP] Window monitoring not available on this platform")

        self.logger.info("[DLP] Guard started successfully")

    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration from dashboard."""
        old_block = self.block_all
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))

        self.logger.info(f"[DLP] Config update: Block={block_all} (was {old_block})")

        if old_block != self.block_all:
            self._apply_upload_block(self.block_all)
            if self.block_all:
                self.logger.warning("[DLP] Upload blocking ENABLED")
            else:
                self.logger.info("[DLP] Upload blocking DISABLED")

    def update_approvals(self, dashboard_url: str, api_key: str):
        """Sync approved file hashes from dashboard."""
        try:
            import httpx
            url = f"{dashboard_url}/api/v1/agent/uploads/approved"
            headers = {"X-API-Key": api_key}
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    hashes = data.get('approved_hashes', [])
                    self._approved_files = {h: True for h in hashes}
                    self.logger.info(f"[DLP] Synced {len(hashes)} approved file hashes")
        except Exception as e:
            self.logger.debug(f"[DLP] Could not sync approvals: {e}")

    def request_temporary_unlock(self, file_path: str, file_hash: str, duration_seconds: int = 45):
        """Temporarily allow a specific approved file to be uploaded."""
        if not self.block_all:
            return True

        if file_hash not in self._approved_files:
            self.logger.warning(f"[DLP] Unlock rejected: Hash not approved")
            return False

        try:
            # Prepare gateway folder
            if os.path.exists(self._gateway_dir):
                shutil.rmtree(self._gateway_dir)
            os.makedirs(self._gateway_dir, exist_ok=True)

            # Copy approved file
            file_name = os.path.basename(file_path)
            shutil.copy2(file_path, os.path.join(self._gateway_dir, file_name))

            # Unlock
            self._is_temporarily_unlocked = True
            self._unlock_expiry = time.time() + duration_seconds
            self._apply_upload_block(False)

            self.logger.warning(f"[DLP] Temporary unlock: {file_name} for {duration_seconds}s")
            return True

        except Exception as e:
            self.logger.error(f"[DLP] Failed to setup gateway: {e}")
            return False

    def stop(self):
        """Stop the DLP guard."""
        self._running = False

        # Re-enable uploads when stopping
        if self._registry_manager and self.block_all:
            self._apply_upload_block(False)

        if self._thread:
            self._thread.join(timeout=2)
        if self._win_thread:
            self._win_thread.join(timeout=2)

        self.logger.info(f"[DLP] Guard stopped - blocked {self._blocked_count} dialogs total")
