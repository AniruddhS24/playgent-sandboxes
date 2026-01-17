/**
 * Gmail Sandbox Seeding Examples
 *
 * This file demonstrates various ways to seed a Gmail sandbox with synthetic data.
 * Agents can use these examples as templates or write custom seeding logic.
 */

import {
  initializeGmailSandbox,
  generateTestMessages,
  generateTestDrafts,
  createMessage,
  createDraft,
  GmailMessage,
  GmailDraft,
} from '../src/gmail';

/**
 * Example 1: Basic sandbox initialization with a few messages
 */
async function example1_basicInitialization() {
  console.log('\n=== Example 1: Basic Initialization ===\n');

  const response = await initializeGmailSandbox('sandbox_001', {
    messages: [
      {
        subject: 'Welcome to the team!',
        to: 'newbie@company.com',
        body: 'Hi! Welcome aboard. We're excited to have you join our team.',
        from: 'manager@company.com',
        labels: ['INBOX', 'IMPORTANT'],
      },
      {
        subject: 'Project Kickoff Meeting',
        to: 'team@company.com',
        body: 'The kickoff meeting is scheduled for tomorrow at 10 AM.',
        from: 'pm@company.com',
        labels: ['INBOX'],
      },
    ],
    drafts: [
      {
        subject: 'Re: Budget Approval',
        to: 'finance@company.com',
        body: 'Thank you for reviewing the budget proposal. I have made the requested changes...',
        from: 'manager@company.com',
      },
    ],
  });

  console.log('Initialization response:', response);
}

/**
 * Example 2: Generate bulk test data using helpers
 */
async function example2_bulkGeneration() {
  console.log('\n=== Example 2: Bulk Generation ===\n');

  const messages = generateTestMessages(50, {
    labels: ['INBOX'],
    fromDomain: 'company.com',
    toDomain: 'company.com',
  });

  const drafts = generateTestDrafts(10, {
    fromDomain: 'company.com',
    toDomain: 'clients.com',
  });

  const response = await initializeGmailSandbox('sandbox_002', {
    messages,
    drafts,
  });

  console.log('Created', response.records_created.messages, 'messages');
  console.log('Created', response.records_created.drafts, 'drafts');
}

/**
 * Example 3: Simulate a support inbox with customer emails
 */
async function example3_supportInbox() {
  console.log('\n=== Example 3: Support Inbox Simulation ===\n');

  const supportMessages: GmailMessage[] = [
    {
      subject: 'Login Issue - Urgent',
      to: 'support@company.com',
      from: 'customer1@example.com',
      body: "I can't log into my account. Please help!",
      labels: ['INBOX', 'URGENT'],
    },
    {
      subject: 'Feature Request: Dark Mode',
      to: 'support@company.com',
      from: 'customer2@example.com',
      body: 'It would be great if you could add a dark mode option.',
      labels: ['INBOX'],
    },
    {
      subject: 'Billing Question',
      to: 'support@company.com',
      from: 'customer3@example.com',
      body: 'I was charged twice this month. Can you check my account?',
      labels: ['INBOX', 'IMPORTANT'],
    },
    {
      subject: 'Thank You!',
      to: 'support@company.com',
      from: 'customer4@example.com',
      body: 'Your support team was amazing. Thank you for resolving my issue so quickly!',
      labels: ['INBOX'],
    },
  ];

  const supportDrafts: GmailDraft[] = [
    {
      subject: 'Re: Login Issue - Urgent',
      to: 'customer1@example.com',
      from: 'support@company.com',
      body: 'Hi, I looked into your account and I see the issue. Please try resetting your password...',
    },
    {
      subject: 'Re: Billing Question',
      to: 'customer3@example.com',
      from: 'support@company.com',
      body: "I've reviewed your billing and you're correct - there was a duplicate charge. I've initiated a refund...",
    },
  ];

  const response = await initializeGmailSandbox('sandbox_003', {
    messages: supportMessages,
    drafts: supportDrafts,
  });

  console.log('Support inbox initialized:', response);
}

/**
 * Example 4: Create messages incrementally with custom logic
 */
async function example4_customLogic() {
  console.log('\n=== Example 4: Custom Logic ===\n');

  // Initialize empty sandbox
  await initializeGmailSandbox('sandbox_004', {});

  // Generate messages based on custom logic
  const departments = ['Engineering', 'Sales', 'Marketing', 'HR'];
  const priorities = ['IMPORTANT', 'URGENT'];

  for (let i = 0; i < 20; i++) {
    const department = departments[i % departments.length];
    const isUrgent = Math.random() > 0.7;
    const labels = ['INBOX'];

    if (isUrgent) {
      labels.push(priorities[Math.floor(Math.random() * priorities.length)]);
    }

    await createMessage({
      subject: `${department} Update #${i + 1}`,
      to: 'employee@company.com',
      from: `${department.toLowerCase()}@company.com`,
      body: `This is an update from the ${department} department.`,
      labels,
    });
  }

  console.log('Created 20 messages with custom logic');
}

/**
 * Example 5: Simulate email threads with replies
 */
