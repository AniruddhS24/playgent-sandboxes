import os
import logging
from contextlib import asynccontextmanager
from logging import getLogger

import httpx
from blaxel.core import SandboxInstance
from pydantic_ai import Agent, Tool
from pydantic_ai.mcp import MCPServerStreamableHTTP
from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
logging.getLogger("mcp.client").setLevel(logging.DEBUG)
logging.getLogger("pydantic_ai").setLevel(logging.DEBUG)

SYSTEM_PROMPT = """You are a coding agent that can write, edit, and execute TypeScript/JavaScript code in a Node.js sandbox environment.

## Environment
- **Runtime**: Node.js with TypeScript support
- **Package Manager**: npm/pnpm available
- **Primary Languages**: TypeScript (.ts), JavaScript (.js)
- **Working Directory**: /blaxel

## Available Tools via MCP

### File Operations:
- **fsReadFile** - Read file contents
- **fsWriteFile** - Create or update entire files
- **fsListDirectory** - List directory contents
- **codegenListDir** - Directory listing (optimized for codegen)

### Intelligent Code Editing:
- **codegenEditFile** - Apply targeted edits to existing files (RECOMMENDED for modifications)
  - Uses AI-powered editing (Relace backend)
  - Much faster than rewriting entire files
  - Format: Provide clear instructions like "add a function to calculate circle area"
- **codegenParallelApply** - Apply same edit across multiple files
- **codegenReapply** - Retry failed edits

### Code Search & Discovery:
- **codegenFileSearch** - Fast filename matching
- **codegenGrepSearch** - Pattern/text search in files
- **codegenCodebaseSearch** - Semantic code search
- **codegenReadFileRange** - Read specific line ranges (max 250 lines)
- **codegenRerank** - Semantic reranking of search results

### Execution:
- **processExecute** - Run shell commands, npm scripts, or node programs
  - Examples: `npm install`, `node script.js`, `tsc --noEmit`

### Other Tools:
- **fetch_data** - Fetch data from external databases (placeholder)

## Workflow
1. **Search & Read**: Use codegen search tools to understand existing code structure
2. **Edit Efficiently**: Prefer `codegenEditFile` for modifications over full rewrites
3. **Write New Files**: Use `fsWriteFile` only for new files
4. **Execute & Test**: Run code with `processExecute` (e.g., `node file.js`, `npm test`)
5. **Iterate**: Fix errors by reading output and applying targeted edits

## Best Practices
- **Always use TypeScript/JavaScript** - This is a Node.js environment
- **Use targeted edits** - `codegenEditFile` is faster than rewriting files
- **Test your code** - Execute and verify output
- **Install dependencies** - Use `npm install <package>` when needed

Be concise and iterate until the task is complete."""


def fetch_data(query: str) -> str:
    """Fetch data from external database.

    Args:
        query: The query to fetch data for

    Returns:
        The fetched data as a string
    """
    # TODO: Implement actual database fetching
    return f"TODO: fetch data for query: {query}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Server running on port {os.getenv('PORT', 80)}")
    yield
    logger.info("Server shutting down")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_request(request: Request, call_next):
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    return response

@app.post("/")
async def handle_request(request: Request):
    body = await request.json()
    user_message = body.get("inputs", "")

    if not user_message:
        return {"response": "Please provide an input message"}
    
    sandbox = await SandboxInstance.create_if_not_exists({
        "name": "playgent-coding-sandbox-ts",
        "image": "blaxel/ts-app:latest",
        "memory": 4096,
        "ports": [
            { "name": "preview", "target": 3000 }
        ],
        "envs": [
            { "name": "RELACE_API_KEY", "value": os.getenv("RELACE_API_KEY") },
        ]
    })
    
    # Connect to sandbox MCP with auth (get URL from sandbox instance)
    sandbox_url = "https://run.blaxel.ai/pharmie-agents/sandboxes/codegen-sandbox/mcp"

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {os.getenv('BLAXEL_API_KEY')}"}
    ) as http_client:
        logger.info(f"Creating MCP connection to sandbox at {sandbox_url}...")
        sandbox_mcp = MCPServerStreamableHTTP(
            sandbox_url,
            http_client=http_client,
        )

        # Create agent with sandbox tools + custom tools
        agent = Agent(
            'anthropic:claude-sonnet-4-0',
            system_prompt=SYSTEM_PROMPT,
            toolsets=[sandbox_mcp],
            tools=[Tool(fetch_data)],
        )

        logger.info("Entering agent context manager...")
        async with agent:
            # Run agent
            logger.info(f"Running agent with message: {user_message}")
            result = await agent.run(user_message)

            # Log raw result
            logger.info(f"Agent completed. Raw result: {result}")

        logger.info("Agent context closed successfully")

    return {"response": result.output}


FastAPIInstrumentor.instrument_app(app, exclude_spans=["receive", "send"])
