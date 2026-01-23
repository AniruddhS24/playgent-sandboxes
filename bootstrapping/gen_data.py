import json
import argparse
import sys
from typing import Any, Dict, List, Union, Optional
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

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
        Parsed JSON data (can be dict, list, or other JSON types)
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

def extract_objects(data: Union[List[Any], Any], count: int, source_name: str) -> List[Any]:
    """Extract up to 'count' objects from data array.

    Args:
        data: List of objects or single object to extract from
        count: Number of objects to extract
        source_name: Name of the data source for logging

    Returns:
        List of extracted objects (up to count)
    """
    if not isinstance(data, list):
        log(f"Warning: {source_name} data is not a list, wrapping in list", to_stdout=False)
        data = [data]

    available: int = len(data)
    extracted: int = min(count, available)

    log(f"Extracting {extracted} objects from {source_name} (requested: {count}, available: {available})", to_stdout=False)

    return data[:extracted]

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments and return parsed args.

    Returns:
        Namespace object containing parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='gen_data.py',
        description='Generate synthetic JSON objects from seed data using LLM',
        epilog='''
Example usage:
  python3 gen_data.py --seed data/seed_data.json --synthetic data/synthetic_data.json --schema data/schema.json -n 2 -m 1 --target 10 --log generation.log
  python3 gen_data.py --seed gmail/gmail_data_seed.json --synthetic gmail/gmail_data_synthetic.json --schema gmail/gmail_message_schema.json -n 3 -m 2 --target 20

The script will iteratively generate synthetic JSON objects until the total count (seed + synthetic) reaches the target.
Each iteration uses a mix of seed and synthetic objects as templates for the LLM.
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Required arguments
    required = parser.add_argument_group('required arguments')
    required.add_argument('--seed',
                         required=True,
                         metavar='FILE',
                         help='Path to sample_data_seed.json file (required)')
    required.add_argument('--synthetic',
                         required=True,
                         metavar='FILE',
                         help='Path to sample_data_synthetic.json file (required)')
    required.add_argument('--schema',
                         required=True,
                         metavar='FILE',
                         help='Path to json_schema.json file (required)')
    required.add_argument('-n',
                         type=int,
                         required=True,
                         metavar='NUM',
                         help='Number of objects to extract from seed file (required)')
    required.add_argument('-m',
                         type=int,
                         required=True,
                         metavar='NUM',
                         help='Number of objects to extract from synthetic file (required)')
    required.add_argument('--target',
                         type=int,
                         required=True,
                         metavar='NUM',
                         help='Target total number of objects (seed + synthetic) to generate (required)')

    # Optional arguments
    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('--log',
                         metavar='FILE',
                         help='Path to log file for verbose output (optional)')
    optional.add_argument('--context',
                         metavar='TEXT',
                         help='Additional context words/instructions to guide LLM generation (optional)')

    return parser.parse_args()

def perform_data_extraction(
    seed_path: str,
    synthetic_path: str,
    schema_path: str,
    n_seed: int,
    m_synthetic: int
) -> Dict[str, Any]:
    """Load files and extract specified number of objects from each.

    Args:
        seed_path: Path to seed data JSON file
        synthetic_path: Path to synthetic data JSON file
        schema_path: Path to schema JSON file
        n_seed: Number of objects to extract from seed file
        m_synthetic: Number of objects to extract from synthetic file

    Returns:
        Dictionary containing schema, seed_objects, and synthetic_objects
    """
    log("=" * 60, to_stdout=False)
    log("Step 1: Loading and Extracting Data", to_stdout=False)
    log("=" * 60, to_stdout=False)

    # Load schema
    log(f"Loading schema from: {schema_path}", to_stdout=False)
    schema: Any = load_json_file(schema_path)
    log(f"✓ Schema loaded successfully", to_stdout=False)

    # Load and extract from seed file
    log(f"Loading seed data from: {seed_path}", to_stdout=False)
    seed_data: Any = load_json_file(seed_path)
    seed_objects: List[Any] = extract_objects(seed_data, n_seed, "seed")

    # Load and extract from synthetic file
    log(f"Loading synthetic data from: {synthetic_path}", to_stdout=False)
    synthetic_data: Any = load_json_file(synthetic_path)
    synthetic_objects: List[Any] = extract_objects(synthetic_data, m_synthetic, "synthetic")

    # Summary (log only)
    log("=" * 60, to_stdout=False)
    log("Extraction Summary:", to_stdout=False)
    log(f"  Seed objects extracted: {len(seed_objects)}", to_stdout=False)
    log(f"  Synthetic objects extracted: {len(synthetic_objects)}", to_stdout=False)
    log(f"  Total objects: {len(seed_objects) + len(synthetic_objects)}", to_stdout=False)
    log("=" * 60, to_stdout=False)

    # Return extracted data
    return {
        "schema": schema,
        "seed_objects": seed_objects,
        "synthetic_objects": synthetic_objects
    }

def generate_synthetic_object(
    schema: Dict[str, Any],
    seed_objects: List[Any],
    synthetic_objects: List[Any],
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a synthetic JSON object using LLM based on schema and templates.

    Args:
        schema: JSON schema defining the object structure
        seed_objects: Seed objects to use as templates
        synthetic_objects: Synthetic objects to use as templates
        context: Additional context/instructions for generation (optional)

    Returns:
        Generated synthetic object as a dictionary
    """
    log("=" * 60, to_stdout=False)
    log("Step 2: Generating Synthetic Object with LLM", to_stdout=False)
    log("=" * 60, to_stdout=False)

    # Initialize LLM client with GPT-5
    log("Initializing LLM client with gpt-5...", to_stdout=False)
    client = LLMClient(model="gpt-5")
    log("✓ LLM client initialized", to_stdout=False)

    # Prepare the conversation messages
    all_templates = seed_objects + synthetic_objects

    # Message 1: Provide the JSON schema with optional context
    system_content = "You are a data generation assistant. Here is the JSON schema you must follow:\n\n{}\n\n".format(json.dumps(schema, indent=2))

    if context:
        system_content += f"Additional context: {context}\n\n"
        log(f"Using additional context: {context}", to_stdout=False)

    system_content += "Follow the schema exactly and generate realistic, varied data."

    message_1 = {
        "role": "system",
        "content": system_content
    }

    # Message 2: Provide template examples
    message_2 = {
        "role": "user",
        "content": f"Here are some example JSON objects that follow this schema:\n\n{json.dumps(all_templates, indent=2)}"
    }

    # Message 3: Request a similar object (with context if provided)
    generation_request = "Please generate a new JSON object similar to these templates but with different content. The object should be realistic and follow the same schema."

    if context:
        generation_request += f" You also know the following information about the JSON objects: {context}"

    generation_request += " Return only valid JSON matching the schema."

    message_3 = {
        "role": "user",
        "content": generation_request
    }

    messages = [message_1, message_2, message_3]

    log("Sending request to LLM...", to_stdout=False)
    log(f"  - Model: {client.get_model()}", to_stdout=False)
    log(f"  - Messages: {len(messages)}", to_stdout=False)
    log(f"  - Templates provided: {len(all_templates)}", to_stdout=False)

    # Call LLM with JSON response format
    response = client.create_chat_completion(
        messages=messages,
        response_format={"type": "json_object"}
    )

    log("✓ LLM response received", to_stdout=False)

    # Extract JSON from response
    generated_object = client.extract_json_response(response)

    # Log full object to file only
    log("Generated Object:", to_stdout=False)
    log("=" * 60, to_stdout=False)
    log(json.dumps(generated_object, indent=2), to_stdout=False)
    log("=" * 60, to_stdout=False)

    # Print compact representation to stdout
    object_str = json.dumps(generated_object, separators=(',', ':'))
    if len(object_str) > 80:
        object_str = object_str[:77] + "..."
    print(f"  Generated: {object_str}")

    return generated_object

def llm_filter(
    generated_object: Dict[str, Any],
    seed_objects: List[Any],
    synthetic_objects: List[Any],
    schema: Dict[str, Any]
) -> bool:
    """Use LLM to determine if generated object fits the constraints.

    Args:
        generated_object: The newly generated JSON object to validate
        seed_objects: Seed objects used as templates
        synthetic_objects: Synthetic objects used as templates
        schema: JSON schema defining the structure

    Returns:
        True if object passes filter, False otherwise
    """
    log("=" * 60, to_stdout=False)
    log("LLM Filter: Validating Generated Object", to_stdout=False)
    log("=" * 60, to_stdout=False)

    # Initialize LLM client for filtering (using GPT-4)
    log("Initializing filter LLM client with gpt-4...", to_stdout=False)
    filter_client = LLMClient(model="gpt-4")
    log("✓ Filter LLM client initialized", to_stdout=False)

    # Prepare context: combine templates
    all_templates = seed_objects + synthetic_objects

    # Build the filtering prompt
    system_message = {
        "role": "system",
        "content": "You are a data quality validator. Your task is to determine if a newly generated JSON object fits the pattern and constraints of the provided template examples. You must respond with ONLY 'YES' or 'NO'."
    }

    user_message = {
        "role": "user",
        "content": f"""Here is the JSON schema:
{json.dumps(schema, indent=2)}

Here are the template examples that define the expected pattern:
{json.dumps(all_templates, indent=2)}

Here is the newly generated object to validate:
{json.dumps(generated_object, indent=2)}

Does this newly generated object fit the pattern and constraints of the templates? Consider:
- Does it follow the same structure and schema?
- Are the field values realistic and consistent with the templates?
- Does it maintain the same style and format as the examples?
- Be very strict, it is okay to answer 'NO' with a decent frequency!

Answer with ONLY 'YES' or 'NO'."""
    }

    messages = [system_message, user_message]

    log("Sending filter request to LLM...", to_stdout=False)

    # Call LLM for validation
    response = filter_client.create_chat_completion(
        messages=messages,
        temperature=0.0,  # Use deterministic filtering
        max_tokens=10     # We only need YES or NO
    )

    log("✓ Filter response received", to_stdout=False)

    # Extract response
    response_text = filter_client.extract_content(response).strip().upper()

    log(f"Filter response: {response_text}", to_stdout=False)

    # Parse YES/NO response
    if "YES" in response_text:
        log("✓ Object PASSED filter", to_stdout=False)
        log("=" * 60, to_stdout=False)
        return True
    elif "NO" in response_text:
        log("✗ Object REJECTED by filter", to_stdout=False)
        log("=" * 60, to_stdout=False)
        return False
    else:
        # If ambiguous, log warning and accept (fail-open)
        log(f"⚠ Ambiguous filter response: '{response_text}', accepting object", to_stdout=False)
        log("=" * 60, to_stdout=False)
        return True

def append_to_synthetic_file(filepath: str, new_data: Dict[str, Any]) -> None:
    """Append generated data to the synthetic JSON file.

    Args:
        filepath: Path to the synthetic data JSON file
        new_data: New data object to append
    """
    log("=" * 60, to_stdout=False)
    log("Step 3: Saving to Synthetic Data File", to_stdout=False)
    log("=" * 60, to_stdout=False)

    # Load existing data
    log(f"Loading existing synthetic data from: {filepath}", to_stdout=False)
    existing_data: Any = load_json_file(filepath)

    # Ensure it's a list
    if not isinstance(existing_data, list):
        log("Warning: Synthetic data is not a list, converting to list", to_stdout=False)
        existing_data = [existing_data] if existing_data else []

    # Append new data
    existing_data.append(new_data)
    log(f"✓ Appending new data (total objects: {len(existing_data)})", to_stdout=False)

    # Write back to file
    log(f"Writing updated data to: {filepath}", to_stdout=False)
    try:
        with open(filepath, 'w') as f:
            json.dump(existing_data, f, indent=2)
        log(f"✓ Successfully saved {len(existing_data)} objects to synthetic file", to_stdout=False)
    except Exception as e:
        log(f"Error writing to file: {e}", to_stdout=True)
        sys.exit(1)

    log("=" * 60, to_stdout=False)

def get_current_total_count(seed_path: str, synthetic_path: str) -> int:
    """Get the current total count of seed + synthetic objects.

    Args:
        seed_path: Path to seed data file
        synthetic_path: Path to synthetic data file

    Returns:
        Total count of objects in both files
    """
    seed_data = load_json_file(seed_path)
    synthetic_data = load_json_file(synthetic_path)

    seed_count = len(seed_data) if isinstance(seed_data, list) else 1
    synthetic_count = len(synthetic_data) if isinstance(synthetic_data, list) else (1 if synthetic_data else 0)

    return seed_count + synthetic_count

def main(args: argparse.Namespace) -> Dict[str, Any]:
    """Main function to orchestrate data generation.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing extracted data and schema
    """
    global log_file

    # Initialize log file if provided
    if args.log:
        try:
            log_file = open(args.log, 'a')
            log(f"Log file opened: {args.log}", to_stdout=False)
            log("=" * 60, to_stdout=False)
        except Exception as e:
            print(f"Error opening log file: {e}")
            sys.exit(1)

    print()
    print("=" * 60)
    print("Synthetic Data Generation Loop")
    print("=" * 60)
    print(f"Target total objects: {args.target}")
    if args.log:
        print(f"Log file: {args.log}")
    print("=" * 60)
    print()

    log(f"Starting data generation with target: {args.target}", to_stdout=False)

    # Load schema once (doesn't change)
    schema = load_json_file(args.schema)

    iteration = 0
    generated_objects: List[Dict[str, Any]] = []

    while True:
        iteration += 1

        # Check current total
        current_total = get_current_total_count(args.seed, args.synthetic)

        print(f"Iteration {iteration}:")
        print(f"  Current: {current_total} | Target: {args.target}")

        log(f"Iteration {iteration}: Current={current_total}, Target={args.target}", to_stdout=False)

        if current_total >= args.target:
            print(f"  ✓ Target reached!")
            log(f"Target reached! ({current_total} >= {args.target})", to_stdout=False)
            print()
            break

        print(f"  Generating... ({args.target - current_total} more needed)")

        log(f"Generating {args.target - current_total} more object(s)...", to_stdout=False)

        # Step 1: Extract data for this iteration
        result: Dict[str, Any] = perform_data_extraction(
            args.seed,
            args.synthetic,
            args.schema,
            args.n,
            args.m
        )

        # Step 2: Generate synthetic object using LLM
        generated_object = generate_synthetic_object(
            result["schema"],
            result["seed_objects"],
            result["synthetic_objects"],
            context=args.context
        )

        # Step 2.5: Filter the generated object with LLM
        if not llm_filter(
            generated_object,
            result["seed_objects"],
            result["synthetic_objects"],
            result["schema"]
        ):
            log("Object rejected by filter, retrying...", to_stdout=False)
            print("  ✗ Rejected by filter, retrying...")
            print()
            log("-" * 60, to_stdout=False)
            continue  # Skip to next iteration without incrementing count

        # Step 3: Append generated object to synthetic file
        append_to_synthetic_file(args.synthetic, generated_object)

        # Track generated objects
        generated_objects.append(generated_object)

        print()

        log("-" * 60, to_stdout=False)

    # Final summary
    final_total = get_current_total_count(args.seed, args.synthetic)
    print("=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"  Iterations: {iteration}")
    print(f"  Generated: {len(generated_objects)} objects")
    print(f"  Final total: {final_total} objects")
    print("=" * 60)
    print()

    log(f"Generation complete! Iterations={iteration}, Generated={len(generated_objects)}, Final total={final_total}", to_stdout=False)

    # Close log file if opened
    if log_file:
        log("=" * 60, to_stdout=False)
        log("Log file closed", to_stdout=False)
        log_file.close()

    return {
        "schema": schema,
        "generated_objects": generated_objects,
        "iterations": iteration,
        "final_total": final_total
    }

if __name__ == "__main__":
    args: argparse.Namespace = parse_arguments()
    result: Dict[str, Any] = main(args)
