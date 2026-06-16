# ============================================================
# Multi-Agent Data Analysis Workflow
# Using Semantic Kernel — MagenticOrchestration Pattern
# ============================================================

import os
import asyncio
import pandas as pd
import json
import logging
import traceback
from dotenv import load_dotenv

from semantic_kernel.agents import (
    ChatCompletionAgent,
    StandardMagenticManager,
    MagenticOrchestration,
)
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.agents.runtime import InProcessRuntime


# -----------------
# Logging Setup
# -----------------
os.makedirs("logs", exist_ok=True)
os.makedirs("artifacts", exist_ok=True)

agent_logger = logging.getLogger("semantic_kernel.agents")
agent_logger.setLevel(logging.DEBUG)
agent_logger.propagate = False

agent_chat_handler = logging.FileHandler("logs/agent_chat.log", mode='w', encoding='utf-8')
agent_chat_handler.setLevel(logging.DEBUG)
chat_formatter = logging.Formatter('%(asctime)s - %(name)s:%(message)s')
agent_chat_handler.setFormatter(chat_formatter)
agent_logger.addHandler(agent_chat_handler)


def log_agent_message(name, content):
    agent_logger.info(f"Agent: {name}: {content}")


# -----------------
# Environment Setup
# -----------------
load_dotenv()
API_KEY = os.getenv("AZURE_OPENAI_KEY")
BASE_URL = os.getenv("URL")
API_VERSION = "2025-04-01-preview"


# -----------------
# Chat Service (matches your reference exactly)
# -----------------
chat_service = AzureChatCompletion(
    deployment_name="gpt-4.1",   # Must match your Azure deployment name
    api_key=API_KEY,
    endpoint=BASE_URL,
    api_version=API_VERSION,
)


# -----------------
# Helper Functions
# -----------------
def load_quality_instructions(file_path):
    full_path = os.path.join("specs", file_path)
    if not os.path.exists(full_path):
        return []
    with open(full_path, "r", encoding="utf-8") as f:
        return [line for line in f.readlines() if line.strip()]


def load_reports_instructions(file_path):
    full_path = os.path.join("specs", file_path)
    if not os.path.exists(full_path):
        return []
    with open(full_path, "r", encoding="utf-8") as f:
        return [line for line in f.readlines() if line.strip()]


def load_logs(file_path):
    full_path = os.path.join("logs", file_path)
    if not os.path.exists(full_path):
        return []
    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        return [line for line in f.readlines() if line.strip()]


def get_csv_name():
    data_dir = "data"
    if not os.path.exists(data_dir):
        print("Error: 'data' directory not found.")
        return None
    csv_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".csv")])
    if not csv_files:
        print("No CSV files found in the 'data' directory.")
        return None

    print("\nAvailable CSV files:")
    for i, fname in enumerate(csv_files, start=1):
        print(f"  {i}. {fname}")

    while True:
        try:
            choice = int(input("\nSelect a file by number: "))
            if 1 <= choice <= len(csv_files):
                selected = os.path.join(data_dir, csv_files[choice - 1])
                print(f"Selected: {selected}")
                return selected
        except ValueError:
            pass
        print("Invalid selection. Please try again.")


def load_csv_file(file_path):
    df = pd.read_csv(file_path)
    header = ", ".join(df.columns.tolist())
    data_list = df.values.flatten().tolist()
    data_str = ", ".join(str(item) for item in data_list)
    return f"Columns: {header}\nData: {data_str}"


