from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="gmail_list_threads", description="Get all email threads with full message data", app="gmail")
def list_threads() -> list:
    """Get all email threads with complete message data."""
    threads = query_state("gmail", "thread")
    return [{"thread_id": t["id"], **t["json_data"]} for t in threads]


@action(name="gmail_get_thread", description="Get a single email thread by ID", app="gmail")
def get_thread(thread_id: str) -> dict:
    """Get a single email thread with all its messages."""
    thread = get_state(thread_id)
    return {"thread_id": thread["id"], **thread["json_data"]}


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


@action(name="gmail_update_thread", description="Update labels on all messages in a thread", app="gmail")
def update_thread(thread_id: str, labels: list) -> dict:
    """Update labels on all messages in a thread."""
    thread = get_state(thread_id)
    for msg in thread["json_data"].get("messages", []):
        msg["labels"] = labels
    return update_state(thread_id, thread["json_data"])
