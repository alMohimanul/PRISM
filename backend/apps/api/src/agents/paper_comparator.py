"""Paper Comparator - Generates side-by-side comparison matrices for research papers."""

import json
import logging
import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..services.vector_store import VectorStoreService
from ..services.llm_provider import MultiProviderLLMClient, Provider

logger = logging.getLogger(__name__)


class ComparisonState(TypedDict):
    """State for Paper Comparison workflow."""

    # Input
    document_ids: List[str]
    focus: Optional[str]  # "methodology", "datasets", "results", "all"

    # Retrieved contexts
    paper_contexts: List[Dict[str, Any]]  # [{doc_id, title, context}]

    # Output
    comparison_matrix: Dict[str, Any]
    markdown_table: str
    insights: Dict[str, Any]
    error: Optional[str]


class PaperComparator:
    """Compares multiple research papers across key dimensions."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_client: MultiProviderLLMClient,
    ):
        """Initialize Paper Comparator.

        Args:
            vector_store: Vector store service for retrieving paper chunks
            llm_client: Multi-provider LLM client
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.graph = self._build_graph()

    @staticmethod
    def _parse_comparison_payload(response: str) -> Dict[str, Any]:
        """Parse comparison JSON from raw LLM output.

        Gemini sometimes wraps JSON in markdown fences or adds prose. This parser
        tries strict JSON first, then fenced JSON, then the first JSON object span.
        """
        response = response.strip()

        # 1) Strict JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 2) Markdown fenced JSON block
        fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", response, re.IGNORECASE)
        if fenced_match:
            return json.loads(fenced_match.group(1))

        # 3) First top-level JSON object-like span
        start_idx = response.find("{")
        end_idx = response.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return json.loads(response[start_idx:end_idx + 1])

        raise json.JSONDecodeError("No JSON object found in response", response, 0)

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow for paper comparison."""
        workflow = StateGraph(ComparisonState)

        # Add nodes
        workflow.add_node("retrieve_contexts", self._retrieve_contexts)
        workflow.add_node("generate_comparison", self._generate_comparison)

        # Define edges
        workflow.set_entry_point("retrieve_contexts")
        workflow.add_edge("retrieve_contexts", "generate_comparison")
        workflow.add_edge("generate_comparison", END)

        return workflow.compile()

    async def _retrieve_contexts(self, state: ComparisonState) -> ComparisonState:
        """Retrieve relevant contexts for each paper.

        Args:
            state: Current workflow state

        Returns:
            Updated state with paper contexts
        """
        document_ids = state.get("document_ids", [])
        paper_contexts = []

        for doc_id in document_ids:
            try:
                # Get top chunks for this paper (focus on abstract/intro/methods)
                results = self.vector_store.search(
                    query="abstract introduction methodology approach dataset experiment results",
                    top_k=5,  # Get 5 most relevant chunks
                    filter_document_ids=[doc_id],  # Filter to this specific paper
                )

                if results:
                    # Concatenate chunks to form paper context
                    context = "\n\n".join([r["text"] for r in results])

                    # Try to extract title from metadata
                    title = results[0].get("metadata", {}).get("title", f"Paper {doc_id[:8]}")

                    paper_contexts.append({
                        "document_id": doc_id,
                        "title": title,
                        "context": context[:3000],  # Limit to 3K chars (~750 tokens) per paper
                    })
                    logger.info(f"Retrieved context for paper {doc_id[:8]}: {len(context)} chars")
                else:
                    logger.warning(f"No chunks found for document {doc_id}")
                    paper_contexts.append({
                        "document_id": doc_id,
                        "title": f"Paper {doc_id[:8]}",
                        "context": "No content available for this paper.",
                    })

            except Exception as e:
                logger.error(f"Error retrieving context for {doc_id}: {e}")
                paper_contexts.append({
                    "document_id": doc_id,
                    "title": f"Paper {doc_id[:8]}",
                    "context": f"Error retrieving content: {str(e)}",
                })

        state["paper_contexts"] = paper_contexts
        return state

    async def _generate_comparison(self, state: ComparisonState) -> ComparisonState:
        """Generate comparison matrix using LLM.

        Args:
            state: Current workflow state with paper contexts

        Returns:
            Updated state with comparison matrix and insights
        """
        paper_contexts = state.get("paper_contexts", [])
        focus = state.get("focus", "all")

        if len(paper_contexts) < 2:
            state["error"] = "Need at least 2 papers to compare"
            state["comparison_matrix"] = {}
            state["markdown_table"] = ""
            state["insights"] = {}
            return state

        # Build papers text for prompt
        papers_text = ""
        for i, pc in enumerate(paper_contexts, 1):
            papers_text += f"\n\n{'='*60}\nPAPER {i}: {pc['title']}\n{'='*60}\n{pc['context']}"

        # Define comparison dimensions based on focus
        if focus == "methodology":
            dimensions = ["Problem Addressed", "Methodology/Approach", "Key Algorithms", "Novel Contributions"]
        elif focus == "datasets":
            dimensions = ["Datasets Used", "Dataset Size", "Data Preprocessing", "Evaluation Metrics"]
        elif focus == "results":
            dimensions = ["Key Metrics", "Main Results", "Performance Comparison", "Limitations"]
        else:  # "all"
            dimensions = [
                "Problem Addressed",
                "Methodology",
                "Datasets",
                "Key Metrics",
                "Main Results",
                "Limitations",
                "Novel Contribution"
            ]

        dimensions_str = "\n".join([f"{i+1}. {dim}" for i, dim in enumerate(dimensions)])
        prompt = f"""You are a research paper analyst. Compare these {len(paper_contexts)} papers across the specified dimensions.

