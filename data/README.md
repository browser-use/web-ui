# Settings Data Directory

This directory contains persistent settings and configuration files for the Browser Use Web UI.

## Directory Structure

```plaintext
data/
├── mcp.json                # MCP (Model Context Protocol) server configuration
├── default_settings.json    # Default settings loaded on startup
├── saved_configs/          # Archived timestamped configurations
│   └── YYYYMMDD-HHMMSS.json # Timestamped config snapshots
└── README.md               # This file
```

## Files

### `mcp.json`

Model Context Protocol (MCP) server configuration. This file defines which MCP servers are available to agents and their configuration (API keys, paths, etc.).

**Editing:** Use the MCP Settings tab in the Web UI or edit directly with a text editor.

**Git:** This file is gitignored by default (user-specific configuration).

### `default_settings.json`

Automatically loaded when the application starts. Contains your preferred settings for:

- LLM provider and model configuration
- Browser settings (headless, keep open, window size, etc.)
- MCP server configuration status
- Advanced agent parameters (max steps, temperature, etc.)

Save current settings as default using the "💾 Save as Default" button in the Settings panel.

### `saved_configs/`

Directory containing timestamped copies of settings saved via the "💾 Save" button. Each file is named with the format `YYYYMMDD-HHMMSS.json`.

These can be loaded later via the "📂 Load" button to restore previous configurations.

## What Gets Saved

**Persisted Settings:**

- MCP server configuration (`mcp.json`)
- LLM provider and model name
- LLM parameters (temperature, vision enable, etc.)
- Browser configuration (headless, keep open, window size, paths)
- Agent parameters (max steps, max actions, tool calling method)
- System prompts (override/extend)

**NOT Saved (Runtime Only):**

- Chat history
- Agent task state
- Browser context/instances
- Controller instances
- File uploads
- Button states
- Current task execution state

## Configuration Management

### Loading Default Settings

Default settings are automatically loaded on application startup.

### Saving Default Settings

1. Configure your settings in the Settings panel
2. Click "💾 Save as Default" button
3. Settings are saved to `default_settings.json`

### Loading Previous Configuration

1. Click "📂 Load" button
2. Select a `.json` file from `saved_configs/` directory (or upload your own)
3. Settings are restored and components update automatically

### Creating Timestamped Backup

1. Configure your settings
2. Click "💾 Save" button
3. A timestamped copy is saved to `saved_configs/YYYYMMDD-HHMMSS.json`

## Migration

Settings previously stored in `./tmp/webui_settings/` are automatically migrated to `./data/saved_configs/` on first startup after upgrading.