def extract_code(text):
    """Strip markdown code fences from LLM output."""
    if "```python" in text:
        text = text.split("```python", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return text.strip()


class PythonExecutor:
    def __init__(self, max_attempts=3):
        self.max_attempts = max_attempts

    def run(self, code):
        try:
            exec(code, {})
            return True, None
        except Exception:
            return False, traceback.format_exc()


def save_final_report(report, path='artifacts/final_report.md'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Report saved to {path}")


# -----------------
# Agent Instructions
# -----------------
data_quality_instructions = ''.join(load_quality_instructions("Data_Quality_Instructions.txt"))
report_instructions = ''.join(load_reports_instructions("Report_Instructions.txt"))

AGENT_CONFIG = {
    "PythonExecutorAgent": {
        "description": "Generates runnable Python code for data visualization using matplotlib.",
        "instructions": (
            "You are a Python Code Generator specializing in data visualization.\n\n"
            "Rules:\n"
            "- Use matplotlib to create a single line chart.\n"
            "- Plot ORIGINAL data as a blue line (label='Original').\n"
            "- Plot CLEANED data as a green line (label='Cleaned').\n"
            "- Add title, axis labels, and legend.\n"
            "- Ensure output dir exists: os.makedirs('artifacts', exist_ok=True)\n"
            "- Save to 'artifacts/data_visualization.png'.\n"
            "- Include ALL necessary imports at the top.\n"
            "- Output ONLY raw executable Python code.\n"
            "- No explanations, comments, markdown fences, or prose."
        ),
    },
    "DataCleaning": {
        "description": "Cleans and preprocesses raw datasets by removing outliers and handling missing values.",
        "instructions": (
            "You are a Data Cleaning Assistant.\n\n"
            "Process:\n"
            "1. Present your CLEANING PLAN: describe issues and fixes.\n"
            "2. Perform cleaning: parse dates, remove outliers (IQR method), handle missing values.\n"
            "3. Final output must be ONLY the cleaned data, no additional commentary."
        ),
    },
    "DataStatistics": {
        "description": "Calculates comprehensive descriptive statistics on datasets.",
        "instructions": (
            "You are a Data Statistics Assistant.\n\n"
            "Calculate: Count, Mean, Median, Mode, Std Dev, Variance, Min, Max, Range, "
            "Q1, Q3, IQR, Skewness, Kurtosis.\n\n"
            "Output ONLY the statistical description. No commentary."
        ),
    },
    "AnalysisChecker": {
        "description": "Validates data analysis quality and ensures outliers were removed before statistics.",
        "instructions": (
            "You are a Data Validation Auditor.\n\n"
            "Check:\n"
            "1. Outliers were removed BEFORE statistics were calculated.\n"
            "2. Cleaning steps were appropriate.\n"
            "3. Statistics are consistent with cleaned data.\n\n"
            f"Quality rules:\n{data_quality_instructions}\n\n"
            "If ALL checks pass, respond with 'APPROVED'. Otherwise describe issues."
        ),
    },
    "ReportGenerator": {
        "description": "Writes comprehensive markdown reports synthesizing the entire analysis workflow.",
        "instructions": (
            "You are a Report Generator.\n\n"
            "Synthesize the workflow into a markdown report covering:\n"
            "- Data Cleaning, Statistical Analysis, Validation, Visualization.\n\n"
            f"Follow this structure:\n{report_instructions}\n\n"
            "Use proper markdown with headers, tables, and bullet points."
        ),
    },
    "ReportChecker": {
        "description": "Validates report completeness and accuracy against structural requirements.",
        "instructions": (
            "You are a Report Validation Auditor.\n\n"
            f"Validate against:\n{report_instructions}\n\n"
            "Check: all sections present, accurate reflection of analysis, no missing info.\n"
            "If ALL requirements met, respond with 'APPROVED'. Otherwise describe issues."
        ),
    },
}


# -----------------
# Agent Instantiation (matches reference pattern — no kernel, no execution_settings)
# -----------------
python_agent = ChatCompletionAgent(
    name="PythonExecutorAgent",
    description=AGENT_CONFIG["PythonExecutorAgent"]["description"],
    instructions=AGENT_CONFIG["PythonExecutorAgent"]["instructions"],
    service=chat_service,
)

cleaning_agent = ChatCompletionAgent(
    name="DataCleaning",
    description=AGENT_CONFIG["DataCleaning"]["description"],
    instructions=AGENT_CONFIG["DataCleaning"]["instructions"],
    service=chat_service,
)

stats_agent = ChatCompletionAgent(
    name="DataStatistics",
    description=AGENT_CONFIG["DataStatistics"]["description"],
    instructions=AGENT_CONFIG["DataStatistics"]["instructions"],
    service=chat_service,
)

checker_agent = ChatCompletionAgent(
    name="AnalysisChecker",
    description=AGENT_CONFIG["AnalysisChecker"]["description"],
    instructions=AGENT_CONFIG["AnalysisChecker"]["instructions"],
    service=chat_service,
)

report_agent = ChatCompletionAgent(
    name="ReportGenerator",
    description=AGENT_CONFIG["ReportGenerator"]["description"],
    instructions=AGENT_CONFIG["ReportGenerator"]["instructions"],
    service=chat_service,
)

report_checker_agent = ChatCompletionAgent(
    name="ReportChecker",
    description=AGENT_CONFIG["ReportChecker"]["description"],
    instructions=AGENT_CONFIG["ReportChecker"]["instructions"],
    service=chat_service,
)


# -----------------
# Main Workflow
# -----------------
async def main():
    runtime = InProcessRuntime()
    runtime.start()

    # ===================================================================
    # STEP 1 — Load the user-selected CSV data
    # ===================================================================
    csv_path = get_csv_name()
    if not csv_path:
        print("No file selected. Exiting.")
        await runtime.stop_when_idle()
        return

    csv_data = load_csv_file(csv_path)

    print(f"\n{'='*60}")
    print("PHASE 1: DATA ANALYSIS  (DataCleaning → DataStatistics → AnalysisChecker)")
    print(f"{'='*60}")

    # ===================================================================
    # STEP 2 — Analysis orchestration (clean → stats → validate)
    # ===================================================================
    analysis_history = []

    def analysis_callback(msg):
        analysis_history.append(msg)
        log_agent_message(msg.name, msg.content)
        print(f"\n  [{msg.name}]: {msg.content[:300]}{'...' if len(msg.content) > 300 else ''}")

    analysis_manager = StandardMagenticManager(chat_completion_service=chat_service)
    analysis_orch = MagenticOrchestration(
        members=[cleaning_agent, stats_agent, checker_agent],
        manager=analysis_manager,
        agent_response_callback=analysis_callback,
    )

    analysis_prompt = (
        "Perform a complete data analysis on the following raw CSV data.\n\n"
        f"{csv_data}\n\n"
        "Workflow:\n"
        "1. DataCleaning  — Clean the data: parse dates, remove outliers (IQR), handle missing values.\n"
        "2. DataStatistics — Calculate descriptive statistics on the CLEANED data.\n"
        "3. AnalysisChecker — Validate that outliers were removed before statistics were calculated.\n"
        "Each agent should complete its task fully before the next agent begins."
    )

    analysis_result = await analysis_orch.invoke(task=analysis_prompt, runtime=runtime)
    analysis_output = str(await analysis_result.get())

    print(f"\n{'='*60}")
    print("Analysis phase complete.")
    print(f"{'='*60}")

    # ===================================================================
    # STEP 3 — Human approval
    # ===================================================================
    approval = input("\nDo you approve the analysis results? (yes/no): ").strip().lower()
    if approval != "yes":
        print("❌ Analysis not approved. Workflow terminated.")
        await runtime.stop_when_idle()
        return
    print("✅ Approved. Proceeding...\n")

    # ===================================================================
    # STEP 4 — Extract & save cleaned data
    # ===================================================================
    cleaned_data = None
    for msg in reversed(analysis_history):
        if msg.name == "DataCleaning":
            cleaned_data = msg.content
            break

    if not cleaned_data:
        cleaned_data = analysis_output  # fallback

    with open("data-cleaned.json", "w", encoding="utf-8") as f:
        json.dump({"cleaned_data": cleaned_data}, f, indent=2)
    print("✅ Cleaned data saved to data-cleaned.json")

    # ===================================================================
    # STEP 5 — Code generation (direct agent invoke, same as reference)
    # ===================================================================
    print(f"\n{'='*60}")
    print("PHASE 2: VISUALIZATION CODE GENERATION  (PythonExecutorAgent)")
    print(f"{'='*60}")

    code_prompt = (
        "Generate Python code to visualize the following data.\n\n"
        f"ORIGINAL data (plot as BLUE line labeled 'Original'):\n{csv_data}\n\n"
        f"CLEANED data (plot as GREEN line labeled 'Cleaned'):\n{cleaned_data}\n\n"
        "Requirements:\n"
        "- Use matplotlib. Both lines on one chart with a legend.\n"
        "- os.makedirs('artifacts', exist_ok=True)\n"
        "- Save the plot to 'artifacts/data_visualization.png'.\n"
        "- Output ONLY raw executable Python code, no markdown fences."
    )

    generated_code = ""
    async for msg in python_agent.invoke(code_prompt):
        generated_code = str(msg.content)
        log_agent_message("PythonExecutorAgent", generated_code[:500])

    generated_code = extract_code(generated_code)
    print(f"  Code generated ({len(generated_code)} chars)")

    # ===================================================================
    # STEP 6 — Execute with retry loop
    # ===================================================================
    print(f"\n{'='*60}")
    print("PHASE 3: CODE EXECUTION  (retry up to 3 times)")
    print(f"{'='*60}")

    executor = PythonExecutor(max_attempts=3)
    success = False

    for attempt in range(executor.max_attempts):
        print(f"\n  Attempt {attempt + 1}/{executor.max_attempts}...")
        success, error = executor.run(generated_code)

        if success:
            print("  ✅ Code executed successfully!")
            break
        else:
            print(f"  ❌ Failed:\n{error}")
            if attempt < executor.max_attempts - 1:
                retry_prompt = (
                    f"The previous code failed with this error:\n\n{error}\n\n"
                    "Provide the COMPLETE corrected Python code. "
                    "Output ONLY raw executable code, no markdown fences."
                )
                async for msg in python_agent.invoke(retry_prompt):
                    generated_code = extract_code(str(msg.content))
                    log_agent_message("PythonExecutorAgent", f"Retry {attempt + 2}")
                print(f"  Fixed code received ({len(generated_code)} chars)")

    if not success:
        print("\n⚠️  Visualization code failed after all attempts. Continuing to report phase.")

    # ===================================================================
    # STEP 7 — Save working script
    # ===================================================================
    with open("artifacts/data_visualization_code.py", "w", encoding="utf-8") as f:
        f.write(generated_code)
    print("✅ Script saved to artifacts/data_visualization_code.py")

    # ===================================================================
    # STEP 8 — Report orchestration (generate → validate)
    # ===================================================================
    print(f"\n{'='*60}")
    print("PHASE 4: REPORT GENERATION  (ReportGenerator → ReportChecker)")
    print(f"{'='*60}")

    log_entries = load_logs("agent_chat.log")
    log_content = "\n".join(log_entries)

    report_prompt = (
        "Generate a comprehensive final markdown report for the data analysis workflow.\n\n"
        f"=== FULL AGENT INTERACTION LOG ===\n{log_content}\n=== END LOG ===\n\n"
        "The report must cover: data cleaning, statistical analysis, validation, "
        "and visualization. Reference the generated plot at 'artifacts/data_visualization.png'."
    )

    report_history = []

    def report_callback(msg):
        report_history.append(msg)
        log_agent_message(msg.name, msg.content[:500])
        print(f"\n  [{msg.name}]: {msg.content[:300]}{'...' if len(msg.content) > 300 else ''}")

    report_manager = StandardMagenticManager(chat_completion_service=chat_service)
    report_orch = MagenticOrchestration(
        members=[report_agent, report_checker_agent],
        manager=report_manager,
        agent_response_callback=report_callback,
    )

    report_result = await report_orch.invoke(task=report_prompt, runtime=runtime)
    report_output = str(await report_result.get())

    # ===================================================================
    # STEP 9 — Save final report
    # ===================================================================
    # Prefer the ReportGenerator's output over the manager's synthesis
    final_report = report_output
    for msg in reversed(report_history):
        if msg.name == "ReportGenerator":
            final_report = msg.content
            break

    save_final_report(final_report)

    # ===================================================================
    # Summary
    # ===================================================================
    print(f"\n{'='*60}")
    print("🎉 WORKFLOW COMPLETE — Deliverables:")
    print(f"{'='*60}")
    print("  1. data-cleaned.json                     ← Cleaned dataset (JSON)")
    print("  2. artifacts/data_visualization_code.py   ← Working Python script")
    print("  3. artifacts/data_visualization.png        ← Generated plot (PNG)")
    print("  4. artifacts/final_report.md               ← Final markdown report")
    print(f"{'='*60}\n")

    await runtime.stop_when_idle()


# -----------------
# Entry Point
# -----------------
if __name__ == "__main__":
    print("\n=== Starting Multi-Agent Data Analysis Workflow ===\n")
    asyncio.run(main())