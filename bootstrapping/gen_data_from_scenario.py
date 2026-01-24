"""
gen_data_from_scenario.py - Generate synthetic JSON data from scenario descriptions

This script generates synthetic JSON data based on detailed scenario descriptions
(data environments to SET UP) and JSON schemas. Scenarios describe characters,
situations, data sources, and relationships - creating "data-rich worlds" for
agent testing.

Example usage:
  python gen_data_from_scenario.py \
    --scenario "Set up a customer support environment where John Smith is frustrated about a missing refund..." \
    --schema gmail_thread.json \
    --output data/

  python gen_data_from_scenario.py \
    --scenario-file scenario.txt \
    --schema email.json \
    --schema customer.json \
    --output support_data/ \
    --model claude-sonnet-4-5
"""

import json
import argparse
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from llm_access import LLMClient


def load_json_file(filepath: str) -> Any:
    """Load and return JSON data from a file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def load_text_file(filepath: str) -> str:
    """Load and return text from a file."""
    try:
        with open(filepath, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog='gen_data_from_scenario.py',
        description='Generate synthetic JSON data from scenario descriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example scenarios describe "data-rich worlds":
  "Set up a customer support environment where customer John Smith is
   frustrated about not receiving a refund for order #12345. Create an
   email thread with 3 messages showing escalating frustration."
        '''
    )

    # Scenario input (mutually exclusive)
    scenario_group = parser.add_mutually_exclusive_group(required=True)
    scenario_group.add_argument('--scenario', '-s',
                                metavar='TEXT',
                                help='Scenario description text')
    scenario_group.add_argument('--scenario-file', '-f',
                                metavar='FILE',
                                help='Path to file containing scenario description')

    # Required arguments
    parser.add_argument('--schema',
                        action='append',
                        required=True,
                        metavar='FILE',
                        dest='schemas',
                        help='Path to JSON schema file (can specify multiple)')
    parser.add_argument('--output', '-o',
                        required=True,
                        metavar='DIR',
                        help='Output directory for generated data')

    # Optional arguments
    parser.add_argument('--model', '-m',
                        default='gpt-4o-mini',
                        help='Model to use (default: gpt-4o-mini)')
    parser.add_argument('--count', '-n',
                        type=int,
                        default=1,
                        metavar='N',
                        help='Number of objects to generate per schema (default: 1)')

    return parser.parse_args()


def load_schemas(schema_paths: List[str]) -> List[Dict[str, Any]]:
    """Load all schema files."""
    schemas = []
    for path in schema_paths:
        schema = load_json_file(path)
        schema_name = Path(path).stem
        schemas.append({
            'path': path,
            'name': schema_name,
            'schema': schema
        })
    return schemas


def build_generation_prompt(
    scenario: str,
    schema: Dict[str, Any],
    schema_name: str,
    existing_objects: List[Dict[str, Any]] = None,
    object_index: int = 0,
    total_count: int = 1,
) -> List[Dict[str, str]]:
    """Build the prompt for generating data from a scenario."""

    # Build context about existing objects for consistency
    existing_context = ""
    if existing_objects:
        existing_context = f"""

Previously generated objects (maintain consistency with these):
{json.dumps(existing_objects, indent=2)}
"""

    # Indicate position if generating multiple
    position_hint = ""
    if total_count > 1:
        position_hint = f"\n\nYou are generating object {object_index + 1} of {total_count}. Ensure variety while maintaining scenario consistency."

    system_content = f"""You are a synthetic data generation assistant creating realistic test data.

SCENARIO (the data environment to set up):
{scenario}

SCHEMA ({schema_name}):
{json.dumps(schema, indent=2)}
{existing_context}
Generate a JSON object that:
1. Follows the schema structure EXACTLY
2. Is deeply grounded in the scenario details (characters, situation, tone)
3. Contains realistic, contextually appropriate content
4. Maintains internal consistency
5. References scenario-specific details (names, situations, relationships){position_hint}

