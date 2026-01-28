from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="linear_list_projects", description="Get all Linear projects with full data", app="linear")
def list_projects() -> list:
    """Get all Linear projects with issues and comments."""
    projects = query_state("linear", "projects")
    return [{"project_id": p["id"], **p["json_data"]} for p in projects]


@action(name="linear_get_project", description="Get a single Linear project by ID", app="linear")
def get_project(project_id: str) -> dict:
    """Get a Linear project with all its issues and comments."""
    project = get_state(project_id)
    return {"project_id": project["id"], **project["json_data"]}


@action(name="linear_create_issue", description="Create a new issue in a Linear project", app="linear")
def create_issue(project_id: str, title: str, description: str = "", priority: int = 0, state_name: str = "Todo") -> dict:
    """Create a new issue in a Linear project."""
    project = get_state(project_id)
    issue = {
        "title": title,
        "description": description,
        "priority": priority,
        "state_name": state_name,
        "comments": []
    }
    project["json_data"].setdefault("issues", []).append(issue)
    return update_state(project_id, project["json_data"])


@action(name="linear_update_issue", description="Update an issue in a Linear project", app="linear")
def update_issue(project_id: str, issue_index: int, title: str = None, description: str = None, priority: int = None, state_name: str = None, comment: str = None) -> dict:
    """Update an existing issue in a Linear project. Optionally add a comment."""
    project = get_state(project_id)
    issues = project["json_data"].get("issues", [])
    if 0 <= issue_index < len(issues):
        if title is not None:
            issues[issue_index]["title"] = title
        if description is not None:
            issues[issue_index]["description"] = description
        if priority is not None:
            issues[issue_index]["priority"] = priority
        if state_name is not None:
            issues[issue_index]["state_name"] = state_name
        if comment is not None:
            issues[issue_index].setdefault("comments", []).append({"body": comment})
        return update_state(project_id, project["json_data"])
    return {"error": "Issue not found"}
