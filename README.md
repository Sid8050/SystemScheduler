# Endpoint Security Agent

A comprehensive Data Loss Prevention (DLP) and endpoint security solution for Windows environments.

## Features

- **USB Device Control** - Monitor, whitelist, or block USB storage devices
- **Data Loss Prevention** - Prevent unauthorized file uploads to websites
- **Network Monitoring** - Block access to restricted websites
- **File Backup** - Automatic backup of important files to S3
- **Centralized Dashboard** - Web-based management console

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DASHBOARD (Web UI)                        │
│                     http://your-server:8000                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │   Policies  │  │  Endpoints  │  │   Events    │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │ USB Control │  │  Blocked    │  │   Upload    │             │
│   │  & Whitelist│  │   Sites     │  │  Requests   │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ENDPOINT AGENT (Windows)                      │
│                   Runs as Windows Service                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │     USB     │  │     DLP     │  │   Network   │             │
│   │  Controller │  │    Guard    │  │    Guard    │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                   │
│   ┌─────────────┐  ┌─────────────┐                               │
│   │    File     │  │   System    │                               │
│   │   Scanner   │  │    Tray     │                               │
│   └─────────────┘  └─────────────┘                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### For Development/Testing

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

### For Production Deployment

See [docs/INSTALLATION.md](docs/INSTALLATION.md)

## Project Structure

```
SystemScheduler/
├── agent/                    # Windows Endpoint Agent
│   ├── core/                 # Core agent functionality
│   │   ├── config.py         # Configuration management
│   │   ├── logger.py         # Logging system
│   │   ├── service.py        # Windows Service wrapper
│   │   └── guardian.py       # Self-protection module
│   ├── modules/              # Security modules
│   │   ├── usb_control.py    # USB device management
│   │   ├── dlp_guard.py      # Data Loss Prevention
│   │   ├── network_guard.py  # Website blocking
│   │   ├── file_scanner.py   # File backup scanner
│   │   └── data_detector.py  # Sensitive data detection
│   ├── utils/                # Utilities
│   │   ├── registry.py       # Windows Registry operations
│   │   ├── request_ui.py     # Upload request GUI
│   │   └── s3_client.py      # AWS S3 client
│   └── main.py               # Agent entry point
│
├── dashboard/                # Web Dashboard
│   ├── backend/              # FastAPI Backend
│   │   ├── api/              # API endpoints
│   │   ├── models/           # Database models
│   │   └── main.py           # Backend entry point
│   └── frontend/             # React Frontend
│       ├── src/
│       │   ├── pages/        # Page components
│       │   ├── components/   # Shared components
│       │   └── api/          # API client
│       └── package.json
│
├── installer/                # Installation files
│   ├── build.py              # PyInstaller build script
│   ├── installer.iss         # Inno Setup script
│   └── assets/               # Icons, images
│
├── docs/                     # Documentation
│   ├── INSTALLATION.md       # Production installation guide
│   ├── DEVELOPMENT.md        # Development setup guide
│   ├── ARCHITECTURE.md       # System architecture
│   ├── API.md                # API documentation
│   └── TROUBLESHOOTING.md    # Common issues & solutions
│
├── config/                   # Configuration files
│   └── default_config.yaml   # Default agent configuration
│
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Security Modules

### USB Device Control

| Mode | Behavior |
|------|----------|
| `monitor` | Log all USB activity, allow all devices |
| `block` | Block all USB storage devices |
| `whitelist` | Only allow approved devices |

Protected device types (never blocked):
- Keyboards, mice, input devices
- Network adapters
- Bluetooth adapters
- Audio devices
- Webcams

### Data Loss Prevention (DLP)

When enabled:
- Blocks file picker dialogs in browsers
- Prevents drag & drop file uploads
- Allows approved files via request workflow

Approval workflow:
1. User requests permission via system tray
2. Admin approves in dashboard
3. User gets 45-second window to upload

### Network Guard

- Block websites by domain
- Block by category (coming soon)
- Modify Windows hosts file or use DNS filtering

## Requirements

### Agent (Windows Endpoint)
- Windows 10/11
- Python 3.9+ (for development) or standalone installer
- Administrator privileges

### Dashboard Server
- Python 3.9+
- Node.js 18+ (for frontend)
- Any OS (Windows, Linux, macOS)

## License

Proprietary - Internal use only

## Support

For issues, contact the IT Security team.
