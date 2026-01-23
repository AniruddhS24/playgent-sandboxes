import os
import json
import uuid
import logging
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from logging import getLogger
from typing import Literal, List, AsyncGenerator, Any, Union
import copy

import httpx
from blaxel.core import SandboxInstance
from pydantic_ai import Agent, Tool, RunContext, AgentRunResultEvent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelMessage,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    TextPartDelta,
)
from pydantic_core import to_jsonable_python
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from supabase import create_client, Client
from src.error import init_error_handlers, RecordNotFoundError, KeyPathError, SchemaValidationError
from src.templates import (
    TEMPLATE_STATE_HELPERS,
    TEMPLATE_ACTIONS_INIT,
    TEMPLATE_GMAIL_ACTIONS,
    TEMPLATE_CUSTOM_ACTIONS,
    TEMPLATE_MCP_SERVER,
)

supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
logging.getLogger("mcp.client").setLevel(logging.DEBUG)
logging.getLogger("pydantic_ai").setLevel(logging.DEBUG)

SYSTEM_PROMPT = open("src/system_prompt.txt", "r").read()


@dataclass
class RunDeps:
    thread_id: str
    user_id: str | None = None


def parse_sse_response(text: str) -> dict:
    """Parse Server-Sent Events response to extract JSON data.

    FastMCP's streamable-http transport returns responses in SSE format:
    event: message
    data: {"jsonrpc":"2.0",...}

    This function extracts the JSON from the data: line.
    """
    for line in text.split('\n'):
        if line.startswith('data: '):
            return json.loads(line[6:])  # Skip 'data: ' prefix
    raise ValueError("No data line found in SSE response")


def parse_key_path(key: str) -> List[Union[str, int]]:
    """Parse a dot-notation key path into a list of keys/indices.

    Args:
        key: Dot-notation path like "emails.0.subject"

    Returns:
        List of path segments, with integers for array indices

    Examples:
        "name" -> ["name"]
        "user.profile.name" -> ["user", "profile", "name"]
        "emails.0.subject" -> ["emails", 0, "subject"]
    """
    if not key or not key.strip():
        raise KeyPathError("Key path cannot be empty")

    parts = key.split(".")
    result = []
    for part in parts:
        if not part:
            raise KeyPathError(f"Invalid key path '{key}': contains empty segment")
        if part.isdigit():
            result.append(int(part))
        else:
            result.append(part)
    return result


def validate_key_exists(data: Any, path: List[Union[str, int]]) -> None:
    """Validate that the entire key path exists in the data structure.

    Raises:
        KeyPathError: If the key path doesn't exist or is invalid
    """
    current = data
    traversed = []

    for segment in path:
        traversed.append(str(segment))
        current_path = ".".join(traversed)

        if isinstance(current, dict):
            if segment not in current:
                available = list(current.keys())
                raise KeyPathError(
                    f"Key '{current_path}' does not exist. "
                    f"Available keys at this level: {available}"
                )
            current = current[segment]
        elif isinstance(current, list):
            if not isinstance(segment, int):
                raise KeyPathError(
                    f"Expected integer index at '{current_path}', got string '{segment}'"
                )
            if segment < 0 or segment >= len(current):
                raise KeyPathError(
                    f"Index {segment} out of bounds at '{current_path}'. "
                    f"Array has {len(current)} elements (indices 0-{len(current)-1})"
                )
            current = current[segment]
        else:
            parent_path = ".".join(traversed[:-1]) if len(traversed) > 1 else "(root)"
            raise KeyPathError(
                f"Cannot traverse into value at '{parent_path}': "
                f"expected dict or list, got {type(current).__name__}"
            )


def set_nested_value(data: dict, path: List[Union[str, int]], value: Any) -> dict:
    """Set a value at a nested path. Returns a deep copy with the modification."""
    data_copy = copy.deepcopy(data)

    current = data_copy
    for segment in path[:-1]:
        current = current[segment]

    current[path[-1]] = value
    return data_copy


