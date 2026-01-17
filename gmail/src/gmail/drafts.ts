/**
 * Gmail Drafts API
 *
 * Methods for creating and managing Gmail drafts in the sandbox environment.
 */

import { promises as fs } from 'fs';
import { GmailDraft, GmailUserConfig, GmailMessage } from './types';
import { createMessage } from './messages';

const DRAFTS_FILE = '/app/data/drafts.json';

/**
 * Internal draft type with ID
 */
interface StoredDraft extends GmailDraft {
  id: string;
  created_at: string;
  updated_at: string;
}

/**
 * Read drafts from JSON file
 */
async function readDrafts(): Promise<StoredDraft[]> {
  try {
    const data = await fs.readFile(DRAFTS_FILE, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    // If file doesn't exist or is empty, return empty array
    return [];
  }
}

/**
 * Write drafts to JSON file
 */
async function writeDrafts(drafts: StoredDraft[]): Promise<void> {
  await fs.writeFile(DRAFTS_FILE, JSON.stringify(drafts, null, 2), 'utf-8');
}

/**
 * Creates a single Gmail draft in the sandbox
 *
 * @param draft - The draft data to create
 * @param userConfig - Optional user configuration (defaults will be used if not provided)
 * @returns Promise resolving to the created draft ID
 */
export async function createDraft(
  draft: GmailDraft,
  userConfig?: GmailUserConfig
): Promise<string> {
  // Validate required fields
  validateDraft(draft);

  // Set defaults
  const from = draft.from || userConfig?.email || 'user@example.com';

  // Generate draft ID
  const draftId = `draft_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const timestamp = new Date().toISOString();

  // Create stored draft
  const storedDraft: StoredDraft = {
    ...draft,
    from,
    id: draftId,
    created_at: timestamp,
    updated_at: timestamp,
  };

  // Read existing drafts
  const drafts = await readDrafts();

  // Add new draft
  drafts.push(storedDraft);

  // Write back to file
  await writeDrafts(drafts);

  console.log('[Gmail Sandbox] Creating draft:', {
    subject: draft.subject,
    to: draft.to,
    from,
  });

  return draftId;
}

/**
 * Creates multiple Gmail drafts in bulk
 *
 * @param drafts - Array of draft data to create
 * @param userConfig - Optional user configuration
 * @returns Promise resolving to array of created draft IDs
 */
export async function createDrafts(
  drafts: GmailDraft[],
  userConfig?: GmailUserConfig
): Promise<string[]> {
  const draftIds: string[] = [];

  for (const draft of drafts) {
    try {
      const id = await createDraft(draft, userConfig);
      draftIds.push(id);
    } catch (error) {
      console.error('[Gmail Sandbox] Error creating draft:', error);
      throw error;
    }
  }

  console.log(`[Gmail Sandbox] Created ${draftIds.length} drafts`);
  return draftIds;
}

/**
 * Retrieves a draft by ID
 *
 * @param draftId - The draft ID to retrieve
 * @returns Promise resolving to the draft data
 */
export async function getDraft(draftId: string): Promise<GmailDraft | null> {
  console.log('[Gmail Sandbox] Retrieving draft:', draftId);

  const drafts = await readDrafts();
  const draft = drafts.find(d => d.id === draftId);

  if (!draft) {
    return null;
  }

  // Return without internal fields
  const { id, created_at, updated_at, ...draftData } = draft;
  return draftData;
}

/**
 * Lists all drafts with optional filtering
 *
 * @param options - Filter options (from, to, etc.)
 * @returns Promise resolving to array of drafts
 */
export async function listDrafts(options?: {
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}): Promise<GmailDraft[]> {
  console.log('[Gmail Sandbox] Listing drafts with options:', options);

  let drafts = await readDrafts();

  // Apply filters
  if (options?.from) {
    drafts = drafts.filter(d => d.from === options.from);
  }

  if (options?.to) {
    drafts = drafts.filter(d => d.to === options.to);
  }

  // Sort by updated_at DESC (newest first)
  drafts.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

  // Apply pagination
  const offset = options?.offset || 0;
  const limit = options?.limit || drafts.length;
  drafts = drafts.slice(offset, offset + limit);

  // Return without internal fields
  return drafts.map(({ id, created_at, updated_at, ...draftData }) => draftData);
}

/**
 * Updates a draft
 *
 * @param draftId - The draft ID to update
 * @param updates - Partial draft data to update
 * @returns Promise resolving when update is complete
 */
export async function updateDraft(
  draftId: string,
  updates: Partial<GmailDraft>
): Promise<void> {
  // Validate updates if they include required fields
  if (updates.subject !== undefined && updates.subject.length > 255) {
    throw new Error('Draft subject must be 255 characters or less');
  }

  console.log('[Gmail Sandbox] Updating draft:', draftId, updates);

  const drafts = await readDrafts();
  const draft = drafts.find(d => d.id === draftId);

  if (!draft) {
    throw new Error(`Draft not found: ${draftId}`);
  }

  // Apply updates
  Object.assign(draft, updates);

  // Update timestamp
  draft.updated_at = new Date().toISOString();

  await writeDrafts(drafts);
}

/**
 * Deletes a draft by ID
 *
 * @param draftId - The draft ID to delete
 * @returns Promise resolving when deletion is complete
 */
export async function deleteDraft(draftId: string): Promise<void> {
  console.log('[Gmail Sandbox] Deleting draft:', draftId);

  const drafts = await readDrafts();
  const filteredDrafts = drafts.filter(d => d.id !== draftId);

  await writeDrafts(filteredDrafts);
}

/**
 * Sends a draft (converts it to a message)
 *
 * @param draftId - The draft ID to send
 * @returns Promise resolving to the created message ID
 */
export async function sendDraft(draftId: string): Promise<string> {
  console.log('[Gmail Sandbox] Sending draft:', draftId);

  // Read the draft
  const drafts = await readDrafts();
  const draft = drafts.find(d => d.id === draftId);

  if (!draft) {
    throw new Error(`Draft not found: ${draftId}`);
  }

  // Convert draft to message with SENT label
  const message: GmailMessage = {
    subject: draft.subject,
    to: draft.to,
    body: draft.body,
    cc: draft.cc,
    bcc: draft.bcc,
    from: draft.from,
    reply_to: draft.reply_to,
    labels: ['SENT'],
  };

  // Create the message
  const messageId = await createMessage(message);

  // Delete the draft
  await deleteDraft(draftId);

  return messageId;
}

/**
 * Validates a draft object
 */
function validateDraft(draft: GmailDraft): void {
  if (!draft.subject || draft.subject.length === 0) {
    throw new Error('Draft subject is required');
  }

  if (draft.subject.length > 255) {
    throw new Error('Draft subject must be 255 characters or less');
  }

  if (!draft.to || draft.to.length === 0) {
    throw new Error('Draft recipient (to) is required');
  }

  if (!draft.body || draft.body.length === 0) {
    throw new Error('Draft body is required');
  }

  // Basic email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(draft.to)) {
    throw new Error('Invalid recipient email address');
  }
}
