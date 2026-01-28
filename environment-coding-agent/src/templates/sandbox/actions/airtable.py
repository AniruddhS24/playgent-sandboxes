from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


@action(name="airtable_list_tables", description="Get all Airtable tables with full data", app="airtable")
def list_tables() -> list:
    """Get all Airtable tables with fields and records."""
    tables_data = query_state("airtable", "table")
    return [{"table_id": t["id"], **t["json_data"]} for t in tables_data]


@action(name="airtable_get_table", description="Get a single Airtable table by ID", app="airtable")
def get_table(table_id: str) -> dict:
    """Get an Airtable table with all its fields and records."""
    table = get_state(table_id)
    return {"table_id": table["id"], **table["json_data"]}


@action(name="airtable_create_record", description="Create a new record in an Airtable table", app="airtable")
def create_record(table_id: str, fields: dict) -> dict:
    """Create a new record in an Airtable table."""
    table = get_state(table_id)
    table["json_data"].setdefault("records", []).append(fields)
    return update_state(table_id, table["json_data"])


@action(name="airtable_update_record", description="Update a record in an Airtable table", app="airtable")
def update_record(table_id: str, record_index: int, fields: dict) -> dict:
    """Update an existing record in an Airtable table."""
    table = get_state(table_id)
    records = table["json_data"].get("records", [])
    if 0 <= record_index < len(records):
        records[record_index].update(fields)
        return update_state(table_id, table["json_data"])
    return {"error": "Record not found"}