Return ONLY valid JSON matching the schema."""

    user_content = "Generate the JSON object for this scenario."

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]


def generate_object(
    client: LLMClient,
    scenario: str,
    schema_info: Dict[str, Any],
    existing_objects: List[Dict[str, Any]] = None,
    object_index: int = 0,
    total_count: int = 1,
) -> Dict[str, Any]:
    """Generate a single object from the scenario."""
    messages = build_generation_prompt(
        scenario=scenario,
        schema=schema_info['schema'],
        schema_name=schema_info['name'],
        existing_objects=existing_objects,
        object_index=object_index,
        total_count=total_count,
    )

    response = client.create_chat_completion(
        messages=messages,
        response_format={"type": "json_object"}
    )

    return client.extract_json_response(response)


def generate_for_schema(
    client: LLMClient,
    scenario: str,
    schema_info: Dict[str, Any],
    count: int = 1,
) -> List[Dict[str, Any]]:
    """Generate objects for a single schema."""
    schema_name = schema_info['name']
    print(f"\nGenerating {count} object(s) for: {schema_name}")

    objects = []
    for i in range(count):
        try:
            obj = generate_object(
                client=client,
                scenario=scenario,
                schema_info=schema_info,
                existing_objects=objects if objects else None,
                object_index=i,
                total_count=count,
            )
            objects.append(obj)
            print(f"  ✓ Generated object {i + 1}/{count}")
        except Exception as e:
            print(f"  ✗ Error generating object {i + 1}: {e}")

    return objects


def save_results(
    objects: List[Dict[str, Any]],
    output_dir: str,
    schema_name: str,
) -> str:
    """Save generated objects to output file."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{schema_name}_data.json")

    # Save as array if multiple, single object otherwise
    data = objects if len(objects) > 1 else objects[0] if objects else {}

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    return output_path


def main(args: argparse.Namespace) -> Dict[str, Any]:
    """Main function to orchestrate scenario-based data generation."""
    start_time = datetime.now()

    # Load scenario
    if args.scenario:
        scenario = args.scenario
    else:
        scenario = load_text_file(args.scenario_file)

    # Load schemas
    schemas = load_schemas(args.schemas)

    # Print header
    print()
    print("=" * 60)
    print("Scenario-Based Data Generation")
    print("=" * 60)
    print(f"Scenario: {scenario[:100]}{'...' if len(scenario) > 100 else ''}")
    print(f"Schemas: {', '.join(s['name'] for s in schemas)}")
    print(f"Objects per schema: {args.count}")
    print(f"Model: {args.model}")
    print("=" * 60)

    # Initialize client
    client = LLMClient(model=args.model)

    # Generate for each schema
    results = {}
    total_generated = 0

    for schema_info in schemas:
        schema_name = schema_info['name']

        try:
            objects = generate_for_schema(
                client=client,
                scenario=scenario,
                schema_info=schema_info,
                count=args.count,
            )

            if objects:
                output_path = save_results(objects, args.output, schema_name)
                results[schema_name] = {
                    'success': True,
                    'count': len(objects),
                    'output_path': output_path
                }
                total_generated += len(objects)
                print(f"  Saved: {output_path}")
            else:
                results[schema_name] = {
                    'success': False,
                    'error': 'No objects generated'
                }

        except Exception as e:
            print(f"  Error: {e}")
            results[schema_name] = {
                'success': False,
                'error': str(e)
            }

    # Print summary
    elapsed = (datetime.now() - start_time).total_seconds()

    print()
    print("=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"  Total objects: {total_generated}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print(f"  Output: {args.output}")
    print("=" * 60)
    print()

    return {
        'scenario_length': len(scenario),
        'schemas': [s['name'] for s in schemas],
        'results': results,
        'total_generated': total_generated,
        'elapsed_seconds': elapsed
    }


if __name__ == "__main__":
    args = parse_arguments()
    result = main(args)
