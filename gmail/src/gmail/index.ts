/**
 * Gmail Sandbox API
 *
 * Main module for initializing and managing a Gmail sandbox environment.
 * Inspired by Klavis AI's Gmail sandbox approach.
 *
 * This module provides a code-based API for agents to synthetically generate
 * Gmail data (messages, drafts) for testing and development purposes.
 */

import {
  GmailMessage,
  GmailDraft,
  GmailSandboxData,
  GmailSandboxResponse,
  GmailUserConfig,
} from './types';
import { createMessages } from './messages';
import { createDrafts } from './drafts';

// Re-export all types and functions
export * from './types';
export * from './messages';
export * from './drafts';

/**
 * Default user configuration for the sandbox
 */
const DEFAULT_USER_CONFIG: GmailUserConfig = {
  email: 'user@example.com',
  name: 'Sandbox User',
};

/**
 * Initializes the Gmail sandbox with seed data
 *
 * This is the primary method for seeding a Gmail sandbox environment.
 * It accepts messages and drafts and creates them in bulk.
 *
 * @param sandboxId - Unique identifier for this sandbox instance
 * @param data - The Gmail data to seed (messages and/or drafts)
 * @param userConfig - Optional user configuration
 * @param reset - If true, clears existing data before seeding
 * @returns Promise resolving to initialization response
 *
 * @example
 * ```typescript
 * const response = await initializeGmailSandbox('sandbox_123', {
 *   messages: [
 *     {
 *       subject: 'Welcome to the team!',
 *       to: 'newbie@example.com',
 *       body: 'Welcome aboard! We're excited to have you.',
 *       labels: ['INBOX', 'IMPORTANT'],
 *     },
 *   ],
 *   drafts: [
 *     {
 *       subject: 'Meeting follow-up',
 *       to: 'boss@example.com',
 *       body: 'Thanks for the meeting today...',
 *     },
 *   ],
 * }, undefined, true);
 * ```
 */
export async function initializeGmailSandbox(
  sandboxId: string,
  data: GmailSandboxData,
  userConfig?: GmailUserConfig,
  reset: boolean = false
): Promise<GmailSandboxResponse> {
  const config = userConfig || DEFAULT_USER_CONFIG;

  console.log(`[Gmail Sandbox] Initializing sandbox: ${sandboxId}`);
  console.log(`[Gmail Sandbox] User: ${config.email}`);
  console.log(`[Gmail Sandbox] Reset: ${reset}`);

  // Reset data files if requested
  if (reset) {
    console.log('[Gmail Sandbox] Resetting sandbox data...');
    await resetGmailSandbox(sandboxId);
  }

  const recordsCreated = {
    messages: 0,
    drafts: 0,
  };

  try {
    // Create messages if provided
    if (data.messages && data.messages.length > 0) {
      const messageIds = await createMessages(data.messages, config);
      recordsCreated.messages = messageIds.length;
    }

    // Create drafts if provided
    if (data.drafts && data.drafts.length > 0) {
      const draftIds = await createDrafts(data.drafts, config);
      recordsCreated.drafts = draftIds.length;
    }

    const response: GmailSandboxResponse = {
      sandbox_id: sandboxId,
      status: 'idle',
      message: `Successfully initialized Gmail sandbox with ${recordsCreated.messages} messages and ${recordsCreated.drafts} drafts`,
      records_created: recordsCreated,
    };

    console.log('[Gmail Sandbox] Initialization complete:', response);
    return response;
  } catch (error) {
    console.error('[Gmail Sandbox] Initialization failed:', error);
    throw error;
  }
}

/**
 * Resets a Gmail sandbox, deleting all data
 *
 * @param sandboxId - The sandbox ID to reset
 * @returns Promise resolving when reset is complete
 */
export async function resetGmailSandbox(sandboxId: string): Promise<void> {
  console.log(`[Gmail Sandbox] Resetting sandbox: ${sandboxId}`);

  const { promises: fs } = await import('fs');

  // Clear the data files
  await fs.writeFile('/app/data/messages.json', '[]', 'utf-8');
  await fs.writeFile('/app/data/drafts.json', '[]', 'utf-8');

  console.log('[Gmail Sandbox] Reset complete');
}

/**
 * Gets the current status of a Gmail sandbox
 *
 * @param sandboxId - The sandbox ID to check
 * @returns Promise resolving to sandbox status information
 */
