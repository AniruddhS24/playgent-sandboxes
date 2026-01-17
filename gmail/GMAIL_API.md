# Gmail Sandbox API Documentation

A code-based API for synthetically generating Gmail data in a sandbox environment. This allows AI agents to write flexible code that seeds realistic Gmail scenarios for testing and development.

## 🎯 Overview

The Gmail Sandbox API is inspired by:
- **[Klavis AI's Gmail Sandbox](https://www.klavis.ai/docs/api-reference/sandbox/gmail/initialize-gmail)** - Data structure and initialization approach
- **[Anthropic's Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)** - Code-based flexibility for agents

Instead of making direct API calls, agents write TypeScript code using these methods to create complex, realistic Gmail environments.

## 📦 Installation

The API is included in the sandbox. Import it in your code:

```typescript
import {
  initializeGmailSandbox,
  createMessage,
  createDraft,
  generateTestMessages,
  generateTestDrafts,
} from './src/gmail';
```

## 🚀 Quick Start

### Basic Initialization

```typescript
import { initializeGmailSandbox } from './src/gmail';

const response = await initializeGmailSandbox('my-sandbox', {
  messages: [
    {
      subject: 'Welcome!',
      to: 'user@example.com',
      body: 'Welcome to our platform!',
      labels: ['INBOX', 'IMPORTANT'],
    },
  ],
  drafts: [
    {
      subject: 'Re: Meeting',
      to: 'colleague@example.com',
      body: 'Thanks for the meeting today...',
    },
  ],
});

console.log(response);
// {
//   sandbox_id: 'my-sandbox',
//   status: 'idle',
//   message: 'Successfully initialized Gmail sandbox with 1 messages and 1 drafts',
//   records_created: { messages: 1, drafts: 1 }
// }
```

## 📚 API Reference

### Core Types

#### `GmailMessage`

```typescript
interface GmailMessage {
  subject: string;              // Required, max 255 chars
  to: string;                   // Required, recipient email
  body: string;                 // Required, email content
  cc?: string | null;           // Optional, comma-separated
  bcc?: string | null;          // Optional, comma-separated
  from?: string | null;         // Optional, defaults to authenticated user
  reply_to?: string | null;     // Optional
  labels?: string[] | null;     // Optional, e.g., ['INBOX', 'SENT']
}
```

#### `GmailDraft`

```typescript
interface GmailDraft {
  subject: string;              // Required, max 255 chars
  to: string;                   // Required, recipient email
  body: string;                 // Required, draft content
  cc?: string | null;           // Optional, comma-separated
  bcc?: string | null;          // Optional, comma-separated
  from?: string | null;         // Optional, defaults to authenticated user
  reply_to?: string | null;     // Optional
}
```

### Initialization Functions

#### `initializeGmailSandbox()`

Primary method for seeding a Gmail sandbox with bulk data.

```typescript
async function initializeGmailSandbox(
  sandboxId: string,
  data: GmailSandboxData,
  userConfig?: GmailUserConfig
): Promise<GmailSandboxResponse>
```

**Parameters:**
- `sandboxId` - Unique identifier for this sandbox instance
- `data` - Object containing `messages` and/or `drafts` arrays
- `userConfig` - Optional user configuration (email, name)

**Returns:**
- `GmailSandboxResponse` with sandbox_id, status, message, and records_created

**Example:**
```typescript
const response = await initializeGmailSandbox('sandbox_001', {
  messages: [...],
  drafts: [...]
});
```

#### `resetGmailSandbox()`

Deletes all data from a sandbox.

```typescript
async function resetGmailSandbox(sandboxId: string): Promise<void>
```

#### `getGmailSandboxStatus()`

Gets the current status and statistics of a sandbox.

```typescript
async function getGmailSandboxStatus(sandboxId: string): Promise<{
  sandbox_id: string;
  status: 'idle' | 'occupied';
  message_count: number;
  draft_count: number;
  created_at: string;
  updated_at: string;
}>
```

### Message Functions

#### `createMessage()`

Creates a single Gmail message.

```typescript
async function createMessage(
  message: GmailMessage,
  userConfig?: GmailUserConfig
): Promise<string>
```

**Returns:** Message ID

**Example:**
```typescript
const messageId = await createMessage({
  subject: 'Hello!',
  to: 'friend@example.com',
  body: 'Just saying hi!',
  labels: ['INBOX', 'PERSONAL']
});
```

#### `createMessages()`

Creates multiple Gmail messages in bulk.

```typescript
async function createMessages(
  messages: GmailMessage[],
  userConfig?: GmailUserConfig
): Promise<string[]>
```

**Returns:** Array of message IDs

#### `getMessage()`

Retrieves a message by ID.

```typescript
async function getMessage(messageId: string): Promise<GmailMessage | null>
```

#### `listMessages()`

Lists all messages with optional filtering.

```typescript
async function listMessages(options?: {
  labels?: string[];
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}): Promise<GmailMessage[]>
```

#### `deleteMessage()`

Deletes a message by ID.

```typescript
async function deleteMessage(messageId: string): Promise<void>
```

#### `updateMessageLabels()`

Updates labels on a message.

```typescript
async function updateMessageLabels(
  messageId: string,
  addLabels?: string[],
  removeLabels?: string[]
): Promise<void>
```

### Draft Functions

#### `createDraft()`

Creates a single Gmail draft.

```typescript
async function createDraft(
  draft: GmailDraft,
  userConfig?: GmailUserConfig
): Promise<string>
```

**Returns:** Draft ID

#### `createDrafts()`

Creates multiple Gmail drafts in bulk.

```typescript
async function createDrafts(
  drafts: GmailDraft[],
  userConfig?: GmailUserConfig
): Promise<string[]>
```

**Returns:** Array of draft IDs

#### `getDraft()`

Retrieves a draft by ID.

```typescript
async function getDraft(draftId: string): Promise<GmailDraft | null>
```

#### `listDrafts()`

Lists all drafts with optional filtering.

```typescript
async function listDrafts(options?: {
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}): Promise<GmailDraft[]>
```

#### `updateDraft()`

Updates a draft.

```typescript
async function updateDraft(
  draftId: string,
  updates: Partial<GmailDraft>
): Promise<void>
```

#### `deleteDraft()`

Deletes a draft by ID.

```typescript
async function deleteDraft(draftId: string): Promise<void>
```

#### `sendDraft()`

Sends a draft (converts it to a message).

```typescript
async function sendDraft(draftId: string): Promise<string>
```

**Returns:** Message ID of the sent email

### Helper Functions

#### `generateTestMessages()`

Generates realistic test messages automatically.

```typescript
function generateTestMessages(
  count: number,
  options?: {
    labels?: string[];
    fromDomain?: string;
    toDomain?: string;
  }
): GmailMessage[]
```

**Example:**
```typescript
const messages = generateTestMessages(50, {
  labels: ['INBOX'],
  fromDomain: 'company.com',
  toDomain: 'company.com'
});
```

#### `generateTestDrafts()`

Generates realistic test drafts automatically.

```typescript
function generateTestDrafts(
  count: number,
  options?: {
    fromDomain?: string;
    toDomain?: string;
  }
): GmailDraft[]
```

## 💡 Usage Examples

### Example 1: Support Inbox

```typescript
const supportMessages: GmailMessage[] = [
  {
    subject: 'Login Issue - Urgent',
    to: 'support@company.com',
    from: 'customer@example.com',
    body: "I can't log into my account. Please help!",
    labels: ['INBOX', 'URGENT'],
  },
  {
    subject: 'Feature Request: Dark Mode',
    to: 'support@company.com',
    from: 'customer2@example.com',
    body: 'It would be great if you could add dark mode.',
    labels: ['INBOX'],
  },
];

await initializeGmailSandbox('support-sandbox', {
  messages: supportMessages
});
```

### Example 2: Bulk Generation

```typescript
const messages = generateTestMessages(100, {
  labels: ['INBOX'],
  fromDomain: 'company.com',
  toDomain: 'company.com'
});

const drafts = generateTestDrafts(20, {
  fromDomain: 'company.com',
  toDomain: 'clients.com'
});

await initializeGmailSandbox('bulk-sandbox', {
  messages,
  drafts
});
```

### Example 3: Email Thread

```typescript
const threadMessages: GmailMessage[] = [
  {
    subject: 'Q1 Planning Discussion',
    to: 'team@company.com',
    from: 'manager@company.com',
    body: "Let's discuss our Q1 priorities.",
    labels: ['INBOX', 'SENT'],
  },
  {
    subject: 'Re: Q1 Planning Discussion',
    to: 'manager@company.com',
    from: 'engineer@company.com',
    body: 'I think we should focus on performance.',
    labels: ['INBOX'],
    reply_to: 'manager@company.com',
  },
];

await initializeGmailSandbox('thread-sandbox', {
  messages: threadMessages
});
```

### Example 4: Custom Logic

```typescript
// Initialize empty sandbox
await initializeGmailSandbox('custom-sandbox', {});

// Create messages with custom logic
const departments = ['Engineering', 'Sales', 'Marketing'];

for (let i = 0; i < 20; i++) {
  const dept = departments[i % departments.length];
  const isUrgent = Math.random() > 0.7;

  await createMessage({
    subject: `${dept} Update #${i + 1}`,
    to: 'employee@company.com',
    from: `${dept.toLowerCase()}@company.com`,
    body: `Update from ${dept} department.`,
    labels: isUrgent ? ['INBOX', 'URGENT'] : ['INBOX'],
  });
}
```

## 🔧 Advanced Usage

### Working with Labels

Gmail labels are used to organize messages. Common labels:

- `INBOX` - Messages in the inbox
- `SENT` - Sent messages
- `DRAFT` - Draft messages
- `IMPORTANT` - Important messages
- `STARRED` - Starred messages
- `TRASH` - Deleted messages
- `SPAM` - Spam messages
- Custom labels - Any string

**Example:**
```typescript
await createMessage({
  subject: 'Important Project Update',
  to: 'team@company.com',
  body: 'Critical information...',
  labels: ['INBOX', 'IMPORTANT', 'STARRED', 'PROJECT_ALPHA']
});
```

### Managing Labels

```typescript
// Add labels
await updateMessageLabels(messageId, ['IMPORTANT', 'URGENT']);

