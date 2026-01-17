# Gmail Sandbox Architecture

## Overview

The Gmail Sandbox is a code-based environment that allows AI agents to synthetically generate Gmail data for testing and development. This document explains the architectural decisions and design philosophy.

## Design Philosophy

### Code-First Approach

Instead of providing a REST API or GraphQL endpoint, we provide a **code-based API** that agents can import and use directly. This approach is inspired by [Anthropic's Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp).

**Benefits:**
- **Ultimate Flexibility**: Agents can write custom logic, loops, and conditionals
- **Reduced Token Usage**: Processing happens in the sandbox, not in agent context
- **Privacy**: Intermediate data stays in the execution environment
- **Power**: Full programming language capabilities instead of limited API calls

### Klavis AI Inspiration

The data structure and API design is inspired by [Klavis AI's Gmail Sandbox](https://www.klavis.ai/docs/api-reference/sandbox/gmail/initialize-gmail), which provides a clean, well-structured approach to seeding Gmail data.

**Key Concepts Adopted:**
- Messages and drafts as primary objects
- Comprehensive field support (to, from, cc, bcc, reply_to, labels)
- Bulk initialization pattern
- Validation and error handling

## Architecture Components

### 1. Type System (`src/gmail/types.ts`)

Comprehensive TypeScript types ensure type safety and provide excellent IDE autocomplete:

- `GmailMessage` - Complete message structure
- `GmailDraft` - Draft email structure
- `GmailSandboxData` - Initialization payload
- `GmailSandboxResponse` - API response format
- `GmailUserConfig` - User configuration

### 2. Messages API (`src/gmail/messages.ts`)

Handles all message-related operations:

- **CRUD Operations**: Create, read, update, delete
- **Bulk Operations**: Efficient batch creation
- **Label Management**: Add/remove labels
- **Validation**: Email format, required fields, character limits

### 3. Drafts API (`src/gmail/drafts.ts`)

Manages draft emails:

- **Draft Lifecycle**: Create, update, delete, send
- **Draft to Message Conversion**: Send draft → creates message
- **Similar Structure**: Consistent with messages API

### 4. Main Module (`src/gmail/index.ts`)

Central initialization and coordination:

- **Primary Entry Point**: `initializeGmailSandbox()`
- **Helper Functions**: Generate test data automatically
- **Re-exports**: All types and functions from sub-modules
- **Sandbox Management**: Reset, status checking

### 5. Examples (`examples/seed-gmail.ts`)

Seven comprehensive examples showing different usage patterns:

1. Basic initialization
2. Bulk generation
3. Support inbox simulation
4. Custom logic with loops
5. Email threads with replies
6. Historical data generation
7. Complete onboarding scenario

## Data Flow

```
Agent Code (TypeScript)
    ↓
Gmail Sandbox API
    ↓
[Future] Supabase Database
    ↓
[Future] Mock Gmail UI
```

Currently, the API logs operations to console. The Supabase integration will be added later.

## Database Design (Future)

### Core Tables

**sandboxes**
- Tracks individual sandbox instances
- Status management (idle/occupied)
- User association

**gmail_messages**
- Message metadata
- Foreign keys to related tables

**message_bodies**
- Separated for performance (text can be large)

**message_labels**
- Many-to-many relationship
- Supports multiple labels per message

**gmail_drafts**
- Draft metadata
- Similar structure to messages

**draft_bodies**
- Draft content storage

### Join Tables

**sandbox_messages**
- Links messages to sandboxes
- Enables sandbox isolation

**sandbox_drafts**
- Links drafts to sandboxes

### Advantages

- **Scalability**: Separate body storage handles large emails
- **Flexibility**: Easy to add new fields or relationships
- **Isolation**: Each sandbox is independent
- **Performance**: Indexed lookups on common queries

## Security Considerations

### Sandbox Isolation

Each sandbox instance is isolated:
- Separate sandbox_id identifies each instance
- Join tables ensure data separation
- No cross-sandbox data leakage

### Validation

All inputs are validated:
- Required fields checked
- Email format validation
- Character limits enforced (subject max 255)
- Prevents injection attacks

### Resource Limits

Future implementations should include:
- Max messages per sandbox
- Max body size limits
- Rate limiting on creation
- Automatic cleanup of old sandboxes

## Extension Points

The architecture is designed to be extensible:

### Additional Email Features
- Attachments (file storage integration)
- HTML formatting (rich text bodies)
- Read/unread status
- Importance/priority flags
- Categories/folders

### Gmail-Specific Features
- Filters and rules
- Auto-responders
- Vacation replies
- Signatures
- Forwarding rules

### Threading
- Conversation IDs
- Thread hierarchy
- Reply chains
- Thread statistics

### Search and Query
- Full-text search on body
- Advanced filters
- Date range queries
- Label-based search

### Calendar Integration
- Meeting invites in emails
- RSVP tracking
- Calendar event creation

### Contacts
- Contact management
- Auto-complete suggestions
- Contact groups

## Performance Optimizations

### Current Design
- Bulk operations avoid N+1 queries
- Validation happens before database calls
- Helper functions reduce code duplication

### Future Optimizations
- **Batch Inserts**: Use Supabase batch operations
- **Transactions**: Wrap multi-table operations
- **Indexes**: On frequently queried fields (labels, from, to)
- **Caching**: Cache sandbox metadata
- **Pagination**: Limit query results
- **Lazy Loading**: Load message bodies on demand

## Testing Strategy

### Unit Tests
- Validation logic
- Helper functions
- Type checking

### Integration Tests
- Full initialization flow
- CRUD operations
- Error handling

### Agent Testing
- Run example scenarios
- Verify token usage reduction
- Test custom scenarios

## Deployment

### Container
- Node.js 22 Alpine base
- TypeScript compilation
- Next.js dev server
- Sandbox API integration

### Blaxel Platform
- Deployed as Blaxel sandbox
- Exposed on port 3000
- Integrated with Claude Code

## Future Roadmap

### Phase 1: Supabase Integration (Current)
- Set up Supabase project
- Create database schema
- Implement data persistence
- Replace mock implementations

### Phase 2: UI Layer
- Mock Gmail interface
- View messages and drafts
- Basic interactions (read, delete, send)

### Phase 3: Advanced Features
- Email attachments
- Threading support
- Search functionality
- Filters and rules

### Phase 4: Additional Integrations
- Calendar
- Contacts
- Drive (for attachments)
- Meet (for video links)

## Inspiration and Credits

This project draws inspiration from:

- **[Klavis AI Gmail Sandbox](https://www.klavis.ai/docs/api-reference/sandbox/gmail/initialize-gmail)**
  - Clean API design
  - Comprehensive field support
  - Initialization pattern

- **[Anthropic Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)**
  - Code-first philosophy
  - Token efficiency
  - Agent flexibility

- **[Gmail API](https://developers.google.com/gmail/api)**
  - Label system
  - Message structure
  - Threading concepts

## Contributing

When contributing to this project, please:

1. Follow existing code patterns
2. Add comprehensive comments
3. Include TODO markers for Supabase logic
4. Write examples for new features
5. Update documentation
6. Maintain type safety

## Questions?

For questions or suggestions:
- Open an issue on GitHub
- Join the Blaxel Discord community
- Check the documentation in GMAIL_API.md
