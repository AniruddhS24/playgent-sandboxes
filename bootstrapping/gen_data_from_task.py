"""
gen_data_from_task.py - Generate synthetic JSON data from task descriptions

This script generates synthetic JSON data based on natural language task descriptions
and JSON schemas, without requiring seed data. It can generate data for multiple
schemas in a single run.

Example usage:
  python gen_data_from_task.py \
    --task "Generate customer support tickets for a SaaS company" \
    --schema ticket_schema.json \
    --output data/ \
    --model claude-sonnet-4-5

  python gen_data_from_task.py \
    --task "Generate e-commerce data with products, orders, and customers" \
    --schema product_schema.json \
    --schema order_schema.json \
    --schema customer_schema.json \
    --output ecommerce_data/ \
    --model gpt-4o-mini
"""

import json
import argparse
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import LLM access module
from llm_access import LLMClient

# Global log file handle
log_file: Optional[Any] = None


def log(message: str, to_stdout: bool = True) -> None:
    """Write message to log file and optionally to stdout.

    Args:
        message: Message to log
        to_stdout: Whether to also print to stdout (default: True)
    """
    global log_file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"

    if log_file:
        log_file.write(log_message + "\n")
        log_file.flush()

    if to_stdout:
        print(message)


def load_json_file(filepath: str) -> Any:
    """Load and return JSON data from a file.

    Args:
        filepath: Path to the JSON file

    Returns:
        Parsed JSON data

    Raises:
        SystemExit: If file not found or invalid JSON
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Namespace object containing parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='gen_data_from_task.py',
        description='Generate synthetic JSON objects from task descriptions and schemas',
        epilog='''
Example usage:
  python gen_data_from_task.py --task "Generate email data for a sales team" --schema email_schema.json --output data/ --model claude-sonnet-4-5
  python gen_data_from_task.py --task "Generate e-commerce data" --schema product_schema.json --schema order_schema.json --output data/ --model gpt-4o-mini
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Required arguments
    required = parser.add_argument_group('required arguments')
    required.add_argument('--task',
                         required=True,
                         metavar='TEXT',
                         help='Natural language task description for data generation (required)')
    required.add_argument('--schema',
                         action='append',
                         required=True,
                         metavar='FILE',
                         dest='schemas',
                         help='Path to JSON schema file (can be specified multiple times) (required)')
    required.add_argument('--output',
                         required=True,
                         metavar='DIR',
                         help='Output directory for generated data files (required)')

    # Optional arguments
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('--model',
                         metavar='NAME',
                         default='gpt-4o-mini',
                         help='Model to use for generation (default: gpt-4o-mini)')
    optional.add_argument('--filter',
                         action='store_true',
                         help='Enable LLM-based quality filtering (default: False)')
    optional.add_argument('--log',
                         metavar='FILE',
                         help='Path to log file for verbose output (optional)')

    return parser.parse_args()


def load_schemas(schema_paths: List[str]) -> List[Dict[str, Any]]:
    """Load and validate all schema files.

    Args:
        schema_paths: List of paths to schema files

    Returns:
        List of schema info dictionaries with keys: path, name, schema

    Raises:
        SystemExit: If any schema file is invalid
    """
    schemas = []
    log("=" * 60, to_stdout=False)
    log("Loading Schemas", to_stdout=False)
    log("=" * 60, to_stdout=False)

    for path in schema_paths:
        log(f"Loading schema from: {path}", to_stdout=False)
        schema = load_json_file(path)
        schema_name = Path(path).stem

        schemas.append({
            'path': path,
            'name': schema_name,
            'schema': schema
        })
        log(f"✓ Loaded: {schema_name}", to_stdout=False)

    log(f"Total schemas loaded: {len(schemas)}", to_stdout=False)
    log("=" * 60, to_stdout=False)

    return schemas


def build_generation_messages(
    task: str,
    schema: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Build messages for LLM generation request.

    Args:
        task: Task description
        schema: JSON schema

    Returns:
        List of message dictionaries for LLM API
    """
    system_content = f"""You are a synthetic data generation assistant. Generate a realistic JSON object based on the task description and schema provided.

Task: {task}

Schema:
{json.dumps(schema, indent=2)}

Generate a realistic JSON object that:
1. Follows the schema exactly
2. Is relevant to the task description
3. Has realistic, varied content
4. Is internally consistent

Return ONLY valid JSON."""

    user_content = "Generate a JSON object matching the schema and task description. Ensure realism in the generated data."

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content}
    ]


