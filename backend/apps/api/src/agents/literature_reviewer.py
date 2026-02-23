"""Literature Reviewer Agent with RAG capabilities."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..services.vector_store import VectorStoreService
from ..services.llm_provider import MultiProviderLLMClient

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the Literature Reviewer agent."""

    query: str
    context: List[Dict[str, Any]]
    draft_answer: str
    used_chunks: List[str]
    response: str
    sources: List[Dict[str, Any]]
    confidence: float
    unsupported_spans: List[Dict[str, Any]]
    error: Optional[str]
    # Multi-document support
    document_id: Optional[str]  # Single document filter (deprecated)
    document_ids: Optional[List[str]]  # Multi-document filter


class LiteratureReviewerAgent:
    """Literature Reviewer agent for answering questions about research papers using RAG."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        llm_client: MultiProviderLLMClient,
        reranker_top_k: int = 20,
        final_top_k: int = 5,
    ):
        """Initialize Literature Reviewer agent.

        Args:
            vector_store: Vector store service for retrieving relevant chunks
            llm_client: Multi-provider LLM client (handles Groq + NVIDIA with load balancing)
            reranker_top_k: Number of candidates to retrieve before reranking
            final_top_k: Number of final chunks to use for generation
        """
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.reranker_top_k = reranker_top_k
        self.final_top_k = final_top_k

        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for the agent.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("retrieve", self._retrieve_context)
        workflow.add_node("draft", self._generate_draft)
        workflow.add_node("validate", self._validate_grounding)

        # Add edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "draft")
        workflow.add_edge("draft", "validate")
        workflow.add_edge("validate", END)

        return workflow.compile()

    async def _rate_limited_llm_call(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        preferred_provider: Optional[str] = None,
        use_cache: bool = True,
    ) -> str:
        """Wrapper for async LLM calls.

        Args:
            messages: Chat messages
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            preferred_provider: Preferred provider ("gemini" or "groq")
            use_cache: Whether to use caching

        Returns:
            Generated response text
        """
        # Convert provider string to enum if specified
        from ..services.llm_provider import Provider
        provider_enum = None
        if preferred_provider:
            provider_enum = Provider.GEMINI if preferred_provider == "gemini" else Provider.GROQ

        return await self.llm_client.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            preferred_provider=provider_enum,
            use_cache=use_cache,
        )

    async def _retrieve_context(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from vector store with intelligent section-aware strategy.

        Strategy:
        1. Detect query intent (what section it's asking about)
        2. Retrieve larger candidate pool (top 30-50)
        3. Apply strong section boosting (2x for matching sections)
        4. Diversity filter (avoid too many chunks from same location)
        5. Select top 5 most representative chunks

        Args:
            state: Current agent state

        Returns:
            Updated state with context
        """
        query = state["query"]

        try:
            # Phase 1: Detect query intent and target sections
            target_sections = self._detect_target_sections(query)

            # Phase 2: Retrieve candidate pool (heavily reduced for token management)
            # Quality over quantity - fewer but more relevant chunks
            candidate_pool_size = min(8, self.reranker_top_k)

            # Get document filters from state
            filter_document_id = state.get("document_id")
            filter_document_ids = state.get("document_ids")

            results = self.vector_store.search(
                query,
                top_k=candidate_pool_size,
                filter_document_id=filter_document_id,
                filter_document_ids=filter_document_ids,
                reranker_top_k=candidate_pool_size
            )

            # Phase 3: Apply intelligent section-aware scoring
            results = self._score_by_section_relevance(query, results, target_sections)

            # Phase 4: Diversity filtering to avoid redundancy
            results = self._apply_diversity_filter(results)

            # Phase 5: Select top 2 most representative chunks (heavily reduced for token limits)
            # Quality over quantity - 2 highly relevant chunks are sufficient
            results = results[:2]

            # Assign chunk IDs
            for i, r in enumerate(results):
                r["chunk_id"] = f"c{i+1}"

            state["context"] = results
            state["sources"] = []  # Will be populated after validation

            logger.info(f"Retrieved {len(results)} chunks for query: {query[:50]}...")

        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            state["error"] = f"Error retrieving context: {str(e)}"
            state["context"] = []
            state["sources"] = []

        return state

    def _detect_target_sections(self, query: str) -> set:
        """Detect which sections the query is asking about.

        Args:
            query: User query

        Returns:
            Set of target section types
        """
        query_lower = query.lower()
        target_sections = set()

        # More comprehensive section detection
        section_keywords = {
            # Results/Findings
            ("result", "finding", "performance", "accuracy", "achieve", "obtain", "metric"):
                ["results", "experiments", "evaluation"],

            # Methods/Implementation
            ("method", "approach", "implement", "algorithm", "technique", "procedure", "how", "process"):
                ["methodology", "methods", "experiments"],

            # Background/Context
            ("what is", "define", "background", "context", "introduction", "overview"):
                ["introduction", "background", "abstract"],

            # Related Work
            ("related", "previous", "prior", "existing", "literature"):
                ["related_work", "background"],

            # Discussion/Analysis
            ("discuss", "analyze", "interpret", "explain", "why"):
                ["discussion", "results", "conclusion"],

            # Conclusions
            ("conclusion", "summary", "contribution", "future", "limitation"):
                ["conclusion", "discussion"],

            # Datasets/Experiments
            ("dataset", "data", "experiment", "evaluation", "benchmark"):
                ["experiments", "results", "methodology"],
        }

        for keywords, sections in section_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                target_sections.update(sections)

        # Default to all sections if nothing detected
        if not target_sections:
            target_sections = {"introduction", "methods", "results"}

        return target_sections

    def _score_by_section_relevance(
        self, query: str, results: list, target_sections: set
    ) -> list:
        """Apply intelligent section-based scoring.

        Args:
            query: User query
            results: Candidate results
            target_sections: Target sections detected from query

        Returns:
            Results with adjusted scores
        """
        scored_results = []

        for result in results:
            section_type = result.get("metadata", {}).get("section_type", "")
            original_score = result.get("score", 0)

            # Strong boost for exact section matches (2x)
            if section_type in target_sections:
                boost_factor = 2.0
                result["section_match"] = "exact"
            # Moderate boost for related sections (1.3x)
            elif self._is_related_section(section_type, target_sections):
                boost_factor = 1.3
                result["section_match"] = "related"
            # No penalty, keep original score
            else:
                boost_factor = 1.0
                result["section_match"] = "none"

            result["score"] = original_score * boost_factor
            result["original_score"] = original_score
            scored_results.append(result)

        # Sort by adjusted score
        scored_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return scored_results

    def _is_related_section(self, section: str, target_sections: set) -> bool:
        """Check if a section is related to target sections.

        Args:
            section: Section to check
            target_sections: Target sections

        Returns:
            True if related
        """
        # Define related section groups
        related_groups = [
            {"results", "experiments", "evaluation"},
            {"methodology", "methods", "experiments"},
            {"introduction", "background", "abstract"},
            {"discussion", "conclusion", "results"},
        ]

        for group in related_groups:
            if section in group and any(t in group for t in target_sections):
                return True

        return False

    def _apply_diversity_filter(self, results: list) -> list:
        """Apply diversity filtering to avoid redundant chunks.

        Prevents selecting multiple chunks from the exact same location.

        Args:
            results: Scored results

        Returns:
            Filtered results with diversity
        """
        diverse_results = []
        seen_locations = set()

        for result in results:
            # Create location signature (document + page + chunk_index proximity)
            doc_id = result.get("document_id", "")
            page = result.get("metadata", {}).get("page_number", 0)
            chunk_idx = result.get("chunk_index", 0)

            # Group chunks within 3 positions as "same location"
            location = (doc_id, page, chunk_idx // 3)

            # Only take first chunk from each location
            if location not in seen_locations:
                diverse_results.append(result)
                seen_locations.add(location)

            # Stop when we have enough diverse results
            if len(diverse_results) >= self.final_top_k * 3:
                break

        return diverse_results

    def _compress_chunks_for_llm(
        self, chunks: List[Dict[str, Any]], max_tokens: int = 3000
    ) -> List[Dict[str, Any]]:
        """Intelligently compress chunks to fit token budget while maintaining quality.

        Strategy:
        1. Keep high-scoring chunks intact
        2. Truncate lower-scoring chunks intelligently
        3. Preserve key sentences with technical terms

        Args:
            chunks: List of chunks to compress
            max_tokens: Maximum tokens for all chunks combined (~4 chars per token)

        Returns:
            Compressed chunks that fit within budget
        """
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        compressed = []
        total_chars = 0

        for chunk in chunks:
            text = chunk["text"]
            chunk_chars = len(text)

            # If adding this chunk would exceed budget
            if total_chars + chunk_chars > max_chars:
                remaining_chars = max_chars - total_chars

                if remaining_chars < 200:  # Not enough space for meaningful content
                    break

                # Intelligently truncate: keep first sentences up to remaining budget
                sentences = text.split('. ')
                truncated_text = ""
                for sent in sentences:
                    if len(truncated_text) + len(sent) + 2 <= remaining_chars:
                        truncated_text += sent + '. '
                    else:
                        break

                if truncated_text:
                    compressed_chunk = chunk.copy()
                    compressed_chunk["text"] = truncated_text.strip()
                    compressed.append(compressed_chunk)
                    total_chars += len(truncated_text)
                break
            else:
                # Add full chunk
                compressed.append(chunk)
                total_chars += chunk_chars

        logger.info(f"Compressed {len(chunks)} chunks to {len(compressed)} chunks ({total_chars} chars)")
        return compressed

    async def _generate_draft(self, state: AgentState) -> AgentState:
        """Generate draft answer with chunk references.

        Args:
            state: Current agent state

        Returns:
            Updated state with draft answer and used chunks
        """
        if state.get("error"):
            state["draft_answer"] = f"I encountered an error: {state['error']}"
            state["used_chunks"] = []
            return state

        query = state["query"]
        context = state["context"]

        if not context:
            state[
                "draft_answer"
            ] = "I don't have any relevant information in my knowledge base to answer your question. Please upload some research papers first."
            state["used_chunks"] = []
            return state

        # Compress chunks intelligently to fit strict token budget
        # Free tier limit: 8000 tokens total (input + output)
        # Budget: 800 tokens (~3200 chars) for context to leave room for prompts
        compressed_context = self._compress_chunks_for_llm(context, max_tokens=800)

        # Build context string with chunk IDs
        context_str = "\n\n".join(
            [
                f"[{c['chunk_id']} - Document: {c['document_id']}]\n{c['text']}"
                for c in compressed_context
            ]
        )

        # Check if this is a multi-document query
        unique_docs = set(c['document_id'] for c in context)
        is_multi_doc = len(unique_docs) > 1

        # Build prompt for draft generation
        base_requirements = """Requirements:
1. Cite chunks using [c1], [c2] format in your answer
2. Only use information explicitly in the chunks
3. If info is missing, state "The provided context does not contain information about..."
4. List all chunk IDs you referenced"""

        multi_doc_requirements = """
5. When comparing/contrasting multiple papers, explicitly identify which findings come from which document
6. Synthesize insights across documents by highlighting agreements, disagreements, and complementary findings
7. If asked to compare, structure your answer to clearly show similarities and differences"""

        if is_multi_doc:
            requirements_text = base_requirements + multi_doc_requirements
        else:
            requirements_text = base_requirements

        system_prompt = f"""You are an expert research assistant. Answer questions using ONLY the provided chunks.

CRITICAL: Return ONLY a valid JSON object, nothing else. No explanations, no markdown.

{requirements_text}

Exact JSON format:
{{"answer": "Your answer with [c1] citations...", "used_chunks": ["c1", "c3"]}}"""

        user_prompt = f"""Chunks:

{context_str}

Question: {query}

JSON only:"""

        try:
            # Call LLM using async wrapper (Gemini primary, Groq fallback)
            response_text = await self._rate_limited_llm_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for more focused responses
                max_tokens=512,  # Reduced to manage token budget
            )

            # Try to extract JSON from response
            try:
                import re
                import json

                # Remove markdown code blocks if present
                cleaned_text = response_text
                if "```" in cleaned_text:
                    # Extract content between code blocks
                    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_text, re.DOTALL)
                    if match:
                        cleaned_text = match.group(1)

                # Try direct JSON parse first
                try:
                    draft_data = json.loads(cleaned_text)
                except json.JSONDecodeError:
                    # If that fails, try to find the JSON object more carefully
                    # Look for opening brace and match balanced braces
                    start = cleaned_text.find('{')
                    if start != -1:
                        brace_count = 0
                        end = start
                        for i in range(start, len(cleaned_text)):
                            if cleaned_text[i] == '{':
                                brace_count += 1
                            elif cleaned_text[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end = i + 1
                                    break

                        if end > start:
                            json_str = cleaned_text[start:end]
                            draft_data = json.loads(json_str)
                        else:
                            raise json.JSONDecodeError("No valid JSON found", cleaned_text, 0)
                    else:
                        raise json.JSONDecodeError("No JSON object found", cleaned_text, 0)

                state["draft_answer"] = draft_data.get("answer", "")
                state["used_chunks"] = draft_data.get("used_chunks", [])

                # If answer is empty, fall back to entire response
                if not state["draft_answer"]:
                    state["draft_answer"] = response_text
                    chunk_ids = re.findall(r'\[c(\d+)\]', response_text)
                    state["used_chunks"] = [f"c{cid}" for cid in chunk_ids]

            except (json.JSONDecodeError, AttributeError, ValueError) as parse_error:
                # Fallback: treat entire response as answer, extract chunk IDs
                import re
                state["draft_answer"] = response_text
                # Extract chunk IDs from [cN] patterns
                chunk_ids = re.findall(r'\[c(\d+)\]', response_text)
                state["used_chunks"] = [f"c{cid}" for cid in chunk_ids]

            logger.info(f"Generated draft answer: {len(state['draft_answer'])} chars, {len(state['used_chunks'])} chunks")

        except Exception as e:
            logger.error(f"Error generating draft: {e}")
            state["error"] = f"Error generating draft: {str(e)}"
            state["draft_answer"] = ""
            state["used_chunks"] = []

        return state

    async def _validate_grounding(self, state: AgentState) -> AgentState:
        """Validate that the answer is grounded in the chunks.

        Args:
            state: Current agent state

        Returns:
            Updated state with validation results
        """
        if state.get("error") or not state.get("draft_answer"):
            state["response"] = state.get("draft_answer", "")
            state["confidence"] = 0.0
            state["unsupported_spans"] = []
            state["sources"] = []
            return state

        draft_answer = state["draft_answer"]
        used_chunks = state.get("used_chunks", [])
        context = state["context"]

        # Build context for validation
        chunk_map = {c["chunk_id"]: c for c in context}
        used_chunk_texts = "\n\n".join(
            [
                f"[{cid}]\n{chunk_map[cid]['text']}"
                for cid in used_chunks
                if cid in chunk_map
            ]
        )

        if not used_chunk_texts:
            # No chunks used, low confidence
            state["response"] = draft_answer
            state["confidence"] = 0.2
            state["unsupported_spans"] = []
            state["sources"] = []
            return state

        # Build validation prompt
        system_prompt = """You are a fact-checking expert. Your job is to verify if statements are supported by source text.

Analyze the provided answer and check if EACH sentence is fully supported by the referenced chunks.

Return a JSON object with:
{
  "supported_sentences": 5,
  "total_sentences": 7,
  "confidence": 0.71,
  "unsupported_spans": [
    {"text": "...", "reason": "not found in chunks"}
  ]
}

confidence = supported_sentences / total_sentences"""

        user_prompt = f"""Answer to verify:
{draft_answer}

Referenced chunks:
{used_chunk_texts}

Check if each statement in the answer is supported by the chunks. Return JSON only."""

        try:
            # Call LLM using async wrapper (Gemini primary, Groq fallback)
            response_text = await self._rate_limited_llm_call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Very low temperature for validation
                max_tokens=256,  # Validation needs less tokens
            )

            # Extract JSON
            try:
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                    response_text = response_text.strip()

                validation_data = json.loads(response_text)
                confidence = validation_data.get("confidence", 0.5)
                unsupported_spans = validation_data.get("unsupported_spans", [])

                state["confidence"] = confidence
                state["unsupported_spans"] = unsupported_spans
            except json.JSONDecodeError:
                # Fallback: medium confidence
                state["confidence"] = 0.5
                state["unsupported_spans"] = []

        except Exception as e:
            # On validation error, assume medium confidence
            state["confidence"] = 0.5
            state["unsupported_spans"] = []

        # Build final response with sources
        state["response"] = draft_answer
        logger.info(f"Final response: {len(draft_answer)} chars, confidence: {state['confidence']}, sources: {len(context)}")
        state["sources"] = [
            {
                "chunk_id": cid,
                "document_id": chunk_map[cid]["document_id"],
                "text": chunk_map[cid]["text"],
                "score": chunk_map[cid].get("score", 0.0),
                "page": chunk_map[cid].get("metadata", {}).get("page", None),
            }
            for cid in used_chunks
            if cid in chunk_map
        ]

        return state

    async def query(
        self,
        question: str,
        document_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Query the agent with a question.

        Args:
            question: User question
            document_id: Optional single document ID to filter context (deprecated, use document_ids)
            document_ids: Optional list of document IDs to filter context (for multi-doc queries)

        Returns:
            Response dictionary with answer, sources, confidence, and validation
        """
        # Initialize state
        initial_state: AgentState = {
            "query": question,
            "context": [],
            "draft_answer": "",
            "used_chunks": [],
            "response": "",
            "sources": [],
            "confidence": 0.0,
            "unsupported_spans": [],
            "error": None,
            "document_id": document_id,
            "document_ids": document_ids,
        }

        # Run the graph asynchronously
        final_state = await self.graph.ainvoke(initial_state)

        return {
            "response": final_state["response"],
            "sources": final_state["sources"],
            "confidence": final_state.get("confidence", 0.0),
            "unsupported_spans": final_state.get("unsupported_spans", []),
            "error": final_state.get("error"),
        }

    async def query_with_history(
        self,
        question: str,
        chat_history: List[Dict[str, str]],
        document_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Query the agent with conversation history for context.

        Args:
            question: User question
            chat_history: Previous conversation messages
            document_id: Optional single document ID to filter context (deprecated, use document_ids)
            document_ids: Optional list of document IDs to filter context (for multi-doc queries)

        Returns:
            Response dictionary with answer and sources
        """
        # For now, we just use the current question
        # In future, we can implement conversation summarization
        return await self.query(question, document_id, document_ids)
