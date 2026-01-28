"""
Scenario Planner - Creates coherent worlds from task sets.

Given a set of tasks an agent should be able to complete, this module:
1. Analyzes tasks to find shared entity types
2. Plans coherent entities that enable all tasks
3. Generates scenes (data to create) using those entities
4. Persists world state for future runs
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


# =============================================================================
# LLM Prompt for Scenario Planning
# =============================================================================

SCENARIO_PLANNER_SYSTEM_PROMPT = """You design COHERENT TEST ENVIRONMENTS for AI agent evaluation.

Given tasks an agent should complete, create the MINIMAL DATA that must exist for the agent to work. All data should feel like ONE company's actual operations.

PROCESS:
1. ANALYZE tasks to find what data the agent needs to READ/QUERY
2. PLAN coherent entities that appear across multiple data objects
3. OUTPUT world description + scenes with data to generate

KEY PRINCIPLE:
Only create PRECONDITIONS - the minimal context needed for tasks. If a task says "find frustrated emails and create Linear issues", you create the frustrated emails (precondition). The agent creates the Linear issues (that's the task).

COHERENCE:
- Same customer should appear in emails AND tables
- Realistic details (names, emails, amounts, dates)
- Mix of scenarios: some positive, some negative, some edge cases

SCHEMA CONSTRAINT:
- ONLY use schemas from the AVAILABLE SCHEMAS list
- Each node.schema_id must match exactly (format: "app/component")

EXISTING WORLD:
If a world already exists, EXTEND it - keep existing entities, add only what's needed.

OUTPUT FORMAT:
{
  "world_markdown": "# World: [Company Name]\\n\\n## Summary\\n[Brief description]\\n\\n## Entities\\n\\n### [Entity Type]\\n- **[Name]** (id: [snake_case_id])\\n  - [Key details]\\n  - Traits: [traits]",

  "scenes": [
    {
      "name": "Scene name",
      "description": "What this scene represents",
      "entity_refs": ["entity_id"],
      "nodes": [
        {
          "id": "unique_node_id",
          "schema_id": "app/component",
          "instruction": "Clear directive for generating this data",
          "context": {"entity_ref": "entity_id", "tone": "frustrated"},
          "depends_on": [],
          "update_existing_id": null
        }
      ]
    }
  ]
}

EXAMPLE:
Tasks: ["Find frustrated customer emails and create Linear issues", "Follow up on stale deals"]

What data is needed?
- Frustrated customer emails (so agent can find them)
- Customer table with ARR/renewal info (so agent can filter high-value)
- Stale deal emails (so agent can identify deals needing follow-up)

Output:
{
  "world_markdown": "# World: TechCorp SaaS\\n\\n## Summary\\nB2B SaaS company with enterprise customers.\\n\\n## Entities\\n\\n### Customers\\n- **Acme Corp** (id: acme_corp)\\n  - ARR: $75,000 | Renewal: 30 days\\n  - Contact: John Smith (john@acme.com)\\n  - Traits: enterprise, frustrated, high-value\\n\\n- **Beta Inc** (id: beta_inc)\\n  - ARR: $120,000 | Renewal: 90 days\\n  - Contact: Sarah Chen (sarah@beta.com)\\n  - Traits: enterprise, stale-deal",

  "scenes": [
    {
      "name": "Acme billing complaint",
      "description": "High-value frustrated customer email",
      "entity_refs": ["acme_corp"],
      "nodes": [
        {
          "id": "acme_frustrated_email",
          "schema_id": "gmail/thread",
          "instruction": "Create frustrated email from John at Acme about unexpected billing charges. He's considering cancellation.",
          "context": {"entity_ref": "acme_corp", "tone": "frustrated"},
          "depends_on": [],
          "update_existing_id": null
        }
      ]
    },
    {
      "name": "Customer records",
      "description": "Central customer database",
      "entity_refs": ["acme_corp", "beta_inc"],
      "nodes": [
        {
          "id": "customers_table",
          "schema_id": "airtable/table",
          "instruction": "Create Customers table with: Acme Corp ($75k ARR, renews in 30 days, john@acme.com) and Beta Inc ($120k ARR, renews in 90 days, sarah@beta.com)",
          "context": {"purpose": "customer_database"},
          "depends_on": [],
          "update_existing_id": null
        }
      ]
    },
    {
      "name": "Beta stale deal thread",
      "description": "Deal conversation that went cold",
      "entity_refs": ["beta_inc"],
      "nodes": [
        {
          "id": "beta_stale_email",
          "schema_id": "gmail/thread",
          "instruction": "Create email thread about enterprise expansion with Beta Inc. Last message was 3 weeks ago, no response.",
          "context": {"entity_ref": "beta_inc", "tone": "professional"},
          "depends_on": [],
          "update_existing_id": null
        }
      ]
    }
  ]
}"""


def build_scenario_prompt(
    tasks: List[str],
    schemas: List[Dict[str, Any]],
    existing_world: Optional[str] = None,
    existing_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build the user prompt for scenario planning."""
    # Format tasks
    tasks_text = "\n".join(f"- {task}" for task in tasks)

    # Format schemas
    schema_lines = []
    for s in schemas:
        schema_id = f"{s['app']}/{s['component_name']}"
        desc = s.get('description', 'No description')
        schema_lines.append(f"- {schema_id}: {desc}")
    schemas_text = "\n".join(schema_lines)

    # Format existing world
    world_text = ""
    if existing_world:
        world_text = f"\n\nEXISTING WORLD (extend, don't replace):\n{existing_world}"

    # Format existing data
    existing_text = ""
    if existing_data:
        existing_text = "\n\nEXISTING DATA IN ENVIRONMENT:\n"
        for record in existing_data[:10]:
            app = record['app']
            component = record['component_name']
            record_id = record.get('id', 'unknown')
            data = record.get('json_data', {})
            name = data.get('name') or data.get('title') or data.get('subject') or 'unnamed'
            existing_text += f"- {app}/{component}: id=\"{record_id}\" name=\"{name}\"\n"

    return f"""TASKS (what the AI agent should be able to do):
{tasks_text}

AVAILABLE SCHEMAS (you may ONLY use these):
{schemas_text}
{world_text}
{existing_text}
Design a coherent environment that enables ALL these tasks.
Remember: Create PRECONDITIONS only. The agent creates the outputs (issues, drafts, etc).

Respond with valid JSON matching the output format specified in the system prompt."""


# =============================================================================
# Scenario Planner Class
# =============================================================================

@dataclass
class Scene:
    """A coherent grouping of data to generate."""
    name: str
    description: str
    entity_refs: List[str]
    nodes: List[Dict[str, Any]]


@dataclass
class EnvironmentPlan:
    """Complete environment setup plan."""
    world_markdown: str
    scenes: List[Scene]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_markdown": self.world_markdown,
            "scenes": [
                {
                    "name": scene.name,
                    "description": scene.description,
                    "entity_refs": scene.entity_refs,
                    "nodes": scene.nodes,
                }
                for scene in self.scenes
            ],
        }


