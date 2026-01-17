# Gmail Sandbox Agent

A Blaxel-hosted AI agent that generates and executes TypeScript code to create synthetic Gmail data in sandbox environments.

## Overview

This agent receives natural language requests for Gmail data generation and:
1. Creates/connects to a Gmail sandbox
2. Uses an LLM (Claude Sonnet 4.5) to generate TypeScript code
3. Writes and executes the code in the sandbox using MCP tools
4. Returns the results to the user

## Architecture

```
User Request → Agent → LLM generates code → Sandbox MCP Tools → Execute in Gmail Sandbox → Return Results
```

## Prerequisites

1. **Gmail Sandbox Deployed**: First deploy the Gmail sandbox template:
   ```bash
   cd ../gmail
   bl deploy
   ```
   Note the image name (e.g., `your-workspace/gmail:latest`)

2. **Update Configuration**: Update `GMAIL_SANDBOX_IMAGE` in `blaxel.toml` with your deployed Gmail sandbox image name

3. **Blaxel CLI**: Ensure you're logged in:
   ```bash
   bl login your-workspace
   ```

## Local Development

### 1. Install Dependencies

```bash
pnpm install
```

### 2. Serve Locally

```bash
bl serve --hotreload
```

The agent will be available at `http://localhost:8080`

### 3. Test the Agent

```bash
# Basic test
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"inputs": "Create 10 test emails with various labels"}'

# With user ID
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"inputs": "Create 50 support emails with urgent labels", "userId": "user123"}'
```

## Deployment

### Deploy to Blaxel

```bash
bl deploy
```

### Test Deployed Agent

```bash
# Using Blaxel CLI
bl chat sandboxing-agent

# Using curl
curl -X POST https://run.blaxel.ai/{your-workspace}/agents/sandboxing-agent \
  -H "Authorization: Bearer $(bl token)" \
  -H "Content-Type: application/json" \
  -d '{"inputs": "Create 20 onboarding emails for new employees"}'
```

## Usage Examples

### Example 1: Generate Test Messages

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": "Create 50 emails from the last week with various labels",
    "userId": "test-user"
  }'
```

**What happens:**
1. Agent creates/connects to `gmail-sandbox-test-user`
2. LLM generates TypeScript code using `generateTestMessages()`
3. Code is written to `/app/seed-script.ts` in the sandbox
4. Code is executed with `npx ts-node`
5. Results are returned

### Example 2: Custom Support Inbox

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": "Set up a support inbox with 10 urgent tickets and 5 draft responses"
  }'
```

**Generated code might look like:**
```typescript
import { initializeGmailSandbox, GmailMessage, GmailDraft } from '/app/src/gmail';

async function seed() {
  const urgentTickets: GmailMessage[] = [];
  for (let i = 0; i < 10; i++) {
    urgentTickets.push({
      subject: `Urgent: Customer Issue #${i + 1}`,
      to: 'support@company.com',
      from: `customer${i}@example.com`,
      body: 'Need immediate help with...',
      labels: ['INBOX', 'URGENT']
    });
  }

  const responses: GmailDraft[] = urgentTickets.slice(0, 5).map((ticket, i) => ({
    subject: `Re: ${ticket.subject}`,
    to: ticket.from!,
    from: 'support@company.com',
    body: 'Thank you for contacting us. We are looking into your issue...'
  }));

  await initializeGmailSandbox('support-sandbox', {
    messages: urgentTickets,
    drafts: responses
  });

  console.log('Created 10 urgent tickets and 5 draft responses');
}

seed().catch(console.error);
```

### Example 3: Email Thread Simulation

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": "Create a conversation thread about Q1 planning with 4 replies"
  }'
```

## Response Format

### Success Response

```json
{
  "success": true,
  "message": "Successfully created 50 messages and 10 drafts in the Gmail sandbox.",
  "sandbox": {
    "name": "gmail-sandbox-user123",
    "status": "active",
    "image": "gmail:latest"
  },
  "toolCalls": [
    {
      "toolName": "fsWriteFile",
      "args": {
        "path": "/app/seed-script.ts",
        "content": "..."
      }
    },
    {
      "toolName": "processExecute",
      "args": {
        "command": "npx ts-node /app/seed-script.ts"
      },
      "result": "Created 50 messages\n..."
    }
  ],
  "usage": {
    "promptTokens": 2500,
    "completionTokens": 800,
    "totalTokens": 3300
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message",
  "details": "Stack trace..."
}
```

## How It Works

### 1. Request Processing

