import csv
import json
import asyncio
from app.main import run_request, create_kernel
from app.eval.llm_judge import LLMJudge
from pydantic import ValidationError

# Define test scenarios
TEST_CASES = [
    {
        "name": "Test 1",
        "query": "Plan a trip to Paris from June 1-8, 2026. I have a BankGold card."
    },
    {
        "name": "Test 2",
        "query": "Plan a trip to Tokyo from July 10-17, 2026. I have a BankGold card."
    },
    {
        "name": "Test 3",
        "query": "Plan a trip to Barcelona from August 15-22, 2026. I have a BankGold card."
    }
]

async def evaluate(case, judge):
    """Evaluate a test case using LLM-as-Judge"""
    try:
        print(f"\n🔄 Running agent for: {case['name']}")
        response = await run_request(case["query"])

        # Parse response
        response_data = json.loads(response)
        structured_output = response_data.get("trip_plan", {})
        citations = structured_output.get("citations", []) or []

        print(f"✅ Agent response received")

        # LLM-as-Judge evaluation
        print(f"⚖️ Running LLM-as-Judge evaluation...")
        result = await judge.evaluate_response(
            user_query=case["query"],
            agent_response=response,
            structured_output=structured_output,
            tool_calls=response_data.get("metadata", {}).get("tools_called", []),
            citations=citations,
        )

        return {
            "name": case["name"],
            "query": case["query"],
            "overall_score": result.overall_score,
            "passed": result.passed,
            "accuracy": result.criteria_scores.get("accuracy", 0),
            "completeness": result.criteria_scores.get("completeness", 0),
            "relevance": result.criteria_scores.get("relevance", 0),
            "tool_usage": result.criteria_scores.get("tool_usage", 0),
            "reasoning": result.reasoning[:200] + "..." if len(result.reasoning) > 200 else result.reasoning
        }

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        return {
            "name": case["name"],
            "query": case["query"],
            "overall_score": 0,
            "passed": False,
            "accuracy": 0,
            "completeness": 0,
            "relevance": 0,
            "tool_usage": 0,
            "reasoning": f"Error: {e}"
        }

async def main():
    print("🏥 Travel Concierge Agent - LLM-as-Judge Evaluation")
    print("=" * 60)

    # Create kernel and judge
    kernel = create_kernel()
    judge = LLMJudge(kernel)

    results = []
    passed_count = 0

    for case in TEST_CASES:
        outcome = await evaluate(case, judge)
        results.append(outcome)

        # Print result
        status = "✅ PASS" if outcome["passed"] else "❌ FAIL"
        print(f"\n{status} {outcome['name']}: {outcome['overall_score']:.1f}/5")
        print(f"   Accuracy: {outcome['accuracy']}, Completeness: {outcome['completeness']}")
        print(f"   Relevance: {outcome['relevance']}, Tool Usage: {outcome['tool_usage']}")

        if outcome["passed"]:
            passed_count += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Summary: {passed_count}/{len(TEST_CASES)} tests passed")
    print(f"   Average Score: {sum(r['overall_score'] for r in results) / len(results):.2f}/5")

    # Write results to CSV
    with open("app/eval/results.csv", "w", newline="") as f:
        fieldnames = ["name", "query", "overall_score", "passed", "accuracy", "completeness", "relevance", "tool_usage", "reasoning"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("\n✅ Results saved to app/eval/results.csv")

if __name__ == "__main__":
    asyncio.run(main())
