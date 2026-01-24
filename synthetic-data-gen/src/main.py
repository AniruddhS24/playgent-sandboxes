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
    """Fetch existing data for all allowed apps in the environment."""
    with tracer.start_as_current_span(name="fetch_existing_data"):
        response = supabase.table('artificial_data') \
            .select('id, app, component_name, json_data') \
            .eq('environment_id', environment_id) \
            .in_('app', allowed_apps) \
            .execute()

        logger.info(f"Fetched {len(response.data or [])} existing records")
        return response.data or []


# =============================================================================
# Stage 1: Generate Raw Data Text
# =============================================================================

def build_generation_prompt(
    scenario: str,
    schemas: List[Dict[str, Any]],
    existing_data: List[Dict[str, Any]]
) -> str:
    """Build the prompt for raw data generation."""

    # Format schemas for the prompt
    schema_descriptions = []
    for s in schemas:
        schema_descriptions.append(f"""
App: {s['app']}
Component: {s['component_name']}
Description: {s.get('description', 'N/A')}
Schema: {json.dumps(s['schema'], indent=2)}
""")

    # Format existing data summary
    existing_summary = ""
    if existing_data:
        existing_summary = "\n\nEXISTING DATA (avoid duplicates, maintain consistency):\n"
        for record in existing_data[:10]:  # Limit to avoid token overflow
            existing_summary += f"- {record['app']}/{record['component_name']}: {json.dumps(record['json_data'])[:200]}...\n"

    return f"""You are a synthetic data generation assistant creating realistic test data for agent testing environments.

SCENARIO:
{scenario}

AVAILABLE SCHEMAS:
{''.join(schema_descriptions)}
{existing_summary}

YOUR TASK:
Generate detailed, realistic data for EACH schema that fits the scenario. Write out the complete data as structured text.

For each piece of data, clearly indicate:
1. Which app and component it belongs to
2. All the field values matching the schema structure
3. Realistic content grounded in the scenario

Be thorough - generate ALL the data needed to set up this scenario. Include specific names, realistic email content, proper timestamps, etc.

Format your response as sections, one per data object:

=== APP: [app_name] | COMPONENT: [component_name] ===
[Detailed data following the schema structure]

Generate complete, scenario-appropriate data for each relevant schema."""


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
# Main Job Entry Point
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

        # Log results
        logger.info("=" * 60)
        logger.info("Generation Complete!")
        logger.info("=" * 60)
        logger.info(f"Raw data length: {result.get('raw_data_length', 0)} chars")
        logger.info(f"Schemas processed: {result.get('schemas_processed', 0)}")
        logger.info(f"Data objects generated: {len(result.get('generated', []))}")

        for item in result.get('generated', []):
            logger.info(f"  - {item['app']}/{item['component_name']}")

        logger.info("=" * 60)


# Start the Blaxel job
bl_start_job.start(generate_data_from_scenario)