async function example5_emailThreads() {
  console.log('\n=== Example 5: Email Threads ===\n');

  const threadMessages: GmailMessage[] = [
    // Original email
    {
      subject: 'Q1 Planning Discussion',
      to: 'team@company.com',
      from: 'manager@company.com',
      body: "Let's discuss our Q1 priorities. What are everyone's thoughts?",
      labels: ['INBOX', 'SENT'],
    },
    // Reply 1
    {
      subject: 'Re: Q1 Planning Discussion',
      to: 'manager@company.com',
      from: 'engineer1@company.com',
      body: 'I think we should focus on improving performance and fixing bugs.',
      labels: ['INBOX'],
      reply_to: 'manager@company.com',
    },
    // Reply 2
    {
      subject: 'Re: Q1 Planning Discussion',
      to: 'manager@company.com',
      from: 'designer@company.com',
      body: 'Agreed with the engineering priorities, but we also need to refresh the UI.',
      labels: ['INBOX'],
      reply_to: 'manager@company.com',
    },
    // Reply 3
    {
      subject: 'Re: Q1 Planning Discussion',
      to: 'team@company.com',
      from: 'manager@company.com',
      body: 'Great feedback everyone! Let me compile these into a roadmap document.',
      labels: ['INBOX', 'SENT'],
      reply_to: 'designer@company.com',
    },
  ];

  const response = await initializeGmailSandbox('sandbox_005', {
    messages: threadMessages,
  });

  console.log('Email thread created:', response);
}

/**
 * Example 6: Generate messages with different date ranges (simulated)
 */
async function example6_dateRanges() {
  console.log('\n=== Example 6: Date Ranges Simulation ===\n');

  // Note: In a real implementation, you would pass timestamps to the API
  // For now, we'll just create messages with metadata that could be used
  // to set timestamps in the Supabase logic

  const historicalMessages: GmailMessage[] = [];

  // Generate messages for "last 30 days"
  for (let day = 30; day > 0; day--) {
    historicalMessages.push({
      subject: `Daily Report - Day -${day}`,
      to: 'manager@company.com',
      from: 'system@company.com',
      body: `Automated daily report for ${day} days ago.`,
      labels: ['INBOX', 'AUTOMATED'],
    });
  }

  const response = await initializeGmailSandbox('sandbox_006', {
    messages: historicalMessages,
  });

  console.log('Created 30 days of historical messages:', response);
}

/**
 * Example 7: Comprehensive scenario - New employee onboarding
 */
async function example7_onboardingScenario() {
  console.log('\n=== Example 7: Onboarding Scenario ===\n');

  const onboardingMessages: GmailMessage[] = [
    {
      subject: 'Welcome to Acme Corp!',
      to: 'newemployee@company.com',
      from: 'hr@company.com',
      body: 'Welcome! Here is everything you need to know for your first day...',
      labels: ['INBOX', 'IMPORTANT'],
    },
    {
      subject: 'Your IT Equipment',
      to: 'newemployee@company.com',
      from: 'it@company.com',
      body: 'Your laptop and access credentials will be ready on your first day.',
      labels: ['INBOX'],
    },
    {
      subject: 'Team Introduction',
      to: 'newemployee@company.com',
      from: 'manager@company.com',
      body: "Looking forward to having you on the team! Let's schedule a 1:1 for your first week.",
      labels: ['INBOX', 'IMPORTANT'],
    },
    {
      subject: 'Onboarding Checklist',
      to: 'newemployee@company.com',
      from: 'hr@company.com',
      body: 'Please complete the following items before your start date: [list]',
      labels: ['INBOX'],
    },
  ];

  const onboardingDrafts: GmailDraft[] = [
    {
      subject: 'Re: Welcome to Acme Corp!',
      to: 'hr@company.com',
      from: 'newemployee@company.com',
      body: 'Thank you so much! I am excited to join the team.',
    },
    {
      subject: 'Questions about First Day',
      to: 'manager@company.com',
      from: 'newemployee@company.com',
      body: 'Hi! I have a few questions about what to expect on my first day...',
    },
  ];

  const response = await initializeGmailSandbox('sandbox_007', {
    messages: onboardingMessages,
    drafts: onboardingDrafts,
  });

  console.log('Onboarding scenario initialized:', response);
}

/**
 * Main function - Run all examples
 */
async function main() {
  console.log('='.repeat(60));
  console.log('Gmail Sandbox Seeding Examples');
  console.log('='.repeat(60));

  try {
    // Uncomment the examples you want to run:

    await example1_basicInitialization();
    // await example2_bulkGeneration();
    // await example3_supportInbox();
    // await example4_customLogic();
    // await example5_emailThreads();
    // await example6_dateRanges();
    // await example7_onboardingScenario();

    console.log('\n' + '='.repeat(60));
    console.log('All examples completed successfully!');
    console.log('='.repeat(60) + '\n');
  } catch (error) {
    console.error('Error running examples:', error);
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}

// Export for use in other scripts
export {
  example1_basicInitialization,
  example2_bulkGeneration,
  example3_supportInbox,
  example4_customLogic,
  example5_emailThreads,
  example6_dateRanges,
  example7_onboardingScenario,
};
