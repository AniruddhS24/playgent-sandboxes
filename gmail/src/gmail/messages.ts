/**
 * Gmail Messages API
 *
 * Methods for creating and managing Gmail messages in the sandbox environment.
 */

import { promises as fs } from 'fs';
import { GmailMessage, GmailUserConfig } from './types';

const MESSAGES_FILE = '/app/data/messages.json';

/**
 * Internal message type with ID
 */
interface StoredMessage extends GmailMessage {
  id: string;
  created_at: string;
  updated_at: string;
}

/**
 * Read messages from JSON file
 */
async function readMessages(): Promise<StoredMessage[]> {
  try {
    const data = await fs.readFile(MESSAGES_FILE, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    // If file doesn't exist or is empty, return empty array
    return [];
  }
}

/**
 * Write messages to JSON file
 */
async function writeMessages(messages: StoredMessage[]): Promise<void> {
  await fs.writeFile(MESSAGES_FILE, JSON.stringify(messages, null, 2), 'utf-8');
}

/**
 * Creates a single Gmail message in the sandbox
 *
 * @param message - The message data to create
 * @param userConfig - Optional user configuration (defaults will be used if not provided)
 * @returns Promise resolving to the created message ID
 */
export async function createMessage(
  message: GmailMessage,
  userConfig?: GmailUserConfig
): Promise<string> {
  // Validate required fields
  validateMessage(message);

  // Set defaults
  const from = message.from || userConfig?.email || 'user@example.com';
  const labels = message.labels || ['INBOX'];

  // Generate message ID
  const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const timestamp = new Date().toISOString();

  // Create stored message
  const storedMessage: StoredMessage = {
    ...message,
    from,
    labels,
    id: messageId,
    created_at: timestamp,
    updated_at: timestamp,
  };

  // Read existing messages
  const messages = await readMessages();

  // Add new message
  messages.push(storedMessage);

  // Write back to file
  await writeMessages(messages);

  console.log('[Gmail Sandbox] Creating message:', {
    subject: message.subject,
    to: message.to,
    from,
    labels,
  });

  return messageId;
}

/**
 * Creates multiple Gmail messages in bulk
 *
 * @param messages - Array of message data to create
 * @param userConfig - Optional user configuration
 * @returns Promise resolving to array of created message IDs
 */
export async function createMessages(
  messages: GmailMessage[],
  userConfig?: GmailUserConfig
): Promise<string[]> {
  const messageIds: string[] = [];

  for (const message of messages) {
    try {
      const id = await createMessage(message, userConfig);
      messageIds.push(id);
    } catch (error) {
      console.error('[Gmail Sandbox] Error creating message:', error);
      throw error;
    }
  }

  console.log(`[Gmail Sandbox] Created ${messageIds.length} messages`);
  return messageIds;
}

/**
 * Retrieves a message by ID
 *
 * @param messageId - The message ID to retrieve
 * @returns Promise resolving to the message data
 */
export async function getMessage(messageId: string): Promise<GmailMessage | null> {
  console.log('[Gmail Sandbox] Retrieving message:', messageId);

  const messages = await readMessages();
  const message = messages.find(m => m.id === messageId);

  if (!message) {
    return null;
  }

  // Return without internal fields
  const { id, created_at, updated_at, ...messageData } = message;
  return messageData;
}

/**
 * Lists all messages with optional filtering
 *
 * @param options - Filter options (labels, from, to, etc.)
 * @returns Promise resolving to array of messages
 */
export async function listMessages(options?: {
  labels?: string[];
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}): Promise<GmailMessage[]> {
  console.log('[Gmail Sandbox] Listing messages with options:', options);

  let messages = await readMessages();

  // Apply filters
  if (options?.labels && options.labels.length > 0) {
    messages = messages.filter(m =>
      m.labels && options.labels!.some(label => m.labels!.includes(label))
    );
  }

  if (options?.from) {
    messages = messages.filter(m => m.from === options.from);
  }

  if (options?.to) {
    messages = messages.filter(m => m.to === options.to);
  }

  // Sort by created_at DESC (newest first)
  messages.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  // Apply pagination
  const offset = options?.offset || 0;
  const limit = options?.limit || messages.length;
  messages = messages.slice(offset, offset + limit);

  // Return without internal fields
  return messages.map(({ id, created_at, updated_at, ...messageData }) => messageData);
}

/**
 * Deletes a message by ID
 *
 * @param messageId - The message ID to delete
 * @returns Promise resolving when deletion is complete
 */
export async function deleteMessage(messageId: string): Promise<void> {
  console.log('[Gmail Sandbox] Deleting message:', messageId);

  const messages = await readMessages();
  const filteredMessages = messages.filter(m => m.id !== messageId);

  await writeMessages(filteredMessages);
}

/**
 * Updates message labels (add/remove)
 *
 * @param messageId - The message ID
 * @param addLabels - Labels to add
 * @param removeLabels - Labels to remove
 * @returns Promise resolving when update is complete
 */
export async function updateMessageLabels(
  messageId: string,
  addLabels?: string[],
  removeLabels?: string[]
): Promise<void> {
  console.log('[Gmail Sandbox] Updating labels for message:', messageId, {
    add: addLabels,
    remove: removeLabels,
  });

  const messages = await readMessages();
  const message = messages.find(m => m.id === messageId);

  if (!message) {
    throw new Error(`Message not found: ${messageId}`);
  }

  // Initialize labels if not present
  if (!message.labels) {
    message.labels = [];
  }

  // Remove labels
  if (removeLabels && removeLabels.length > 0) {
    message.labels = message.labels.filter(label => !removeLabels.includes(label));
  }

  // Add labels
  if (addLabels && addLabels.length > 0) {
    for (const label of addLabels) {
      if (!message.labels.includes(label)) {
        message.labels.push(label);
      }
    }
  }

  // Update timestamp
  message.updated_at = new Date().toISOString();

  await writeMessages(messages);
}

/**
 * Validates a message object
 */
function validateMessage(message: GmailMessage): void {
  if (!message.subject || message.subject.length === 0) {
    throw new Error('Message subject is required');
  }

  if (message.subject.length > 255) {
    throw new Error('Message subject must be 255 characters or less');
  }

  if (!message.to || message.to.length === 0) {
    throw new Error('Message recipient (to) is required');
  }

  if (!message.body || message.body.length === 0) {
    throw new Error('Message body is required');
  }

  // Basic email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(message.to)) {
    throw new Error('Invalid recipient email address');
  }
}