// Remove labels
await updateMessageLabels(messageId, [], ['INBOX']);

// Replace labels (remove then add)
await updateMessageLabels(messageId, ['ARCHIVED'], ['INBOX']);
```

### User Configuration

Set default user information:

```typescript
const userConfig = {
  email: 'john.doe@company.com',
  name: 'John Doe'
};

await initializeGmailSandbox('my-sandbox', {
  messages: [...]
}, userConfig);
```

## 🗄️ Database Schema (Future)

When Supabase integration is added, the following tables will be created:

### `sandboxes`
- `sandbox_id` (PK)
- `user_email`
- `status` ('idle' | 'occupied')
- `created_at`
- `updated_at`

### `gmail_messages`
- `message_id` (PK)
- `subject`
- `to`
- `from`
- `cc`
- `bcc`
- `reply_to`
- `created_at`
- `updated_at`

### `message_bodies`
- `message_id` (FK)
- `body` (text)

### `message_labels`
- `message_id` (FK)
- `label` (string)

### `gmail_drafts`
- `draft_id` (PK)
- `subject`
- `to`
- `from`
- `cc`
- `bcc`
- `reply_to`
- `is_sent` (boolean)
- `created_at`
- `updated_at`

### `draft_bodies`
- `draft_id` (FK)
- `body` (text)

### `sandbox_messages` (join table)
- `sandbox_id` (FK)
- `message_id` (FK)

### `sandbox_drafts` (join table)
- `sandbox_id` (FK)
- `draft_id` (FK)

## 🎓 Learning Resources

- [Klavis AI Gmail Sandbox](https://www.klavis.ai/docs/api-reference/sandbox/gmail/initialize-gmail) - Inspiration for data structure
- [Anthropic Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) - Code-based agent approach
- [Gmail API Labels](https://developers.google.com/gmail/api/guides/labels) - Gmail label reference

## 🤝 Contributing

The API is designed to be extensible. Future additions could include:

- Email attachments support
- Thread management (conversation IDs)
- Search functionality
- Filters and rules
- Contact management
- Calendar integration
- More realistic email generation (using templates, AI, etc.)

## 📄 License

MIT License
