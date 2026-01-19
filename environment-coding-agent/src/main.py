import os
from contextlib import asynccontextmanager
from logging import getLogger

from blaxel.core import SandboxInstance
# from blaxel.pydantic import bl_tools
from fastapi import FastAPI, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


logger = getLogger(__name__)

SYSTEM_PROMPT = """You are a coding assistant that can write and execute code in a sandbox environment.

You have access to two tools:
1. write_file - Write code or content to files in the sandbox
2. execute_command - Run shell commands (e.g., python script.py, pip install, etc.)

When asked to write and run code:
1. First write the code to a file using write_file
2. Then execute it using execute_command

Be concise and helpful. After executing code, summarize the results."""


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

# Main inference endpoitn
@app.post("/")
async def handle_request(request: Request):
    body = await request.json()
    user_message = body.get("inputs", "")

    if not user_message:
        return {"response": "Please provide an input message"}

    # Create or get sandbox
    sandbox = await SandboxInstance.create_if_not_exists({
        "name": "coding-agent-sandbox-testing",
        "image": "blaxel/base-image:latest",
        "memory": 4096,
    })

    files = [
        {"path": "src/gmail_api.py", "content": "<put the file content>"},
        {"path": "src/runner.py", "content": "<file content>"}
    ]
    await sandbox.fs.write_tree(files, "/blaxel/app")


    # model = await bl_model("claude-sonnet-4-5-20250929")
    # codegen_tools = await bl_tools([f"sandboxes/{sandbox.metadata.name}"])
    
    # Agent loop
    while True:
        # Run the model given user_message and a system prompt (need to write)
        # Get the model's code-gen output
        result = sandbox.process.exec("python3 src/runner.py")
        # if result == "success"
        break

    return {"response": "final model response"}


FastAPIInstrumentor.instrument_app(app, exclude_spans=["receive", "send"])
