"""
System Tray Application for Endpoint Security Agent

Provides a user-friendly interface for:
- Viewing agent status
- Requesting upload permissions
- Viewing notifications
"""

import os
import sys
import threading
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import pystray
    from pystray import MenuItem as Item
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    print("Warning: pystray or PIL not installed. System tray not available.")
    print("Install with: pip install pystray pillow")


class SystemTrayApp:
    """System tray icon for the Endpoint Security Agent."""

    def __init__(self, agent=None):
        self.agent = agent
        self.icon = None
        self._running = False

        # Status tracking
        self.usb_blocked = False
        self.dlp_enabled = False
        self.connected = False

    def create_icon_image(self, color="green"):
        """Create a simple icon image."""
        # Create a simple shield icon
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Color based on status
        colors = {
            "green": (16, 185, 129),   # Connected
            "yellow": (245, 158, 11),  # Warning
            "red": (239, 68, 68),      # Error/Blocked
            "gray": (113, 113, 122),   # Offline
        }
        fill_color = colors.get(color, colors["gray"])

        # Draw shield shape
        points = [
            (size//2, 5),           # Top
            (size-5, 15),           # Top right
            (size-5, size//2),      # Middle right
            (size//2, size-5),      # Bottom
            (5, size//2),           # Middle left
            (5, 15),                # Top left
        ]
        draw.polygon(points, fill=fill_color)

        # Draw lock symbol in white
        lock_color = (255, 255, 255)
        # Lock body
        draw.rectangle([size//2-8, size//2-2, size//2+8, size//2+12], fill=lock_color)
        # Lock shackle
        draw.arc([size//2-6, size//2-12, size//2+6, size//2+2], 0, 180, fill=lock_color, width=3)

        return image

    def get_status_text(self):
        """Get current status text."""
        if not self.connected:
            return "⚪ Disconnected"

        status_parts = ["🟢 Protected"]

        if self.usb_blocked:
            status_parts.append("🔒 USB Blocked")
        if self.dlp_enabled:
            status_parts.append("🔒 Uploads Blocked")

        return " | ".join(status_parts)

    def update_status(self):
        """Update status from agent."""
        if self.agent:
            self.connected = self.agent._running

            if self.agent.usb_controller:
                from agent.modules.usb_control import USBMode
                self.usb_blocked = self.agent.usb_controller.mode == USBMode.BLOCK

            if self.agent.dlp_guard:
                self.dlp_enabled = self.agent.dlp_guard.block_all

        # Update icon color
        if self.icon:
            if not self.connected:
                self.icon.icon = self.create_icon_image("gray")
            elif self.usb_blocked or self.dlp_enabled:
                self.icon.icon = self.create_icon_image("red")
            else:
                self.icon.icon = self.create_icon_image("green")

    def request_upload(self, icon=None, item=None):
        """Open the upload request UI."""
        try:
            if self.agent:
                config = self.agent.config
                dashboard_url = config.agent.dashboard_url
                api_key = config.agent.api_key

                from agent.utils.request_ui import UploadRequestApp
                app = UploadRequestApp(dashboard_url, api_key)
                # Run in separate thread to not block tray
                threading.Thread(target=app.run, daemon=True).start()
            else:
                # Standalone mode - try to load config
                from agent.core.config import get_config
                config = get_config()
                from agent.utils.request_ui import UploadRequestApp
                app = UploadRequestApp(config.agent.dashboard_url, config.agent.api_key)
                threading.Thread(target=app.run, daemon=True).start()
        except Exception as e:
            print(f"Error opening request UI: {e}")

    def show_about(self, icon=None, item=None):
        """Show about dialog."""
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(
                "Endpoint Security Agent",
                "Endpoint Security Agent v1.0.0\n\n"
                "Protects your system from:\n"
                "• Unauthorized USB devices\n"
                "• Data leaks via file uploads\n"
                "• Restricted websites\n\n"
                "For support, contact IT Security."
            )
            root.destroy()
        except Exception as e:
            print(f"Error showing about: {e}")

    def quit_app(self, icon=None, item=None):
        """Quit the system tray (not the agent)."""
        self._running = False
        if self.icon:
            self.icon.stop()

    def create_menu(self):
        """Create the system tray menu."""
        return pystray.Menu(
            Item(
                lambda text: self.get_status_text(),
                None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            Item(
                "📤 Request Upload Permission",
                self.request_upload
            ),
            Item(
                "🔄 Refresh Status",
                lambda: self.update_status()
            ),
            pystray.Menu.SEPARATOR,
            Item(
                "ℹ️ About",
                self.show_about
            ),
            Item(
                "❌ Hide Tray Icon",
                self.quit_app
            ),
        )

    def run(self):
        """Run the system tray application."""
        if not HAS_TRAY:
            print("System tray not available. Install pystray and pillow.")
            return

        self._running = True

        # Create icon
        self.icon = pystray.Icon(
            "EndpointSecurity",
            self.create_icon_image("gray"),
            "Endpoint Security Agent",
            menu=self.create_menu()
        )

        # Start status update thread
        def update_loop():
            while self._running:
                try:
                    self.update_status()
                except Exception:
                    pass
                time.sleep(5)

        threading.Thread(target=update_loop, daemon=True).start()

        # Run icon (blocking)
        self.icon.run()

    def run_detached(self):
        """Run system tray in a separate thread."""
        threading.Thread(target=self.run, daemon=True).start()


def main():
    """Standalone entry point."""
    app = SystemTrayApp()
    app.run()


if __name__ == "__main__":
    main()
