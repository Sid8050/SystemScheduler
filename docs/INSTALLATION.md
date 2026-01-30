# Production Installation Guide

This guide covers deploying the Endpoint Security solution in a production environment.

## Overview

The solution has two components:

1. **Dashboard Server** - Web-based management console (runs on your server)
2. **Endpoint Agent** - Installed on each Windows workstation

## Part 1: Dashboard Server Setup

### Option A: Docker Deployment (Recommended)

Coming soon...

### Option B: Manual Deployment

#### Prerequisites
- Linux/Windows Server with Python 3.9+
- Node.js 18+
- Reverse proxy (nginx/Apache) recommended for HTTPS

#### Steps

```bash
# Clone repository
git clone https://github.com/Sid8050/SystemScheduler.git
cd SystemScheduler

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build frontend
cd dashboard/frontend
npm install
npm run build

# Start backend (production)
cd ../..
python -m dashboard.backend.main
```

For production, use a process manager like `systemd` or `supervisor`:

```ini
# /etc/systemd/system/endpoint-dashboard.service
[Unit]
Description=Endpoint Security Dashboard
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/SystemScheduler
ExecStart=/opt/SystemScheduler/venv/bin/python -m dashboard.backend.main
Restart=always

[Install]
WantedBy=multi-user.target
```

## Part 2: Endpoint Agent Deployment

### Option A: Standalone Installer (Recommended for IT)

#### Building the Installer

On a Windows development machine:

```powershell
# Install build tools
pip install pyinstaller

# Run build script
cd installer
python build.py
```

This creates:
- `dist/EndpointSecurityAgent.exe` - Standalone agent
- `dist/RequestUpload.exe` - Upload request utility
- `dist/EndpointSecuritySetup.exe` - Full installer

#### Deploying via Group Policy

1. Copy installer to network share: `\\server\software\EndpointSecuritySetup.exe`
2. Create GPO for software installation
3. Assign to target computers/OUs
4. Agent installs silently and starts automatically

#### Silent Installation

```powershell
# Silent install with custom dashboard URL
EndpointSecuritySetup.exe /SILENT /DASHBOARD_URL=https://your-server:8000

# Fully unattended
EndpointSecuritySetup.exe /VERYSILENT /SUPPRESSMSGBOXES
```

### Option B: Manual Installation (For Testing)

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to agent directory
cd C:\EndpointSecurity

# 3. Install as Windows Service
python agent/main.py install

# 4. Start the service
python agent/main.py start

# 5. Verify
python agent/main.py status
```

### Option C: Deploy via Intune/SCCM

1. Package the installer as Win32 app
2. Detection rule: Check for service "EndpointSecurityAgent"
3. Install command: `EndpointSecuritySetup.exe /VERYSILENT`
4. Uninstall command: `EndpointSecuritySetup.exe /UNINSTALL /VERYSILENT`

## Configuration

### Dashboard URL

The agent needs to know where to connect. Set during installation or edit:

```yaml
# C:\ProgramData\EndpointSecurity\config.yaml
agent:
  dashboard_url: "https://your-dashboard-server:8000"
```

### Initial Setup

1. Open Dashboard in browser: `https://your-server:8000`
2. Complete initial admin setup
3. Create your first policy
4. Agents will auto-register on first heartbeat

## Post-Installation Verification

### On the Dashboard

1. Go to **Endpoints** page
2. Verify new endpoints appear with status "Online"
3. Check **Events** for agent activity

### On the Endpoint

```powershell
# Check service status
sc query EndpointSecurityAgent

# Check logs
Get-Content C:\ProgramData\EndpointSecurity\logs\agent.log -Tail 50
```

## Security Considerations

### Network Requirements

| Direction | Port | Purpose |
|-----------|------|---------|
| Agent → Dashboard | 8000 (HTTPS) | Heartbeat, config sync |
| Dashboard → Agent | None | No inbound required |

### Firewall Rules

Agents only need **outbound** access to the dashboard server.

### HTTPS Configuration

For production, configure HTTPS on your dashboard:

1. Obtain SSL certificate
2. Configure reverse proxy (nginx):

```nginx
server {
    listen 443 ssl;
    server_name security.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Updating Agents

### Automatic Updates (Coming Soon)

Agents will check for updates on each heartbeat.

### Manual Update

1. Stop service: `net stop EndpointSecurityAgent`
2. Replace files in installation directory
3. Start service: `net start EndpointSecurityAgent`

## Uninstallation

### Via Control Panel
- Programs and Features → Endpoint Security Agent → Uninstall

### Via Command Line
```powershell
python agent/main.py uninstall
# or
EndpointSecuritySetup.exe /UNINSTALL /SILENT
```

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.

## Support

For issues:
1. Check agent logs: `C:\ProgramData\EndpointSecurity\logs\`
2. Check dashboard Events page
3. Contact IT Security team
