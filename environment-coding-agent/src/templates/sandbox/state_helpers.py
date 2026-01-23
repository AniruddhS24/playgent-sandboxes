import os
from supabase import create_client

ENVIRONMENT_ID = os.environ["ENVIRONMENT_ID"]
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def get_state(record_id: str) -> dict:
    """Fetch a state record by ID."""
    return supabase.table('artificial_data').select('*') \
        .eq("id", record_id).eq("environment_id", ENVIRONMENT_ID) \
        .single().execute().data


def query_state(app: str, component_name: str = None) -> list:
    """Query state records."""
    query = supabase.table('artificial_data').select('*') \
        .eq("app", app).eq("environment_id", ENVIRONMENT_ID)
    if component_name:
        query = query.eq("component_name", component_name)
    return query.execute().data


def insert_state(app: str, component_name: str, json_data: dict) -> dict:
    """Insert a new state record."""
    return supabase.table('artificial_data').insert({
        "app": app,
        "component_name": component_name,
        "json_data": json_data,
        "environment_id": ENVIRONMENT_ID,
    }).execute().data[0]


def update_state(record_id: str, json_data: dict) -> dict:
    """Update a state record's json_data."""
    return supabase.table('artificial_data').update({"json_data": json_data}) \
        .eq("id", record_id).eq("environment_id", ENVIRONMENT_ID) \
        .execute().data[0]


def delete_state(record_id: str) -> bool:
    """Delete a state record."""
    supabase.table('artificial_data').delete() \
        .eq("id", record_id).eq("environment_id", ENVIRONMENT_ID).execute()
    return True
