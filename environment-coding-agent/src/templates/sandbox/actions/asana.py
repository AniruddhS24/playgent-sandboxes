from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="asana_list_projects", description="Get all Asana projects with full data", app="asana")
def list_projects() -> list:
    """Get all Asana projects with tasks."""
    projects = query_state("asana", "project")
    return [{"project_id": p["id"], **p["json_data"]} for p in projects]


@action(name="asana_get_project", description="Get a single Asana project by ID", app="asana")
def get_project(project_id: str) -> dict:
    """Get an Asana project with all its tasks."""
    project = get_state(project_id)
    return {"project_id": project["id"], **project["json_data"]}


@action(name="asana_create_task", description="Create a new task in an Asana project", app="asana")
def create_task(project_id: str, name: str, description: str = "", assignee: str = None, due_date: str = None) -> dict:
    """Create a new task in an Asana project."""
    project = get_state(project_id)
    task = {
        "gid": "",
        "name": name,
        "description": description,
        "assignee": assignee or "",
        "due_date": due_date or "",
        "start_date": "",
        "due_datetime": "",
        "completed": False,
        "stories": []
    }
    project["json_data"].setdefault("tasks", []).append(task)
    return update_state(project_id, project["json_data"])


@action(name="asana_update_task", description="Update a task in an Asana project", app="asana")
def update_task(project_id: str, task_index: int, name: str = None, description: str = None, assignee: str = None, due_date: str = None, completed: bool = None) -> dict:
    """Update an existing task in an Asana project."""
    project = get_state(project_id)
    tasks = project["json_data"].get("tasks", [])
    if 0 <= task_index < len(tasks):
        if name is not None:
            tasks[task_index]["name"] = name
        if description is not None:
            tasks[task_index]["description"] = description
        if assignee is not None:
            tasks[task_index]["assignee"] = assignee
        if due_date is not None:
            tasks[task_index]["due_date"] = due_date
        if completed is not None:
            tasks[task_index]["completed"] = completed
        return update_state(project_id, project["json_data"])
    return {"error": "Task not found"}