def fetch_synthetic_data(
    ctx: RunContext[RunDeps],
    app: Literal["gmail"],
    search_pattern: str | None = None,
) -> list:
    """Fetch data from external database with optional regex filtering.

    Args:
        app: The app to fetch data for within the environment (gmail, slack, etc)
        search_pattern: Optional regex pattern to filter records (case-insensitive).
            Searches the entire json_data field as text.
            Examples:
              - "urgent" - find records containing "urgent"
              - "test@" - find email addresses starting with "test@"
              - "2024-01-\\d{2}" - find dates in January 2024

    Returns:
        List of matching records
    """
    response = supabase.table('artificial_data').select('*') \
        .eq("app", app) \
        .eq("environment_id", ctx.deps.thread_id) \
        .execute()

    if not search_pattern:
        return response.data

    # Filter using regex on json_data content
    try:
        pattern = re.compile(search_pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{search_pattern}': {e}")

    filtered = []
    for record in response.data:
        json_str = json.dumps(record.get("json_data", {}))
        if pattern.search(json_str):
            filtered.append(record)

    return filtered


def update_synthetic_data(
    ctx: RunContext[RunDeps],
    id: str,
    key: str,
    value: Any,
) -> dict:
    """Update a specific key within json_data of an existing record.

    This function performs a targeted update of a single key within the json_data
    field, rather than replacing the entire object. The key must already exist
    in the data structure.

    Args:
        id: The UUID of the record to update
        key: Dot-notation path to the key to update. Supports:
             - Simple keys: "name"
             - Nested objects: "user.profile.name"
             - Array indices: "emails.0.subject"
             - Mixed paths: "users.0.addresses.1.city"
        value: The new value to set at the specified key

    Returns:
        dict: The complete updated record

    Raises:
        RecordNotFoundError: If no record exists with the given id
        KeyPathError: If the key path is invalid or doesn't exist in json_data

    Examples:
        # Update email subject
        update_synthetic_data(ctx, "uuid-123", "emails.0.subject", "New Subject")

        # Update nested user field
        update_synthetic_data(ctx, "uuid-123", "user.profile.name", "John Doe")
    """
    # Fetch the current record
    response = supabase.table('artificial_data') \
        .select('*') \
        .eq("id", id) \
        .eq("environment_id", ctx.deps.thread_id) \
        .execute()

    if not response.data:
        raise RecordNotFoundError(
            f"Record with id '{id}' not found in environment '{ctx.deps.thread_id}'"
        )

    record = response.data[0]
    current_json_data = record.get("json_data", {})

    # Parse and validate the key path
    path = parse_key_path(key)
    validate_key_exists(current_json_data, path)

    # Update the value at the specified path
    updated_json_data = set_nested_value(current_json_data, path, value)

    # Save the updated json_data back to the database
    update_response = supabase.table('artificial_data') \
        .update({"json_data": updated_json_data}) \
        .eq("id", id) \
        .eq("environment_id", ctx.deps.thread_id) \
        .execute()

    return update_response.data[0] if update_response.data else record


def delete_synthetic_data(ctx: RunContext[RunDeps], id: str) -> str:
    """Delete a record from the artificial_data table.

    Args:
        id: The UUID of the record to delete

    Returns:
        Confirmation of deletion
    """
    response = supabase.table('artificial_data').delete().eq("id", id).eq("environment_id", ctx.deps.thread_id).execute()
    return response.data


async def reload_actions(ctx: RunContext[RunDeps]) -> str:
    """Reload the actions MCP server to pick up new or modified actions.

    Use this tool after writing new action files or modifying existing ones
    in the sandbox (e.g., /app/actions/custom.py) to make the new actions available.

    Returns:
        Confirmation message that actions were reloaded
    """
    environment_id = ctx.deps.thread_id
    sandbox = await SandboxInstance.get(f"sandbox-{environment_id}")

    # Kill existing MCP server
    try:
        await sandbox.process.kill("mcp-server")
        logger.info("Killed existing MCP server process for reload")
    except Exception:
        pass  # Process doesn't exist, that's fine

    # Restart MCP server
    await sandbox.process.exec({
        "name": "mcp-server",
        "command": "cd /app && python mcp_server.py",
        "env": {"PORT": "9000"},
        "waitForPorts": [9000]
    })

    logger.info(f"Reloaded actions MCP server for environment {environment_id}")
    return "Actions reloaded successfully. New tools are now available."


def fetch_schema(
    ctx: RunContext[RunDeps],
    app: str,
    component_name: str | None = None,
) -> list:
    """Fetch the JSON schema for a given app and optional component.

    Args:
        app: The app to fetch schema for (e.g., "gmail")
        component_name: Optional component name (e.g., "thread")

    Returns:
        List of schema records matching the query
    """
    query = supabase.table('schemas').select('*').eq("app", app)

    if component_name:
        query = query.eq("component_name", component_name)

    response = query.execute()
    return response.data


def validate_against_schema(data: dict, schema: dict) -> None:
    """Validate that data matches the expected schema structure.

    Checks that all required keys exist and types match.
    Raises SchemaValidationError if validation fails.
    """
    def check_structure(data_part, schema_part, path=""):
        if isinstance(schema_part, dict):
            if not isinstance(data_part, dict):
                raise SchemaValidationError(
                    f"Expected object at '{path}', got {type(data_part).__name__}"
                )
            for key, value in schema_part.items():
                if key not in data_part:
                    raise SchemaValidationError(
                        f"Missing required key '{path}.{key}'" if path else f"Missing required key '{key}'"
                    )
                check_structure(data_part[key], value, f"{path}.{key}" if path else key)
        elif isinstance(schema_part, list) and len(schema_part) > 0:
            if not isinstance(data_part, list):
                raise SchemaValidationError(
                    f"Expected array at '{path}', got {type(data_part).__name__}"
                )
            # Validate each item against the first schema element
            for i, item in enumerate(data_part):
                check_structure(item, schema_part[0], f"{path}[{i}]")

    check_structure(data, schema)


def insert_synthetic_data(
    ctx: RunContext[RunDeps],
    app: str,
    component_name: str,
    json_data: dict,
) -> dict:
    """Insert a new record into the artificial_data table.

    The json_data must match the schema for the given app/component_name.
    Use fetch_schema first to see the required structure.

    Args:
        app: The app name (e.g., "gmail")
        component_name: The component name (e.g., "thread")
        json_data: The data to insert (must match schema)

    Returns:
        The inserted record

    Raises:
        SchemaValidationError: If json_data doesn't match the schema
        ValueError: If no schema found for app/component_name
    """
    # Fetch the schema
    schema_response = supabase.table('schemas') \
        .select('schema') \
        .eq("app", app) \
        .eq("component_name", component_name) \
        .execute()

    if not schema_response.data:
        raise ValueError(f"No schema found for app='{app}', component_name='{component_name}'")

    schema_str = schema_response.data[0]["schema"]
    schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str

    # Validate the data against schema
    validate_against_schema(json_data, schema)

    # Insert the record
    insert_response = supabase.table('artificial_data').insert({
        "app": app,
        "component_name": component_name,
        "json_data": json_data,
        "environment_id": ctx.deps.thread_id,
    }).execute()

    return insert_response.data[0] if insert_response.data else {}


def load_thread_history(thread_id: str) -> List[ModelMessage]:
    """Load all messages for a thread, ordered by creation time."""
    response = supabase.table('messages') \
        .select('message') \
        .eq('thread_id', thread_id) \
        .order('created_at', desc=False) \
        .execute()

    all_messages: List[ModelMessage] = []
    for row in response.data:
        # Each row is one message - deserialize individually
        msg_data = row['message']
        # Handle case where message is stored as JSON string
        if isinstance(msg_data, str):
            msg_data = json.loads(msg_data)
        message = ModelMessagesTypeAdapter.validate_python([msg_data])[0]
        all_messages.append(message)
    return all_messages


def save_messages(thread_id: str, messages: List[ModelMessage], user_id: str = "") -> None:
    """Save messages to the database (one row per message)."""
    rows = []
    for msg in messages:
        msg_json = to_jsonable_python(msg)
        rows.append({
            'thread_id': thread_id,
            'user_id': user_id,
            'message_kind': msg_json.get('kind', 'unknown'),
            'message': msg_json
        })
    supabase.table('messages').insert(rows).execute()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Server running on port {os.getenv('PORT', 80)}")
    yield
    logger.info("Server shutting down")


app = FastAPI(lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)
init_error_handlers(app)

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    # Handle preflight OPTIONS requests
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With, Accept, Origin, X-Request-Id, X-Blaxel-Request-Id, X-Pharmacy-Authorization"
        )
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Access-Control-Expose-Headers"] = "X-Request-Id, X-Blaxel-Request-Id"
        return response

    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)

    # Add CORS headers to all responses
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Requested-With, Accept, Origin, X-Request-Id, X-Blaxel-Request-Id, X-Pharmacy-Authorization"
    )
    response.headers["Access-Control-Max-Age"] = "86400"
    response.headers["Access-Control-Expose-Headers"] = "X-Request-Id, X-Blaxel-Request-Id"

    return response


