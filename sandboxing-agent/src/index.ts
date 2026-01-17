import '@blaxel/telemetry';
import Fastify from "fastify";
import { SandboxInstance, env } from "@blaxel/core";
import { blModel } from "@blaxel/vercel";
import { generateText } from "ai";

interface RequestBody {
  inputs: string;
  userId?: string;
}

interface ExecutionError {
  type: 'syntax' | 'runtime' | 'module_not_found' | 'timeout' | 'unknown';
  message: string;
  stack?: string;
  missingModule?: string;
}

interface AttemptRecord {
  iteration: number;
  timestamp: string;
  generatedCode: string;
  executionLogs: string;
  success: boolean;
  error?: ExecutionError;
}

interface IterationState {
  currentIteration: number;
  conversationHistory: Array<{ role: string; content: string }>;
  attemptLog: AttemptRecord[];
  lastGeneratedCode: string;
  lastError: ExecutionError | null;
}

interface AgenticResult {
  success: boolean;
  iterations: number;
  output: string;
  generatedCode: string;
  attemptLog: AttemptRecord[];
  error?: ExecutionError;
  sandbox: {
    name: string;
    image: string;
  };
}

function parseExecutionError(logs: string): ExecutionError | null {
  // TypeScript compilation errors
  const tsErrorMatch = logs.match(/TSError: ⨯ Unable to compile TypeScript:\n(.+?)(?:\n\n|$)/s);
  if (tsErrorMatch) {
    const errorDetails = tsErrorMatch[1];

    // Check for module not found
    if (errorDetails.includes("Cannot find module")) {
      const moduleMatch = errorDetails.match(/Cannot find module '([^']+)'/);
      return {
        type: 'module_not_found',
        message: errorDetails.trim(),
        missingModule: moduleMatch?.[1]
      };
    }

    return {
      type: 'syntax',
      message: errorDetails.trim()
    };
  }

  // Runtime errors
  if (logs.includes('Error:') && !logs.includes('TSError:')) {
    const errorMatch = logs.match(/(\w+Error): (.+?)(?:\n|$)/);
    if (errorMatch) {
      return {
        type: 'runtime',
        message: `${errorMatch[1]}: ${errorMatch[2]}`,
        stack: logs.match(/at .+?:\d+:\d+/g)?.join('\n')
      };
    }
  }

  // Check for process failure
  if (logs.includes('exit code 1') || logs.includes('Command failed')) {
    return {
      type: 'unknown',
      message: logs.substring(0, 500)
    };
  }

  return null;
}

function getErrorGuidance(error: ExecutionError): string {
  switch (error.type) {
    case 'module_not_found':
      return `The import path is incorrect. Fix:
- Use ABSOLUTE path: import { ... } from '/app/src/gmail';
- NOT relative path like './src/gmail'
- The Gmail API files are located at /app/src/gmail/`;

    case 'syntax':
      return `There is a TypeScript syntax error. Common fixes:
- Check for missing brackets, parentheses, or semicolons
- Verify type annotations are correct
- Ensure all variables are properly declared`;

    case 'runtime':
      return `The code compiled but failed during execution. Common fixes:
- Check for null/undefined references
- Verify async/await usage is correct
- Add proper error handling with try-catch`;

    default:
      return `Review the error carefully and fix the issue.`;
  }
}

function buildErrorFixPrompt(
  originalRequest: string,
  lastCode: string,
  error: ExecutionError,
  iteration: number
): string {
  return `You previously generated TypeScript code that FAILED to execute.

ORIGINAL USER REQUEST:
${originalRequest}

YOUR PREVIOUS CODE (Attempt ${iteration - 1}):
\`\`\`typescript
${lastCode}
\`\`\`

EXECUTION ERROR:
Type: ${error.type}
${error.missingModule ? `Missing Module: ${error.missingModule}\n` : ''}Message:
${error.message}

${getErrorGuidance(error)}

Generate CORRECTED TypeScript code that fixes this error.
Return ONLY the complete corrected TypeScript code with no explanations or markdown formatting.`;
}

