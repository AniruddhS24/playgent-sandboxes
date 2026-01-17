# Gmail Sandbox Examples

This directory contains comprehensive examples demonstrating how to use the Gmail Sandbox API.

## Running Examples

### Option 1: Using ts-node (Recommended for Development)

```bash
# Install dependencies (if not already installed)
npm install -D ts-node @types/node

# Run a specific example
npx ts-node examples/seed-gmail.ts
```

### Option 2: Compile and Run

```bash
# Compile TypeScript to JavaScript
npx tsc --project tsconfig.gmail.json

# Run compiled JavaScript
node dist/examples/seed-gmail.js
```

### Option 3: Import in Your Own Code

```typescript
import {
  example1_basicInitialization,
  example2_bulkGeneration,
  example3_supportInbox,
} from './examples/seed-gmail';

// Run specific example
await example1_basicInitialization();
```

## Available Examples

The `seed-gmail.ts` file contains 7 comprehensive examples:

1. **Basic Initialization** - Simple sandbox setup with a few messages and drafts
2. **Bulk Generation** - Generate 50+ messages using helper functions
3. **Support Inbox** - Simulate a customer support inbox with various ticket types
4. **Custom Logic** - Create messages dynamically with conditional logic
5. **Email Threads** - Simulate conversation threads with replies
6. **Date Ranges** - Generate historical messages spanning multiple days
7. **Onboarding Scenario** - Complete new employee onboarding email sequence

## Creating Your Own Examples

You can create your own seeding scripts by importing from the Gmail API:

```typescript
import {
  initializeGmailSandbox,
  createMessage,
  createDraft,
  generateTestMessages,
  generateTestDrafts,
  GmailMessage,
  GmailDraft,
} from '../src/gmail';

async function myCustomScenario() {
  // Your custom logic here
  const messages: GmailMessage[] = [
    {
      subject: 'My Custom Email',
      to: 'recipient@example.com',
      body: 'Custom email body',
      labels: ['INBOX'],
    },
  ];

  await initializeGmailSandbox('my-custom-sandbox', {
    messages,
  });
}

myCustomScenario();
```

## Tips for AI Agents

When writing code to seed Gmail data:

1. **Start Simple** - Begin with `initializeGmailSandbox()` and a few messages
2. **Use Helpers** - The `generateTestMessages()` and `generateTestDrafts()` functions quickly create realistic data
3. **Be Flexible** - Write custom loops and logic to create complex scenarios
4. **Label Appropriately** - Use labels like 'INBOX', 'SENT', 'IMPORTANT', 'URGENT' to organize messages
5. **Consider Threads** - Use `reply_to` field to create conversation threads
6. **Validate Data** - The API validates required fields and email formats automatically

## Example Scenarios to Try

- Sales pipeline emails (leads, follow-ups, closed deals)
- Project management threads (tasks, updates, deadlines)
- Newsletter campaigns (bulk sends with different content)
- Support ticket lifecycle (new, in-progress, resolved)
- Team collaboration (meetings, documents, discussions)
- Automated notifications (system alerts, reports, reminders)

## Need Help?

- See the [Gmail API Documentation](../GMAIL_API.md) for complete API reference
- Check the [main README](../README.md) for sandbox setup instructions
- Review the inline comments in `seed-gmail.ts` for detailed explanations