async def bootstrap_sandbox_actions(sandbox_name: str, environment_id: str) -> str:
    """Write action templates to sandbox and start MCP server using Blaxel SDK.

    Returns the preview URL for the action MCP server.
    """
    sandbox = await SandboxInstance.get(sandbox_name)

    # Write all template files at once using write_tree
    files = [
        {"path": "state_helpers.py", "content": TEMPLATE_STATE_HELPERS},
        {"path": "actions/__init__.py", "content": TEMPLATE_ACTIONS_INIT},
        {"path": "actions/gmail.py", "content": TEMPLATE_GMAIL_ACTIONS},
        {"path": "actions/custom.py", "content": TEMPLATE_CUSTOM_ACTIONS},
        {"path": "mcp_server.py", "content": TEMPLATE_MCP_SERVER},
    ]
    await sandbox.fs.write_tree(files, "/app")
    logger.info("Wrote all template files to /app")

    # Load any custom actions from Supabase and append to custom.py
    actions_response = supabase.table('actions').select('*') \
        .eq("environment_id", environment_id) \
        .eq("is_preset", False) \
        .execute()

    if actions_response.data:
        custom_code = TEMPLATE_CUSTOM_ACTIONS + "\n\n"
        custom_code += "\n\n".join(a["code"] for a in actions_response.data)
        await sandbox.fs.write("/app/actions/custom.py", custom_code)
        logger.info(f"Loaded {len(actions_response.data)} custom actions from Supabase")

    # Step 1: Install dependencies
    try:
        logger.info("Installing dependencies...")
        await sandbox.process.exec({
            "name": "pip-install",
            "command": "cd /app && pip install supabase mcp",
            "waitForCompletion": True
        })
        logger.info("Dependencies installed")

        # Step 2: Kill existing MCP server if running (for re-initialization)
        try:
            await sandbox.process.kill("mcp-server")
            logger.info("Killed existing MCP server process")
        except Exception:
            pass  # Process doesn't exist, that's fine

        # Step 3: Start MCP server on port 9000 (port 80 is reserved for previews)
        logger.info("Starting MCP server on port 9000...")
        await sandbox.process.exec({
            "name": "mcp-server",
            "command": "cd /app && python mcp_server.py",
            "env": {"PORT": "9000"},
            "waitForPorts": [9000]
        })
        logger.info("MCP server started and listening on port 9000")

        # Step 3: Get logs from mcp-server to see any errors
        logs = await sandbox.process.logs("mcp-server")
        logger.info(f"MCP server logs: {logs[:2000]}")

        # Step 4: Create preview URL for the MCP server
        preview = await sandbox.previews.create_if_not_exists({
            "metadata": {"name": "action-mcp"},
            "spec": {"port": 9000, "public": True}
        })
        action_mcp_url = preview.spec.url
        logger.info(f"Created preview URL: {action_mcp_url}")

        return action_mcp_url
    except Exception as e:
        logger.warning(f"Failed to start MCP server: {e}")
        return ""


