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
import psutil
import httpx
from typing import List, Set, Optional
from datetime import datetime
from agent.core.logger import Logger
from agent.utils.registry import get_registry_manager, RegistryHive, RegistryValueType


class DataLossGuard:
    """
    Surgical DLP Guard that blocks file upload actions without blocking websites.
    """

    def __init__(self, logger: Logger, block_all: bool = False, whitelist: List[str] = None):
        self.logger = logger
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))
        self._running = False
        self._thread = None
        self._win_thread = None
        self._registry_manager = get_registry_manager()
        self._approved_files = {}  # file_hash -> {path, name, expires_at}
        self._is_temporarily_unlocked = False
        self._unlock_expiry = 0
        self._gateway_dir = os.path.join(
            os.environ.get("Public", "C:\\Users\\Public"),
            "SecureUploadGateway"
        )

    def _sync_approved_hashes(self, dashboard_url: str, api_key: str):
        """Fetch approved file hashes from dashboard."""
        try:
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
            self.logger.error(f"[DLP] Failed to sync approvals: {e}")

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

            # Notify shell of the change
            try:
                import ctypes
                ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
            except Exception:
                pass

            return result
        except Exception as e:
            self.logger.error(f"[DLP] Failed to apply upload block: {e}")
            return False

    def _check_unlock_state(self):
        """Check if temporary unlock has expired and cleanup."""
        if self._is_temporarily_unlocked and time.time() > self._unlock_expiry:
            self.logger.info("[DLP] Gateway expired: Relocking system")
            self._is_temporarily_unlocked = False

            # Cleanup gateway folder
            try:
                if os.path.exists(self._gateway_dir):
                    shutil.rmtree(self._gateway_dir)
            except Exception:
                pass

            # Re-apply block
            if self.block_all:
                self._apply_upload_block(True)

    def _window_monitor_loop(self):
        """Active window monitoring to close unauthorized file picker dialogs."""
        if sys.platform != 'win32':
            return

        try:
            import win32gui
            import win32con
        except ImportError:
            self.logger.warning("[DLP] win32gui not available, window monitoring disabled")
            return

        # Dialog window titles to watch for
        target_titles = [
            "Open", "Save", "Save As", "Select File", "Select files",
            "Upload", "Upload files", "Choose File", "Open File",
            "Attach", "Browse", "Select"
        ]

        while self._running:
            try:
                self._check_unlock_state()

                # Only actively close dialogs if blocking is enabled
                if self.block_all and not self._is_temporarily_unlocked:

                    def enum_windows_callback(hwnd, _):
                        if not win32gui.IsWindowVisible(hwnd):
                            return True

                        title = win32gui.GetWindowText(hwnd)
                        class_name = win32gui.GetClassName(hwnd)

                        # Detect file dialogs:
                        # - #32770 is the Windows common dialog class
                        # - Also check for matching titles
                        is_file_dialog = (
                            class_name == "#32770" or
                            any(t.lower() in title.lower() for t in target_titles)
                        )

                        if is_file_dialog and title:  # Ignore empty titles
                            self.logger.warning(f"[DLP] Blocked file dialog: '{title}'")
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

                        return True

                    win32gui.EnumWindows(enum_windows_callback, None)

            except Exception as e:
                # Silently continue - window monitoring is best-effort
                pass

            time.sleep(0.2)  # Check every 200ms for responsive blocking

    def _monitor_loop(self):
        """Background monitor thread for periodic tasks."""
        while self._running:
            try:
                self._check_unlock_state()
            except Exception:
                pass
            time.sleep(5)

    def start_guard(self):
        """Start the DLP monitoring."""
        if self._running:
            return

        self._running = True
        self.logger.info(f"[DLP] Starting guard - Block mode: {self.block_all}")

        # Apply initial policy
        if self.block_all:
            self._apply_upload_block(True)

        # Start background monitor
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        # Start window monitor on Windows
        if sys.platform == 'win32':
            self._win_thread = threading.Thread(target=self._window_monitor_loop, daemon=True)
            self._win_thread.start()

        self.logger.info("[DLP] Guard started successfully")

    def set_config(self, block_all: bool, whitelist: List[str]):
        """Update guard configuration from dashboard."""
        old_block = self.block_all
        self.block_all = block_all
        self.whitelist = set(s.lower() for s in (whitelist or []))

        self.logger.info(f"[DLP] Config update: Block={block_all} (was {old_block})")

        if old_block != self.block_all:
            self._apply_upload_block(self.block_all)

    def update_approvals(self, dashboard_url: str, api_key: str):
        """Sync approved file hashes from dashboard."""
        self._sync_approved_hashes(dashboard_url, api_key)

    def request_temporary_unlock(self, file_path: str, file_hash: str, duration_seconds: int = 45):
        """
        Temporarily allow a specific approved file to be uploaded.
        Creates a secure gateway containing only that file.
        """
        if not self.block_all:
            return True  # Not blocking, no need to unlock

        if file_hash not in self._approved_files:
            self.logger.warning(f"[DLP] Unlock rejected: Hash {file_hash[:8]}... not approved")
            return False

        try:
            # Prepare gateway folder
            if os.path.exists(self._gateway_dir):
                shutil.rmtree(self._gateway_dir)
            os.makedirs(self._gateway_dir, exist_ok=True)

            # Copy approved file to gateway
            file_name = os.path.basename(file_path)
            gateway_file = os.path.join(self._gateway_dir, file_name)
            shutil.copy2(file_path, gateway_file)

            # Temporarily unlock
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
        if self._registry_manager:
            self._apply_upload_block(False)

        if self._thread:
            self._thread.join(timeout=2)
        if self._win_thread:
            self._win_thread.join(timeout=2)

        self.logger.info("[DLP] Guard stopped")