class ScenarioPlanner:
    """Plans coherent environments from task sets."""

    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o"):
        self.openai_client = openai_client
        self.model = model

    def plan_environment(
        self,
        tasks: List[str],
        schemas: List[Dict[str, Any]],
        existing_world: Optional[str] = None,
        existing_data: Optional[List[Dict[str, Any]]] = None,
    ) -> EnvironmentPlan:
        """Plan a coherent environment for the given tasks.

        Args:
            tasks: List of tasks the agent should be able to complete
            schemas: Available schemas from Supabase
            existing_world: Existing world_markdown (if any)
            existing_data: Existing data in the environment

        Returns:
            EnvironmentPlan with world description and scenes to generate
        """
        prompt = build_scenario_prompt(tasks, schemas, existing_world, existing_data)

        logger.info(f"Planning environment for {len(tasks)} tasks...")
        schema_keys = [f"{s['app']}/{s['component_name']}" for s in schemas]
        logger.info(f"Available schemas: {schema_keys}")

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SCENARIO_PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)

        # Parse into EnvironmentPlan
        scenes = [
            Scene(
                name=s["name"],
                description=s.get("description", ""),
                entity_refs=s.get("entity_refs", []),
                nodes=s.get("nodes", []),
            )
            for s in result.get("scenes", [])
        ]

        plan = EnvironmentPlan(
            world_markdown=result.get("world_markdown", ""),
            scenes=scenes,
        )

        # Validate schemas in nodes
        valid_schemas = {f"{s['app']}/{s['component_name']}" for s in schemas}
        for scene in plan.scenes:
            for node in scene.nodes:
                schema_id = node.get("schema_id", "")
                if schema_id not in valid_schemas:
                    logger.warning(
                        f"Scene '{scene.name}' node '{node.get('id')}' uses invalid schema '{schema_id}'"
                    )

        logger.info(f"Planned {len(plan.scenes)} scenes with {sum(len(s.nodes) for s in plan.scenes)} total nodes")

        return plan
