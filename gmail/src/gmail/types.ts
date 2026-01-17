/**
 * Gmail Sandbox Types
 *
 * Type definitions for Gmail sandbox data structures.
 * Inspired by Klavis AI's Gmail sandbox API.
 */

/**
 * Represents a Gmail message with all supported fields
 */
export interface GmailMessage {
  /** Email subject (required, max 255 characters) */
  subject: string;

  /** Recipient email address (required) */
  to: string;

  /** Email body content (required) */
  body: string;

  /** CC email addresses (comma-separated, optional) */
  cc?: string | null;

  /** BCC email addresses (comma-separated, optional) */
  bcc?: string | null;

  /** Sender email address (optional, defaults to authenticated user) */
  from?: string | null;

  /** Reply-to email address (optional) */
  reply_to?: string | null;

  /** Gmail labels (e.g., INBOX, SENT, IMPORTANT, optional) */
  labels?: string[] | null;
}

/**
 * Represents a Gmail draft with all supported fields
 */
export interface GmailDraft {
  /** Draft subject (required, max 255 characters) */
  subject: string;

  /** Recipient email address (required) */
  to: string;

  /** Draft body content (required) */
  body: string;

  /** CC email addresses (comma-separated, optional) */
  cc?: string | null;

  /** BCC email addresses (comma-separated, optional) */
  bcc?: string | null;

  /** Sender email address (optional, defaults to authenticated user) */
  from?: string | null;

  /** Reply-to email address (optional) */
  reply_to?: string | null;
}

/**
 * Complete Gmail sandbox initialization data structure
 */
export interface GmailSandboxData {
  /** List of Gmail messages to send */
  messages?: GmailMessage[] | null;

  /** List of Gmail drafts to create */
  drafts?: GmailDraft[] | null;
}

/**
 * Response from Gmail sandbox initialization
 */
export interface GmailSandboxResponse {
  /** Sandbox identifier */
  sandbox_id: string;

  /** Current sandbox status */
  status: 'idle' | 'occupied';

  /** Initialization message */
  message: string;

  /** Count of records created per object type */
  records_created: {
    messages: number;
    drafts: number;
  };
}

/**
 * Configuration for the authenticated user (sandbox owner)
 */
export interface GmailUserConfig {
  /** User's email address */
  email: string;

  /** User's display name */
  name?: string;
}