The agent receives a POST request with:
- `inputs`: Natural language description of Gmail data to create
- `userId` (optional): User identifier for sandbox isolation

### 2. Sandbox Connection

The agent creates or connects to a Gmail sandbox:
- Sandbox name: `gmail-sandbox-{userId}`
- Uses the Gmail sandbox template image
- 8GB memory allocation
- Isolated per user

### 3. Tool Loading

The agent loads sandbox MCP tools:
- `fsWriteFile`: Write code files
- `fsReadFile`: Read files
- `processExecute`: Execute commands
- `codegenEditFile`: AI-assisted editing
- Other filesystem and process tools

### 4. Code Generation

Claude Sonnet 4.5 generates TypeScript code that:
- Uses the Gmail Sandbox API (`/app/src/gmail/`)
- Creates messages, drafts, or both
- Uses helper functions or custom logic
- Includes proper error handling and logging

### 5. Execution

The agent:
1. Writes generated code to `/app/seed-script.ts`
2. Executes with `npx ts-node /app/seed-script.ts`
3. Captures output and errors
4. Returns results to user

### 6. Sandbox Persistence

- Sandbox remains in standby after request completes
- Resumes in <25ms for next request
- Data persists in sandbox filesystem (in-memory)
- Auto-scales to zero when idle

## Available Gmail API Methods

The generated code can use these methods from `/app/src/gmail/`:

### Initialization
- `initializeGmailSandbox(sandboxId, { messages?, drafts? })`

### Messages
- `createMessage(message, userConfig?)`
- `createMessages(messages, userConfig?)`
- `getMessage(messageId)`
- `listMessages(options?)`
- `deleteMessage(messageId)`
- `updateMessageLabels(messageId, addLabels?, removeLabels?)`

### Drafts
- `createDraft(draft, userConfig?)`
- `createDrafts(drafts, userConfig?)`
- `getDraft(draftId)`
- `listDrafts(options?)`
- `updateDraft(draftId, updates)`
- `deleteDraft(draftId)`
- `sendDraft(draftId)`

### Helpers
- `generateTestMessages(count, options?)`
- `generateTestDrafts(count, options?)`

## Configuration

### blaxel.toml

```toml
type = "agent"
name = "sandboxing-agent"

# Preload model access for better performance
models = ["claude-sonnet-4-5"]

[runtime]
generation = "mk3"
memory = 4096
timeout = 300

[env]
# Gmail sandbox template name
GMAIL_SANDBOX_IMAGE = "gmail:latest"
```

## Troubleshooting

### Sandbox Not Found

**Error**: "Sandbox image 'gmail:latest' not found"

**Solution**: Deploy the Gmail sandbox template first:
```bash
cd ../gmail
bl deploy
```

Update `GMAIL_SANDBOX_IMAGE` in `blaxel.toml` with the deployed image name.

### Code Execution Errors

**Error**: "Cannot find module '/app/src/gmail'"

**Solution**: Ensure the Gmail sandbox template includes the Gmail API files at `/app/src/gmail/`

### Memory Issues

**Error**: "Out of memory"

**Solution**: The Gmail sandbox uses 8GB RAM. If you need more, update the `memory` setting in the sandbox creation code.

### Timeout Errors

**Error**: "Request timeout"

**Solution**: Increase the `timeout` setting in `blaxel.toml` (currently 300 seconds)

## Development Tips

### Testing Locally

1. **Mock Sandbox**: For faster local testing, you can mock the sandbox connection
2. **Logging**: Check console output for detailed execution logs
3. **Hot Reload**: Use `bl serve --hotreload` for live code updates

### Debugging Generated Code

To see the generated code, check the `toolCalls` array in the response:

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"inputs": "Create 5 test emails"}' | jq .toolCalls
```

### Customizing System Prompt

Edit the `systemPrompt` in `src/index.ts` to:
- Add more examples
- Change code style
- Add specific constraints
- Improve error handling

## Next Steps

1. **Add Supabase**: Integrate Supabase to persist Gmail data
2. **Preview URL**: Create preview URLs for viewing generated data
3. **Multi-agent**: Chain with other agents for complex workflows
4. **Volumes**: Use volumes for long-term data persistence
5. **UI Layer**: Build a UI to visualize generated Gmail data

## Resources

- [Blaxel Documentation](https://docs.blaxel.ai)
- [Gmail Sandbox API Docs](../gmail/GMAIL_API.md)
- [Implementation Plan](../.claude/plans/sunny-zooming-milner.md)

## License

MIT
