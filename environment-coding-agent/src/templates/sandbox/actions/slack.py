from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="slack_list_channels", description="Get all Slack channels", app="slack")
def list_channels() -> list:
    """Get all Slack channels with their data."""
    channels = query_state("slack", "channel")
    return [{"channel_id": ch["id"], **ch["json_data"]} for ch in channels]


@action(name="slack_get_channel", description="Get a single Slack channel by ID", app="slack")
def get_channel(channel_id: str) -> dict:
    """Get a Slack channel with all its messages."""
    channel = get_state(channel_id)
    return {"channel_id": channel["id"], **channel["json_data"]}


@action(name="slack_create_channel", description="Create a new Slack channel", app="slack")
def create_channel(name: str, description: str = "", members: list = None) -> dict:
    """Create a new Slack channel."""
    channel_data = {
        "name": name,
        "description": description,
        "members": members or [],
        "messages": []
    }
    return insert_state("slack", "channel", channel_data)


@action(name="slack_add_member", description="Add a member to a Slack channel", app="slack")
def add_member(channel_id: str, email: str) -> dict:
    """Add a member (by email) to a Slack channel."""
    channel = get_state(channel_id)
    channel["json_data"].setdefault("members", []).append(email)
    return update_state(channel_id, channel["json_data"])


@action(name="slack_send_message", description="Send a message to a Slack channel", app="slack")
def send_message(channel_id: str, to: str, from_email: str, message: str) -> dict:
    """Send a message to a Slack channel."""
    channel = get_state(channel_id)
    msg = {
        "to": to,
        "from": from_email,
        "message": message
    }
    channel["json_data"].setdefault("messages", []).append(msg)
    return update_state(channel_id, channel["json_data"])
