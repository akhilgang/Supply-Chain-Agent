# app/state.py - Agent State Machine
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class Phase(Enum):
    """Agent state machine phases for processing"""
    Init = "Init"
    ClarifyRequirements = "ClarifyRequirements"
    PlanTools = "PlanTools"
    ExecuteTools = "ExecuteTools"
    AnalyzeResults = "AnalyzeResults"
    ResolveIssues = "ResolveIssues"
    ProduceStructuredOutput = "ProduceStructuredOutput"
    Done = "Done"


class AgentState:
    """
    Manages agent execution state through workflow phases.

    The state machine tracks:
    - Current phase in the workflow
    - Session identification
    - Requirements and clarifications
    - Tool calls and results
    - Issues and resolutions
    - Structured output generation
    """

    def __init__(self):
        # Core state
        self.phase: Phase = Phase.Init
        self.session_id: str = self._generate_session_id()
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

        # Optional tracking (basic)
        self.destination: Optional[str] = None
        self.dates: Optional[str] = None
        self.card: Optional[str] = None

        # Requirements management
        self.requirements: Dict[str, Any] = {}
        self.required_fields: List[str] = []
        self.clarification_questions: List[str] = []

        # Tool execution tracking
        self.tools_called: List[str] = []
        self.tool_results: Dict[str, Any] = {}
        self.tool_errors: Dict[str, str] = {}

        # Analysis and validation
        self.analysis_results: Optional[Dict[str, Any]] = None
        self.data_completeness: float = 0.0
        self.validation_errors: List[str] = []

        # Issue resolution
        self.issues: List[str] = []
        self.resolution_attempts: List[str] = []
        self.resolved_issues: List[str] = []

        # Output generation
        self.structured_output: Optional[Dict[str, Any]] = None
        self.natural_language_summary: Optional[str] = None
        self.citations: List[str] = []

        # Context and metadata
        self.context: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        import uuid
        return f"session_{uuid.uuid4().hex[:8]}"

    def advance(self) -> bool:
        """
        Advance to the next phase in the state machine.

        Returns:
            True if advanced successfully, False if already at Done

        TODO: Implement phase advancement
        - Get list of phases from Phase enum
        - Find current phase index
        - Move to next phase if not at end
        - Update timestamp and return result
        """
        phases = list(Phase)
        current_index = phases.index(self.phase)

        if current_index < len(phases) - 1:
            self.phase = phases[current_index + 1]
            self.updated_at = datetime.now()
            return True

        # Already at the final phase (Done)
        return False

    def reset(self) -> None:
        """
        Reset the agent state to initial state.

        Reinitializes all tracking data, generates a new session id,
        and resets the phase back to Init.
        """
        self.__init__()

    def is_complete(self) -> bool:
        """Check if the agent process is complete"""
        return self.phase == Phase.Done

    # Requirements management methods
    def set_requirements(self, requirements: Dict[str, Any]) -> None:
        """Set the requirements dictionary"""
        self.requirements = requirements
        self.updated_at = datetime.now()

    def add_clarification_question(self, question: str) -> None:
        """Add a clarification question (prevents duplicates)"""
        if question not in self.clarification_questions:
            self.clarification_questions.append(question)
            self.updated_at = datetime.now()

    def mark_requirement_clarified(self, field: str) -> None:
        """Mark a required field as clarified (remove from required_fields)"""
        if field in self.required_fields:
            self.required_fields.remove(field)
            self.updated_at = datetime.now()

    # Tool execution methods
    def add_tool_call(self, tool_name: str, result: Any = None, error: str = None) -> None:
        """
        Add a tool call and its result/error.

        Args:
            tool_name: Name of the tool called
            result: Result from the tool (if successful)
            error: Error message (if failed)
        """
        if tool_name not in self.tools_called:
            self.tools_called.append(tool_name)

        if result is not None:
            self.tool_results[tool_name] = result

        if error is not None:
            self.tool_errors[tool_name] = error

        self.updated_at = datetime.now()

    # Analysis methods
    def set_analysis_results(self, results: Dict[str, Any]) -> None:
        """Set analysis results and calculate data completeness"""
        self.analysis_results = results
        self._calculate_data_completeness()
        self.updated_at = datetime.now()

    def _calculate_data_completeness(self) -> None:
        """Calculate data completeness based on required fields"""
        if not self.required_fields:
            self.data_completeness = 1.0
            return

        completed = sum(1 for field in self.required_fields if field in self.requirements)
        self.data_completeness = completed / len(self.required_fields)

    def is_data_complete(self, threshold: float = 0.8) -> bool:
        """Check if data completeness meets the threshold"""
        return self.data_completeness >= threshold

    # Issue management methods
    def add_issue(self, issue: str) -> None:
        """Add an issue to track"""
        if issue not in self.issues:
            self.issues.append(issue)
            self.updated_at = datetime.now()

    def add_resolution_attempt(self, attempt: str) -> None:
        """Add a resolution attempt"""
        self.resolution_attempts.append(attempt)
        self.updated_at = datetime.now()

    def resolve_issue(self, issue: str) -> None:
        """Mark an issue as resolved"""
        if issue in self.issues:
            self.issues.remove(issue)
            self.resolved_issues.append(issue)
            self.updated_at = datetime.now()

    def has_issues(self) -> bool:
        """Check if there are unresolved issues"""
        return len(self.issues) > 0

    # Output generation methods
    def set_structured_output(self, output: Dict[str, Any], summary: str = None) -> None:
        """Set the structured output and optional summary"""
        self.structured_output = output
        if summary:
            self.natural_language_summary = summary
        self.updated_at = datetime.now()

    def add_citation(self, citation: str) -> None:
        """Add a citation (prevents duplicates)"""
        if citation not in self.citations:
            self.citations.append(citation)
            self.updated_at = datetime.now()

    # Status and description methods
    def get_phase_description(self) -> str:
        """Get a human-readable description of the current phase"""
        descriptions = {
            Phase.Init: "Initialize session and capture user goal",
            Phase.ClarifyRequirements: "Ask targeted questions to gather required information",
            Phase.PlanTools: "Decide which tools to call and with what parameters",
            Phase.ExecuteTools: "Execute planned tools and collect results",
            Phase.AnalyzeResults: "Process tool outputs and validate data completeness",
            Phase.ResolveIssues: "Handle any problems or edge cases identified",
            Phase.ProduceStructuredOutput: "Generate Pydantic-validated JSON and natural language summary",
            Phase.Done: "Process complete"
        }
        return descriptions.get(self.phase, "Unknown phase")

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a comprehensive status summary"""
        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "phase_description": self.get_phase_description(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "requirements": self.requirements,
            "tools_called": self.tools_called,
            "issues": self.issues,
            "data_completeness": self.data_completeness,
            "has_structured_output": self.structured_output is not None,
            "citations_count": len(self.citations)
        }
