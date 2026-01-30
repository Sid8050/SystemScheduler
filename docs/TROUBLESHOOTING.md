# Troubleshooting Guide

Common issues and solutions for the Endpoint Security Agent.

## Agent Issues

### Agent won't start

**Symptoms:**
- Service fails to start
- "Access denied" errors

**Solutions:**
1. Run as Administrator
2. Check Windows Event Viewer for errors
3. Verify Python and dependencies are installed

```powershell
# Check service status
sc query EndpointSecurityAgent

# View detailed error
Get-EventLog -LogName Application -Source "EndpointSecurityAgent" -Newest 10
```

### Agent not appearing in Dashboard

**Symptoms:**
- Endpoint list is empty
- No heartbeats received

**Solutions:**
1. Verify dashboard URL is correct in config
2. Check firewall allows outbound connections to port 8000
3. Clear stale API key and re-register

```powershell
# Check config
type C:\ProgramData\EndpointSecurity\config.yaml

# Clear stale API key (forces re-registration)
# Delete the api_key line from config.yaml, then restart agent
```

### 401 Unauthorized on heartbeat

**Cause:** Stale API key from previous registration

**Solution:**
```powershell
# 1. Stop the agent
net stop EndpointSecurityAgent

# 2. Delete the config to force re-registration
del C:\ProgramData\EndpointSecurity\config.yaml

# 3. Restart the agent
net start EndpointSecurityAgent
```

## USB Control Issues

### USB devices not showing in Dashboard

**Symptoms:**
- Dashboard shows 0 USB devices
- Agent logs show devices connecting

**Solutions:**
1. Wait for next heartbeat (default: 30 seconds)
2. Check agent logs for USB detection messages
3. Verify USB module is enabled

```powershell
# Check agent logs
Get-Content C:\ProgramData\EndpointSecurity\logs\agent.log -Tail 50 | Select-String "USB"
```

### USB blocking not working

**Symptoms:**
- USB storage devices still accessible
- Policy shows "Block" but devices work

**Solutions:**
1. Verify agent is running as Administrator/SYSTEM
2. Run Group Policy update manually
3. Restart the agent after policy change

```powershell
# Force Group Policy refresh
gpupdate /force

# Restart agent
net stop EndpointSecurityAgent && net start EndpointSecurityAgent
```

### Mouse/Keyboard stopped working

**This should NOT happen** - the agent protects HID devices.

If it does:
1. Unplug and replug the device
2. Use a PS/2 keyboard/mouse if available
3. Boot into Safe Mode and uninstall the agent

```powershell
# Emergency: Disable USB blocking via registry
reg add "HKLM\SYSTEM\CurrentControlSet\Services\USBSTOR" /v Start /t REG_DWORD /d 3 /f
```

## DLP Issues

### File picker not being blocked

**Symptoms:**
- Can still attach files in browsers
- DLP shows as disabled in logs

**Solutions:**
1. Verify DLP is enabled in policy
2. Check that agent received the policy update
3. Restart browser after enabling DLP

```powershell
# Check DLP status in logs
Get-Content C:\ProgramData\EndpointSecurity\logs\agent.log -Tail 100 | Select-String "DLP"
```

### Can't upload approved files

**Symptoms:**
- Request approved but still blocked
- 45-second window not working

**Solutions:**
1. Use the "Start Approved Upload" button in request UI
2. Select file from SecureUploadGateway folder
3. Complete upload within 45 seconds

### Request UI blocked by DLP

**Symptoms:**
- File picker closes in request UI too

**Solution:** This is a bug - the request UI should be whitelisted. Update to latest version.

## Network Guard Issues

### Websites still accessible after blocking

**Symptoms:**
- Added site to blocked list
- Site still loads in browser

**Solutions:**
1. Clear browser DNS cache
2. Flush Windows DNS cache
3. Wait for hosts file update

```powershell
# Flush DNS cache
ipconfig /flushdns

# Clear browser cache (Chrome)
# chrome://net-internals/#dns -> Clear host cache
```

### Legitimate sites blocked

**Symptoms:**
- Can't access required work sites
- False positive blocking

**Solutions:**
1. Add site to allowed list in Dashboard
2. Check for subdomain blocking issues
3. Verify exact domain spelling

## Dashboard Issues

### Dashboard not loading

**Symptoms:**
- Can't access http://localhost:8000
- Connection refused

**Solutions:**
1. Verify backend is running
2. Check port is not in use
3. Review backend logs

```bash
# Check if port is in use
netstat -an | findstr :8000

# Start backend manually
python -m dashboard.backend.main
```

### Frontend shows API errors

**Symptoms:**
- "Failed to fetch" errors
- Data not loading

**Solutions:**
1. Verify backend is running
2. Check browser console for CORS errors
3. Ensure frontend is accessing correct API URL

### Database errors

**Symptoms:**
- SQLite errors in logs
- "Database is locked"

**Solutions:**
```bash
# Reset database (WARNING: loses all data)
rm dashboard/dashboard.db
python -m dashboard.backend.main  # Recreates database
```

## Performance Issues

### High CPU usage

**Symptoms:**
- Agent using excessive CPU
- System slowdown

**Solutions:**
1. Reduce file scan frequency
2. Exclude large directories from monitoring
3. Check for infinite loop in logs

### High memory usage

**Symptoms:**
- Agent memory grows over time
- Eventually crashes

**Solutions:**
1. Restart agent periodically
2. Check for memory leaks in logs
3. Reduce monitored paths

## Logs Location

| Component | Log Location |
|-----------|--------------|
| Agent | `C:\ProgramData\EndpointSecurity\logs\agent.log` |
| Dashboard | Console output or `dashboard/logs/` |
| Windows Service | Event Viewer > Application |

## Getting Help

1. Check logs for error messages
2. Review Dashboard Events page
3. Collect logs and config for support
4. Contact IT Security team

### Collecting Debug Info

```powershell
# Create debug bundle
$debugDir = "$env:TEMP\EndpointSecurityDebug"
New-Item -ItemType Directory -Path $debugDir -Force

# Copy logs
Copy-Item "C:\ProgramData\EndpointSecurity\logs\*" $debugDir

# Copy config (remove sensitive data)
Copy-Item "C:\ProgramData\EndpointSecurity\config.yaml" $debugDir

# Get service status
sc query EndpointSecurityAgent > "$debugDir\service_status.txt"

# Get system info
systeminfo > "$debugDir\systeminfo.txt"

# Create zip
Compress-Archive -Path $debugDir -DestinationPath "$env:TEMP\EndpointSecurityDebug.zip"

Write-Host "Debug bundle: $env:TEMP\EndpointSecurityDebug.zip"
```