@app.post("/environment/{environment_id}/initialize")
async def initialize_environment(environment_id: str):
    """Create and bootstrap sandbox for an environment. Call once per environment."""

    # 1. Create sandbox
    sandbox = await SandboxInstance.create_if_not_exists({
        "name": f"sandbox-{environment_id}",
        "image": "blaxel/py-app:latest",
        "memory": 4096,
        "ports": [
            {"name": "preview", "target": 3000},
            {"name": "action-mcp", "target": 9000}
        ],
        "envs": [
            {"name": "SUPABASE_URL", "value": os.getenv("SUPABASE_URL")},
            {"name": "SUPABASE_KEY", "value": os.getenv("SUPABASE_KEY")},
            {"name": "ENVIRONMENT_ID", "value": environment_id},
            {"name": "RELACE_API_KEY", "value": os.getenv("RELACE_API_KEY")},
        ]
    })

    # 2. Bootstrap filesystem and start MCP server, get preview URL
    action_mcp_url = await bootstrap_sandbox_actions(f"sandbox-{environment_id}", environment_id)

    return {
        "status": "initialized",
        "environment_id": environment_id,
        "action_mcp_url": action_mcp_url,
        "sandbox_url": f"{sandbox.metadata.url}/mcp",
    }


@app.post("/")
async def handle_request(request: Request):
    body = await request.json()
    user_message = body.get("inputs", "")
    thread_id = body.get("thread_id") or str(uuid.uuid4())
    user_id = body.get("user_id", None)

    if not user_message:
        return {"error": "Please provide an input message", "thread_id": thread_id}

    # Load existing conversation history if continuing a thread
    message_history: List[ModelMessage] = []
    if body.get("thread_id"):
        logger.info(f"Loading history for thread: {thread_id}")
        message_history = load_thread_history(thread_id)
        logger.info(f"Loaded {len(message_history)} messages from history")

    async def stream_response() -> AsyncGenerator[str, None]:
        # Connect to sandbox MCP (assumes already initialized via /environment/{id}/initialize)
        sandbox = await SandboxInstance.get(f"sandbox-{thread_id}")
        sandbox_url = f"{sandbox.metadata.url}/mcp"

        logger.info(f"Creating MCP connection to sandbox at {sandbox_url}...")
        sandbox_mcp = MCPServerStreamableHTTP(
            sandbox_url,
            headers={"Authorization": f"Bearer {os.getenv('BLAXEL_API_KEY')}"}
        )

        # Create agent with sandbox MCP as toolset (exposes all sandbox tools)
        agent = Agent(
            'anthropic:claude-sonnet-4-0',
            system_prompt=SYSTEM_PROMPT,
            deps_type=RunDeps,
            toolsets=[sandbox_mcp],
            tools=[
                Tool(fetch_schema),
                Tool(fetch_synthetic_data),
                Tool(insert_synthetic_data),
                Tool(update_synthetic_data),
                Tool(delete_synthetic_data),
                Tool(reload_actions),
            ],
        )

        logger.info("Entering agent context manager...")
        async with agent:
            logger.info(f"Running agent with message: {user_message}")
            logger.info(f"Message History: {message_history}")
            try:
                result = None
                deps = RunDeps(thread_id=thread_id, user_id=user_id)
                async for event in agent.run_stream_events(
                    user_message,
                    message_history=message_history,
                    deps=deps,
                ):
                    if isinstance(event, AgentRunResultEvent):
                        result = event.result
                    elif isinstance(event, FunctionToolCallEvent):
                        yield f"data: {json.dumps({'event': 'tool_call', 'tool_name': event.part.tool_name, 'args': event.part.args})}\n\n"
                    elif isinstance(event, FunctionToolResultEvent):
                        yield f"data: {json.dumps({'event': 'tool_result', 'tool_name': event.result.tool_name, 'result': str(event.content)})}\n\n"
                    elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                        yield f"data: {json.dumps({'text': event.delta.content_delta})}\n\n"

                # Save messages to Supabase
                if result:
                    new_messages = result.new_messages()
                    save_messages(thread_id, new_messages, user_id)
                    logger.info(f"Saved {len(new_messages)} messages for thread: {thread_id}")

                # Send final event with thread_id
                yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"

            except Exception as e:
                raise e
                logger.error(f"Agent error: {e}")
                yield f"data: {json.dumps({'error': str(e), 'thread_id': thread_id})}\n\n"

        logger.info("Agent context closed successfully")

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/environment/{environment_id}/state/{id}")
async def get_state_item(environment_id: str, id: str):
    """Get a single state item by ID within an environment."""
    response = supabase.table('artificial_data') \
        .select('*') \
        .eq("id", id) \
        .eq("environment_id", environment_id) \
        .execute()

    if not response.data:
        raise HTTPException(status_code=404, detail=f"Item '{id}' not found")

    return response.data[0]


