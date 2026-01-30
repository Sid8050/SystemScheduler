# System Architecture

This document describes the architecture of the Endpoint Security Agent.

## Overview

The system consists of two main components:

1. **Dashboard Server** - Centralized management console
2. **Endpoint Agent** - Security client on Windows workstations

## Component Diagram

```
                                    INTERNET
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DASHBOARD SERVER                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      FastAPI Backend                         │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │   REST API   │  │  WebSocket  │  │  Background Tasks   │  │ │
│  │  │  /api/v1/*   │  │   (future)  │  │   (cleanup, etc)    │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  │                                                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │                  SQLite Database                         │ │ │
│  │  │  endpoints | policies | events | upload_requests | ...   │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     React Frontend                           │ │
│  │                                                               │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │ │
│  │  │Dashboard│ │Endpoints│ │ Policies│ │ Events  │ │ Uploads │ │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS (Heartbeat API)
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────┐                     ┌───────────────────┐
│   ENDPOINT #1     │                     │   ENDPOINT #2     │
│   (Windows PC)    │                     │   (Windows PC)    │
│                   │                     │                   │
│ ┌───────────────┐ │                     │ ┌───────────────┐ │
│ │    Agent      │ │                     │ │    Agent      │ │
│ │  (Service)    │ │                     │ │  (Service)    │ │
│ └───────────────┘ │                     │ └───────────────┘ │
│                   │                     │                   │
│ ┌───────────────┐ │                     │ ┌───────────────┐ │
│ │  System Tray  │ │                     │ │  System Tray  │ │
│ └───────────────┘ │                     │ └───────────────┘ │
└───────────────────┘                     └───────────────────┘
```

## Agent Architecture

### Module System

The agent uses a modular architecture where each security feature is implemented as an independent module:

```
EndpointSecurityAgent
        │
        ├── USBController      - USB device monitoring and blocking
        │
        ├── DataLossGuard      - File upload prevention
        │
        ├── NetworkGuard       - Website blocking
        │
        ├── FileScanner        - File backup to S3
        │
        └── DataDetector       - Sensitive data detection
```

### USB Controller

```
USBController
     │
     ├── WMI Monitoring Thread
     │        │
     │        └── Detects device insertion/removal
     │
     ├── Device Cache
     │        │
     │        └── Tracks connected devices
     │
     └── Policy Enforcement
              │
              ├── Registry manipulation
              └── Group Policy refresh
```

**Blocking Mechanism:**
1. Monitors WMI for USB device events
2. On device insertion, checks device type
3. Protected devices (HID, network, audio) are always allowed
4. Mass storage devices are blocked based on policy:
   - BLOCK mode: Disables USBSTOR service, ejects devices
   - WHITELIST mode: Only allows specific device IDs
   - MONITOR mode: Logs only, no blocking

### DLP Guard (Data Loss Prevention)

```
DataLossGuard
     │
     ├── Window Monitor Thread (100ms loop)
     │        │
     │        └── EnumWindows callback
     │
     ├── Dialog Detection
     │        │
     │        ├── Window class check (#32770)
     │        └── Title text analysis
     │
     └── Process Whitelist
              │
              └── Allows our own tools
```

**Blocking Mechanism:**
1. Continuously monitors all windows
2. Identifies file dialogs by class (#32770) and title
3. Checks if owning process is whitelisted
4. Closes unauthorized dialogs with WM_CLOSE

### Network Guard

```
NetworkGuard
     │
     ├── Hosts File Modifier
     │        │
     │        └── Blocks domains at OS level
     │
     └── DNS Monitor (optional)
              │
              └── Logs DNS queries
```

### File Scanner

```
FileScanner
     │
     ├── Watchdog Observer
     │        │
     │        └── Monitors file system events
     │
     ├── Hash Database (SQLite)
     │        │
     │        └── Tracks file hashes
     │
     └── S3 Upload Queue
              │
              └── Background uploads
```

## Communication Flow

### Agent Registration

```
1. Agent starts
2. Checks for existing API key in config
3. If no key, calls POST /api/v1/endpoints/register
4. Dashboard creates endpoint record
5. Returns API key
6. Agent saves key to config
```

### Heartbeat Loop

```
Every 30 seconds:
1. Agent collects:
   - Status (online)
   - Statistics (files backed up, etc.)
   - Connected USB devices
2. Sends POST /api/v1/agent/heartbeat
3. Dashboard responds with:
   - Policy configuration
   - Blocked sites list
   - USB mode/whitelist
   - DLP settings
4. Agent applies new configuration
```

### Upload Request Flow

```
1. User launches Request Upload UI
2. Selects file, enters reason
3. UI sends POST /api/v1/uploads/request
4. Admin sees request in Dashboard
5. Admin approves
6. On next heartbeat, agent gets approval
7. User clicks "Start Approved Upload"
8. System unlocks for 45 seconds
9. User completes upload from secure gateway
```

## Security Considerations

### Agent Protection

- Runs as SYSTEM service
- Guardian process monitors agent health
- Restarts automatically if terminated
- Protected files and registry keys

### Communication Security

- HTTPS recommended for production
- API key authentication
- Key stored in protected config file

### Policy Enforcement

- Policies enforced locally even when offline
- Configuration cached in registry
- Fallback to strict mode if dashboard unreachable

## Database Schema

### Key Tables

| Table | Purpose |
|-------|---------|
| `endpoints` | Registered agent machines |
| `policies` | Security policy definitions |
| `endpoint_policies` | Policy assignments |
| `events` | Security event log |
| `usb_devices` | Known USB devices |
| `usb_whitelist` | Approved devices |
| `upload_requests` | Pending file upload requests |
| `blocked_sites` | Blocked domain list |

## Configuration

### Agent Config (`config.yaml`)

```yaml
agent:
  dashboard_url: "http://localhost:8000"
  api_key: "<auto-generated>"
  heartbeat_interval: 30

usb:
  enabled: true
  mode: "monitor"
  whitelist: []

network:
  enabled: true
  blocked_sites: []

backup:
  enabled: false
  scan_paths: []
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `ES_DASHBOARD_URL` | Override dashboard URL |
| `ES_API_KEY` | Override API key |
| `AWS_ACCESS_KEY_ID` | S3 credentials |
| `AWS_SECRET_ACCESS_KEY` | S3 credentials |
