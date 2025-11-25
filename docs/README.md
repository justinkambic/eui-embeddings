# Documentation Index

Welcome to the EUI Icon Embeddings documentation. This guide helps you navigate all available documentation.

## Getting Started

- **[Setup Guide](setup.md)** - Initial setup and installation instructions
- **[Deployment Guide](deployment.md)** - Complete guide for deploying to Cloud Run

## Core Documentation

### Setup and Configuration
- **[Setup Guide](setup.md)** - How to set up the project locally
- **[Environment Variables](api/environment-variables.md)** - Complete reference for all environment variables

### Deployment
- **[Deployment Guide](deployment.md)** - Cloud Run deployment guide (consolidated from BASIC_DEPLOYMENT_* docs)
- **[Docker Guide](infrastructure/docker.md)** - Docker setup and usage
- **[GCP Setup](infrastructure/gcp-setup.md)** - Google Cloud Platform project setup
- **[HTTPS Setup](infrastructure/https-setup.md)** - HTTPS/SSL configuration
- **[GCP Admin Request](infrastructure/gcp-admin.md)** - Requesting GCP admin access

### Observability
- **[Observability Guide](observability.md)** - OpenTelemetry setup and usage
- **[OTEL Plan](OTEL_PLAN.md)** - OpenTelemetry implementation plan
- **[OTEL Verification](OTEL_VERIFICATION.md)** - Verification steps for OpenTelemetry

### API Documentation
- **[MCP Server](api/mcp-server.md)** - Model Context Protocol server documentation
- **[API Key Rotation](api/api-key-rotation.md)** - How to rotate API keys securely

### Troubleshooting
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Known Issues and Fixes](KNOWN_ISSUES_FIXES.md)** - Documented issues and their fixes

## Archive

Historical and phase-specific documentation has been moved to the archive:

- **[Phase Implementation Docs](archive/phases/)** - Phase-specific implementation documentation
- **[Planning Docs](archive/planning/)** - Completed planning documents

## Quick Links

- **Main README**: See [README.md](../README.md) in project root
- **Changelog**: See [CHANGELOG.md](../CHANGELOG.md) for version history
- **Scripts**: See [scripts/](../scripts/) directory for deployment and utility scripts

## Documentation Structure

```
docs/
├── README.md (this file)
├── setup.md
├── deployment.md
├── observability.md
├── troubleshooting.md
├── OTEL_PLAN.md
├── OTEL_VERIFICATION.md
├── KNOWN_ISSUES_FIXES.md
├── api/
│   ├── mcp-server.md
│   ├── environment-variables.md
│   └── api-key-rotation.md
├── infrastructure/
│   ├── docker.md
│   ├── gcp-setup.md
│   ├── https-setup.md
│   └── gcp-admin.md
└── archive/
    ├── phases/
    └── planning/
```

## Contributing

When adding new documentation:
1. Place it in the appropriate directory
2. Update this README with a link
3. Follow the existing documentation style
4. Include examples where helpful