@app.get("/environment/{environment_id}/state")
async def list_state_items(
    environment_id: str,
    app: str | None = None,
    component_name: str | None = None,
):
    """List state items with optional filters."""
    query = supabase.table('artificial_data') \
        .select('*') \
        .eq("environment_id", environment_id)

    if app:
        query = query.eq("app", app)
    if component_name:
        query = query.eq("component_name", component_name.lower())

    response = query.execute()
    return response.data


@app.post("/environment/{environment_id}/state/reset")
async def reset_state(environment_id: str):
    """Reset all state data for an environment."""
    response = supabase.table('artificial_data') \
        .delete() \
        .eq("environment_id", environment_id) \
        .execute()

    return {"message": "Environment state reset", "deleted_count": len(response.data)}


@app.post("/environment/{environment_id}/action/{action_name}")
async def execute_action(environment_id: str, action_name: str, request: Request):
    """Execute a specific action via sandbox MCP."""
    body = await request.json()
    arguments = body.get("arguments", {})

    # Get the preview URL for the action MCP
    sandbox = await SandboxInstance.get(f"sandbox-{environment_id}")
    preview = await sandbox.previews.get("action-mcp")
    sandbox_action_url = f"{preview.spec.url}/mcp"  # FastMCP serves at /mcp path

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {os.getenv('BLAXEL_API_KEY')}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        },
        timeout=30.0
    ) as client:
        try:
            response = await client.post(sandbox_action_url, json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 1,
                "params": {
                    "name": action_name,
                    "arguments": arguments
                }
            })

            # Check if response is valid before parsing JSON
            if response.status_code != 200:
                logger.warning(f"Action MCP returned status {response.status_code}: {response.text[:200]}")
                raise HTTPException(status_code=503, detail=f"Action server returned status {response.status_code}")

            # Parse SSE response format from streamable-http transport
            try:
                result = parse_sse_response(response.text)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Action MCP returned invalid response: {response.text[:200]}")
                raise HTTPException(status_code=503, detail=f"Action server returned invalid response: {e}")

            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])

            return result.get("result")
        except httpx.RequestError as e:
            logger.warning(f"Failed to connect to action MCP: {e}")
            raise HTTPException(status_code=503, detail=f"Failed to connect to action server: {e}")


