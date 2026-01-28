from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="github_list_repos", description="Get all GitHub repositories with full data", app="github")
def list_repos() -> list:
    """Get all GitHub repositories with issues and PRs."""
    repos = query_state("github", "repo")
    return [{"repo_id": r["id"], **r["json_data"]} for r in repos]


@action(name="github_get_repo", description="Get a single GitHub repository by ID", app="github")
def get_repo(repo_id: str) -> dict:
    """Get a GitHub repository with all its issues and PRs."""
    repo = get_state(repo_id)
    return {"repo_id": repo["id"], **repo["json_data"]}


@action(name="github_create_issue", description="Create a new issue in a GitHub repository", app="github")
def create_issue(repo_id: str, title: str, description: str = "", labels: list = None) -> dict:
    """Create a new issue in a GitHub repository."""
    repo = get_state(repo_id)
    issues = repo["json_data"].get("issues", [])
    new_id = max([i.get("id", 0) for i in issues], default=0) + 1
    issue = {
        "id": new_id,
        "issue_title": title,
        "description": description,
        "status": "open",
        "labels": labels or []
    }
    repo["json_data"].setdefault("issues", []).append(issue)
    return update_state(repo_id, repo["json_data"])


@action(name="github_update_issue", description="Update an issue in a GitHub repository", app="github")
def update_issue(repo_id: str, issue_index: int, title: str = None, description: str = None, status: str = None, labels: list = None) -> dict:
    """Update an existing issue in a GitHub repository."""
    repo = get_state(repo_id)
    issues = repo["json_data"].get("issues", [])
    if 0 <= issue_index < len(issues):
        if title is not None:
            issues[issue_index]["issue_title"] = title
        if description is not None:
            issues[issue_index]["description"] = description
        if status is not None:
            issues[issue_index]["status"] = status
        if labels is not None:
            issues[issue_index]["labels"] = labels
        return update_state(repo_id, repo["json_data"])
    return {"error": "Issue not found"}