def generate_object(
    client: LLMClient,
    task: str,
    schema: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a single object via API call.

    Args:
        client: LLM client instance
        task: Task description
        schema: JSON schema

    Returns:
        Generated object

    Raises:
        Exception: If generation or parsing fails
    """
    log(f"Generating object...", to_stdout=False)

    messages = build_generation_messages(task, schema)

    response = client.create_chat_completion(
        messages=messages,
        response_format={"type": "json_object"}
    )

    result = client.extract_json_response(response)

    log(f"✓ Generated object", to_stdout=False)

    return result


def filter_object(
    client: LLMClient,
    obj: Dict[str, Any],
    schema: Dict[str, Any],
    task: str
) -> bool:
    """Use LLM to validate quality of generated object.

    Args:
        client: LLM client instance
        obj: Generated object to validate
        schema: JSON schema
        task: Original task description

    Returns:
        True if object passes filter, False otherwise
    """
    log("Filtering object with LLM...", to_stdout=False)

    system_message = {
        "role": "system",
        "content": "You are a data quality validator. Determine if a generated JSON object is valid, realistic, and matches the task requirements. Respond with ONLY 'YES' or 'NO'."
    }

    user_message = {
        "role": "user",
        "content": f"""Task: {task}

Schema:
{json.dumps(schema, indent=2)}

Generated object:
{json.dumps(obj, indent=2)}

Does this object meet the following criteria?
- Follows the schema correctly
- Realistic and well-formed values
- Relevant to the task description
- Internally consistent and high quality

Answer with ONLY 'YES' or 'NO'."""
    }

    response = client.create_chat_completion(
        messages=[system_message, user_message],
        temperature=0.0,
        max_tokens=10
    )

    response_text = client.extract_content(response).strip().upper()
    passed = "YES" in response_text

    log(f"Filter result: {response_text} ({'PASS' if passed else 'REJECT'})", to_stdout=False)

    return passed


def generate_for_schema(
    task: str,
    schema_info: Dict[str, Any],
    model: str,
    enable_filter: bool = False
) -> Dict[str, Any]:
    """Generate one object for the given schema.

    Args:
        task: Task description
        schema_info: Schema information dictionary
        model: Model name to use
        enable_filter: Whether to enable LLM filtering

    Returns:
        Generated object
    """
    schema = schema_info['schema']
    schema_name = schema_info['name']

    log(f"\nProcessing: {schema_name}", to_stdout=True)
    log("=" * 60, to_stdout=False)

    client = LLMClient(model=model)
    filter_client = LLMClient(model="gpt-4") if enable_filter else None

    try:
        obj = generate_object(client, task, schema)

        # Apply filtering if enabled
        if enable_filter and filter_client:
            if filter_object(filter_client, obj, schema, task):
                log(f"Object passed filter", to_stdout=False)
                print(f"  ✓ Generated and validated")
            else:
                log(f"Object rejected by filter, regenerating...", to_stdout=False)
                print(f"  ✗ Rejected by filter, regenerating...")
                # Regenerate once if rejected
                obj = generate_object(client, task, schema)
                print(f"  ✓ Generated")
        else:
            print(f"  ✓ Generated")

    except Exception as e:
        log(f"Error generating object: {e}", to_stdout=True)
        log(f"Generation error: {e}", to_stdout=False)
        import traceback
        log(traceback.format_exc(), to_stdout=False)
        raise

    log(f"Object generated for {schema_name}", to_stdout=False)
    log("=" * 60, to_stdout=False)

    return obj


def save_object(
    obj: Dict[str, Any],
    output_dir: str,
    schema_name: str
) -> str:
    """Save generated object to output file.

    Args:
        obj: Generated object
        output_dir: Output directory path
        schema_name: Name of the schema (used for filename)

    Returns:
        Path to saved file

    Raises:
        Exception: If file write fails
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{schema_name}_data.json")

    log(f"Saving object to {output_path}...", to_stdout=False)

    with open(output_path, 'w') as f:
        json.dump(obj, f, indent=2)

    log(f"✓ Saved to: {output_path}", to_stdout=False)

    return output_path


def main(args: argparse.Namespace) -> Dict[str, Any]:
    """Main function to orchestrate data generation.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing generation summary
    """
    global log_file

    # Initialize log file if provided
    if args.log:
        try:
            log_file = open(args.log, 'a')
            log(f"Log file opened: {args.log}", to_stdout=False)
        except Exception as e:
            print(f"Error opening log file: {e}")
            sys.exit(1)

    start_time = datetime.now()

    print()
    print("=" * 60)
    print("Task-Based Data Generation")
    print("=" * 60)
    print(f"Task: {args.task}")
    print(f"Schemas: {len(args.schemas)}")
    for schema_path in args.schemas:
        print(f"  - {Path(schema_path).stem}")
    print(f"Model: {args.model}")
    print(f"Filter: {'Enabled' if args.filter else 'Disabled'}")
    if args.log:
        print(f"Log file: {args.log}")
    print("=" * 60)

    log(f"Starting task-based data generation", to_stdout=False)
    log(f"Task: {args.task}", to_stdout=False)

    # Load schemas
    schemas = load_schemas(args.schemas)

    # Generate data for each schema
    results = {}
    total_generated = 0

    for schema_info in schemas:
        schema_name = schema_info['name']

        try:
            obj = generate_for_schema(
                task=args.task,
                schema_info=schema_info,
                model=args.model,
                enable_filter=args.filter
            )

            output_path = save_object(obj, args.output, schema_name)

            results[schema_name] = {
                'success': True,
                'output_path': output_path
            }
            total_generated += 1

            print(f"  Saved: {output_path}")

        except Exception as e:
            log(f"Error processing schema {schema_name}: {e}", to_stdout=True)
            results[schema_name] = {
                'success': False,
                'error': str(e)
            }

    # Final summary
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print()
    print("=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"  Schemas processed: {total_generated}/{len(schemas)}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print(f"  Output directory: {args.output}")
    print("=" * 60)
    print()

    log(f"Generation complete! Schemas: {total_generated}/{len(schemas)}, Time: {elapsed:.1f}s", to_stdout=False)

    # Close log file if opened
    if log_file:
        log("=" * 60, to_stdout=False)
        log("Log file closed", to_stdout=False)
        log_file.close()

    return {
        'task': args.task,
        'schemas': [s['name'] for s in schemas],
        'results': results,
        'total_generated': total_generated,
        'elapsed_seconds': elapsed
    }


if __name__ == "__main__":
    args = parse_arguments()
    result = main(args)
