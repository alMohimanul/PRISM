"""Literature Reviewer Agent with RAG capabilities."""

from typing import Any, Dict, List, Optional, TypedDict

from groq import Groq
from langgraph.graph import END, StateGraph

from ..services.vector_store import VectorStoreService


class AgentState(TypedDict):
    """State for the Literature Reviewer agent."""

    query: str
    context: List[Dict[str, Any]]
    response: str
    sources: List[Dict[str, Any]]
    error: Optional[str]


class LiteratureReviewerAgent:
    """Literature Reviewer agent for answering questions about research papers using RAG."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        groq_api_key: str,
        groq_model: str = "llama-3.1-70b-versatile",
    ):
        """Initialize Literature Reviewer agent.

        Args:
            vector_store: Vector store service for retrieving relevant chunks
            groq_api_key: Groq API key
            groq_model: Groq model to use
        """
        self.vector_store = vector_store
        self.groq_client = Groq(api_key=groq_api_key)
        self.groq_model = groq_model

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
        workflow.add_node("generate", self._generate_response)

        # Add edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    def _retrieve_context(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from vector store.

        Args:
            state: Current agent state

        Returns:
            Updated state with context
        """
        query = state["query"]

        try:
            # Search for relevant chunks
            results = self.vector_store.search(query, top_k=5)

            state["context"] = results
            state["sources"] = [
                {
                    "document_id": r["document_id"],
                    "text": r["text"][:200] + "...",  # Preview
                    "score": r["score"],
                }
                for r in results
            ]

        except Exception as e:
            state["error"] = f"Error retrieving context: {str(e)}"
            state["context"] = []
            state["sources"] = []

        return state

    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate response using LLM with retrieved context.

        Args:
            state: Current agent state

        Returns:
            Updated state with response
        """
        if state.get("error"):
            state["response"] = f"I encountered an error: {state['error']}"
            return state

        query = state["query"]
        context = state["context"]

        if not context:
            state[
                "response"
            ] = "I don't have any relevant information in my knowledge base to answer your question. Please upload some research papers first."
            return state

        # Build context string
        context_str = "\n\n".join(
            [
                f"[Source {i+1} - Document: {c['document_id']}]\n{c['text']}"
                for i, c in enumerate(context)
            ]
        )

        # Build prompt
        system_prompt = """You are an expert research assistant helping researchers understand and analyze academic papers.

Your task is to answer questions about research papers based on the provided context.
Follow these guidelines:
1. Answer directly and concisely based on the context provided
2. Cite sources by referencing [Source N] where appropriate
3. If the context doesn't contain enough information, acknowledge this
4. Focus on accuracy over speculation
5. When discussing methodologies, be precise about experimental details
6. Highlight key findings and their implications"""

        user_prompt = f"""Context from research papers:

{context_str}

Question: {query}

Please provide a comprehensive answer based on the context above."""

        try:
            # Call Groq API
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.groq_model,
                temperature=0.7,
                max_tokens=1024,
            )

            response = chat_completion.choices[0].message.content
            state["response"] = response

        except Exception as e:
            state["error"] = f"Error generating response: {str(e)}"
            state[
                "response"
            ] = f"I encountered an error while generating the response: {str(e)}"

        return state

    async def query(self, question: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Query the agent with a question.

        Args:
            question: User question
            document_id: Optional document ID to filter context

        Returns:
            Response dictionary with answer and sources
        """
        # Initialize state
        initial_state: AgentState = {
            "query": question,
            "context": [],
            "response": "",
            "sources": [],
            "error": None,
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        return {
            "response": final_state["response"],
            "sources": final_state["sources"],
            "error": final_state.get("error"),
        }

    async def query_with_history(
        self, question: str, chat_history: List[Dict[str, str]], document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query the agent with conversation history for context.

        Args:
            question: User question
            chat_history: Previous conversation messages
            document_id: Optional document ID to filter context

        Returns:
            Response dictionary with answer and sources
        """
        # For now, we just use the current question
        # In future, we can implement conversation summarization
        return await self.query(question, document_id)
