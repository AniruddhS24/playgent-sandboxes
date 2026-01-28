"""
DAG Builder for Synthetic Data Generation (MVP)

Minimal, declarative DAG construction inspired by:
- DSPy (NeurIPS 2023, ICLR 2024): Declarative signatures
- KGGen (2025): Structured entity extraction
- S-DAG: Subject-based dependency construction

Each node is self-contained - an LLM can generate data from the node alone.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import networkx as nx
from openai import OpenAI

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures (Minimal MVP)
# =============================================================================

@dataclass
class DAGNode:
    """Self-contained node with everything needed for generation."""
    # Identity
    id: str                                     # e.g., "gmail_thread_1"
    schema_id: str                              # e.g., "gmail/thread"

    # Generation context (for LLM)
    instruction: str                            # Clear directive for generation
    context: Dict[str, Any] = field(default_factory=dict)  # entities, tone, purpose

    # Lineage
    depends_on: List[str] = field(default_factory=list)    # Parent node IDs

    # Future: few-shot examples
    reference_examples: List[Dict] = field(default_factory=list)

    # Attached at runtime
    schema: Dict[str, Any] = field(default_factory=dict)

    # Reference to existing object from artificial_data table
    # If set, the node updates/adds to existing object instead of creating new
    update_existing_id: Optional[str] = None


@dataclass
class DAGEdge:
    """Simple dependency edge."""
    source: str                                 # Parent node ID
    target: str                                 # Child node ID
    relationship: str = "data_flow"             # data_flow | reference | derives_from
    mapping: Dict[str, str] = field(default_factory=dict)  # field mappings


@dataclass
class GenerationDAG:
    """Container for the complete DAG."""
    task: str
    nodes: Dict[str, DAGNode] = field(default_factory=dict)
    edges: List[DAGEdge] = field(default_factory=list)

    def add_node(self, node: DAGNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: DAGEdge) -> None:
        self.edges.append(edge)
        if edge.target in self.nodes:
            if edge.source not in self.nodes[edge.target].depends_on:
                self.nodes[edge.target].depends_on.append(edge.source)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to flat structure."""
        return {
            "task": self.task,
            "nodes": [
                {
                    "id": node.id,
                    "schema_id": node.schema_id,
                    "instruction": node.instruction,
                    "context": node.context,
                    "depends_on": node.depends_on,
                    "reference_examples": node.reference_examples,
                    "update_existing_id": node.update_existing_id,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "relationship": edge.relationship,
                    "mapping": edge.mapping,
                }
                for edge in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenerationDAG":
        """Deserialize from dictionary."""
        dag = cls(task=data["task"])

        for node_data in data.get("nodes", []):
            dag.add_node(DAGNode(
                id=node_data["id"],
                schema_id=node_data["schema_id"],
                instruction=node_data.get("instruction", ""),
                context=node_data.get("context", {}),
                depends_on=node_data.get("depends_on", []),
                reference_examples=node_data.get("reference_examples", []),
                update_existing_id=node_data.get("update_existing_id"),
            ))

        for edge_data in data.get("edges", []):
            dag.add_edge(DAGEdge(
                source=edge_data["source"],
                target=edge_data["target"],
                relationship=edge_data.get("relationship", "data_flow"),
                mapping=edge_data.get("mapping", {}),
            ))

        return dag

    def to_mermaid(self) -> str:
        """Export as Mermaid diagram."""
        lines = ["graph TD"]

        for node_id, node in self.nodes.items():
            safe_id = node_id.replace("/", "_").replace("-", "_").replace(" ", "_")
            lines.append(f'    {safe_id}["{node.schema_id}"]')

        for edge in self.edges:
            source = edge.source.replace("/", "_").replace("-", "_").replace(" ", "_")
            target = edge.target.replace("/", "_").replace("-", "_").replace(" ", "_")
            lines.append(f"    {source} -->|{edge.relationship}| {target}")

        return "\n".join(lines)


# =============================================================================
# LLM Prompt (DSPy-Inspired, Minimal)
# =============================================================================

DAG_SYSTEM_PROMPT = """You create SYNTHETIC TEST DATA for AI agent evaluation.

Your job: Given a task an AI agent must complete, determine what data needs to EXIST in the environment for the agent to work with. You are NOT modeling the agent's workflow - you are generating the TEST DATA the agent will encounter.

INPUT: A task description + available schemas + existing data
OUTPUT: JSON with nodes (data objects to create) and edges (dependencies)

CRITICAL RULES:
1. ONLY use schemas from the AVAILABLE SCHEMAS list - DO NOT invent schemas like "analysis/intermediate" or "workflow/step"
2. Each node = one piece of synthetic data to generate (an email, a table, an issue, etc.)
3. Think: "What data must exist for an agent to do this task?" NOT "What steps does the agent take?"
4. node.instruction = directive for generating realistic synthetic content
5. Sources (emails, messages) come BEFORE derived data (CRM records, tasks)

EXAMPLE REASONING:
Task: "Find frustrated customer emails and create Linear issues for high-value ones"
- What data needs to exist? → Frustrated customer emails (gmail/thread), Customer table with values (airtable/table)
- What does the agent CREATE? → Linear issues (linear/projects) - but we may want to pre-create the project
- NOT valid: "analysis/filter" or "workflow/decision" nodes - these aren't data!

UPDATE_EXISTING_ID:
- Set update_existing_id to reference an existing object when adding to it
- Example: To add a record to existing Airtable table, set update_existing_id to the table's ID
- Leave null when creating something entirely new

OUTPUT FORMAT:
{
  "nodes": [
    {
      "id": "unique_descriptive_id",
      "schema_id": "app/component",
      "instruction": "Clear, specific generation directive",
      "context": {
        "entities": {"person": "...", "company": "...", "email": "..."},
        "tone": "professional|casual|urgent",
        "purpose": "what this data represents"
      },
      "depends_on": [],
      "reference_examples": [],
      "update_existing_id": "abc123" or null
    }
  ],
  "edges": [
    {
      "source": "parent_node_id",
      "target": "child_node_id",
      "relationship": "data_flow",
      "mapping": {"source.field": "target.field"}
    }
  ]
}"""


def build_dag_prompt(
    task: str,
    schemas: List[Dict[str, Any]],
    existing_data: List[Dict[str, Any]]
) -> str:
    """Build minimal user prompt."""
    # Format schemas simply
    schema_lines = []
    for s in schemas:
        schema_id = f"{s['app']}/{s['component_name']}"
        desc = s.get('description', 'No description')
        schema_lines.append(f"- {schema_id}: {desc}")

    schemas_text = "\n".join(schema_lines)

    # Show existing data with IDs and full field definitions (but no records)
    existing_text = ""
    if existing_data:
        existing_text = "\n\nEXISTING DATA (set update_existing_id to add to these):\n"
        for record in existing_data[:10]:
            app = record['app']
            component = record['component_name']
            record_id = record.get('id', 'unknown')
            data = record.get('json_data', {})
            # Extract name and fields
            name = data.get('name') or data.get('title') or data.get('subject') or 'unnamed'
            existing_text += f"- {app}/{component}: id=\"{record_id}\" name=\"{name}\"\n"
            # Show fields if available (for airtable tables)
            if 'fields' in data:
                existing_text += f"  fields: {json.dumps(data['fields'])}\n"

    return f"""TASK (what the AI agent must do): {task}

AVAILABLE SCHEMAS (you may ONLY use these - no others):
{schemas_text}
{existing_text}
Create synthetic test data for this task. Each node = one data object to generate.
Remember: You're creating DATA that will exist in the environment, not modeling the agent's workflow.
ONLY use schema_ids from the list above."""


# =============================================================================
# DAG Builder
# =============================================================================

class DAGBuilder:
    """Builds generation DAGs from task descriptions."""

    def __init__(self, openai_client: OpenAI, model: str = "gpt-4o"):
        self.openai_client = openai_client
        self.model = model

    def build_dag_from_task(
        self,
        task: str,
        schemas: List[Dict[str, Any]],
        existing_data: Optional[List[Dict[str, Any]]] = None,
    ) -> GenerationDAG:
        """Build a DAG from task description."""
        # Build schema lookup
        valid_schemas = {
            f"{s['app']}/{s['component_name']}": s
            for s in schemas
        }

        prompt = build_dag_prompt(task, schemas, existing_data or [])

        logger.info(f"Building DAG for task: {task[:100]}...")

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DAG_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        dag_json = json.loads(response.choices[0].message.content)
        dag = self._parse_response(task, dag_json, valid_schemas)
        self._validate_dag(dag, valid_schemas)

        logger.info(f"Built DAG with {len(dag.nodes)} nodes and {len(dag.edges)} edges")
        return dag

    def _parse_response(
        self,
        task: str,
        dag_json: Dict[str, Any],
        valid_schemas: Dict[str, Dict[str, Any]]
    ) -> GenerationDAG:
        """Parse LLM response into GenerationDAG."""
        dag = GenerationDAG(task=task)

        for node_data in dag_json.get("nodes", []):
            schema_id = node_data.get("schema_id", "")
            schema = valid_schemas.get(schema_id, {}).get('schema', {})

            node = DAGNode(
                id=node_data["id"],
                schema_id=schema_id,
                instruction=node_data.get("instruction", ""),
                context=node_data.get("context", {}),
                depends_on=node_data.get("depends_on", []),
                reference_examples=node_data.get("reference_examples", []),
                schema=schema,
                update_existing_id=node_data.get("update_existing_id"),
            )
            dag.add_node(node)

        for edge_data in dag_json.get("edges", []):
            edge = DAGEdge(
                source=edge_data.get("source", ""),
                target=edge_data.get("target", ""),
                relationship=edge_data.get("relationship", "data_flow"),
                mapping=edge_data.get("mapping", {}),
            )
            dag.add_edge(edge)

        return dag

    def _validate_dag(
        self,
        dag: GenerationDAG,
        valid_schemas: Dict[str, Dict[str, Any]]
    ) -> None:
        """Validate DAG structure."""
        # Check schemas exist
        for node_id, node in dag.nodes.items():
            if node.schema_id not in valid_schemas:
                raise ValueError(
                    f"Node '{node_id}' uses invalid schema '{node.schema_id}'. "
                    f"Valid: {list(valid_schemas.keys())}"
                )

        # Check acyclic
        G = self.to_networkx(dag)
        if not nx.is_directed_acyclic_graph(G):
            cycles = list(nx.find_cycle(G))
            raise ValueError(f"DAG contains cycles: {cycles}")

    def to_networkx(self, dag: GenerationDAG) -> nx.DiGraph:
        """Convert to networkx graph."""
        G = nx.DiGraph()

        for node_id, node in dag.nodes.items():
            G.add_node(node_id, **{
                "schema_id": node.schema_id,
                "instruction": node.instruction,
                "context": node.context,
            })

        for edge in dag.edges:
            G.add_edge(edge.source, edge.target, **{
                "relationship": edge.relationship,
                "mapping": edge.mapping,
            })

        return G

    def get_generation_order(self, dag: GenerationDAG) -> List[List[str]]:
        """Get topological generations for parallel execution."""
        G = self.to_networkx(dag)
        return [list(gen) for gen in nx.topological_generations(G)]

    def get_linear_order(self, dag: GenerationDAG) -> List[str]:
        """Get single topological order for sequential execution."""
        G = self.to_networkx(dag)
        return list(nx.topological_sort(G))
