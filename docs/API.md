# API Documentation

This document describes the REST API endpoints for the Endpoint Security Dashboard.

## Base URL

```
http://your-server:8000/api/v1
```

## Authentication

Most endpoints require an API key passed in the `X-API-Key` header:

```
X-API-Key: <your-api-key>
```

## Endpoints

### Agent Registration

#### Register Agent
```
POST /endpoints/register
```

Registers a new endpoint with the dashboard.

**Request Body:**
```json
{
  "machine_id": "unique-machine-identifier",
  "hostname": "WORKSTATION-01",
  "agent_version": "1.0.0",
  "os_version": "Windows 10",
  "ip_address": "192.168.1.100"
}
```

**Response:**
```json
{
  "endpoint_id": 1,
  "api_key": "generated-api-key",
  "message": "Endpoint registered successfully"
}
```

### Heartbeat

#### Send Heartbeat
```
POST /agent/heartbeat
```

Sends periodic status update from agent.

**Headers:**
```
X-API-Key: <api-key>
```

**Request Body:**
```json
{
  "status": "online",
  "stats": {
    "files_backed_up": 150,
    "backup_size": 1073741824
  },
  "usb_devices": [
    {
      "device_id": "USB\\VID_0781&PID_5567\\12345678",
      "vendor_id": "0781",
      "product_id": "5567",
      "serial_number": "12345678",
      "description": "SanDisk Cruzer",
      "drive_letter": "E:",
      "device_type": "mass_storage",
      "connected_time": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "status": "ok",
  "config": {
    "usb": {
      "mode": "monitor",
      "whitelist": []
    },
    "network": {
      "blocked_sites": ["malware.com", "phishing.net"]
    },
    "uploads": {
      "block_all": true,
      "whitelist": []
    }
  }
}
```

### Endpoints Management

#### List Endpoints
```
GET /endpoints
```

Returns all registered endpoints.

**Response:**
```json
{
  "endpoints": [
    {
      "id": 1,
      "machine_id": "abc123",
      "hostname": "WORKSTATION-01",
      "status": "online",
      "last_seen": "2024-01-15T10:30:00Z",
      "agent_version": "1.0.0",
      "ip_address": "192.168.1.100"
    }
  ],
  "total": 1,
  "online": 1
}
```

#### Get Endpoint Details
```
GET /endpoints/{endpoint_id}
```

#### Delete Endpoint
```
DELETE /endpoints/{endpoint_id}
```

### USB Management

#### Get Connected USB Devices
```
GET /usb/connected
```

Returns USB devices across all endpoints.

**Response:**
```json
{
  "devices": [
    {
      "endpoint_id": 1,
      "endpoint_hostname": "WORKSTATION-01",
      "device_id": "USB\\VID_0781&PID_5567\\12345678",
      "description": "SanDisk Cruzer",
      "drive_letter": "E:",
      "connected_time": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Get USB Whitelist
```
GET /usb/whitelist
```

#### Add Device to Whitelist
```
POST /usb/whitelist
```

**Request Body:**
```json
{
  "device_id": "USB\\VID_0781&PID_5567\\12345678",
  "description": "Corporate USB Drive",
  "approved_by": "admin@company.com"
}
```

#### Remove from Whitelist
```
DELETE /usb/whitelist/{device_id}
```

### Policies

#### List Policies
```
GET /policies
```

#### Get Policy
```
GET /policies/{policy_id}
```

#### Create Policy
```
POST /policies
```

**Request Body:**
```json
{
  "name": "Standard Security",
  "description": "Default security policy",
  "usb_mode": "monitor",
  "block_uploads": false,
  "blocked_sites": []
}
```

#### Update Policy
```
PUT /policies/{policy_id}
```

#### Delete Policy
```
DELETE /policies/{policy_id}
```

#### Assign Policy to Endpoint
```
POST /policies/{policy_id}/assign
```

**Request Body:**
```json
{
  "endpoint_ids": [1, 2, 3]
}
```

### Blocked Sites

#### List Blocked Sites
```
GET /sites/blocked
```

#### Add Blocked Site
```
POST /sites/blocked
```

**Request Body:**
```json
{
  "domain": "malware.com",
  "reason": "Known malware distribution site",
  "category": "malware"
}
```

#### Remove Blocked Site
```
DELETE /sites/blocked/{site_id}
```

### Upload Requests

#### List Upload Requests
```
GET /uploads/requests
```

**Query Parameters:**
- `status`: Filter by status (pending, approved, rejected)

#### Create Upload Request
```
POST /uploads/requests
```

**Request Body:**
```json
{
  "file_path": "C:\\Users\\John\\Documents\\report.pdf",
  "file_hash": "sha256:abc123...",
  "file_size": 1048576,
  "reason": "Quarterly report for external auditor",
  "destination": "auditor@external.com"
}
```

#### Approve Request
```
POST /uploads/requests/{request_id}/approve
```

**Request Body:**
```json
{
  "approved_by": "admin@company.com",
  "notes": "Approved for quarterly audit"
}
```

#### Reject Request
```
POST /uploads/requests/{request_id}/reject
```

**Request Body:**
```json
{
  "rejected_by": "admin@company.com",
  "reason": "Sensitive data detected"
}
```

#### Get Approved Files
```
GET /uploads/approved
```

Returns currently approved file hashes for the requesting agent.

### Events

#### List Events
```
GET /events
```

**Query Parameters:**
- `type`: Filter by event type
- `endpoint_id`: Filter by endpoint
- `start_date`: Start of date range
- `end_date`: End of date range
- `limit`: Number of results (default: 100)
- `offset`: Pagination offset

**Response:**
```json
{
  "events": [
    {
      "id": 1,
      "endpoint_id": 1,
      "event_type": "usb_blocked",
      "description": "USB device blocked: SanDisk Cruzer",
      "details": {
        "device_id": "USB\\VID_0781&PID_5567\\12345678"
      },
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 100
}
```

### Dashboard Statistics

#### Get Dashboard Stats
```
GET /dashboard/stats
```

**Response:**
```json
{
  "total_endpoints": 50,
  "online_endpoints": 45,
  "total_events_today": 1250,
  "blocked_uploads": 23,
  "blocked_usb": 15,
  "blocked_sites": 89
}
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized (missing/invalid API key) |
| 404 | Not Found |
| 500 | Server Error |

## Rate Limiting

Currently no rate limiting is implemented. For production deployments, consider adding rate limiting at the reverse proxy level.

## Webhooks (Future)

Planned webhook support for:
- New endpoint registration
- Security events
- Upload request status changes
