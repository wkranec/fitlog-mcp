# fitlog-mcp

A personal fitness and health tracking MCP (Model Context Protocol) server. Log workouts, track metrics, and query your training history through an AI assistant interface.

This project is free for personal and non-commercial use (MIT + Commons Clause).

---

## Vault Setup

The vault directory holds all your personal fitlog data (logs, exercises, goals).

1. Create the vault directory:
   ```bash
   mkdir -p vault/exercises vault/logs
   ```

2. Set `FITLOG_VAULT_PATH` in your `.env` file (see Environment Variables below).

3. Add your exercise definitions in `vault/exercises/` (see `vault/exercises/example.yaml` for the schema).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FITLOG_VAULT_PATH` | `./vault` | Path to the vault directory where all fitlog data is stored |

---

## Development Quickstart

```bash
# Clone and enter the repo
git clone <repo-url>
cd fitlog-mcp

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy the example env file and configure your vault path
cp .env.example .env

# Run the test suite
pytest

# Start the development server
dev
```