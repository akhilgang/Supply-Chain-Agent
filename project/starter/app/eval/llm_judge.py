"""
LLM-as-Judge Evaluation System
Implements comprehensive evaluation using LLM to judge agent responses.
"""

import logging
import json
import os
import traceback
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory, ChatMessageContent, AuthorRole

logger = logging.getLogger(__name__)


# ---------------- Data classes ----------------

@dataclass
class EvaluationCriteria:
    """Evaluation criteria for LLM-as-judge"""
    name: str
    description: str
    weight: float
    max_score: float = 5.0


@dataclass
class EvaluationResult:
    """Result of LLM-as-judge evaluation"""
    overall_score: float
    criteria_scores: Dict[str, float]
    reasoning: str
    recommendations: List[str]
    passed: bool


# ---------------- Main Judge class ----------------

class LLMJudge:
    """LLM-as-Judge evaluation system"""

    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.criteria = self._setup_evaluation_criteria()

    def _setup_evaluation_criteria(self) -> List[EvaluationCriteria]:
        """Set up evaluation criteria"""
        return [
            EvaluationCriteria("accuracy", "Accuracy of information provided", 0.25),
            EvaluationCriteria("completeness", "Completeness of response to user query", 0.20),
            EvaluationCriteria("relevance", "Relevance of information to user's needs", 0.20),
            EvaluationCriteria("tool_usage", "Appropriate and effective use of tools", 0.15),
            EvaluationCriteria("structure", "Clear structure and organization of response", 0.10),
            EvaluationCriteria("citations", "Proper citations and source attribution", 0.10),
        ]

    async def evaluate_response(
        self,
        user_query: str,
        agent_response: str,
        structured_output: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
        citations: List[str],
        reference_facts: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """
        Evaluate agent response using LLM-as-judge.
        """
        try:
            logger.info("⚖️ Starting LLM-as-judge evaluation")

            # Build the evaluation prompt
            evaluation_prompt = self._create_evaluation_prompt(
                user_query, agent_response, structured_output,
                tool_calls, citations, reference_facts
            )

            logger.debug("Evaluation prompt (truncated to 500 chars):\n%s", evaluation_prompt[:500])
            logger.debug("Available services in kernel: %s", list(self.kernel.services.keys()))

            # Look up the chat service (using the deployment name as ID)
            service_id = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
            chat_service = self.kernel.get_service(service_id)

            # Build chat history manually (since from_messages may not exist)
            chat_history = ChatHistory()
            chat_history.add_message(
                ChatMessageContent(role=AuthorRole.USER, content=evaluation_prompt)
            )

            from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

            settings = OpenAIChatPromptExecutionSettings(
                max_completion_tokens=2000
            )

            response = await chat_service.get_chat_message_contents(
                chat_history=chat_history,
                settings=settings,
                kernel=self.kernel,
            )

            # Parse evaluation result
            evaluation_text = response[0].content.strip() if response else ""
            logger.debug("Raw LLM judge response: %s", evaluation_text[:500])
            result = self._parse_evaluation_result(evaluation_text)

            logger.info("⚖️ Evaluation completed. Overall score: %.2f", result.overall_score)
            return result

        except Exception as e:
            logger.error("❌ LLM-as-judge evaluation failed: %s", e, exc_info=True)
            return EvaluationResult(
                overall_score=0.0,
                criteria_scores={},
                reasoning=f"Evaluation failed: {e}",
                recommendations=["Fix evaluation system"],
                passed=False,
            )

    def _create_evaluation_prompt(
        self,
        user_query: str,
        agent_response: str,
        structured_output: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
        citations: List[str],
        reference_facts: Optional[List[str]] = None,
    ) -> str:
        """Create evaluation prompt for LLM"""

        criteria_text = "\n".join([
            f"- {c.name} ({c.weight*100:.0f}%): {c.description} (0-{c.max_score})"
            for c in self.criteria
        ])

        if tool_calls:
            tool_calls_text = "\n".join([
                f"- {call.get('name', 'unknown')}: {call.get('arguments', {})}"
                if isinstance(call, dict) else f"- {call}"
                for call in tool_calls
            ])
        else:
            tool_calls_text = "None"

        citations_text = "\n".join([f"- {c}" for c in citations]) if citations else "None"
        reference_facts_text = "\n".join([f"- {f}" for f in reference_facts]) if reference_facts else "None"

        return f"""
You are an expert evaluator assessing a Travel Credit Card Concierge agent's response.

USER QUERY:
{user_query}

AGENT RESPONSE:
{agent_response}

STRUCTURED OUTPUT:
{json.dumps(structured_output, indent=2)}

TOOL CALLS MADE:
{tool_calls_text}

CITATIONS PROVIDED:
{citations_text}

REFERENCE FACTS (for accuracy checking):
{reference_facts_text}

EVALUATION CRITERIA:
{criteria_text}

Please evaluate the agent's response and provide:
1. A score (0-5) for each criterion
2. An overall weighted score (0-5)
3. Detailed reasoning for each score
4. Specific recommendations for improvement
5. Whether the response passes (overall score >= 3.0)

Focus on:
- Accuracy of travel information, weather data, and recommendations
- Appropriate tool usage for travel planning queries
- Clear and helpful travel concierge responses
- Proper handling of different query types (trip planning, card benefits, weather, currency)
- Professional travel concierge tone and structure
- Quality of credit card recommendations and travel insights

Respond in JSON format:
{{
  "criteria_scores": {{
    "accuracy": 4.5,
    "completeness": 4.0,
    "relevance": 4.5,
    "tool_usage": 3.5,
    "structure": 4.0,
    "citations": 3.0
  }},
  "overall_score": 4.0,
  "reasoning": "Detailed explanation of scores...",
  "recommendations": ["Specific improvement suggestions..."],
  "passed": true
}}
"""

    def _parse_evaluation_result(self, evaluation_text: str) -> EvaluationResult:
        """Parse LLM evaluation result"""
        try:
            start_idx = evaluation_text.find("{")
            end_idx = evaluation_text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_text = evaluation_text[start_idx:end_idx]
                result_data = json.loads(json_text)
                return EvaluationResult(
                    overall_score=float(result_data.get("overall_score", 0.0)),
                    criteria_scores=result_data.get("criteria_scores", {}),
                    reasoning=result_data.get("reasoning", "No reasoning provided"),
                    recommendations=result_data.get("recommendations", []),
                    passed=result_data.get("passed", False),
                )
            else:
                return self._fallback_parse(evaluation_text)
        except Exception as e:
            logger.error("❌ Failed to parse evaluation result: %s", e, exc_info=True)
            return self._fallback_parse(evaluation_text)

    def _fallback_parse(self, evaluation_text: str) -> EvaluationResult:
        """Fallback parsing when JSON parsing fails"""
        score = 3.0
        text = evaluation_text.lower()
        if "excellent" in text:
            score = 5.0
        elif "good" in text:
            score = 4.0
        elif "fair" in text:
            score = 3.0
        elif "poor" in text:
            score = 2.0
        elif "terrible" in text:
            score = 1.0

        return EvaluationResult(
            overall_score=score,
            criteria_scores={},
            reasoning="Fallback parsing used – detailed scores not available",
            recommendations=["Improve response format for better evaluation"],
            passed=score >= 3.0,
        )

    async def evaluate_batch(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate a batch of test cases with LLM-as-judge"""
        try:
            logger.info("⚖️ Starting batch evaluation of %d test cases", len(test_cases))
            results = []
            total_score = 0.0
            passed_count = 0

            for i, tc in enumerate(test_cases):
                logger.info("⚖️ Evaluating test case %d/%d", i+1, len(test_cases))
                result = await self.evaluate_response(
                    user_query=tc.get("user_query", ""),
                    agent_response=tc.get("agent_response", ""),
                    structured_output=tc.get("structured_output", {}),
                    tool_calls=tc.get("tool_calls", []),
                    citations=tc.get("citations", []),
                    reference_facts=tc.get("reference_facts"),
                )
                results.append({"test_case": i+1, "user_query": tc.get("user_query", ""), "evaluation": result})
                total_score += result.overall_score
                if result.passed:
                    passed_count += 1

            avg_score = total_score / len(test_cases) if test_cases else 0.0
            pass_rate = (passed_count / len(test_cases)) * 100 if test_cases else 0.0
            logger.info("⚖️ Batch evaluation completed. Avg score %.2f, Pass rate %.1f%%", avg_score, pass_rate)

            return {
                "total_cases": len(test_cases),
                "average_score": avg_score,
                "pass_rate": pass_rate,
                "passed_cases": passed_count,
                "failed_cases": len(test_cases) - passed_count,
                "results": results,
            }
        except Exception as e:
            logger.error("❌ Batch evaluation failed: %s", e, exc_info=True)
            return {"error": str(e), "total_cases": 0, "average_score": 0.0, "pass_rate": 0.0}
