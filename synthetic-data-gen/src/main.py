"""
Synthetic Data Generation Job - Two-stage generation with structured output

This Blaxel job generates synthetic JSON data using a 2-stage approach:
1. Generate raw text data from the scenario (creative generation)
2. Extract structured JSON for each schema using OpenAI structured outputs

Parameters:
    scenario: Detailed scenario description text
    environment_id: Environment ID to fetch connectors and scope data
    model: LLM model to use (default: "gpt-4o-mini")
"""

import os
import json
import logging
from typing import Any, Dict, List

from blaxel.core.jobs import bl_start_job
from opentelemetry import trace
from supabase import create_client, Client
from openai import OpenAI

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Initialize clients
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL", ""),
    os.environ.get("SUPABASE_KEY", "")
)

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))


# =============================================================================
# Schema Fetching
# =============================================================================

def fetch_schemas_for_apps(allowed_apps: List[str]) -> List[Dict[str, Any]]:
    """Fetch all schemas for the allowed apps."""
    with tracer.start_as_current_span(name="fetch_schemas"):
        response = supabase.table('schemas') \
            .select('app, component_name, schema, description') \
            .in_('app', allowed_apps) \
            .execute()

        schemas = []
        for row in response.data or []:
            schema_str = row.get('schema', '{}')
            schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
            schemas.append({
                'app': row['app'],
                'component_name': row['component_name'],
                'schema': schema,
                'description': row.get('description', '')
            })

        logger.info(f"Fetched {len(schemas)} schemas for apps: {allowed_apps}")
        return schemas


def fetch_existing_data(environment_id: str, allowed_apps: List[str]) -> List[Dict[str, Any]]:
    """Fetch existing airtable tables (hardcoded for now), stripped of records.

    This returns lightweight versions of existing data that the DAG builder
    can reference via update_existing_id. Records are stripped to reduce context size.
    """
    with tracer.start_as_current_span(name="fetch_existing_data"):
        # For now, only fetch airtable tables (hardcoded)
        response = supabase.table('artificial_data') \
            .select('id, app, component_name, json_data') \
            .eq('environment_id', environment_id) \
            .eq('app', 'airtable') \
            .eq('component_name', 'table') \
            .execute()

        results = []
        for record in response.data or []:
            data = record.get('json_data', {})
            # Strip records to reduce context size - keep name, fields, description
            if isinstance(data, dict):
                data = {k: v for k, v in data.items() if k != 'records'}
            results.append({
                'id': record['id'],
                'app': record['app'],
                'component_name': record['component_name'],
                'json_data': data
            })

        logger.info(f"Fetched {len(results)} existing airtable tables (records stripped)")
        return results


def insert_generated_data(
    generated_items: List[Dict[str, Any]],
    environment_id: str
) -> int:
    """Insert generated data into the artificial_data table."""
    with tracer.start_as_current_span(name="insert_generated_data"):
        if not generated_items:
            return 0

        records = [
            {
                'app': item['app'],
                'component_name': item['component_name'],
                'json_data': item['data'],
                'environment_id': environment_id
            }
            for item in generated_items
        ]

        response = supabase.table('artificial_data').insert(records).execute()
        inserted_count = len(response.data) if response.data else 0
        logger.info(f"Inserted {inserted_count} records into artificial_data")
        return inserted_count


# =============================================================================
# Stage 1: Generate Raw Data Text
# =============================================================================