@app.get("/environment/{environment_id}/action")
async def list_actions_endpoint(environment_id: str):
    """List available actions from sandbox MCP."""
    # Get the preview URL for the action MCP
    sandbox = await SandboxInstance.get(f"sandbox-{environment_id}")
    preview = await sandbox.previews.get("action-mcp")
    sandbox_action_url = f"{preview.spec.url}/mcp"  # FastMCP serves at /mcp path

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {os.getenv('BLAXEL_API_KEY')}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        },
        timeout=30.0
    ) as client:
        try:
            response = await client.post(sandbox_action_url, json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            })

            if response.status_code != 200:
                logger.warning(f"Action MCP returned status {response.status_code}: {response.text[:200]}")
                raise HTTPException(status_code=503, detail=f"Action server returned status {response.status_code}")

            # Parse SSE response format from streamable-http transport
            try:
                result = parse_sse_response(response.text)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Action MCP returned invalid response: {response.text[:200]}")
                raise HTTPException(status_code=503, detail=f"Action server returned invalid response: {e}")

            return result.get("result", {}).get("tools", [])
        except httpx.RequestError as e:
            logger.warning(f"Failed to connect to action MCP: {e}")
            raise HTTPException(status_code=503, detail=f"Failed to connect to action server: {e}")


@app.get("/environment/{environment_id}/mcp")
async def get_action_mcp_url(environment_id: str):
    """Get the MCP URL for environment actions."""
    sandbox = await SandboxInstance.get(f"sandbox-{environment_id}")
    preview = await sandbox.previews.get("action-mcp")
    return {"mcp_url": f"{preview.spec.url}/mcp"}



FastAPIInstrumentor.instrument_app(app, exclude_spans=["receive", "send"])
