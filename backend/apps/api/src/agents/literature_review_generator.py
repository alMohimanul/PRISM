"""Literature Review Generator - Auto-generates literature review from papers!"""

import json
import time
import asyncio
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime

from langgraph.graph import END, StateGraph

from ..services.vector_store import VectorStoreService
from ..services.llm_provider import MultiProviderLLMClient


class ReviewState(TypedDict):
    """State for Literature Review Generator."""

    # Input
    document_ids: List[str]
    research_topic: str

    # Paper metadata (for chronological ordering)
    papers: List[Dict[str, Any]]  # {doc_id, title, year, key_contribution}

    # Generated sections
    problem_statement: str
    evolution_sections: List[Dict[str, str]]  # [{era, content}]
    current_sota: str
    research_gaps: List[str]
    conclusion: str

    # Citations
    all_citations: List[Dict[str, Any]]

    # Final output
    full_review: str
    error: Optional[str]


class LiteratureReviewGenerator:
    """Generates comprehensive literature reviews from multiple papers."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_client: MultiProviderLLMClient,
    ):
        """Initialize Literature Review Generator.

        Args:
            vector_store: Vector store service
            llm_client: Multi-provider LLM client
        """
        self.vector_store = vector_store
        self.llm_client = llm_client

        # Build workflow
        self.graph = self._build_graph()

    def _deduplicate_context(self, results: List[Dict[str, Any]], max_chunks: int = 15) -> str:
        """Deduplicate and format retrieved context chunks.

        Removes near-duplicate chunks and formats for LLM consumption.

        Args:
            results: Retrieved chunks from vector store
            max_chunks: Maximum number of chunks to return

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        # Deduplicate by text similarity (simple approach: first 100 chars)
        seen_prefixes = set()
        unique_chunks = []

        for r in results[:max_chunks * 2]:  # Check more than needed
            prefix = r["text"][:100].strip()
            if prefix not in seen_prefixes:
                seen_prefixes.add(prefix)
                unique_chunks.append(r)

            if len(unique_chunks) >= max_chunks:
                break

        # Format with source info
        formatted_chunks = []
        for r in unique_chunks:
            doc_id = r.get("document_id", "unknown")[:8]
            page = r.get("metadata", {}).get("page_number", "?")
            text = r["text"].strip()
            formatted_chunks.append(f"[Paper: {doc_id}, Page {page}]\n{text}")

        return "\n\n".join(formatted_chunks)

    def _llm_call(
        self,
        messages: list,
        temperature: float = 0.5,
        max_tokens: int = 3072,
        preferred_provider: Optional[str] = None,
        use_cache: bool = True,
    ) -> str:
        """Make LLM call using multi-provider client.

        The multi-provider client handles:
        - Rate limiting
        - Load balancing between Groq and NVIDIA
        - Automatic failover and retry logic
        - Caching for repeated queries

        Args:
            messages: Chat messages
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            preferred_provider: Preferred provider ("groq" or "nvidia")
            use_cache: Whether to use caching

        Returns:
            Generated response text
        """
        # Run async chat_completion in sync context
        import nest_asyncio
        nest_asyncio.apply()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in current thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Convert provider string to enum if specified
        from ..services.llm_provider import Provider
        provider_enum = None
        if preferred_provider:
            provider_enum = Provider.NVIDIA if preferred_provider == "nvidia" else Provider.GROQ

        return loop.run_until_complete(
            self.llm_client.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                preferred_provider=provider_enum,
                use_cache=use_cache,
            )
        )

    def _build_graph(self) -> StateGraph:
        """Build the literature review workflow.

        PHASE 3 DEEP AGENT WORKFLOW:
        1. Extract metadata (batched, 1 call)
        2. Generate problem (3 calls: draft → critique → refine)
        3. Generate evolution (N calls for N eras, context-aware)
        4. Generate SOTA (1 call, references evolution)
        5. Identify gaps (2 calls: identify → expand)
        6. Generate conclusion (1 call, synthesizes all sections)
        7. Assemble review (no LLM)
        8. Humanize & polish (1 call: coherence + natural language)
        """
        workflow = StateGraph(ReviewState)

        # Add nodes
        workflow.add_node("extract_metadata", self._extract_metadata)
        workflow.add_node("generate_problem", self._generate_problem_statement)
        workflow.add_node("generate_evolution", self._generate_evolution)
        workflow.add_node("generate_sota", self._generate_current_sota)
        workflow.add_node("identify_gaps", self._identify_research_gaps)
        workflow.add_node("generate_conclusion", self._generate_conclusion)
        workflow.add_node("assemble_review", self._assemble_final_review)
        workflow.add_node("humanize_review", self._humanize_review)  # NEW: Final polish

        # Linear workflow with humanization at the end
        workflow.set_entry_point("extract_metadata")
        workflow.add_edge("extract_metadata", "generate_problem")
        workflow.add_edge("generate_problem", "generate_evolution")
        workflow.add_edge("generate_evolution", "generate_sota")
        workflow.add_edge("generate_sota", "identify_gaps")
        workflow.add_edge("identify_gaps", "generate_conclusion")
        workflow.add_edge("generate_conclusion", "assemble_review")
        workflow.add_edge("assemble_review", "humanize_review")
        workflow.add_edge("humanize_review", END)

        return workflow.compile()

    def _extract_metadata(self, state: ReviewState) -> ReviewState:
        """Extract paper metadata for chronological ordering.

        OPTIMIZATION: Batched extraction - processes all papers in a single LLM call
        instead of N separate calls (5x speedup for 5 papers).

        Args:
            state: Current state

        Returns:
            Updated state with paper metadata
        """
        papers = []

        # Collect contexts from all papers first
        paper_contexts = []
        for doc_id in state["document_ids"]:
            # Retrieve abstract/intro chunks for metadata
            results = self.vector_store.search(
                query="abstract introduction main contribution",
                top_k=3,
                filter_document_ids=[doc_id]
            )

            if results:
                context = "\n\n".join([r["text"] for r in results])
                paper_contexts.append({
                    "document_id": doc_id,
                    "context": context
                })

        # Batched metadata extraction - single LLM call for all papers!
        if paper_contexts:
            # Build batch prompt
            papers_text = ""
            for i, pc in enumerate(paper_contexts, 1):
                papers_text += f"\n\n--- PAPER {i} (ID: {pc['document_id'][:8]}) ---\n{pc['context']}"

            prompt = f"""Extract metadata from these {len(paper_contexts)} papers.

For EACH paper, extract:
- title: Full paper title
- year: Publication year (integer)
- key_contribution: 1-sentence summary of the main contribution
- authors: First author et al.

Papers to analyze:{papers_text}

Return JSON array with one object per paper:
[
  {{
    "document_id": "{paper_contexts[0]['document_id']}",
    "title": "Paper title",
    "year": 2020,
    "key_contribution": "Main contribution in one sentence",
    "authors": "First author et al."
  }},
  ...
]

JSON array only:"""

            try:
                # Use Groq for fast factual extraction
                response = self._llm_call(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,  # Low temp for factual extraction
                    max_tokens=2048,
                    preferred_provider="groq",
                    use_cache=True,  # Cache metadata extractions!
                )

                # Parse JSON array
                papers = json.loads(response)

                # Ensure all papers have document_id
                for i, paper in enumerate(papers):
                    if "document_id" not in paper and i < len(paper_contexts):
                        paper["document_id"] = paper_contexts[i]["document_id"]

            except Exception as e:
                # Fallback: create basic metadata for each paper
                for pc in paper_contexts:
                    papers.append({
                        "document_id": pc["document_id"],
                        "title": f"Paper {pc['document_id'][:8]}",
                        "year": 2020,
                        "key_contribution": "Unknown",
                        "authors": "Unknown"
                    })

        # Sort by year
        papers.sort(key=lambda x: x.get("year", 2020))
        state["papers"] = papers
        state["all_citations"] = []

        return state

    def _generate_problem_statement(self, state: ReviewState) -> ReviewState:
        """Generate problem statement section with self-critique refinement.

        DEEP AGENT: 3-stage process
        1. Draft generation (NVIDIA DeepSeek with reasoning)
        2. Self-critique
        3. Refinement based on feedback

        Args:
            state: Current state

        Returns:
            Updated state with problem statement
        """
        # Retrieve problem/motivation chunks from all papers
        results = self.vector_store.search(
            query="problem motivation challenge limitation background",
            top_k=20,  # Increased for better coverage
            filter_document_ids=state["document_ids"]
        )

        context = self._deduplicate_context(results, max_chunks=15)

        # STAGE 1: Draft generation with DeepSeek reasoning
        draft_prompt = f"""You are writing a literature review for a research paper. Write in natural, human-like academic language - avoid jargon, em dashes (—), and overly complex sentence structures.

Papers being reviewed:
{json.dumps([p['title'] for p in state['papers']], indent=2)}

Context from papers:
{context}

Write a "Problem Statement" section that:
1. Describes the core research problem these papers address in plain but scholarly language
2. Explains why it's challenging without using technical jargon
3. Mentions early limitations and cite with [Paper: XXX]
4. Sets up the motivation for solutions naturally
5. Write 2-3 well-developed paragraphs
6. Use simple, clear sentences that flow naturally
7. Avoid em dashes (—), semicolons in complex ways, and buzzwords
8. Write as if explaining to an intelligent colleague, not showing off vocabulary

Return JSON:
{{
  "problem_statement": "The problem statement text with [Paper: XXX] citations...",
  "citations_used": ["doc_id1", "doc_id2"]
}}

JSON only:"""

        try:
            # Use Groq for deep reasoning
            draft_response = self._llm_call(
                messages=[{"role": "user", "content": draft_prompt}],
                temperature=0.6,  # Slightly higher for natural flow
                max_tokens=3072,
                preferred_provider="groq",  # Fast and reliable
                use_cache=True,
            )

            draft_data = json.loads(draft_response)
            draft_statement = draft_data.get("problem_statement", "")

            # STAGE 2: Self-critique
            critique_prompt = f"""You are a senior researcher reviewing this problem statement draft for a literature review.

Draft problem statement:
{draft_statement}

Critique this draft on:
1. Clarity - Is it clear and easy to understand?
2. Natural flow - Does it read like a human wrote it, not AI?
3. Jargon/complexity - Are there unnecessary technical terms or em dashes (—)?
4. Completeness - Does it cover all key aspects of the problem?
5. Citations - Are sources properly cited?

Provide 3-5 specific, actionable improvements.

Return JSON:
{{
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "suggestions": ["specific suggestion 1", "specific suggestion 2"]
}}

JSON only:"""

            critique_response = self._llm_call(
                messages=[{"role": "user", "content": critique_prompt}],
                temperature=0.4,
                max_tokens=1024,
                preferred_provider="groq",  # Fast critique
                use_cache=False,  # Don't cache critiques
            )

            critique_data = json.loads(critique_response)

            # STAGE 3: Refinement based on critique
            refine_prompt = f"""You are refining a problem statement for a literature review based on peer feedback.

Original draft:
{draft_statement}

Peer critique:
Strengths: {json.dumps(critique_data.get('strengths', []))}
Weaknesses: {json.dumps(critique_data.get('weaknesses', []))}
Suggestions: {json.dumps(critique_data.get('suggestions', []))}

Rewrite the problem statement incorporating the feedback. Maintain:
- Natural, human-like academic language
- No em dashes (—) or unnecessary jargon
- Clear, simple sentences
- All original citations [Paper: XXX]
- 2-3 well-developed paragraphs

Return JSON:
{{
  "problem_statement": "The refined problem statement with [Paper: XXX] citations...",
  "improvements_made": ["improvement 1", "improvement 2"]
}}

JSON only:"""

            refined_response = self._llm_call(
                messages=[{"role": "user", "content": refine_prompt}],
                temperature=0.6,
                max_tokens=3072,
                preferred_provider="groq",  # Fast refinement
                use_cache=False,
            )

            refined_data = json.loads(refined_response)
            state["problem_statement"] = refined_data.get("problem_statement", draft_statement)

        except Exception as e:
            state["error"] = f"Error generating problem statement: {str(e)}"
            state["problem_statement"] = "Problem statement could not be generated."

        return state

    def _generate_evolution(self, state: ReviewState) -> ReviewState:
        """Generate evolution of solutions section with context from problem statement.

        SECTION INTERDEPENDENCE: References problem statement for coherent narrative.

        Args:
            state: Current state

        Returns:
            Updated state with evolution sections
        """
        # Group papers by era (rough 2-3 year periods)
        papers = state["papers"]
        if not papers:
            state["evolution_sections"] = []
            return state

        # Detect eras
        years = [p.get("year", 2020) for p in papers]
        min_year = min(years)
        max_year = max(years)

        # Create 2-3 eras
        era_size = max(2, (max_year - min_year) // 2)
        eras = []

        current_era_start = min_year
        while current_era_start <= max_year:
            era_end = min(current_era_start + era_size, max_year)
            era_papers = [p for p in papers if current_era_start <= p.get("year", 2020) <= era_end]

            if era_papers:
                eras.append({
                    "range": f"{current_era_start}-{era_end}",
                    "papers": era_papers
                })

            current_era_start = era_end + 1

        # Generate content for each era
        evolution_sections = []

        # Get problem context for coherence
        problem_context = state.get("problem_statement", "")[:300]  # First 300 chars

        for i, era in enumerate(eras):
            doc_ids = [p["document_id"] for p in era["papers"]]

            # Retrieve methods/solutions from these papers
            results = self.vector_store.search(
                query="method approach solution technique architecture algorithm results",
                top_k=20,
                filter_document_ids=doc_ids
            )

            context = self._deduplicate_context(results, max_chunks=12)

            paper_list = "\n".join([
                f"- {p['title']} ({p['year']}) - {p['key_contribution']}"
                for p in era["papers"]
            ])

            # Add previous era context for continuity
            previous_era_summary = ""
            if i > 0 and evolution_sections:
                previous_era_summary = f"\nPrevious era summary: {evolution_sections[-1]['content'][:200]}...\n"

            prompt = f"""Write a subsection about this era in the field's evolution. Use natural, flowing language without jargon or em dashes (—).

Problem context (for reference):
{problem_context}...
{previous_era_summary}
Era: {era['range']}

Papers in this era:
{paper_list}

Context from papers:
{context}

Write content that:
1. Describes what approaches were introduced in plain language
2. How they built on previous work (reference problem or earlier eras naturally)
3. Key innovations and improvements explained simply
4. Results/metrics if mentioned
5. Use [Paper: XXX] citations
6. 2-3 well-developed paragraphs
7. Natural, human-like academic tone - no buzzwords or complex jargon
8. Flow naturally from problem statement or previous era

Return JSON:
{{
  "era_name": "Descriptive name for this era (e.g., 'Early Statistical Approaches')",
  "content": "The section text with citations..."
}}

JSON only:"""

            try:
                # Use Groq for evolution (factual, less reasoning needed)
                response = self._llm_call(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.6,
                    max_tokens=2048,
                    preferred_provider="groq",
                    use_cache=True,
                )

                data = json.loads(response)
                evolution_sections.append({
                    "era": data.get("era_name", era["range"]),
                    "content": data.get("content", "")
                })

            except Exception as e:
                evolution_sections.append({
                    "era": era["range"],
                    "content": f"Content for {era['range']} could not be generated."
                })

        state["evolution_sections"] = evolution_sections
        return state

    def _generate_current_sota(self, state: ReviewState) -> ReviewState:
        """Generate current state-of-the-art section with context from evolution.

        SECTION INTERDEPENDENCE: References evolution to show progression.

        Args:
            state: Current state

        Returns:
            Updated state with SOTA section
        """
        # Get most recent papers
        recent_papers = sorted(state["papers"], key=lambda x: x.get("year", 0), reverse=True)[:3]
        recent_ids = [p["document_id"] for p in recent_papers]

        # Retrieve results/performance chunks
        results = self.vector_store.search(
            query="results performance state-of-the-art accuracy metrics benchmark evaluation comparison",
            top_k=20,
            filter_document_ids=recent_ids
        )

        context = self._deduplicate_context(results, max_chunks=15)

        # Get evolution context for narrative flow
        evolution_summary = ""
        if state.get("evolution_sections"):
            last_era = state["evolution_sections"][-1]
            evolution_summary = f"Most recent developments: {last_era['content'][:250]}...\n"

        prompt = f"""Write a "Current State-of-the-Art" section. Use natural, clear language without jargon or em dashes (—).

{evolution_summary}
Recent papers:
{json.dumps([f"{p['title']} ({p['year']})" for p in recent_papers], indent=2)}

Context:
{context}

Write content that:
1. Describes current best methods in plain language
2. Mentions performance metrics and results clearly
3. Compares approaches naturally (building on evolution section)
4. Notes remaining challenges and limitations
5. 2-3 well-developed paragraphs
6. Use [Paper: XXX] citations
7. Natural, human-like academic tone

Return JSON:
{{
  "sota_section": "The SOTA section text with citations..."
}}

JSON only:"""

        try:
            # Use Groq for SOTA (factual comparison)
            response = self._llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2048,
                preferred_provider="groq",
                use_cache=True,
            )

            data = json.loads(response)
            state["current_sota"] = data.get("sota_section", "")

        except Exception as e:
            state["current_sota"] = "Current state-of-the-art could not be determined."

        return state

    def _identify_research_gaps(self, state: ReviewState) -> ReviewState:
        """Identify research gaps with self-critique and expansion.

        DEEP AGENT: 2-stage process
        1. Initial gap identification (NVIDIA DeepSeek reasoning)
        2. Expansion with specific examples and actionable suggestions

        Args:
            state: Current state

        Returns:
            Updated state with research gaps
        """
        # Retrieve limitations/future work sections
        results = self.vector_store.search(
            query="limitation future work gap challenge unexplored open problem",
            top_k=25,
            filter_document_ids=state["document_ids"]
        )

        context = self._deduplicate_context(results, max_chunks=18)

        # Get SOTA context for what's currently achieved
        sota_summary = state.get("current_sota", "")[:300]

        # STAGE 1: Initial gap identification with deep reasoning
        draft_prompt = f"""Identify significant research gaps from these papers. Think deeply about what's missing.

Current state-of-the-art (for context):
{sota_summary}...

Limitations and future work from papers:
{context}

Identify 4-6 meaningful research gaps by analyzing:
1. What fundamental questions remain unanswered?
2. What practical limitations exist in current approaches?
3. What scenarios or datasets haven't been explored?
4. What theoretical aspects need deeper investigation?
5. What real-world applications are still challenging?

Write each gap in plain, clear language (1-2 sentences each). No jargon or em dashes (—).

Return JSON:
{{
  "gaps": [
    "Gap 1: Clear description of what's missing and why it matters",
    "Gap 2: Clear description...",
    ...
  ]
}}

JSON only:"""

        try:
            # Use Groq for deep reasoning
            draft_response = self._llm_call(
                messages=[{"role": "user", "content": draft_prompt}],
                temperature=0.6,
                max_tokens=2048,
                preferred_provider="groq",  # Fast and reliable
                use_cache=True,
            )

            draft_data = json.loads(draft_response)
            draft_gaps = draft_data.get("gaps", [])

            # STAGE 2: Expand gaps with specific, actionable insights
            expansion_prompt = f"""You identified these research gaps:

{json.dumps(draft_gaps, indent=2)}

For each gap, add more depth and specificity:
1. Provide a concrete example or scenario
2. Suggest a potential approach or direction
3. Explain the impact if addressed

Rewrite each gap with more detail (2-3 sentences each). Keep the language natural and accessible.

Return JSON:
{{
  "expanded_gaps": [
    "Gap 1: [Expanded description with example, approach, and impact]",
    "Gap 2: [Expanded description...]",
    ...
  ]
}}

JSON only:"""

            expanded_response = self._llm_call(
                messages=[{"role": "user", "content": expansion_prompt}],
                temperature=0.6,
                max_tokens=3072,
                preferred_provider="groq",  # Fast expansion
                use_cache=False,
            )

            expanded_data = json.loads(expanded_response)
            state["research_gaps"] = expanded_data.get("expanded_gaps", draft_gaps)

        except Exception as e:
            state["research_gaps"] = ["Research gaps could not be identified."]

        return state

    def _generate_conclusion(self, state: ReviewState) -> ReviewState:
        """Generate conclusion section with full review context.

        SECTION INTERDEPENDENCE: Synthesizes all sections for coherent closure.

        Args:
            state: Current state

        Returns:
            Updated state with conclusion
        """
        # Summarize all sections
        problem_summary = state.get("problem_statement", "")[:250]
        sota_summary = state.get("current_sota", "")[:250]
        gaps_summary = "\n".join(state.get("research_gaps", [])[:3])  # Top 3 gaps

        prompt = f"""Write a conclusion for this literature review. Use natural, flowing language without jargon or em dashes (—).

Problem addressed:
{problem_summary}...

Current state-of-the-art:
{sota_summary}...

Key research gaps:
{gaps_summary}

Write a conclusion that:
1. Briefly summarizes the field's evolution from problem to current solutions
2. Highlights key achievements and breakthroughs
3. Acknowledges current limitations honestly
4. Points to promising future directions based on identified gaps
5. 2-3 well-developed paragraphs
6. Natural, human-like academic tone
7. Provides a sense of closure while inspiring future work

Return JSON:
{{
  "conclusion": "The conclusion text..."
}}

JSON only:"""

        try:
            # Use Groq for thoughtful synthesis
            response = self._llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=2048,
                preferred_provider="groq",  # Fast synthesis
                use_cache=False,  # Don't cache conclusions (context-dependent)
            )

            data = json.loads(response)
            state["conclusion"] = data.get("conclusion", "")

        except Exception as e:
            state["conclusion"] = "Conclusion could not be generated."

        return state

    def _assemble_final_review(self, state: ReviewState) -> ReviewState:
        """Assemble all sections into final literature review.

        Args:
            state: Current state

        Returns:
            Updated state with full review
        """
        # Build markdown
        review = f"""# Literature Review: {state.get('research_topic', 'Research Topic')}

## Problem Statement

{state['problem_statement']}

## Evolution of Solutions

"""

        for section in state["evolution_sections"]:
            review += f"""### {section['era']}

{section['content']}

"""

        review += f"""## Current State-of-the-Art

{state['current_sota']}

## Research Gaps

"""

        for i, gap in enumerate(state["research_gaps"], 1):
            review += f"{i}. {gap}\n"

        review += f"""

## Conclusion

{state['conclusion']}

---

**Papers Reviewed:**

"""

        for paper in state["papers"]:
            review += f"- {paper.get('title', 'Unknown')} ({paper.get('year', '?')})\n"

        state["full_review"] = review
        return state

    def _humanize_review(self, state: ReviewState) -> ReviewState:
        """Final coherence check and humanization pass.

        FINAL POLISH: Ensures the review reads naturally like a human wrote it.
        - Removes AI artifacts (em dashes, repetitive phrases, jargon)
        - Improves flow between sections
        - Ensures consistent tone
        - Fixes awkward phrasing

        Args:
            state: Current state with assembled review

        Returns:
            Updated state with humanized review
        """
        draft_review = state.get("full_review", "")

        if not draft_review or len(draft_review) < 100:
            return state

        # Extract just the content sections (skip title and paper list)
        review_lines = draft_review.split("\n")
        content_start = 0
        content_end = len(review_lines)

        for i, line in enumerate(review_lines):
            if line.startswith("---"):
                content_end = i
                break

        content = "\n".join(review_lines[content_start:content_end])

        prompt = f"""You are a senior researcher polishing a literature review to read naturally, like a human wrote it.

Review draft:
{content}

Polish this review to:
1. Remove em dashes (—) - replace with commas, periods, or "and"
2. Eliminate repetitive AI phrases like "Furthermore", "Moreover", "It is worth noting"
3. Replace technical jargon with clearer explanations where possible
4. Improve flow between sentences and paragraphs (add transitions if needed)
5. Ensure consistent, natural academic tone throughout
6. Fix any awkward or overly complex phrasing
7. Keep all [Paper: XXX] citations intact
8. Maintain the same structure and section headings

CRITICAL: Keep the exact same sections and headings. Only improve the prose.

Return JSON:
{{
  "polished_review": "The entire polished review with all sections..."
}}

JSON only:"""

        try:
            # Use Groq for nuanced language polishing
            response = self._llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,  # Lower temp for consistent edits
                max_tokens=8192,  # Need space for full review
                preferred_provider="groq",  # Fast polishing
                use_cache=False,  # Don't cache polishing (unique each time)
            )

            data = json.loads(response)
            polished_content = data.get("polished_review", content)

            # Reassemble with paper list
            paper_list_section = "\n".join(review_lines[content_end:])
            state["full_review"] = polished_content + "\n" + paper_list_section

        except Exception as e:
            # If humanization fails, keep original
            pass

        return state

    async def generate_review(
        self,
        document_ids: List[str],
        research_topic: str = "Research Topic"
    ) -> Dict[str, Any]:
        """Generate literature review from papers.

        Args:
            document_ids: List of document IDs
            research_topic: Optional topic name

        Returns:
            Generated literature review
        """
        if len(document_ids) < 2:
            return {
                "error": "Need at least 2 papers for literature review",
                "full_review": ""
            }

        # Initialize state
        initial_state: ReviewState = {
            "document_ids": document_ids,
            "research_topic": research_topic,
            "papers": [],
            "problem_statement": "",
            "evolution_sections": [],
            "current_sota": "",
            "research_gaps": [],
            "conclusion": "",
            "all_citations": [],
            "full_review": "",
            "error": None
        }

        # Run workflow in thread pool to avoid blocking
        import concurrent.futures
        loop = asyncio.get_event_loop()

        with concurrent.futures.ThreadPoolExecutor() as pool:
            final_state = await loop.run_in_executor(
                pool,
                self.graph.invoke,
                initial_state
            )

        return {
            "full_review": final_state["full_review"],
            "papers": final_state["papers"],
            "sections": {
                "problem": final_state["problem_statement"],
                "evolution": final_state["evolution_sections"],
                "sota": final_state["current_sota"],
                "gaps": final_state["research_gaps"],
                "conclusion": final_state["conclusion"]
            },
            "error": final_state.get("error")
        }