def build_generation_prompt(
    scenario: str,
    schemas: List[Dict[str, Any]],
    existing_data: List[Dict[str, Any]]
) -> str:
    """Build prompt for raw data generation. Handles scenarios with/without reference traces."""

    # Format schemas for the prompt
    schema_descriptions = []
    for s in schemas:
        schema_descriptions.append(f"""
### {s['app']} / {s['component_name']}
Description: {s.get('description', 'N/A')}
Schema:
```json
{json.dumps(s['schema'], indent=2)}
```
""")

    # Format existing data summary
    existing_summary = ""
    if existing_data:
        existing_summary = "\n## EXISTING DATA\nMaintain consistency with these records:\n"
        for record in existing_data[:10]:  # Limit to avoid token overflow
            existing_summary += f"- {record['app']}/{record['component_name']}: {json.dumps(record['json_data'])[:200]}...\n"

    return f"""# SYNTHETIC DATA GENERATION

Generate realistic test data for agent testing environments.

## SCENARIO
{scenario}

## SCHEMAS TO POPULATE
{''.join(schema_descriptions)}
{existing_summary}

## INSTRUCTIONS

1. **If scenario contains REFERENCE AGENTIC TRACE:**
   - Generate data that enables the actions shown in the trace
   - Include specific entities and values the trace references
   - Create supporting context around those interactions

2. **If scenario is text description:**
   - Generate data that would realistically exist in that scenario
   - Create interconnected records with consistent relationships

## REQUIREMENTS
- Match schema structure exactly (all required fields)
- Use realistic values (proper names, valid emails, reasonable dates)
- Ensure coherence across schemas (no orphan references)
- No placeholders like "Lorem ipsum" or "[INSERT]"

## OUTPUT FORMAT

For each data object:
```
=== APP: [app_name] | COMPONENT: [component_name] ===
[field values matching schema]
```

Generate complete data for ALL relevant schemas."""


def generate_raw_data(
    scenario: str,
    schemas: List[Dict[str, Any]],
    existing_data: List[Dict[str, Any]],
    model: str
) -> str:
    """Stage 1: Generate raw text data from the scenario."""
    with tracer.start_as_current_span(name="generate_raw_data"):
        prompt = build_generation_prompt(scenario, schemas, existing_data)

        logger.info("Stage 1: Generating raw data text...")

        response = openai_client.responses.create(
            model=model,
            instructions="You are a synthetic data generator. Create realistic, detailed test data.",
            input=prompt,
        )

        raw_text = response.output_text
        logger.info(f"Stage 1 complete. Generated {len(raw_text)} characters of raw data.")

        return raw_text


# =============================================================================
# Stage 2: Extract Structured JSON for Each Schema
# =============================================================================

def extract_structured_data(
    raw_data: str,
    schema_info: Dict[str, Any],
    scenario: str,
    model: str
) -> Dict[str, Any] | None:
    """Stage 2: Extract structured JSON for a single schema using JSON mode."""
    with tracer.start_as_current_span(name="extract_structured_data"):
        app = schema_info['app']
        component = schema_info['component_name']
        schema = schema_info['schema']

        logger.info(f"Stage 2: Extracting {app}/{component}...")
        logger.info(f"  Schema: {json.dumps(schema)[:300]}...")

        extraction_prompt = f"""Extract the data for {app}/{component} from the raw generated data below.

SCENARIO CONTEXT:
{scenario[:500]}

RAW GENERATED DATA:
{raw_data}

Extract ONLY the data relevant to {app}/{component}.
Return a valid JSON object matching this exact schema structure:
{json.dumps(schema, indent=2)}

IMPORTANT: Return ONLY the JSON object, no markdown, no explanation. The JSON must match the schema exactly.

If no relevant data exists for this component, return an appropriate empty/default structure matching the schema."""

        try:
            # Use json_object mode (more flexible than strict json_schema)
            response = openai_client.responses.create(
                model=model,
                instructions="You are a JSON extraction assistant. Extract and format data as valid JSON matching the provided schema exactly. Return ONLY valid JSON, nothing else.",
                input=extraction_prompt,
                text={
                    "format": {
                        "type": "json_object"
                    }
                }
            )

            # Parse the JSON output
            json_text = response.output_text
            data = json.loads(json_text)

            logger.info(f"  Extracted {app}/{component}: {json.dumps(data)[:200]}...")
            return data

        except Exception as e:
            logger.error(f"  Failed to extract {app}/{component}: {e}")
            return None


# =============================================================================
# Main Generation Pipeline
# =============================================================================

