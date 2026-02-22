"""Debate Arena Agent - Makes research papers debate each other!"""

import json
import random
import time
from typing import Any, Dict, List, Optional, TypedDict

from groq import Groq
from langgraph.graph import END, StateGraph

from ..services.vector_store import VectorStoreService


class DebateState(TypedDict):
    """State for the Debate Arena."""

    # Setup
    document_ids: List[str]
    topic: str
    rounds: int
    humor_level: str  # "low", "medium", "high"

    # Team assignments
    team_a_docs: List[str]
    team_b_docs: List[str]
    team_a_name: str
    team_b_name: str

    # Current round
    current_round: int
    round_topic: str

    # Arguments
    team_a_argument: str
    team_a_citations: List[Dict[str, Any]]
    team_a_verified: bool
    team_a_tone: str

    team_b_argument: str
    team_b_citations: List[Dict[str, Any]]
    team_b_verified: bool
    team_b_tone: str

    # Moderation
    moderator_comment: str
    round_winner: Optional[str]

    # Scores
    team_a_score: float
    team_b_score: float

    # Results
    debate_rounds: List[Dict[str, Any]]
    final_verdict: str
    error: Optional[str]


class DebateArenaAgent:
    """Makes research papers debate each other in a boxing ring format!"""

    def __init__(
        self,
        vector_store: VectorStoreService,
        groq_api_key: str,
        groq_model: str = "llama-3.1-70b-versatile",
    ):
        """Initialize Debate Arena.

        Args:
            vector_store: Vector store service for retrieving context
            groq_api_key: Groq API key
            groq_model: Groq model to use
        """
        self.vector_store = vector_store
        self.groq_client = Groq(api_key=groq_api_key)
        self.groq_model = groq_model

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests

        # Humor templates
        self.humor_templates = {
            "low": {
                "win": ["Strong point.", "Well-argued.", "Convincing evidence."],
                "lose": ["Needs more evidence.", "Weak defense.", "Unconvincing."],
                "tie": ["Both make valid points.", "Inconclusive round.", "Evenly matched."]
            },
            "medium": {
                "win": ["💪 Strong counter!", "🎯 Got 'em!", "Nice citation work!"],
                "lose": ["😅 Weak defense", "📊 Missing data there", "🤔 Hmm, not convinced"],
                "tie": ["🤝 Both have a point", "⚖️ Tied round", "Fair arguments both sides"]
            },
            "high": {
                "win": ["🔥 CRITICAL HIT!", "💀 Destroyed!", "🎤 Mic drop moment!"],
                "lose": ["😬 Ouch, that hurt", "💀 No coming back from that", "🚨 Major L"],
                "tie": ["🥊 Evenly matched!", "🔄 Plot twist - both right!", "🎭 Drama!"]
            }
        }

        # Build LangGraph workflow
        self.graph = self._build_graph()

    def _rate_limited_llm_call(self, messages: list, max_retries: int = 3) -> str:
        """Make a rate-limited LLM call with retry logic.

        Args:
            messages: Messages to send to LLM
            max_retries: Maximum number of retries

        Returns:
            LLM response text

        Raises:
            Exception: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting: ensure minimum interval between requests
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_request_interval:
                    sleep_time = self.min_request_interval - time_since_last
                    time.sleep(sleep_time)

                # Make the call
                response = self.groq_client.chat.completions.create(
                    messages=messages,
                    model=self.groq_model,
                    temperature=0.7,
                    max_tokens=512
                )

                self.last_request_time = time.time()
                return response.choices[0].message.content.strip()

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate" in error_msg.lower():
                    # Rate limit hit - exponential backoff
                    wait_time = (2 ** attempt) * 3  # 3s, 6s, 12s
                    print(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    # Other error - raise immediately
                    raise

        # All retries failed
        raise Exception(f"Failed after {max_retries} retries due to rate limiting")

    def _build_graph(self) -> StateGraph:
        """Build the debate workflow graph.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(DebateState)

        # Add nodes
        workflow.add_node("assign_teams", self._assign_teams)
        workflow.add_node("detect_topics", self._detect_topics)
        workflow.add_node("run_round", self._run_round)
        workflow.add_node("judge_round", self._judge_round)
        workflow.add_node("finalize", self._finalize_debate)

        # Add edges
        workflow.set_entry_point("assign_teams")
        workflow.add_edge("assign_teams", "detect_topics")
        workflow.add_edge("detect_topics", "run_round")
        workflow.add_edge("run_round", "judge_round")

        # Conditional: more rounds or finalize?
        workflow.add_conditional_edges(
            "judge_round",
            self._should_continue,
            {
                "continue": "run_round",
                "end": "finalize"
            }
        )

        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _assign_teams(self, state: DebateState) -> DebateState:
        """Assign papers to teams automatically.

        Strategy:
        - If 2 papers: 1 vs 1
        - If 3+ papers: Try to balance by detecting similar approaches

        Args:
            state: Current debate state

        Returns:
            Updated state with team assignments
        """
        doc_ids = state["document_ids"]

        if len(doc_ids) == 2:
            # Simple 1v1
            state["team_a_docs"] = [doc_ids[0]]
            state["team_b_docs"] = [doc_ids[1]]
            state["team_a_name"] = "Team A"
            state["team_b_name"] = "Team B"

        elif len(doc_ids) == 3:
            # 2v1 or try to find similar papers
            # For now: simple split
            state["team_a_docs"] = [doc_ids[0]]
            state["team_b_docs"] = [doc_ids[1], doc_ids[2]]
            state["team_a_name"] = "Team Classic"
            state["team_b_name"] = "Team Modern"

        else:
            # Split in half
            mid = len(doc_ids) // 2
            state["team_a_docs"] = doc_ids[:mid]
            state["team_b_docs"] = doc_ids[mid:]
            state["team_a_name"] = "Team A"
            state["team_b_name"] = "Team B"

        # Initialize scores
        state["team_a_score"] = 0.0
        state["team_b_score"] = 0.0
        state["current_round"] = 0
        state["debate_rounds"] = []

        return state

    def _detect_topics(self, state: DebateState) -> DebateState:
        """Auto-detect debate topics if not provided.

        Args:
            state: Current debate state

        Returns:
            Updated state with topics
        """
        if state.get("topic"):
            # User provided topic
            return state

        # Auto-detect common debate topics
        default_topics = [
            "Data efficiency",
            "Computational cost",
            "Performance metrics",
            "Model architecture",
            "Training methodology"
        ]

        # For now, use defaults (could enhance with paper analysis)
        state["topic"] = "General comparison"

        return state

    def _run_round(self, state: DebateState) -> DebateState:
        """Run one debate round.

        Args:
            state: Current debate state

        Returns:
            Updated state with round arguments
        """
        state["current_round"] += 1
        round_num = state["current_round"]

        # Pick round topic
        topics = [
            "Data efficiency and sample complexity",
            "Computational cost and scalability",
            "Performance on benchmarks",
            "Model interpretability",
            "Real-world applicability"
        ]

        if round_num <= len(topics):
            state["round_topic"] = topics[round_num - 1]
        else:
            state["round_topic"] = "General comparison"

        try:
            # Team A argues
            team_a_result = self._generate_argument(
                team_docs=state["team_a_docs"],
                opponent_docs=state["team_b_docs"],
                topic=state["round_topic"],
                team_name=state["team_a_name"],
                is_first=True,
                opponent_last_arg=None,
                humor_level=state.get("humor_level", "medium")
            )

            state["team_a_argument"] = team_a_result["argument"]
            state["team_a_citations"] = team_a_result["citations"]
            state["team_a_verified"] = team_a_result["verified"]
            state["team_a_tone"] = team_a_result["tone"]

            # Team B counters
            team_b_result = self._generate_argument(
                team_docs=state["team_b_docs"],
                opponent_docs=state["team_a_docs"],
                topic=state["round_topic"],
                team_name=state["team_b_name"],
                is_first=False,
                opponent_last_arg=team_a_result["argument"],
                humor_level=state.get("humor_level", "medium")
            )

            state["team_b_argument"] = team_b_result["argument"]
            state["team_b_citations"] = team_b_result["citations"]
            state["team_b_verified"] = team_b_result["verified"]
            state["team_b_tone"] = team_b_result["tone"]

        except Exception as e:
            state["error"] = f"Error in round {round_num}: {str(e)}"

        return state

    def _generate_argument(
        self,
        team_docs: List[str],
        opponent_docs: List[str],
        topic: str,
        team_name: str,
        is_first: bool,
        opponent_last_arg: Optional[str],
        humor_level: str
    ) -> Dict[str, Any]:
        """Generate argument for one team.

        Args:
            team_docs: Document IDs for this team
            opponent_docs: Opponent's documents
            topic: Debate topic
            team_name: Team name
            is_first: Whether this is the opening argument
            opponent_last_arg: Opponent's last argument (if countering)
            humor_level: Humor level setting

        Returns:
            Argument with citations and metadata
        """
        # Retrieve relevant context for this topic
        context_results = self.vector_store.search(
            query=topic,
            top_k=5,
            filter_document_ids=team_docs
        )

        # Build context string
        context_str = "\n\n".join([
            f"[{i+1}. Document {r['document_id']}, Page {r.get('metadata', {}).get('page_number', '?')}]\n{r['text']}"
            for i, r in enumerate(context_results)
        ])

        # Build prompt
        if is_first:
            role_instruction = f"""You are arguing for {team_name}.
Make a STRONG opening argument about: {topic}

Requirements:
1. Use ONLY facts from your papers (cite as [1], [2], etc.)
2. Be specific with numbers, metrics, results
3. {"Add subtle humor/personality" if humor_level != "low" else "Stay professional"}
4. Keep it concise (2-3 sentences max)
5. Be factual but {"confident and witty" if humor_level == "high" else "clear"}

Return JSON:
{{"argument": "Your argument with [1] citations...", "tone": "confident/defensive/neutral"}}"""
        else:
            role_instruction = f"""You are arguing for {team_name}.
Your opponent just said: "{opponent_last_arg}"

Counter their argument about: {topic}

Requirements:
1. Address their point directly
2. Use facts from YOUR papers (cite as [1], [2], etc.)
3. Point out weaknesses in their claim if possible
4. {"Add wit/humor when appropriate" if humor_level != "low" else "Stay professional"}
5. Be specific with evidence
6. Admit if they have a point, but pivot to your strength
7. Keep it concise (2-3 sentences)

Return JSON:
{{"argument": "Your counter-argument with [1] citations...", "tone": "confident/defensive/conceding"}}"""

        system_prompt = f"""{role_instruction}

CRITICAL: Return ONLY valid JSON, nothing else."""

        user_prompt = f"""Your evidence:
{context_str}

Topic: {topic}

JSON only:"""

        try:
            # Call Groq with rate limiting
            response_text = self._rate_limited_llm_call([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])

            # Parse JSON
            try:
                # Clean markdown if present
                if "```" in response_text:
                    import re
                    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                    if match:
                        response_text = match.group(1)

                data = json.loads(response_text)
                argument = data.get("argument", "")
                tone = data.get("tone", "neutral")

            except json.JSONDecodeError:
                # Fallback: use raw text
                argument = response_text
                tone = "neutral"

            # Extract citation numbers
            import re
            cited_nums = re.findall(r'\[(\d+)\]', argument)

            # Build citation objects
            citations = []
            for num_str in cited_nums:
                num = int(num_str) - 1  # Convert to 0-indexed
                if 0 <= num < len(context_results):
                    citations.append({
                        "chunk_id": f"c{num+1}",
                        "document_id": context_results[num]["document_id"],
                        "text": context_results[num]["text"][:200] + "...",
                        "page": context_results[num].get("metadata", {}).get("page_number")
                    })

            return {
                "argument": argument,
                "citations": citations,
                "verified": len(citations) > 0,  # Has at least one citation
                "tone": tone
            }

        except Exception as e:
            return {
                "argument": f"[Error generating argument: {str(e)}]",
                "citations": [],
                "verified": False,
                "tone": "error"
            }

    def _judge_round(self, state: DebateState) -> DebateState:
        """Judge the current round and assign scores.

        Args:
            state: Current debate state

        Returns:
            Updated state with round judgment
        """
        team_a_arg = state["team_a_argument"]
        team_b_arg = state["team_b_argument"]
        team_a_cites = len(state["team_a_citations"])
        team_b_cites = len(state["team_b_citations"])
        team_a_tone = state["team_a_tone"]
        team_b_tone = state["team_b_tone"]

        # Simple scoring logic
        team_a_round_score = 0.0
        team_b_round_score = 0.0

        # Citation count matters
        team_a_round_score += min(team_a_cites * 0.3, 1.5)
        team_b_round_score += min(team_b_cites * 0.3, 1.5)

        # Argument length (substance)
        team_a_round_score += min(len(team_a_arg) / 200, 1.0)
        team_b_round_score += min(len(team_b_arg) / 200, 1.0)

        # Tone bonus
        if team_a_tone == "confident":
            team_a_round_score += 0.5
        elif team_a_tone == "defensive":
            team_a_round_score -= 0.3

        if team_b_tone == "confident":
            team_b_round_score += 0.5
        elif team_b_tone == "defensive":
            team_b_round_score -= 0.3

        # Determine winner
        if team_a_round_score > team_b_round_score + 0.5:
            winner = "team_a"
            state["team_a_score"] += 1.0
        elif team_b_round_score > team_a_round_score + 0.5:
            winner = "team_b"
            state["team_b_score"] += 1.0
        else:
            winner = "tie"
            state["team_a_score"] += 0.5
            state["team_b_score"] += 0.5

        state["round_winner"] = winner

        # Generate moderator comment
        humor_level = state.get("humor_level", "medium")
        templates = self.humor_templates.get(humor_level, self.humor_templates["medium"])

        if winner == "team_a":
            comment = random.choice(templates["win"])
        elif winner == "team_b":
            comment = random.choice(templates["win"])
        else:
            comment = random.choice(templates["tie"])

        state["moderator_comment"] = comment

        # Save round
        state["debate_rounds"].append({
            "round": state["current_round"],
            "topic": state["round_topic"],
            "team_a": {
                "argument": team_a_arg,
                "citations": state["team_a_citations"],
                "verified": state["team_a_verified"],
                "tone": team_a_tone
            },
            "team_b": {
                "argument": team_b_arg,
                "citations": state["team_b_citations"],
                "verified": state["team_b_verified"],
                "tone": team_b_tone
            },
            "moderator_comment": comment,
            "winner": winner,
            "scores": {
                "team_a": state["team_a_score"],
                "team_b": state["team_b_score"]
            }
        })

        return state

    def _should_continue(self, state: DebateState) -> str:
        """Check if we should continue to next round.

        Args:
            state: Current debate state

        Returns:
            "continue" or "end"
        """
        if state["current_round"] >= state.get("rounds", 5):
            return "end"
        return "continue"

    def _finalize_debate(self, state: DebateState) -> DebateState:
        """Generate final verdict.

        Args:
            state: Current debate state

        Returns:
            Updated state with final verdict
        """
        team_a_score = state["team_a_score"]
        team_b_score = state["team_b_score"]

        if team_a_score > team_b_score:
            winner = state["team_a_name"]
            verdict = f"🏆 {winner} wins! ({team_a_score} - {team_b_score})"
        elif team_b_score > team_a_score:
            winner = state["team_b_name"]
            verdict = f"🏆 {winner} wins! ({team_b_score} - {team_a_score})"
        else:
            verdict = f"🤝 It's a tie! Both teams scored {team_a_score}"

        state["final_verdict"] = verdict

        return state

    async def start_debate(
        self,
        document_ids: List[str],
        topic: Optional[str] = None,
        rounds: int = 3,  # Reduced to 3 for rate limiting
        humor_level: str = "medium"
    ) -> Dict[str, Any]:
        """Start a debate between papers.

        Args:
            document_ids: List of document IDs (2+)
            topic: Optional specific topic to debate
            rounds: Number of rounds (default 3, was 5 before rate limiting)
            humor_level: "low", "medium", or "high"

        Returns:
            Complete debate results
        """
        if len(document_ids) < 2:
            return {
                "error": "Need at least 2 documents to debate",
                "debate_rounds": [],
                "final_verdict": ""
            }

        # Initialize state
        initial_state: DebateState = {
            "document_ids": document_ids,
            "topic": topic or "",
            "rounds": rounds,
            "humor_level": humor_level,
            "team_a_docs": [],
            "team_b_docs": [],
            "team_a_name": "",
            "team_b_name": "",
            "current_round": 0,
            "round_topic": "",
            "team_a_argument": "",
            "team_a_citations": [],
            "team_a_verified": False,
            "team_a_tone": "",
            "team_b_argument": "",
            "team_b_citations": [],
            "team_b_verified": False,
            "team_b_tone": "",
            "moderator_comment": "",
            "round_winner": None,
            "team_a_score": 0.0,
            "team_b_score": 0.0,
            "debate_rounds": [],
            "final_verdict": "",
            "error": None
        }

        # Run the debate graph
        final_state = self.graph.invoke(initial_state)

        return {
            "team_a": {
                "name": final_state["team_a_name"],
                "documents": final_state["team_a_docs"],
                "score": final_state["team_a_score"]
            },
            "team_b": {
                "name": final_state["team_b_name"],
                "documents": final_state["team_b_docs"],
                "score": final_state["team_b_score"]
            },
            "rounds": final_state["debate_rounds"],
            "final_verdict": final_state["final_verdict"],
            "error": final_state.get("error")
        }
