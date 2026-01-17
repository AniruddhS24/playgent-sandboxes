/**
 * Gmail Sandbox Quick Start
 *
 * Run this file to quickly test the Gmail Sandbox API.
 * This demonstrates the basic functionality in a single script.
 */

import {
  initializeGmailSandbox,
  generateTestMessages,
  generateTestDrafts,
  createMessage,
  GmailMessage,
} from './src/gmail';

async function quickStart() {
  console.log('='.repeat(60));
  console.log('Gmail Sandbox - Quick Start');
  console.log('='.repeat(60));
  console.log();

  try {
    // 1. Create a sandbox with generated test data
    console.log('Step 1: Generating test data...');
    const messages = generateTestMessages(10, {
      labels: ['INBOX'],
      fromDomain: 'company.com',
      toDomain: 'company.com',
    });

    const drafts = generateTestDrafts(3, {
      fromDomain: 'company.com',
      toDomain: 'clients.com',
    });

    console.log(`Generated ${messages.length} messages and ${drafts.length} drafts`);
    console.log();

    // 2. Initialize the sandbox
    console.log('Step 2: Initializing sandbox...');
    const response = await initializeGmailSandbox('quickstart-sandbox', {
      messages,
      drafts,
    });

    console.log('Sandbox initialized:');
    console.log(`  - Sandbox ID: ${response.sandbox_id}`);
    console.log(`  - Status: ${response.status}`);
    console.log(`  - Messages created: ${response.records_created.messages}`);
    console.log(`  - Drafts created: ${response.records_created.drafts}`);
    console.log();

    // 3. Create a custom message
    console.log('Step 3: Creating a custom message...');
    const customMessage: GmailMessage = {
      subject: 'Welcome to Gmail Sandbox!',
      to: 'developer@example.com',
      from: 'sandbox@company.com',
      body: 'This is a test message created by the Gmail Sandbox API. You can create any type of Gmail data you need for testing!',
      labels: ['INBOX', 'IMPORTANT'],
    };

    const messageId = await createMessage(customMessage);
    console.log(`Custom message created with ID: ${messageId}`);
    console.log();

    // Success!
    console.log('='.repeat(60));
    console.log('Quick start completed successfully!');
    console.log();
    console.log('Next steps:');
    console.log('  1. Check examples/seed-gmail.ts for more complex examples');
    console.log('  2. Read GMAIL_API.md for complete API documentation');
    console.log('  3. Write your own custom seeding logic');
    console.log('='.repeat(60));
    console.log();

  } catch (error) {
    console.error('Error during quick start:', error);
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  quickStart();
}

export { quickStart };
