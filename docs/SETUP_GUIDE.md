# Setup Guide

## Python Virtual Environment Setup

### Why Use a Virtual Environment?

On macOS (and modern Linux systems), Python installations are "externally managed" to prevent breaking system packages. You **must** use a virtual environment to install project dependencies.

### Quick Setup

The project already has a `venv/` directory. To use it:

```bash
# Activate the virtual environment
source venv/bin/activate

# Your prompt should now show (venv)
# Install dependencies
pip install -r requirements.txt
```

### Creating a New Virtual Environment

If the `venv/` directory doesn't exist or you want to create a fresh one:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip (recommended)
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Activating the Virtual Environment

**Every time** you work on this project, activate the virtual environment:

```bash
source venv/bin/activate
```

You'll know it's activated when you see `(venv)` in your terminal prompt.

### Deactivating the Virtual Environment

When you're done working:

```bash
deactivate
```

### Running Commands

After activating the virtual environment, you can run:

```bash
# Start the embedding service
uvicorn embed:app --reload --port 8000

# Run the Elasticsearch setup
python utils/es_index_setup.py

# Run tests
python test_elasticsearch_setup.py
```

### Troubleshooting

**Error: "externally-managed-environment"**
- **Solution**: Activate the virtual environment first with `source venv/bin/activate`

**Error: "command not found: uvicorn"**
- **Solution**: Make sure the virtual environment is activated and dependencies are installed

**Error: "No module named 'fastapi'"**
- **Solution**: Activate virtual environment and run `pip install -r requirements.txt`

### Verifying Installation

After installing dependencies, verify everything is installed:

```bash
# With venv activated, check installed packages
pip list | grep -E "fastapi|sentence-transformers|elasticsearch|cairosvg|Pillow"

# You should see:
# fastapi
# sentence-transformers
# elasticsearch
# cairosvg
# Pillow
```

### Common Commands Reference

```bash
# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Upgrade pip
pip install --upgrade pip

# List installed packages
pip list

# Check specific package
pip show fastapi

# Deactivate venv
deactivate
```

