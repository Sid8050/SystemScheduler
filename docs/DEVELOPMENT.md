# Development Setup Guide

This guide is for developers who want to modify or test the Endpoint Security Agent.

## Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher (for frontend)
- Git
- Windows 10/11 (for agent development)
- Administrator access

## Clone the Repository

```bash
git clone https://github.com/Sid8050/SystemScheduler.git
cd SystemScheduler
```

## Backend Setup

### 1. Create Virtual Environment

```powershell
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Start the Backend Server

```powershell
python -m dashboard.backend.main
```

The API will be available at `http://localhost:8000`

## Frontend Setup

### 1. Install Node Dependencies

```powershell
cd dashboard/frontend
npm install
```

### 2. Start Development Server

```powershell
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Agent Setup (Windows Only)

### 1. Activate Virtual Environment

```powershell
cd D:\SystemScheduler\SystemScheduler
.\venv\Scripts\activate
```

### 2. Run Agent in Foreground Mode (for testing)

```powershell
python agent/main.py --foreground
```

This shows all logs in the console for debugging.

### 3. Run Agent as Windows Service (for production)

```powershell
# Install service (one-time)
python agent/main.py install

# Start service
python agent/main.py start

# Check status
python agent/main.py status

# Stop service
python agent/main.py stop

# Uninstall service
python agent/main.py uninstall
```

## Development Commands

### Agent Commands

```powershell
# Run in foreground (development)
python agent/main.py --foreground

# Run with initial file scan
python agent/main.py --foreground --scan

# Open upload request UI
python agent/main.py request-upload

# Temporarily unlock for approved file
python agent/main.py unlock-upload "C:\path\to\file.pdf" "sha256hash"

# Windows Service management
python agent/main.py install|uninstall|start|stop|status
```

### Testing the Features

#### USB Control

1. Open Dashboard → Policies → Edit Default Policy
2. Set USB mode to "Block"
3. Insert a USB flash drive
4. Verify it gets blocked (check agent logs)

#### DLP (Upload Blocking)

1. Open Dashboard → Policies → Edit Default Policy
2. Enable "Block All Web Uploads"
3. Go to any website (Gmail, WeTransfer)
4. Try to attach a file
5. Verify file picker closes immediately

#### Upload Request Workflow

1. Enable DLP blocking (as above)
2. Run: `python agent/main.py request-upload`
3. Select a file and submit request
4. Go to Dashboard → Upload Requests
5. Approve the request
6. In the request UI, click "Refresh Status" then "Start Approved Upload"

## Project Structure for Developers

```
agent/
├── main.py              # Entry point, CLI commands
├── core/
│   ├── config.py        # Configuration dataclasses
│   ├── logger.py        # Logging to file/dashboard
│   └── service.py       # Windows Service wrapper
└── modules/
    ├── usb_control.py   # USB monitoring & blocking
    ├── dlp_guard.py     # File picker blocking
    ├── network_guard.py # Website blocking
    └── file_scanner.py  # File backup system
```

## Key Configuration

Agent configuration is stored at:
- Windows: `C:\ProgramData\EndpointSecurity\config.yaml`

Default settings are in `config/default_config.yaml`

## Environment Variables

```bash
# Override dashboard URL
ES_DASHBOARD_URL=http://your-server:8000

# Override API key (usually auto-generated)
ES_API_KEY=your-api-key

# S3 backup configuration
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
ES_S3_BUCKET=your-bucket
```

## Database

The dashboard uses SQLite by default:
- Location: `dashboard/dashboard.db`
- To reset: Delete the file and restart backend

## Troubleshooting

### Agent won't start
- Run as Administrator
- Check logs in `C:\ProgramData\EndpointSecurity\logs\`

### USB blocking not working
- Agent must run as Administrator
- Restart agent after enabling blocking

### DLP not blocking file pickers
- Check agent console for `[DLP]` logs
- Verify policy has `block_all: true`
- Restart browser after enabling

### Dashboard not connecting
- Verify backend is running on port 8000
- Check CORS settings in `dashboard/backend/main.py`

## Contributing

1. Create a feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## Building for Production

See [INSTALLATION.md](INSTALLATION.md) for creating distributable packages.
