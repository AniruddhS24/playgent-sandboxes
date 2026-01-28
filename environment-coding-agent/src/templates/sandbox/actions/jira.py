from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="jira_list_projects", description="Get all Jira projects with full data", app="jira")
def list_projects() -> list:
    """Get all Jira projects with issues."""
    projects = query_state("jira", "project")
    return [{"project_id": p["id"], **p["json_data"]} for p in projects]


@action(name="jira_get_project", description="Get a single Jira project by ID", app="jira")
def get_project(project_id: str) -> dict:
    """Get a Jira project with all its issues."""
    project = get_state(project_id)
    return {"project_id": project["id"], **project["json_data"]}


@action(name="jira_create_issue", description="Create a new issue in a Jira project", app="jira")
def create_issue(project_id: str, summary: str, issue_type: str, description: str = "", priority: str = "Medium") -> dict:
    """Create a new issue in a Jira project."""
    project = get_state(project_id)
    issue = {
        "summary": summary,
        "issue_type": issue_type,
        "description": description,
        "priority": priority,
        "comments": [],
        "sprint_name": ""
    }
    project["json_data"].setdefault("issues", []).append(issue)
    return update_state(project_id, project["json_data"])


@action(name="jira_update_issue", description="Update an issue in a Jira project", app="jira")
def update_issue(project_id: str, issue_index: int, summary: str = None, description: str = None, priority: str = None, sprint_name: str = None, comment: str = None) -> dict:
    """Update an existing issue in a Jira project. Optionally add a comment."""
    project = get_state(project_id)
    issues = project["json_data"].get("issues", [])
    if 0 <= issue_index < len(issues):
        if summary is not None:
            issues[issue_index]["summary"] = summary
        if description is not None:
            issues[issue_index]["description"] = description
        if priority is not None:
            issues[issue_index]["priority"] = priority
        if sprint_name is not None:
            issues[issue_index]["sprint_name"] = sprint_name
        if comment is not None:
            issues[issue_index].setdefault("comments", []).append({"body": comment})
        return update_state(project_id, project["json_data"])
    return {"error": "Issue not found"}