async function executeAgenticLoop(
  inputs: string,
  sandbox: SandboxInstance,
  sandboxName: string,
  gmailSandboxImage: string
): Promise<AgenticResult> {
  const MAX_ITERATIONS = 5;
  const state: IterationState = {
    currentIteration: 0,
    conversationHistory: [],
    attemptLog: [],
    lastGeneratedCode: '',
    lastError: null
  };

  const systemPrompt = `Generate TypeScript code for Gmail sandbox.

Available Gmail functions at /app/src/gmail/index.ts:
- initializeGmailSandbox(sandboxId, { messages?, drafts? })
- generateTestMessages(count, options?)
- generateTestDrafts(count, options?)
- createMessage(message), createDraft(draft)

IMPORTANT: Use ABSOLUTE import path:
import { initializeGmailSandbox, generateTestMessages } from '/app/src/gmail';

Return ONLY the TypeScript code, no explanations or markdown.

Example:
import { initializeGmailSandbox, generateTestMessages } from '/app/src/gmail';

async function seed() {
  const messages = generateTestMessages(10, { labels: ['INBOX'] });
  await initializeGmailSandbox('${sandboxName}', { messages });
  console.log(\`Created \${messages.length} messages\`);
}

seed().catch(console.error);`;

  while (state.currentIteration < MAX_ITERATIONS) {
    state.currentIteration++;
    console.info(`[Agentic Loop] Starting iteration ${state.currentIteration}/${MAX_ITERATIONS}`);

    try {
      // STEP 1: Generate or fix code
      const userMessage = state.currentIteration === 1
        ? inputs
        : buildErrorFixPrompt(inputs, state.lastGeneratedCode, state.lastError!, state.currentIteration);

      state.conversationHistory.push({ role: 'user', content: userMessage });

      const model = await blModel("gpt-4-1");
      const result = await generateText({
        model,
        messages: state.conversationHistory,
        system: systemPrompt
      });

      const generatedCode = result.text;
      state.lastGeneratedCode = generatedCode;
      state.conversationHistory.push({ role: 'assistant', content: generatedCode });

      console.info(`[Iteration ${state.currentIteration}] Generated ${generatedCode.length} chars of code`);

      // STEP 2: Write to sandbox
      await sandbox.fs.write("/app/seed-script.ts", generatedCode);

      // STEP 3: Execute
      const processName = `seed-script-attempt-${state.currentIteration}`;
      await sandbox.process.exec({
        name: processName,
        command: "npx ts-node /app/seed-script.ts",
        waitForCompletion: true
      });

      const logs = await sandbox.process.logs(processName);
      console.info(`[Iteration ${state.currentIteration}] Execution completed`);

      // STEP 4: Analyze
      const error = parseExecutionError(logs);

      // Record attempt
      state.attemptLog.push({
        iteration: state.currentIteration,
        timestamp: new Date().toISOString(),
        generatedCode,
        executionLogs: logs,
        success: !error,
        error: error || undefined
      });

      // STEP 5: Check success
      if (!error) {
        console.info(`[Agentic Loop] ✓ SUCCESS on iteration ${state.currentIteration}`);
        return {
          success: true,
          iterations: state.currentIteration,
          output: logs,
          generatedCode,
          attemptLog: state.attemptLog,
          sandbox: { name: sandboxName, image: gmailSandboxImage }
        };
      }

      console.warn(`[Iteration ${state.currentIteration}] ✗ ${error.type}: ${error.message.substring(0, 100)}`);
      state.lastError = error;

    } catch (err: any) {
      console.error(`[Iteration ${state.currentIteration}] Unexpected error:`, err);

      state.attemptLog.push({
        iteration: state.currentIteration,
        timestamp: new Date().toISOString(),
        generatedCode: state.lastGeneratedCode,
        executionLogs: err.message || String(err),
        success: false,
        error: {
          type: 'unknown',
          message: err.message || String(err),
          stack: err.stack
        }
      });

      state.lastError = {
        type: 'unknown',
        message: err.message || String(err),
        stack: err.stack
      };
    }
  }

  // Max iterations reached
  console.error(`[Agentic Loop] ✗ Failed after ${MAX_ITERATIONS} attempts`);
  return {
    success: false,
    iterations: MAX_ITERATIONS,
    output: state.attemptLog[state.attemptLog.length - 1]?.executionLogs || 'No execution logs',
    generatedCode: state.lastGeneratedCode,
    attemptLog: state.attemptLog,
    error: state.lastError || undefined,
    sandbox: { name: sandboxName, image: gmailSandboxImage }
  };
}

async function main() {
  console.info("Booting up Gmail Sandbox Agent...");
  const app = Fastify();

  app.addHook("onResponse", async (request, reply) => {
    console.info(`${request.method} ${request.url} ${reply.statusCode} ${Math.round(reply.elapsedTime)}ms`);
  });

  app.addHook("onError", async (request, reply, error) => {
    console.error(error);
  });

  app.post<{ Body: RequestBody }>("/", async (request, reply) => {
    const { inputs, userId = "default-user" } = request.body;

    if (!inputs || typeof inputs !== 'string') {
      return reply.status(400).send({ error: "Invalid request. 'inputs' field is required." });
    }

    console.info(`[Gmail Agent] Request from user ${userId}: ${inputs}`);

    try {
      // Create or connect to Gmail sandbox
      console.info("[Gmail Agent] Creating/connecting to Gmail sandbox...");
      const sandboxName = `gmail-sandbox-${userId}`;
      const gmailSandboxImage = env.GMAIL_SANDBOX_IMAGE || "gmail:latest";

      const sandbox = await SandboxInstance.createIfNotExists({
        name: sandboxName,
        image: gmailSandboxImage,
        memory: 8192,
        ports: [{ target: 3000, protocol: "HTTP" }]
      });

      console.info(`[Gmail Agent] Connected to sandbox: ${sandbox.metadata?.name}`);

      // Execute agentic loop
      const result = await executeAgenticLoop(inputs, sandbox, sandboxName, gmailSandboxImage);

      // Return result
      if (result.success) {
        return reply.send(result);
      } else {
        return reply.status(500).send({
          ...result,
          message: "Code execution failed after maximum iterations"
        });
      }

    } catch (error: any) {
      console.error("[Gmail Agent] Fatal error:", error);
      return reply.status(500).send({
        success: false,
        error: error.message || "An unexpected error occurred",
        details: error.stack
      });
    }
  });

  const port = parseInt(process.env.PORT || "80");
  const host = process.env.HOST || "0.0.0.0";

  await app.listen({ port, host });
  console.info(`Gmail Sandbox Agent is running on ${host}:${port}`);
}

main().catch(console.error);