Papers to compare:
{papers_text}

Create a structured comparison table with these dimensions:
{dimensions_str}

For EACH dimension, extract the relevant information from EACH paper. Be concise but specific.
If information is not available in the paper, write "Not specified".

Also provide:
1. **Best Performer**: For each dimension, which paper is strongest (or "Tie" if equal)
2. **Common Patterns**: What methodologies, datasets, or approaches are shared
3. **Key Differences**: What makes each paper's approach unique

Return a JSON object with this EXACT structure:
{{
  "comparison_matrix": {{
    "{dimensions[0]}": {{
      "Paper 1": "description",
      "Paper 2": "description",
      ...
    }},
    "{dimensions[1]}": {{
      "Paper 1": "description",
      "Paper 2": "description",
      ...
    }},
    ...
  }},
  "insights": {{
    "best_performers": {{
      "{dimensions[0]}": "Paper X",
      "{dimensions[1]}": "Paper Y",
      ...
    }},
    "common_patterns": ["pattern 1", "pattern 2", "pattern 3"],
    "key_differences": ["difference 1", "difference 2", "difference 3"]
  }}
}}

JSON only:"""

        try:
            data = None
            parse_errors: List[str] = []
            last_response = ""

            # Gemini default, then explicit Groq retry if JSON formatting is invalid.
            for provider in [Provider.GEMINI, Provider.GROQ]:
                response = await self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,  # Low temp for structured output
                    max_tokens=2500,  # Allow full JSON output for 2-4 paper comparisons
                    preferred_provider=provider,
                    use_cache=True,  # Cache comparisons (same papers = same result)
                )
                last_response = response

                try:
                    data = self._parse_comparison_payload(response)
                    break
                except json.JSONDecodeError as parse_error:
                    parse_errors.append(f"{provider.value}: {parse_error}")
                    logger.warning(f"{provider.value} returned non-JSON comparison output, trying fallback")

            if data is None:
                raise json.JSONDecodeError(
                    "Failed to parse comparison results from all providers",
                    "; ".join(parse_errors),
                    0,
                )

            comparison_matrix = data.get("comparison_matrix", {})
            insights = data.get("insights", {})

            # Generate markdown table
            markdown_table = self._format_markdown_table(
                comparison_matrix,
                paper_contexts,
                dimensions
            )

            state["comparison_matrix"] = comparison_matrix
            state["insights"] = insights
            state["markdown_table"] = markdown_table
            state["error"] = None

            logger.info(f"Generated comparison for {len(paper_contexts)} papers across {len(dimensions)} dimensions")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            # Graceful fallback: do not fail the endpoint when providers return
            # non-strict JSON; return a usable payload with defaults.
            state["error"] = None
            state["comparison_matrix"] = {}
            state["markdown_table"] = last_response if last_response else "Comparison generated but could not be structured into JSON."
            state["insights"] = {
                "best_performers": {},
                "common_patterns": [],
                "key_differences": [],
            }
        except Exception as e:
            logger.error(f"Error generating comparison: {e}")
            state["error"] = str(e)
            state["comparison_matrix"] = {}
            state["markdown_table"] = ""
            state["insights"] = {}

        return state

    def _format_markdown_table(
        self,
        comparison_matrix: Dict[str, Any],
        paper_contexts: List[Dict[str, Any]],
        dimensions: List[str]
    ) -> str:
        """Format comparison matrix as markdown table.

        Args:
            comparison_matrix: Comparison data from LLM
            paper_contexts: List of paper contexts
            dimensions: Comparison dimensions

        Returns:
            Formatted markdown table
        """
        # Build header row with paper titles
        headers = ["**Dimension**"] + [f"**{pc['title'][:50]}...**" if len(pc['title']) > 50 else f"**{pc['title']}**" for pc in paper_contexts]
        header_row = "| " + " | ".join(headers) + " |"
        separator = "|" + "|".join(["---" for _ in range(len(headers))]) + "|"

        # Build data rows
        rows = [header_row, separator]
        for dimension in dimensions:
            if dimension in comparison_matrix:
                dim_data = comparison_matrix[dimension]
                row_cells = [f"**{dimension}**"]

                for i in range(len(paper_contexts)):
                    paper_key = f"Paper {i+1}"
                    cell_value = dim_data.get(paper_key, "Not specified")
                    row_cells.append(cell_value)

                rows.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(rows)

    async def compare_papers(
        self,
        document_ids: List[str],
        focus: Optional[str] = "all"
    ) -> Dict[str, Any]:
        """Compare multiple papers and return structured comparison.

        Args:
            document_ids: List of document IDs to compare (2-4 papers)
            focus: Focus area - "methodology", "datasets", "results", or "all"

        Returns:
            Dictionary with comparison_matrix, markdown_table, insights, error

        Raises:
            ValueError: If less than 2 or more than 4 papers provided
        """
        if len(document_ids) < 2:
            raise ValueError("Need at least 2 papers to compare")
        if len(document_ids) > 4:
            raise ValueError("Maximum 4 papers can be compared at once")

        # Run workflow
        initial_state: ComparisonState = {
            "document_ids": document_ids,
            "focus": focus,
            "paper_contexts": [],
            "comparison_matrix": {},
            "markdown_table": "",
            "insights": {},
            "error": None,
        }

        final_state = await self.graph.ainvoke(initial_state)

        return {
            "comparison_matrix": final_state.get("comparison_matrix", {}),
            "markdown_table": final_state.get("markdown_table", ""),
            "insights": final_state.get("insights", {}),
            "paper_contexts": final_state.get("paper_contexts", []),
            "error": final_state.get("error"),
        }
