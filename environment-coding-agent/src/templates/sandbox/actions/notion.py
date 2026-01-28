from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="notion_list_pages", description="Get all Notion pages with full data", app="notion")
def list_pages() -> list:
    """Get all Notion pages with content blocks and comments."""
    pages = query_state("notion", "page")
    return [{"page_id": p["id"], **p["json_data"]} for p in pages]


@action(name="notion_get_page", description="Get a single Notion page by ID", app="notion")
def get_page(page_id: str) -> dict:
    """Get a Notion page with all its content blocks and comments."""
    page = get_state(page_id)
    return {"page_id": page["id"], **page["json_data"]}


@action(name="notion_create_page", description="Create a new Notion page", app="notion")
def create_page(name: str, content_blocks: list = None, parent_source: str = "") -> dict:
    """Create a new Notion page."""
    page_data = {
        "name": name,
        "parent_source": parent_source,
        "attributes": {},
        "content_blocks": content_blocks or [],
        "comments": []
    }
    return insert_state("notion", "page", page_data)


@action(name="notion_update_page", description="Update a Notion page", app="notion")
def update_page(page_id: str, name: str = None, attributes: dict = None, content_blocks: list = None) -> dict:
    """Update a Notion page's name, attributes, or content blocks."""
    page = get_state(page_id)
    if name is not None:
        page["json_data"]["name"] = name
    if attributes is not None:
        page["json_data"]["attributes"] = attributes
    if content_blocks is not None:
        page["json_data"]["content_blocks"] = content_blocks
    return update_state(page_id, page["json_data"])
