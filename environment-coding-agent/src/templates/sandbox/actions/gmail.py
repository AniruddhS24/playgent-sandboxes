import re
from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="gmail_send_email", description="Send an email or reply to an existing thread", app="gmail")
def send_email(to: str, subject: str, body: str, thread_id: str = None) -> dict:
    """Send a new email or reply to an existing thread."""
    email = {
        "to": to,
        "from": "user@example.com",
        "subject": subject,
        "body": body,
        "labels": ["SENT"],
        "cc": "",
        "bcc": "",
        "reply_to": ""
    }
    if thread_id:
        thread = get_state(thread_id)
        thread["json_data"]["messages"].append(email)
        return update_state(thread_id, thread["json_data"])
    return insert_state("gmail", "thread", {"messages": [email]})


@action(name="gmail_archive", description="Archive an email thread by removing INBOX label", app="gmail")
def archive(thread_id: str) -> dict:
    """Archive a thread by removing the INBOX label."""
    thread = get_state(thread_id)
    for msg in thread["json_data"]["messages"]:
        if "INBOX" in msg.get("labels", []):
            msg["labels"].remove("INBOX")
    return update_state(thread_id, thread["json_data"])


@action(name="gmail_mark_read", description="Mark all messages in a thread as read", app="gmail")
def mark_read(thread_id: str) -> dict:
    """Mark all messages in a thread as read."""
    thread = get_state(thread_id)
    for msg in thread["json_data"]["messages"]:
        msg["is_read"] = True
    return update_state(thread_id, thread["json_data"])


@action(name="gmail_add_label", description="Add a label to all messages in a thread", app="gmail")
def add_label(thread_id: str, label: str) -> dict:
    """Add a label to all messages in a thread."""
    thread = get_state(thread_id)
    for msg in thread["json_data"]["messages"]:
        if label not in msg.get("labels", []):
            msg.setdefault("labels", []).append(label)
    return update_state(thread_id, thread["json_data"])


@action(name="gmail_remove_label", description="Remove a label from all messages in a thread", app="gmail")
def remove_label(thread_id: str, label: str) -> dict:
    """Remove a label from all messages in a thread."""
    thread = get_state(thread_id)
    for msg in thread["json_data"]["messages"]:
        if label in msg.get("labels", []):
            msg["labels"].remove(label)
    return update_state(thread_id, thread["json_data"])


# Observation tools (read-only)

@action(name="gmail_search_email", description="Search emails by regex pattern in subject or body", app="gmail")
def search_email(pattern: str, label: str = None) -> list:
    """Search emails matching a regex pattern in subject or body."""
    threads = query_state("gmail", "thread")
    results = []
    regex = re.compile(pattern, re.IGNORECASE)

    for thread in threads:
        for msg in thread["json_data"].get("messages", []):
            # Filter by label if specified
            if label and label not in msg.get("labels", []):
                continue
            # Search in subject and body
            if regex.search(msg.get("subject", "")) or regex.search(msg.get("body", "")):
                results.append({
                    "thread_id": thread["id"],
                    "subject": msg.get("subject"),
                    "from": msg.get("from"),
                    "to": msg.get("to"),
                    "labels": msg.get("labels", []),
                    "is_read": msg.get("is_read", False)
                })
                break  # Only include thread once
    return results


@action(name="gmail_get_email", description="Get a single email thread by ID", app="gmail")
def get_email(thread_id: str) -> dict:
    """Get a single email thread with all its messages."""
    thread = get_state(thread_id)
    return {
        "thread_id": thread["id"],
        "messages": thread["json_data"].get("messages", [])
    }
