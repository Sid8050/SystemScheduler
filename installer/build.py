"""
Build Script for Endpoint Security Agent

Creates standalone executables using PyInstaller:
- EndpointSecurityAgent.exe - Main agent (runs as service)
- EndpointSecurityTray.exe - System tray application
- RequestUpload.exe - Upload request utility

Usage:
    python build.py [--clean] [--installer]

Options:
    --clean     Clean build directories before building
    --installer Create Inno Setup installer (requires Inno Setup)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
AGENT_DIR = PROJECT_ROOT / "agent"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLER_DIR = PROJECT_ROOT / "installer"


def clean():
    """Clean build directories."""
    print("Cleaning build directories...")
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed {dir_path}")


def check_requirements():
    """Check if required packages are installed."""
    required = ["pyinstaller", "pystray", "pillow"]
    missing = []

    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    return True


def get_icon_path(icon_name):
    """Get icon path, handling both development and CI environments."""
    icon_path = INSTALLER_DIR / "assets" / icon_name
    if icon_path.exists():
        return str(icon_path)
    # Fallback - no icon
    print(f"  Warning: Icon not found: {icon_path}")
    return None


def build_agent():
    """Build the main agent executable."""
    print("\n=== Building Endpoint Security Agent ===")

    # PyInstaller options
    options = [
        "pyinstaller",
        "--onefile",
        "--name=EndpointSecurityAgent",
        "--hidden-import=win32timezone",
        "--hidden-import=win32serviceutil",
        "--hidden-import=win32service",
        "--hidden-import=win32event",
        "--hidden-import=servicemanager",
        "--hidden-import=wmi",
        "--hidden-import=pythoncom",
        "--hidden-import=pywintypes",
        "--uac-admin",  # Request admin rights
        "--noconsole",  # No console window (runs as service)
    ]

    # Add icon if available
    icon = get_icon_path("shield.ico")
    if icon:
        options.append(f"--icon={icon}")

    # Add config data if exists
    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        options.append("--add-data=config;config")

    options.append(str(AGENT_DIR / "main.py"))

    result = subprocess.run(options, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("ERROR: Agent build failed!")
        return False

    print("Agent build complete!")
    return True


def build_tray():
    """Build the system tray application."""
    print("\n=== Building System Tray Application ===")

    options = [
        "pyinstaller",
        "--onefile",
        "--name=EndpointSecurityTray",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "--noconsole",
    ]

    # Add icon if available
    icon = get_icon_path("shield.ico")
    if icon:
        options.append(f"--icon={icon}")

    options.append(str(AGENT_DIR / "utils" / "system_tray.py"))

    result = subprocess.run(options, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("ERROR: Tray build failed!")
        return False

    print("Tray build complete!")
    return True


def build_request_ui():
    """Build the upload request UI."""
    print("\n=== Building Upload Request UI ===")

    options = [
        "pyinstaller",
        "--onefile",
        "--name=RequestUpload",
        "--noconsole",
    ]

    # Add icon if available
    icon = get_icon_path("upload.ico")
    if icon:
        options.append(f"--icon={icon}")

    options.append(str(AGENT_DIR / "utils" / "request_ui.py"))

    result = subprocess.run(options, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("ERROR: Request UI build failed!")
        return False

    print("Request UI build complete!")
    return True


def create_installer():
    """Create Windows installer using Inno Setup."""
    print("\n=== Creating Windows Installer ===")

    # Check for Inno Setup
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    iscc = None
    for path in inno_paths:
        if os.path.exists(path):
            iscc = path
            break

    if not iscc:
        print("WARNING: Inno Setup not found. Skipping installer creation.")
        print("Download from: https://jrsoftware.org/isdl.php")
        return False

    # Run Inno Setup compiler
    iss_file = INSTALLER_DIR / "installer.iss"
    if not iss_file.exists():
        print(f"WARNING: {iss_file} not found. Skipping installer.")
        return False

    result = subprocess.run([iscc, str(iss_file)], cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print("ERROR: Installer creation failed!")
        return False

    print("Installer created successfully!")
    return True


def main():
    """Main build function."""
    print("=" * 60)
    print("Endpoint Security Agent - Build Script")
    print("=" * 60)

    # Parse arguments
    clean_build = "--clean" in sys.argv
    create_inst = "--installer" in sys.argv

    # Clean if requested
    if clean_build:
        clean()

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Create dist directory
    DIST_DIR.mkdir(exist_ok=True)

    # Build all components
    success = True
    success = build_agent() and success
    success = build_tray() and success
    success = build_request_ui() and success

    # Create installer if requested
    if create_inst:
        create_installer()

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("BUILD SUCCESSFUL!")
        print(f"\nOutput files in: {DIST_DIR}")
        print("\nFiles created:")
        for f in DIST_DIR.glob("*.exe"):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.name} ({size_mb:.1f} MB)")
    else:
        print("BUILD FAILED - Check errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
