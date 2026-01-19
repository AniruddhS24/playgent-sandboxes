import "@blaxel/telemetry";
import Fastify from "fastify";
import { blModel, blTools } from "@blaxel/vercel";
import { generateText, stepCountIs } from "ai";

interface RequestBody {
  inputs: string;
}

const SYSTEM_PROMPT = `You are a coding agent that creates Gmail sandbox data.

## Your Tools
- codegenListDir: List directory contents
- codegenFileSearch: Find files by name
- codegenReadFileRange: Read file contents
- codegenGrepSearch: Regex/text search
- fsWriteFile: Write files
- processExecute: Run commands

## Your Workflow
1. EXPLORE: Use codegenListDir and codegenReadFileRange to understand /app/src/gmail/
2. WRITE: Create /app/seed-script.ts using fsWriteFile
3. EXECUTE: Run with processExecute: npx ts-node /app/seed-script.ts
4. FIX: If errors, read relevant files and fix the script

## Important
- Gmail API is at /app/src/gmail/
- Use absolute imports: import { ... } from '/app/src/gmail'
- Always explore the types and functions before writing code`;

async function runCodingAgent(
  userRequest: string
): Promise<{ success: boolean; output: string; steps: number }> {
  const model = await blModel("claude-sonnet-4-5-20250929");

  // Load tools from existing "gmail" sandbox
  const allTools = await blTools(["sandbox/gmail"]);

  // Filter for codegen, fs, and process tools
  const tools = Object.fromEntries(
    Object.entries(allTools).filter(([key]) =>
      key.startsWith("codegen") ||
      key.startsWith("fs") ||
      key.startsWith("process")
    )
  );

  console.info(`Using ${Object.keys(tools).length} tools: ${Object.keys(tools).join(", ")}`);

  const result = await generateText({
    model,
    tools: tools as any,
    stopWhen: stepCountIs(25),
    system: SYSTEM_PROMPT,
    messages: [{ role: "user", content: userRequest }],
  });

  return {
    success: true,
    output: result.text,
    steps: result.steps?.length || 0,
  };
}

async function main() {
  console.info("Starting Gmail Sandbox Coding Agent...");
  const app = Fastify();

  app.post<{ Body: RequestBody }>("/", async (request, reply) => {
    const { inputs } = request.body;

    if (!inputs || typeof inputs !== "string") {
      return reply
        .status(400)
        .send({ error: "Invalid request. 'inputs' required." });
    }

    try {
      const result = await runCodingAgent(inputs);
      return reply.send(result);
    } catch (error: any) {
      console.error("Error:", error);
      return reply.status(500).send({ error: error.message });
    }
  });

  const port = parseInt(process.env.PORT || "80");
  await app.listen({ port, host: "0.0.0.0" });
  console.info(`Agent running on port ${port}`);
}

main().catch(console.error);