def run_generation_pipeline(
    scenario: str,
    environment_id: str,
    allowed_apps: List[str],
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """Run the 2-stage generation pipeline."""
    with tracer.start_as_current_span(name="generation_pipeline"):

        # Fetch schemas and existing data
        schemas = fetch_schemas_for_apps(allowed_apps)
        existing_data = fetch_existing_data(environment_id, allowed_apps)

        if not schemas:
            logger.warning("No schemas found for the allowed apps")
            return {"error": "No schemas available", "generated": []}

        logger.info(f"Found {len(schemas)} schemas to generate data for")

        # Stage 1: Generate raw data text
        raw_data = generate_raw_data(scenario, schemas, existing_data, model)

        print("\n" + "=" * 60)
        print("STAGE 1 OUTPUT - Raw Generated Data")
        print("=" * 60)
        print(raw_data)
        print("=" * 60 + "\n")

        # Stage 2: Extract structured JSON for each schema
        generated_data = []

        for schema_info in schemas:
            app = schema_info['app']
            component = schema_info['component_name']

            data = extract_structured_data(raw_data, schema_info, scenario, model)

            if data:
                generated_data.append({
                    "app": app,
                    "component_name": component,
                    "data": data
                })

                print(f"\n--- {app}/{component} ---")
                print(json.dumps(data, indent=2))

        print("\n" + "=" * 60)
        print(f"STAGE 2 COMPLETE - Generated {len(generated_data)} data objects")
        print("=" * 60 + "\n")

        return {
            "raw_data_length": len(raw_data),
            "schemas_processed": len(schemas),
            "generated": generated_data
        }


# =============================================================================
# DAG-Based Generation (Task-Driven Approach)
# =============================================================================

from dag_builder import DAGBuilder


def output_dag(
    task: str,
    environment_id: str,
    model: str = "gpt-4o",
) -> Dict[str, Any]:
    """Build and return a DAG from a task for visualization.

    This function constructs a Directed Acyclic Graph (DAG) representing
    the data dependencies for a given task. The DAG can be used to:
    1. Visualize the data flow
    2. Later generate data in topological order

    Args:
        task: Action-oriented description (e.g., "Read email from X, create lead...")
        environment_id: Environment ID to fetch connectors and schemas
        model: LLM model for DAG construction (default: "gpt-4o")

    Returns:
        Dict containing:
        - task: Original task string
        - available_schemas: List of schema keys available for this environment
        - dag: Serialized DAG structure with nodes and edges
        - generation_order: List of lists showing parallel generation levels
        - mermaid: Mermaid diagram syntax for visualization
    """
    with tracer.start_as_current_span(name="output_dag"):
        logger.info("=" * 60)
        logger.info("DAG Construction from Task")
        logger.info("=" * 60)
        logger.info(f"Environment: {environment_id}")
        logger.info(f"Task: {task[:200]}{'...' if len(task) > 200 else ''}")
        logger.info(f"Model: {model}")
        logger.info("=" * 60)

        # 1. Get environment's allowed apps
        env_response = supabase.table('environments') \
            .select('connectors') \
            .eq('id', environment_id) \
            .execute()

        if not env_response.data:
            logger.error(f"Environment not found: {environment_id}")
            return {"error": f"Environment not found: {environment_id}"}

        connectors = env_response.data[0].get('connectors', [])
        allowed_apps = connectors if isinstance(connectors, list) else []

        if not allowed_apps:
            logger.warning("No connectors configured for this environment")
            return {"error": "No connectors configured for this environment"}

        logger.info(f"Allowed apps from connectors: {allowed_apps}")

        # 2. Fetch schemas - THESE DEFINE WHAT NODES ARE POSSIBLE
        schemas = fetch_schemas_for_apps(allowed_apps)
        existing_data = fetch_existing_data(environment_id, allowed_apps)

        if not schemas:
            logger.warning("No schemas found for the allowed apps")
            return {"error": "No schemas available"}

        available_schema_keys = [f"{s['app']}/{s['component_name']}" for s in schemas]
        logger.info(f"Available schemas: {available_schema_keys}")

        # 3. Build DAG with LLM (constrained to schemas)
        dag_builder = DAGBuilder(openai_client, model=model)
        dag = dag_builder.build_dag_from_task(task, schemas, existing_data)

        # 4. Get generation order
        generation_order = dag_builder.get_generation_order(dag)

        # 5. Build flat result (MVP format)
        dag_dict = dag.to_dict()
        result = {
            "task": task,
            "nodes": dag_dict["nodes"],
            "edges": dag_dict["edges"],
            "generation_order": generation_order,
            "mermaid": dag.to_mermaid()
        }

        # Log summary
        logger.info("=" * 60)
        logger.info("DAG Construction Complete!")
        logger.info(f"Nodes: {len(dag.nodes)} | Edges: {len(dag.edges)} | Levels: {len(generation_order)}")
        logger.info("=" * 60)

        # Print clean output
        print("\n" + "=" * 60)
        print("GENERATION DAG")
        print("=" * 60)
        print(f"Task: {task}")
        print(f"\nMermaid:\n{dag.to_mermaid()}")
        print("\n" + "-" * 40)
        print("NODES:")
        for node_id, node in dag.nodes.items():
            print(f"\n  [{node_id}] {node.schema_id}")
            print(f"    Instruction: {node.instruction}")
            print(f"    Context: {json.dumps(node.context)}")
            print(f"    Depends on: {node.depends_on}")
            print(f"    Reference examples: {node.reference_examples}")
            print(f"    update_existing_id: {node.update_existing_id}")

        print("\n" + "-" * 40)
        print("EDGES:")
        for edge in dag.edges:
            print(f"  {edge.source} --> {edge.target} [{edge.relationship}]")
            if edge.mapping:
                print(f"    Mapping: {edge.mapping}")

        print("\n" + "-" * 40)
        print("GENERATION ORDER:")
        for i, level in enumerate(generation_order):
            print(f"  Level {i}: {level}")
        print("=" * 60 + "\n")

        return result


# =============================================================================
# Main Job Entry Point (Scenario-Based - Original)
# =============================================================================

def generate_data_from_scenario(
    scenario: str,
    environment_id: str,
    model: str = "gpt-4o-mini",
) -> None:
    """Generate synthetic data from a scenario description.

    Args:
        scenario: Detailed scenario description text
        environment_id: Environment ID to fetch connectors and scope data
        model: LLM model to use (default: "gpt-4o-mini")
    """
    with tracer.start_as_current_span(name="generate_data_from_scenario"):
        logger.info("=" * 60)
        logger.info("Scenario-Based Data Generation (2-Stage Pipeline)")
        logger.info("=" * 60)
        logger.info(f"Environment: {environment_id}")
        logger.info(f"Scenario: {scenario[:200]}{'...' if len(scenario) > 200 else ''}")
        logger.info(f"Model: {model}")
        logger.info("=" * 60)

        # Fetch environment to get allowed apps (connectors)
        env_response = supabase.table('environments') \
            .select('connectors') \
            .eq('id', environment_id) \
            .execute()

        if not env_response.data:
            logger.error(f"Environment not found: {environment_id}")
            return

        connectors = env_response.data[0].get('connectors', [])
        allowed_apps = connectors if isinstance(connectors, list) else []

        if not allowed_apps:
            logger.warning("No connectors configured for this environment")
            return

        logger.info(f"Allowed apps from connectors: {allowed_apps}")

        # Run the 2-stage pipeline
        result = run_generation_pipeline(
            scenario=scenario,
            environment_id=environment_id,
            allowed_apps=allowed_apps,
            model=model,
        )

        # Insert generated data into database
        inserted = insert_generated_data(result.get('generated', []), environment_id)

        # Log results
        logger.info("=" * 60)
        logger.info("Generation Complete!")
        logger.info("=" * 60)
        logger.info(f"Raw data length: {result.get('raw_data_length', 0)} chars")
        logger.info(f"Schemas processed: {result.get('schemas_processed', 0)}")
        logger.info(f"Data objects generated: {len(result.get('generated', []))}")
        logger.info(f"Records inserted: {inserted}")

        for item in result.get('generated', []):
            logger.info(f"  - {item['app']}/{item['component_name']}")

        logger.info("=" * 60)


# =============================================================================
# New Entry Point: Task-Based DAG Generation (Legacy - Single Task)
# =============================================================================

def generate_data_from_task(
    task: str,
    environment_id: str,
    model: str = "gpt-4o",
) -> Dict[str, Any]:
    """Entry point: Build and display DAG from task (no data generation yet).

    Args:
        task: Action-oriented description (e.g., "Read email from X, create lead...")
        environment_id: Environment ID to fetch connectors and schemas
        model: LLM model for DAG construction (default: "gpt-4o")

    Returns:
        DAG result dictionary with nodes, edges, generation order, and mermaid diagram
    """
    result = output_dag(task, environment_id, model)
    return result


# =============================================================================
# New Entry Point: Coherent Environment Setup (Multiple Tasks)
# =============================================================================

from scenario_planner import ScenarioPlanner


def setup_environment(
    tasks: List[str],
    environment_id: str,
    model: str = "gpt-4o",
) -> Dict[str, Any]:
    """Set up a coherent environment for a set of agent tasks.

    This is the main entry point for the new world-based approach:
    1. Fetches environment config and existing world_markdown
    2. Plans coherent entities and scenes using ScenarioPlanner
    3. Saves updated world_markdown for persistence
    4. Returns scenes ready for data generation

    Args:
        tasks: List of tasks the agent should be able to complete
        environment_id: Environment to set up
        model: LLM model for planning (default: "gpt-4o")

    Returns:
        Dict containing:
        - world_markdown: The world description (saved to DB)
        - scenes: List of scenes with nodes to generate
    """
    with tracer.start_as_current_span(name="setup_environment"):
        # Handle tasks being passed as JSON string from batch runner
        if isinstance(tasks, str):
            try:
                tasks = json.loads(tasks)
            except json.JSONDecodeError:
                # If it's a single task string, wrap it in a list
                tasks = [tasks]

        logger.info("=" * 60)
        logger.info("Coherent Environment Setup")
        logger.info("=" * 60)
        logger.info(f"Environment: {environment_id}")
        logger.info(f"Tasks: {len(tasks)}")
        for i, task in enumerate(tasks, 1):
            logger.info(f"  {i}. {task[:100]}{'...' if len(task) > 100 else ''}")
        logger.info(f"Model: {model}")
        logger.info("=" * 60)

        # 1. Fetch environment (connectors + world_markdown)
        env_response = supabase.table('environments') \
            .select('connectors, world_markdown') \
            .eq('id', environment_id) \
            .execute()

        if not env_response.data:
            logger.error(f"Environment not found: {environment_id}")
            return {"error": f"Environment not found: {environment_id}"}

        connectors = env_response.data[0].get('connectors', [])
        existing_world = env_response.data[0].get('world_markdown')  # May be None
        allowed_apps = connectors if isinstance(connectors, list) else []

        if not allowed_apps:
            logger.warning("No connectors configured for this environment")
            return {"error": "No connectors configured for this environment"}

        logger.info(f"Allowed apps: {allowed_apps}")
        logger.info(f"Existing world: {'Yes' if existing_world else 'No (creating new)'}")

        # 2. Fetch schemas and existing data
        schemas = fetch_schemas_for_apps(allowed_apps)
        existing_data = fetch_existing_data(environment_id, allowed_apps)

        if not schemas:
            logger.warning("No schemas found for the allowed apps")
            return {"error": "No schemas available"}

        available_schema_keys = [f"{s['app']}/{s['component_name']}" for s in schemas]
        logger.info(f"Available schemas: {available_schema_keys}")

        # 3. Plan environment (creates or extends world)
        planner = ScenarioPlanner(openai_client, model=model)
        plan = planner.plan_environment(
            tasks=tasks,
            schemas=schemas,
            existing_world=existing_world,
            existing_data=existing_data,
        )

        # 4. Save updated world_markdown to database
        supabase.table('environments') \
            .update({'world_markdown': plan.world_markdown}) \
            .eq('id', environment_id) \
            .execute()
        logger.info("Saved world_markdown to database")

        # 5. Build result
        result = plan.to_dict()

        # Print clean output
        print("\n" + "=" * 60)
        print("ENVIRONMENT SETUP COMPLETE")
        print("=" * 60)

        print("\n--- WORLD ---")
        print(plan.world_markdown)

        print(f"\n--- SCENES ({len(plan.scenes)}) ---")
        for scene in plan.scenes:
            print(f"\n  [{scene.name}]")
            print(f"    Description: {scene.description}")
            print(f"    Entities: {scene.entity_refs}")
            print(f"    Nodes: {len(scene.nodes)}")
            for node in scene.nodes:
                print(f"      - {node['id']}: {node['schema_id']}")
                print(f"        Instruction: {node['instruction'][:80]}...")

        print("\n" + "=" * 60)

        logger.info("=" * 60)
        logger.info("Environment Setup Complete!")
        logger.info(f"World saved: Yes")
        logger.info(f"Scenes: {len(plan.scenes)}")
        logger.info(f"Total nodes: {sum(len(s.nodes) for s in plan.scenes)}")
        logger.info("=" * 60)

        return result


# Start the Blaxel job with environment setup entry point
bl_start_job.start(setup_environment)
