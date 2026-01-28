# Bootstrap templates for sandbox action system
from pathlib import Path

SANDBOX_TEMPLATE_DIR = Path(__file__).parent / "sandbox"


def get_template(relative_path: str) -> str:
    """Read a template file and return its contents."""
    file_path = SANDBOX_TEMPLATE_DIR / relative_path
    return file_path.read_text()


# Read templates from actual Python files
TEMPLATE_STATE_HELPERS = get_template("state_helpers.py")
TEMPLATE_ACTIONS_INIT = get_template("actions/__init__.py")
TEMPLATE_GMAIL_ACTIONS = get_template("actions/gmail.py")
TEMPLATE_CUSTOM_ACTIONS = get_template("actions/custom.py")
TEMPLATE_MCP_SERVER = get_template("mcp_server.py")

# App-specific action templates
TEMPLATE_SLACK_ACTIONS = get_template("actions/slack.py")
TEMPLATE_JIRA_ACTIONS = get_template("actions/jira.py")
TEMPLATE_ASANA_ACTIONS = get_template("actions/asana.py")
TEMPLATE_LINEAR_ACTIONS = get_template("actions/linear.py")
TEMPLATE_NOTION_ACTIONS = get_template("actions/notion.py")
TEMPLATE_GITHUB_ACTIONS = get_template("actions/github.py")
TEMPLATE_SALESFORCE_ACTIONS = get_template("actions/salesforce.py")
TEMPLATE_AIRTABLE_ACTIONS = get_template("actions/airtable.py")
