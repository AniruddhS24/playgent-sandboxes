import os
import sys
import importlib

# Add app directory to path
sys.path.insert(0, '/app')

from mcp.server.fastmcp import FastMCP
from actions import ACTION_REGISTRY

# Host/port MUST be in constructor per Blaxel docs (not in mcp.run())
mcp = FastMCP(
    "EnvironmentActions",
    stateless_http=True,
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "9000"))
)

# Import action modules to trigger registration
for module in ['gmail', 'custom']:
    try:
        importlib.import_module(f'actions.{module}')
        print(f"Successfully imported actions.{module}")
    except ImportError as e:
        print(f"Warning: Could not import actions.{module}: {e}")

# Register actions as MCP tools
for name, info in ACTION_REGISTRY.items():
    mcp.tool(name=name, description=info['description'])(info['func'])
    print(f"Registered action: {name}")

if __name__ == "__main__":
    print(f"Starting MCP server with {len(ACTION_REGISTRY)} actions")
    sys.stdout.flush()
    mcp.run(transport="streamable-http")
