# Palo Alto Firewall Pair Deployment

A comprehensive web-based deployment tool for configuring and managing **Palo Alto Networks (PAN-OS 11.2)** firewall pairs in High Availability (HA) mode.

## Overview

This project automates the end-to-end deployment of Palo Alto firewall pairs with active-passive HA configuration. It provides an intuitive web interface to configure network settings, security policies, and push configurations to both firewalls using both **XML API** and **REST API**.

**Status**: In-progress

## Features

### 🔧 Configuration Management
- **Firewall Pair Identity**: Set deployment name, management network settings
- **HA Settings**: Configure High Availability with automatic peer synchronization
- **Interfaces & Zones**: Setup security zones and interface IP addresses with floating IPs
- **Routing**: Configure virtual routers and static routes
- **Security Policy**: Define baseline security rules with support for add/edit/delete operations

### 🚀 API Support
- **XML API**: Used for system configuration, HA setup, user creation, and commits
- **REST API**: Used for network, zone, routing, and policy configuration
- Supports both **PAN-OS 11.x** XML and REST API endpoints

### 📊 Deployment Features
- **Phase 0 Console Commands**: Auto-generates console commands for initial firewall setup
- **Connection Testing**: Verify connectivity to both firewalls before deployment
- **Full Deployment Sequence**: Orchestrated 8-step deployment with rollback on failure:
  1. Verify connectivity with initial credentials
  2. Create local user account (local/test123!)
  3. Configure HA settings
  4. Create security zones
  5. Configure interfaces with floating IPs
  6. Setup virtual router and static routes
  7. Push baseline security policies
  8. Final commit on both firewalls

### 📋 Monitoring & Logging
- **Real-time Proxy Status**: Visual indicator showing proxy service availability
- **Audit Log**: Tracks all API calls with timestamps, status indicators, and operation details
- **Response Panels**: Immediate feedback for each configuration operation

## Project Structure

```
Palo_deployment/
├── index.html          # Web UI (85.4% of repository)
│                       # Single-page application with sidebar navigation,
│                       # configuration panels, and deployment orchestration
├── proxy.py            # API Proxy Server (14.6% of repository)
│                       # HTTP-based middleware for firewall API calls
├── .gitignore          # Standard Python/web gitignore
├── LICENSE             # MIT License
└── README.md           # This file
```

## Technology Stack

- **Frontend**: HTML5 + CSS3 + Vanilla JavaScript
- **Backend**: Python 3 (HTTP Server)
- **APIs**: Palo Alto PAN-OS XML API, REST API v11.2
- **Security**: MD5 crypt password hashing (RFC 2014), CORS support

## Getting Started

### Prerequisites
- Two Palo Alto Networks firewalls running PAN-OS 11.2+
- Python 3.7+
- Network connectivity to firewall management interfaces
- Initial admin credentials for first-time access

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/path-ne/Palo_deployment.git
   cd Palo_deployment
   ```

2. **Start the proxy server** (runs on http://localhost:8080):
   ```bash
   python3 proxy.py
   ```

3. **Open the web interface**:
   - Open `index.html` in a web browser
   - Or serve via HTTP:
     ```bash
     python3 -m http.server 8000
     # Then navigate to http://localhost:8000
     ```

### Basic Workflow

1. **Phase 0 - Console Setup**:
   - Fill in deployment name and firewall hostnames
   - The tool auto-generates console commands
   - Connect via console cable to each firewall and run the commands
   - This sets hostname, IP address, and gateway

2. **Firewall Pair Setup**:
   - Enter management IPs for FW1 (Primary) and FW2 (Secondary)
   - Enter initial admin credentials (for first login)
   - Test connectivity to both firewalls
   - The tool creates a new local user (local/test123!) for all subsequent operations

3. **Configuration**:
   - Navigate through tabs: HA Settings → Interfaces → Routing → Security Policy
   - Modify default values for your deployment
   - Push configurations individually or use "Deploy All"

4. **Deployment**:
   - "Deploy All" executes the full 8-step sequence
   - Monitor progress with status dots and response panels
   - Check "Audit Log" for detailed operation history

## API Endpoints

### XML API Operations
- **Configuration**: `POST /api/?type=config&action={set|delete}&xpath=...&element=...`
- **Commit**: `POST /api/?type=commit&cmd=<commit></commit>`
- **User Creation**: Creates MD5-hashed admin user with superuser role

### REST API Operations
- **Zones**: `PUT /restapi/v11.2/Network/Zones`
- **Interfaces**: `PUT /restapi/v11.2/Network/EthernetInterfaces`
- **Virtual Router**: `PUT /restapi/v11.2/Network/VirtualRouters`
- **Security Rules**: `POST /restapi/v11.2/Policies/SecurityRules`

## Security Considerations

- **MD5 Crypt Hashing**: Uses RFC 2014 MD5 crypt for password hashing (compatible with PAN-OS 11.x)
- **HTTPS Enforcement**: All firewall API calls use HTTPS with unverified SSL (for lab environments)
- **Local User**: Creates non-administrative user credentials after initial setup
- **Cleartext Credentials**: Initial admin password required for first deployment (displayed in UI)

## Configuration Reference

### Default Values

| Setting | Value | Purpose |
|---------|-------|---------|
| Management Gateway | 192.168.63.1 | Default gateway for mgmt interface |
| Management Subnet | 255.255.255.0 | /24 management network |
| HA Group ID | 1 | HA cluster identifier |
| HA Mode | active-passive | Primary/secondary failover |
| HA Hello Interval | 8000ms | Peer discovery heartbeat |
| Local User | local | Post-deployment admin username |
| Local Password | test123! | Post-deployment admin password |

### Interface Configuration

**FW1 (Primary - Active)**:
- eth1/1 (untrust): 192.168.10.1/30 → Floating: 192.168.10.9/30
- eth1/2 (inside): 10.1.0.1/24 → Floating: 10.1.0.254/24

**FW2 (Secondary - Passive)**:
- eth1/1 (untrust): 192.168.10.5/30 → Floating: 192.168.10.9/30
- eth1/2 (inside): 10.1.0.2/24 → Floating: 10.1.0.254/24

## Troubleshooting

### Proxy Connection Issues
- **"proxy offline"** tag: Ensure `proxy.py` is running on localhost:8080
- Check firewall connectivity: Use "Test FW1/FW2 connection" buttons

### API Errors
- Review "Audit Log" for error messages
- Common issues:
  - Incorrect credentials: Verify initial admin username/password
  - Network unreachable: Check firewall management IP and routing
  - Configuration conflicts: Some settings may fail if already configured

### HA Synchronization
- Ensure HA interfaces (HA1/HA2) are properly connected
- Verify HA IP addresses don't conflict with management network
- Config sync must be enabled for proper failover

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file for details.

## Author

Created as an automation tool for Palo Alto Networks firewall deployments.

---

**Note**: This tool is designed for lab and controlled environments. Always test in non-production settings first. Ensure proper change management procedures are followed for production deployments.