export async function getGmailSandboxStatus(sandboxId: string): Promise<{
  sandbox_id: string;
  status: 'idle' | 'occupied';
  message_count: number;
  draft_count: number;
  created_at: string;
  updated_at: string;
}> {
  console.log(`[Gmail Sandbox] Getting status for sandbox: ${sandboxId}`);

  const { promises: fs } = await import('fs');

  // Read message and draft counts
  let messageCount = 0;
  let draftCount = 0;

  try {
    const messagesData = await fs.readFile('/app/data/messages.json', 'utf-8');
    const messages = JSON.parse(messagesData);
    messageCount = messages.length;
  } catch (error) {
    // If file doesn't exist, count is 0
  }

  try {
    const draftsData = await fs.readFile('/app/data/drafts.json', 'utf-8');
    const drafts = JSON.parse(draftsData);
    draftCount = drafts.length;
  } catch (error) {
    // If file doesn't exist, count is 0
  }

  return {
    sandbox_id: sandboxId,
    status: 'idle',
    message_count: messageCount,
    draft_count: draftCount,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

/**
 * Helper function to generate realistic test messages
 *
 * This is useful for agents that want to quickly generate a variety of test data
 * without manually specifying every field.
 *
 * @param count - Number of messages to generate
 * @param options - Options for message generation
 * @returns Array of generated messages
 */
export function generateTestMessages(
  count: number,
  options?: {
    labels?: string[];
    fromDomain?: string;
    toDomain?: string;
  }
): GmailMessage[] {
  const messages: GmailMessage[] = [];
  const labels = options?.labels || ['INBOX'];
  const fromDomain = options?.fromDomain || 'example.com';
  const toDomain = options?.toDomain || 'example.com';

  const subjects = [
    'Team Update: Q1 Progress',
    'Project Status Report',
    'Quick Question',
    'Meeting Notes - ',
    'Action Items from Today',
    'Weekly Newsletter',
    'Welcome to the Platform!',
    'Password Reset Request',
    'Invoice #',
    'Your Order Has Shipped',
  ];

  const bodies = [
    'Hi there,\n\nJust wanted to share a quick update...',
    'Hello,\n\nPlease find the attached report...',
    'Hey,\n\nDo you have a moment to discuss...',
    'Hi team,\n\nHere are the key takeaways from our meeting...',
    'Good morning,\n\nHere are the action items we discussed...',
    'Welcome!\n\nWe're excited to have you on board...',
    'Hello,\n\nYou recently requested to reset your password...',
    'Thank you for your purchase!\n\nYour order is on its way...',
  ];

  for (let i = 0; i < count; i++) {
    const subject = subjects[i % subjects.length] + (i > subjects.length ? ` ${i}` : '');
    const body = bodies[i % bodies.length];

    messages.push({
      subject,
      to: `user${i}@${toDomain}`,
      body,
      from: `sender${i}@${fromDomain}`,
      labels,
    });
  }

  return messages;
}

/**
 * Helper function to generate realistic test drafts
 *
 * @param count - Number of drafts to generate
 * @param options - Options for draft generation
 * @returns Array of generated drafts
 */
export function generateTestDrafts(
  count: number,
  options?: {
    fromDomain?: string;
    toDomain?: string;
  }
): GmailDraft[] {
  const drafts: GmailDraft[] = [];
  const fromDomain = options?.fromDomain || 'example.com';
  const toDomain = options?.toDomain || 'example.com';

  const subjects = [
    'Re: Partnership Opportunity',
    'Vacation Request',
    'Feedback on Product',
    'Budget Proposal',
    'Interview Thank You',
  ];

  const bodies = [
    'Hi,\n\nThank you for reaching out about the partnership...',
    'Hello,\n\nI would like to request vacation time...',
    'Hi there,\n\nI wanted to share some feedback about...',
    'Hello,\n\nPlease review the attached budget proposal...',
    'Dear [Name],\n\nThank you for taking the time to interview me...',
  ];

  for (let i = 0; i < count; i++) {
    const subject = subjects[i % subjects.length];
    const body = bodies[i % bodies.length];

    drafts.push({
      subject,
      to: `recipient${i}@${toDomain}`,
      body,
      from: `user@${fromDomain}`,
    });
  }

  return drafts;
}
