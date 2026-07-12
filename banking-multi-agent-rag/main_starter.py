import asyncio
import os
import uuid
import logging
import pyodbc
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent, SequentialOrchestration
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.kernel_pydantic import KernelBaseModel
from semantic_kernel.contents import ChatMessageContent
from rag_utils import extract_banking_policies, create_semantic_kernel_context, extract_text_from_bytes
from blob_connector import BlobStorageConnector
from chroma_manager import ChromaDBManager
from shared_state import SharedState
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def setup_logging():
    """Setup logging with unique file for each run"""
    if not os.path.exists("logs"):
        os.makedirs("logs")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/banking_analysis_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, mode='w', encoding='utf-8'),
        ]
    )

    print(f"Logger started. Log file: {log_filename}")
    return log_filename


class DataConnector:
    """Azure SQL Database connectivity for customer financial data."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv("AZURE_SQL_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError("AZURE_SQL_CONNECTION_STRING is not set in environment variables.")
        self._test_connection()

    def _test_connection(self):
        """Verify the database is reachable on startup."""
        try:
            with self.get_db_connection() as conn:
                conn.execute("SELECT 1")
            logger.info("Azure SQL connection verified successfully.")
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise

    async def fetch_income(self, customer_id: str) -> Optional[float]:
        """Return the latest income value recorded for a customer."""
        await asyncio.sleep(0)  # yield to event loop
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT TOP 1 income FROM transactions "
                    "WHERE customer_id = ? AND income IS NOT NULL "
                    "ORDER BY ts DESC",
                    customer_id,
                )
                row = cursor.fetchone()
                return float(row[0]) if row else None
        except Exception as e:
            logger.error(f"fetch_income failed for {customer_id}: {e}")
            return None

    async def fetch_transactions(self, customer_id: str) -> List[Dict]:
        """Return all transactions for a customer as a list of dicts."""
        await asyncio.sleep(0)
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT transaction_id, customer_id, income, amount, ts, description "
                    "FROM transactions WHERE customer_id = ? ORDER BY ts DESC",
                    customer_id,
                )
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"fetch_transactions failed for {customer_id}: {e}")
            return []

    @contextmanager
    def get_db_connection(self):
        """Context manager that opens and cleanly closes a pyodbc connection.

        Falls back from ODBC Driver 18 → ODBC Driver 17 → built-in SQL Server
        driver so the code works regardless of which driver is installed.
        """
        conn = None
        conn_str = self.connection_string
        # Try substituting available drivers if the configured one is missing
        available = [d for d in pyodbc.drivers() if "SQL Server" in d]
        for driver in available:
            candidate = conn_str
            for old in ("{ODBC Driver 18 for SQL Server}",
                        "{ODBC Driver 17 for SQL Server}",
                        "{SQL Server}"):
                candidate = candidate.replace(old, "{" + driver + "}")
            try:
                conn = pyodbc.connect(candidate)
                break
            except pyodbc.Error:
                continue
        if conn is None:
            raise pyodbc.Error("No compatible SQL Server ODBC driver found.")
        try:
            yield conn
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class EnhancedBankingReport(KernelBaseModel):
    """Comprehensive banking analysis report produced by the multi-agent system."""

    report_id: str = ""
    customer_id: str = ""
    query: str = ""
    summary: str = ""
    key_findings: List[str] = []
    risk_assessment: str = "medium"
    risk_score: float = 0.5
    recommendations: List[str] = []
    actions_taken: List[str] = []
    policy_references: List[str] = []
    agent_contributions: Dict[str, Any] = {}
    processing_metrics: Dict[str, Any] = {}
    generated_by: str = "EnhancedBankingOrchestration"
    generated_at: datetime = None

    def model_post_init(self, __context: Any) -> None:
        if self.generated_at is None:
            object.__setattr__(self, "generated_at", datetime.now())


class CustomerProfile(KernelBaseModel):
    """Customer financial profile used by all banking agents."""

    customer_id: str = ""
    income: float = 0.0
    credit_score: int = 0
    account_type: str = "standard"
    customer_since: str = ""
    risk_tier: str = "medium"
    recent_transactions: List[Dict[str, Any]] = []
    banking_products: List[str] = []
    last_review_date: str = ""

    @property
    def tenure_years(self) -> float:
        """Years since the customer opened their account."""
        if not self.customer_since:
            return 0.0
        try:
            since = datetime.strptime(self.customer_since, "%Y-%m-%d")
            return (datetime.now() - since).days / 365.25
        except ValueError:
            return 0.0

    @property
    def total_monthly_obligations(self) -> float:
        """Sum of debit transactions in the most-recent month."""
        if not self.recent_transactions:
            return 0.0
        debits = [
            abs(float(t.get("amount", 0)))
            for t in self.recent_transactions
            if float(t.get("amount", 0)) < 0
        ]
        return sum(debits)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

class EnhancedBankingSequentialOrchestration:
    """Enhanced banking system coordinating six specialized AI agents."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.blob_connector = BlobStorageConnector()
        self.chroma_store = ChromaDBManager()
        self.shared_state = SharedState()

        # Azure SQL – fall back gracefully so local/demo mode still works
        try:
            self.data_connector = DataConnector()
        except Exception as e:
            self.logger.warning(f"DataConnector unavailable, using sample data: {e}")
            self.data_connector = None

        # Azure AI Foundry kernel
        self.kernel = Kernel()
        self.kernel.add_service(
            AzureChatCompletion(
                service_id="enhanced_banking_chat",
                deployment_name=os.environ["AZURE_TEXTGENERATOR_DEPLOYMENT_NAME"],
                endpoint=os.environ["AZURE_TEXTGENERATOR_DEPLOYMENT_ENDPOINT"],
                api_key=os.environ["AZURE_TEXTGENERATOR_DEPLOYMENT_KEY"],
            )
        )

        self.banking_policies = self._load_enhanced_policies()
        self.customer_profiles: Dict[str, CustomerProfile] = {}

        self.performance_metrics = {
            "total_requests": 0,
            "successful_analyses": 0,
            "average_processing_time": 0.0,
            "agent_performance": {},
        }

    # ------------------------------------------------------------------
    # Policy & document loading
    # ------------------------------------------------------------------

    def _load_enhanced_policies(self) -> Dict[str, Any]:
        """Load banking policies from Blob storage and parse them."""
        try:
            if not self.blob_connector.list_documents():
                self.blob_connector.upload_sample_documents()

            enhanced_docs = []
            for doc_name in self.blob_connector.list_documents():
                content = self.blob_connector.get_document_content(doc_name)
                metadata = self.blob_connector.get_document_metadata(doc_name)
                doc_type = metadata.get("type", "general")
                enhanced_docs.append({
                    "filename": doc_name,
                    "id": f"{doc_type}_{doc_name}",
                    "meta": {
                        **metadata,
                        "priority": "high" if doc_type in ("fraud", "risk") else "medium",
                        "review_frequency": "quarterly" if doc_type in ("fraud", "compliance") else "annually",
                    },
                    "text": content,
                })

            policies = extract_banking_policies(enhanced_docs)
            self.logger.info(f"Loaded {len(enhanced_docs)} banking policy documents.")
            return policies
        except Exception as e:
            self.logger.error(f"Could not load enhanced banking policies: {e}")
            return {}

    async def load_enhanced_documents(self) -> None:
        """Push all Blob documents into ChromaDB for semantic search."""
        try:
            for doc_name in self.blob_connector.list_documents():
                raw = self.blob_connector.get_document_content(doc_name)
                if not raw:
                    continue
                # Convert raw content to plain text (handles PDF, DOCX, markdown)
                if isinstance(raw, bytes):
                    content = extract_text_from_bytes(raw, doc_name)
                else:
                    # BlobStorageConnector returns str for text files;
                    # for PDF/DOCX bytes stored as str, re-encode and parse
                    content = extract_text_from_bytes(raw.encode("utf-8", errors="replace"), doc_name) \
                              if doc_name.lower().endswith((".pdf", ".docx", ".doc")) \
                              else raw
                if not content:
                    self.logger.warning(f"Could not extract text from '{doc_name}', skipping.")
                    continue
                collection_type = self.chroma_store.determine_collection(doc_name, content)
                chunks_stored = await self.chroma_store.chunk_and_store_document(
                    doc_name, content, collection_type
                )
                self.logger.info(
                    f"Indexed '{doc_name}' → collection '{collection_type}' ({chunks_stored} chunks)"
                )
            self.logger.info("Banking documents indexed in ChromaDB.")
        except Exception as e:
            self.logger.warning(f"ChromaDB indexing partially failed: {e}")

    # ------------------------------------------------------------------
    # Customer profile loading
    # ------------------------------------------------------------------

    async def _load_customer_profiles(self) -> Dict[str, CustomerProfile]:
        """Load customer profiles from Azure SQL; fall back to sample data."""
        sample_profiles: Dict[str, CustomerProfile] = {
            "12345": CustomerProfile(
                customer_id="12345",
                income=75000.0,
                credit_score=780,
                account_type="premium_plus",
                customer_since="2019-05-15",
                risk_tier="low",
                banking_products=["checking", "savings", "mortgage", "investment", "credit_card"],
                last_review_date="2024-01-10",
            ),
            "67890": CustomerProfile(
                customer_id="67890",
                income=45000.0,
                credit_score=640,
                account_type="standard",
                customer_since="2021-03-20",
                risk_tier="medium",
                banking_products=["checking", "savings", "credit_card"],
                last_review_date="2024-06-01",
            ),
            "11111": CustomerProfile(
                customer_id="11111",
                income=28000.0,
                credit_score=520,
                account_type="basic",
                customer_since="2023-01-05",
                risk_tier="high",
                banking_products=["checking"],
                last_review_date="2024-09-15",
            ),
        }

        if self.data_connector is None:
            self.logger.info("Using sample profiles (no SQL connection).")
            return sample_profiles

        profiles: Dict[str, CustomerProfile] = {}
        for cid, base_profile in sample_profiles.items():
            try:
                income = await self.data_connector.fetch_income(cid)
                transactions = await self.data_connector.fetch_transactions(cid)

                profiles[cid] = CustomerProfile(
                    customer_id=cid,
                    income=income if income is not None else base_profile.income,
                    credit_score=base_profile.credit_score,
                    account_type=base_profile.account_type,
                    customer_since=base_profile.customer_since,
                    risk_tier=base_profile.risk_tier,
                    recent_transactions=transactions,
                    banking_products=base_profile.banking_products,
                    last_review_date=base_profile.last_review_date,
                )
            except Exception as e:
                self.logger.warning(f"SQL fetch failed for {cid}, using sample: {e}")
                profiles[cid] = base_profile

        return profiles

    # ------------------------------------------------------------------
    # Agent definitions
    # ------------------------------------------------------------------

    def create_enhanced_agents(self) -> List[ChatCompletionAgent]:
        """Create six specialized banking agents with domain-specific instructions."""

        service = self.kernel.get_service("enhanced_banking_chat")

        data_agent = ChatCompletionAgent(
            name="Enhanced_Data_Gatherer",
            instructions="""You are a Senior Banking Data Analyst specializing in comprehensive customer financial profiling.

Your responsibilities:
1. Analyze customer transaction history for patterns: recurring income, regular debits, irregular activity.
2. Assess data completeness and quality; flag missing or inconsistent records.
3. Calculate key financial metrics: monthly cash flow, debt service ratio, savings rate.
4. Cross-reference customer data against retrieved policy documents.
5. Summarize customer financial standing in structured form for downstream agents.

Output format:
- Customer Summary: brief financial snapshot
- Data Quality: completeness rating and any gaps
- Key Metrics: income, obligations, net cash flow
- Policy Alignment: which policies apply to this customer's profile
- Handoff Notes: what the fraud and loan analysts should focus on
""",
            service=service,
        )

        fraud_agent = ChatCompletionAgent(
            name="Enhanced_Fraud_Analyst",
            instructions="""You are a Chief Fraud Intelligence Officer with expertise in real-time transaction monitoring.

Your responsibilities:
1. Identify anomalous transaction patterns: velocity spikes, unusual amounts, off-hours activity.
2. Assess account takeover and social-engineering risk indicators.
3. Cross-reference against fraud detection policies retrieved from the knowledge base.
4. Assign a fraud risk rating: LOW / MEDIUM / HIGH / CRITICAL with supporting evidence.
5. Recommend immediate mitigation actions if elevated risk is detected.

Output format:
- Fraud Risk Rating: LOW | MEDIUM | HIGH | CRITICAL
- Detected Indicators: bulleted list of suspicious signals (or "None detected")
- Policy Violations: any breaches of fraud detection thresholds
- Recommended Actions: immediate steps if risk > LOW
- Confidence Level: percentage certainty in the assessment
""",
            service=service,
        )

        loan_agent = ChatCompletionAgent(
            name="Enhanced_Loan_Analyst",
            instructions="""You are a Senior Credit Risk Officer and Loan Underwriting Specialist.

Your responsibilities:
1. Evaluate loan eligibility against policy-defined income, credit score, and DTI thresholds.
2. Assess creditworthiness using the 5 Cs: Character, Capacity, Capital, Collateral, Conditions.
3. Identify appropriate loan products based on customer profile and query.
4. Calculate maximum loan amounts and realistic repayment schedules.
5. Note any policy-driven restrictions or required documentation.

Output format:
- Eligibility Decision: ELIGIBLE | CONDITIONALLY ELIGIBLE | NOT ELIGIBLE
- Credit Assessment: credit score band, DTI ratio, income adequacy
- Recommended Products: ranked list with rationale
- Loan Parameters: suggested amount range, term, indicative rate
- Conditions / Exceptions: any special requirements or flags
""",
            service=service,
        )

        support_agent = ChatCompletionAgent(
            name="Enhanced_Support_Specialist",
            instructions="""You are a Customer Experience Director and Banking Relationship Manager.

Your responsibilities:
1. Map the customer journey and identify service pain points from their interaction history.
2. Apply customer support protocols to determine optimal resolution paths.
3. Identify proactive outreach opportunities to improve satisfaction and retention.
4. Recommend relevant self-service features, digital tools, or branch services.
5. Ensure all communications are compliant, empathetic, and brand-consistent.

Output format:
- Customer Experience Rating: EXCELLENT | GOOD | NEEDS IMPROVEMENT | AT RISK
- Identified Issues: current or potential service gaps
- Resolution Actions: step-by-step support plan
- Retention Opportunities: personalised engagement suggestions
- Escalation Triggers: conditions that require human intervention
""",
            service=service,
        )

        risk_agent = ChatCompletionAgent(
            name="Enhanced_Risk_Analyst",
            instructions="""You are an Enterprise Risk Management Director with regulatory compliance expertise.

Your responsibilities:
1. Consolidate fraud, credit, and operational risk signals into a unified risk profile.
2. Verify compliance with banking regulations: AML, KYC, BSA, GDPR where applicable.
3. Apply the risk assessment framework from policy documents to calculate an overall risk score.
4. Categorize the customer into a risk tier: LOW / MEDIUM / HIGH / CRITICAL.
5. Define a monitoring plan and escalation thresholds for ongoing oversight.

Output format:
- Overall Risk Score: 0.0 – 1.0 (lower is safer)
- Risk Tier: LOW | MEDIUM | HIGH | CRITICAL
- Compliance Status: COMPLIANT | MINOR GAPS | NON-COMPLIANT
- Risk Drivers: top three factors influencing the score
- Monitoring Plan: frequency of reviews and trigger conditions
""",
            service=service,
        )

        synthesis_agent = ChatCompletionAgent(
            name="Enhanced_Synthesis_Coordinator",
            instructions="""You are the Chief Banking Intelligence Officer responsible for executive-grade synthesis.

Your responsibilities:
1. Integrate findings from all five specialist agents into a coherent executive report.
2. Resolve any conflicting assessments with reasoned adjudication.
3. Produce a prioritised action plan with clear ownership and timelines.
4. Highlight strategic opportunities: cross-sell, upsell, relationship deepening.
5. Ensure the final report is clear, actionable, and suitable for both relationship managers and compliance officers.

Output format:
- Executive Summary: 2–3 sentence overview
- Consolidated Risk Assessment: combined score and tier
- Top Findings: numbered list, highest impact first
- Strategic Recommendations: ranked action items with expected outcomes
- Next Review Date: suggested follow-up timeline
- Compliance Sign-off: statement confirming regulatory alignment
""",
            service=service,
        )

        return [data_agent, fraud_agent, loan_agent, support_agent, risk_agent, synthesis_agent]

    # ------------------------------------------------------------------
    # Main analysis workflow
    # ------------------------------------------------------------------

    async def run_enhanced_analysis(self, customer_id: str, customer_query: str) -> EnhancedBankingReport:
        """Execute the full six-agent sequential banking analysis."""
        start_time = datetime.now()
        self.performance_metrics["total_requests"] += 1

        if not self.customer_profiles:
            self.customer_profiles = await self._load_customer_profiles()

        await self.load_enhanced_documents()

        customer_profile = self.customer_profiles.get(
            customer_id, CustomerProfile(customer_id=customer_id)
        )

        search_results = await self.chroma_store.hybrid_search(
            customer_query,
            ["fraud_detection", "loan_policies", "customer_support",
             "risk_assessment", "transaction_monitoring", "compliance"],
            4,
        )

        banking_context = self._prepare_enhanced_context(customer_profile, search_results, customer_query)
        agents = self.create_enhanced_agents()
        agent_contributions: Dict[str, str] = {}
        agent_timings: Dict[str, float] = {}
        last_agent_time = [start_time]

        def enhanced_agent_callback(message: ChatMessageContent) -> None:
            now = datetime.now()
            name = message.name or "unknown"
            elapsed = (now - last_agent_time[0]).total_seconds()
            agent_contributions[name] = message.content
            agent_timings[name] = elapsed
            last_agent_time[0] = now
            print(f"\n{'=' * 60}")
            print(f"# Agent: {name}  ({elapsed:.1f}s)")
            print(f"{'=' * 60}")
            print(message.content)

        sequential_orchestration = SequentialOrchestration(
            members=agents,
            agent_response_callback=enhanced_agent_callback,
        )

        runtime = InProcessRuntime()
        try:
            runtime.start()

            orchestration_task = f"""
ENHANCED BANKING CUSTOMER ANALYSIS REQUEST
==========================================

{banking_context}

AGENT WORKFLOW INSTRUCTIONS:
1. Enhanced_Data_Gatherer: Profile the customer's financial position using the data above.
2. Enhanced_Fraud_Analyst: Assess fraud risk based on the data gathering output.
3. Enhanced_Loan_Analyst: Evaluate loan eligibility and product fit.
4. Enhanced_Support_Specialist: Identify service needs and retention opportunities.
5. Enhanced_Risk_Analyst: Consolidate all risk signals into an enterprise risk score.
6. Enhanced_Synthesis_Coordinator: Produce a final executive report integrating all analyses.

Each agent must reference the POLICY CONTEXT provided and build on prior agents' outputs.
"""

            orchestration_result = await sequential_orchestration.invoke(
                task=orchestration_task,
                runtime=runtime,
            )
            final_output = await asyncio.wait_for(orchestration_result.get(), timeout=300.0)

        except Exception as e:
            self.logger.error(f"Orchestration error: {e}")
            raise
        finally:
            await runtime.stop_when_idle()

        total_time = (datetime.now() - start_time).total_seconds()
        risk_score = self._calculate_enhanced_risk_score(customer_profile, search_results)
        risk_assessment = self._determine_risk_tier(risk_score)

        policy_refs = list({
            r.get("metadata", {}).get("filename", "")
            for r in search_results
            if r.get("metadata", {}).get("filename")
        })

        report = EnhancedBankingReport(
            report_id=f"enhanced_{uuid.uuid4().hex[:8]}",
            customer_id=customer_id,
            query=customer_query,
            summary=str(final_output),
            key_findings=self._generate_enhanced_findings(customer_profile, search_results, agent_contributions),
            risk_assessment=risk_assessment,
            risk_score=risk_score,
            recommendations=self._generate_enhanced_recommendations(customer_profile, risk_score),
            actions_taken=[
                "Six-agent sequential analysis completed",
                "Hybrid semantic + keyword policy search performed",
                "Enterprise risk assessment conducted",
                f"Processing time: {total_time:.1f}s",
            ],
            policy_references=policy_refs,
            agent_contributions=agent_contributions,
            processing_metrics={
                "total_processing_time_seconds": total_time,
                "agents_used": len(agents),
                "policies_referenced": len(policy_refs),
                "search_results_retrieved": len(search_results),
                "risk_score": risk_score,
                "agent_timings": agent_timings,
            },
            generated_by="EnhancedBankingSequentialOrchestration",
        )

        self.performance_metrics["successful_analyses"] += 1
        n = self.performance_metrics["successful_analyses"]
        prev_avg = self.performance_metrics["average_processing_time"]
        self.performance_metrics["average_processing_time"] = prev_avg + (total_time - prev_avg) / n

        self.shared_state.update_interaction(
            customer_id=customer_id,
            interaction_data={"type": "analysis", "query": customer_query, "risk_score": risk_score},
        )

        return report

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _determine_risk_tier(self, risk_score: float) -> str:
        """Map numeric risk score to a named tier."""
        if risk_score < 0.25:
            return "low"
        if risk_score < 0.50:
            return "medium"
        if risk_score < 0.75:
            return "high"
        return "critical"

    def _calculate_enhanced_risk_score(
        self,
        customer_profile: CustomerProfile,
        search_results: List[Dict],
    ) -> float:
        """Multi-factor risk score in [0, 1]; lower is safer."""
        score = 0.5  # neutral baseline

        # Income factor: higher income → lower risk
        if customer_profile.income >= 100_000:
            score -= 0.15
        elif customer_profile.income >= 60_000:
            score -= 0.10
        elif customer_profile.income >= 35_000:
            score -= 0.05
        elif customer_profile.income < 20_000:
            score += 0.10

        # Credit score factor
        if customer_profile.credit_score >= 750:
            score -= 0.15
        elif customer_profile.credit_score >= 680:
            score -= 0.08
        elif customer_profile.credit_score >= 620:
            score += 0.05
        elif customer_profile.credit_score < 580:
            score += 0.15

        # Customer tenure
        tenure = customer_profile.tenure_years
        if tenure >= 5:
            score -= 0.05
        elif tenure < 1:
            score += 0.05

        # Product breadth: more products → deeper relationship → lower risk
        n_products = len(customer_profile.banking_products)
        if n_products >= 4:
            score -= 0.05
        elif n_products <= 1:
            score += 0.05

        # Search result quality: if we found high-relevance policies, risk is better understood
        if search_results:
            avg_relevance = sum(r.get("final_score", 0) for r in search_results) / len(search_results)
            if avg_relevance > 0.7:
                score -= 0.03

        return round(max(0.0, min(1.0, score)), 3)

    def _generate_enhanced_findings(
        self,
        customer_profile: CustomerProfile,
        search_results: List[Dict],
        agent_contributions: Dict,
    ) -> List[str]:
        """Compile key findings from profile data and agent outputs."""
        findings: List[str] = []

        findings.append(
            f"Customer {customer_profile.customer_id} holds "
            f"{len(customer_profile.banking_products)} banking product(s): "
            f"{', '.join(customer_profile.banking_products) or 'none recorded'}."
        )

        if customer_profile.income > 0:
            findings.append(
                f"Annual income of ${customer_profile.income:,.0f} "
                f"({'above' if customer_profile.income >= 60_000 else 'below'} median threshold)."
            )

        if customer_profile.credit_score > 0:
            band = (
                "excellent" if customer_profile.credit_score >= 750
                else "good" if customer_profile.credit_score >= 680
                else "fair" if customer_profile.credit_score >= 620
                else "poor"
            )
            findings.append(f"Credit score {customer_profile.credit_score} ({band} band).")

        if customer_profile.recent_transactions:
            findings.append(
                f"{len(customer_profile.recent_transactions)} transactions retrieved from Azure SQL."
            )

        if search_results:
            top_docs = list({r.get("metadata", {}).get("filename", "") for r in search_results if r.get("metadata", {}).get("filename")})
            findings.append(f"Policy references retrieved: {', '.join(top_docs[:3])}.")

        for agent_name, contribution in agent_contributions.items():
            if contribution:
                # Extract the first non-empty line as a headline finding
                first_line = next(
                    (ln.strip() for ln in contribution.splitlines() if ln.strip()),
                    None,
                )
                if first_line:
                    findings.append(f"[{agent_name}] {first_line[:200]}")

        return findings

    def _generate_enhanced_recommendations(
        self,
        customer_profile: CustomerProfile,
        risk_score: float,
    ) -> List[str]:
        """Generate actionable recommendations based on risk tier and profile."""
        recs: List[str] = []

        tier = self._determine_risk_tier(risk_score)

        if tier == "low":
            recs.append("Consider proactive wealth management consultation to optimise investment portfolio.")
            recs.append("Offer premium loyalty rewards and relationship banking benefits.")
        elif tier == "medium":
            recs.append("Schedule a financial health review within the next 60 days.")
            recs.append("Explore debt consolidation products if DTI exceeds 35%.")
        elif tier == "high":
            recs.append("Initiate enhanced due diligence review immediately.")
            recs.append("Restrict high-value transactions pending risk officer approval.")
        else:
            recs.append("Escalate to fraud/compliance team for immediate manual review.")
            recs.append("Place account under enhanced monitoring; freeze credit lines if warranted.")

        if customer_profile.credit_score < 620:
            recs.append("Enrol customer in credit improvement programme with monthly progress reviews.")

        if len(customer_profile.banking_products) <= 2:
            recs.append("Present tailored cross-sell offers for savings and protection products.")

        if customer_profile.tenure_years < 1:
            recs.append("Assign a dedicated relationship manager for onboarding support.")

        recs.append("Re-assess risk profile in 90 days or following any significant account event.")

        return recs

    def _prepare_enhanced_context(
        self,
        customer_profile: CustomerProfile,
        search_results: List[Dict],
        customer_query: str,
    ) -> str:
        """Build the LLM context string from profile, policies, and query."""
        customer_context = f"""
CUSTOMER PROFILE:
  Customer ID   : {customer_profile.customer_id}
  Annual Income : ${customer_profile.income:,.2f}
  Credit Score  : {customer_profile.credit_score}
  Account Type  : {customer_profile.account_type}
  Customer Since: {customer_profile.customer_since}
  Risk Tier     : {customer_profile.risk_tier}
  Products      : {', '.join(customer_profile.banking_products) or 'none'}
  Last Review   : {customer_profile.last_review_date}
  Tenure (yrs)  : {customer_profile.tenure_years:.1f}
  Transactions  : {len(customer_profile.recent_transactions)} on record
"""

        policy_context_parts: List[str] = []
        for i, result in enumerate(search_results[:6], 1):
            doc = result.get("document", "")
            score = result.get("final_score", result.get("relevance_score", 0))
            fname = result.get("metadata", {}).get("filename", "unknown")
            policy_context_parts.append(
                f"[Policy {i} | source: {fname} | relevance: {score:.2f}]\n{doc[:600]}"
            )

        policy_context = "\n\n".join(policy_context_parts) if policy_context_parts else "No policy documents retrieved."

        policy_summary = create_semantic_kernel_context(self.banking_policies) if self.banking_policies else ""

        return f"""
CUSTOMER QUERY: {customer_query}

{customer_context}

RETRIEVED POLICY CONTEXT (hybrid RAG search):
{policy_context}

STRUCTURED POLICY SUMMARY:
{policy_summary}
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def enhanced_main():
    """Run comprehensive banking analysis test scenarios."""
    log_filename = setup_logging()

    print("ENHANCED BANKING MULTI-AGENT RAG SYSTEM")
    print("=" * 80)
    print(f"Log: {log_filename}")

    print("\nInitialising EnhancedBankingSequentialOrchestration...")
    system = EnhancedBankingSequentialOrchestration()

    test_scenarios = [
        {
            "customer_id": "12345",
            "query": "I need comprehensive financial planning including investments and retirement options.",
        },
        {
            "customer_id": "67890",
            "query": "I would like to apply for a home improvement loan of $25,000.",
        },
        {
            "customer_id": "11111",
            "query": "I noticed unusual charges on my account and want to report potential fraud.",
        },
    ]

    for scenario in test_scenarios:
        cid = scenario["customer_id"]
        query = scenario["query"]
        print(f"\n{'=' * 80}")
        print(f"SCENARIO  Customer: {cid}")
        print(f"Query   : {query}")
        print("=" * 80)
        try:
            report = await system.run_enhanced_analysis(cid, query)

            print(f"\n--- REPORT SUMMARY ---")
            print(f"Report ID    : {report.report_id}")
            print(f"Risk Score   : {report.risk_score:.3f}  ({report.risk_assessment.upper()})")
            print(f"Generated At : {report.generated_at}")
            print(f"\nKey Findings ({len(report.key_findings)}):")
            for f in report.key_findings:
                print(f"  • {f}")
            print(f"\nRecommendations ({len(report.recommendations)}):")
            for r in report.recommendations:
                print(f"  → {r}")
            print(f"\nProcessing Metrics:")
            for k, v in report.processing_metrics.items():
                print(f"  {k}: {v}")

        except Exception as e:
            print(f"[ERROR] Analysis failed for {cid}: {e}")


async def run_demo():
    """Single-scenario demo for quick smoke testing."""
    setup_logging()
    print("BANKING MULTI-AGENT RAG SYSTEM — DEMO MODE")
    print("=" * 80)
    system = EnhancedBankingSequentialOrchestration()
    report = await system.run_enhanced_analysis(
        "12345",
        "What investment and retirement products are best suited for my financial profile?",
    )
    print(f"\nReport ID   : {report.report_id}")
    print(f"Risk Score  : {report.risk_score:.3f} ({report.risk_assessment.upper()})")
    print(f"Summary     : {report.summary[:400]}...")
    return report


async def run_tests():
    """Validation test suite — checks all agents activate and report is well-formed."""
    setup_logging()
    print("BANKING MULTI-AGENT RAG SYSTEM — TEST MODE")
    print("=" * 80)
    system = EnhancedBankingSequentialOrchestration()

    test_cases = [
        ("12345", "I need comprehensive financial planning including investments and retirement options.", "financial_planning"),
        ("67890", "I would like to apply for a home improvement loan of $25,000.", "loan_application"),
        ("11111", "I noticed unusual charges on my account and want to report potential fraud.", "fraud_report"),
        ("12345", "What are my options for increasing my credit limit on my existing credit card?", "credit_inquiry"),
        ("67890", "I am moving abroad — what do I need to do with my accounts?", "account_management"),
    ]

    passed = 0
    failed = 0
    results = []

    for cid, query, test_name in test_cases:
        print(f"\n[TEST] {test_name} | Customer: {cid}")
        print(f"       Query: {query}")
        try:
            report = await system.run_enhanced_analysis(cid, query)

            # Validation checks
            assert report.report_id.startswith("enhanced_"), "report_id format invalid"
            assert report.customer_id == cid, "customer_id mismatch"
            assert 0.0 <= report.risk_score <= 1.0, "risk_score out of range"
            assert report.risk_assessment in ("low", "medium", "high", "critical"), "invalid risk tier"
            assert len(report.key_findings) > 0, "no key findings"
            assert len(report.recommendations) > 0, "no recommendations"
            assert report.processing_metrics.get("agents_used", 0) == 6, "not all 6 agents ran"

            print(f"       [PASS] risk={report.risk_score:.3f} ({report.risk_assessment}), "
                  f"findings={len(report.key_findings)}, "
                  f"agents={report.processing_metrics.get('agents_used')}, "
                  f"time={report.processing_metrics.get('total_processing_time_seconds', 0):.1f}s")
            passed += 1
            results.append({"test": test_name, "status": "PASS", "risk_score": report.risk_score,
                             "risk_tier": report.risk_assessment,
                             "agents": report.processing_metrics.get("agents_used"),
                             "findings": len(report.key_findings),
                             "time_s": report.processing_metrics.get("total_processing_time_seconds", 0)})
        except Exception as e:
            print(f"       [FAIL] {e}")
            failed += 1
            results.append({"test": test_name, "status": "FAIL", "error": str(e)})

    print(f"\n{'=' * 80}")
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"{'=' * 80}")
    print(f"\nSystem Performance Metrics:")
    for k, v in system.performance_metrics.items():
        if k != "agent_performance":
            print(f"  {k}: {v}")
    return results


async def run_all():
    """Run both demo and full test suite."""
    await run_demo()
    await run_tests()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced Banking Multi-Agent RAG System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_starter.py              # run all three demo scenarios
  python main_starter.py --demo       # single quick smoke test
  python main_starter.py --test       # full 5-scenario validation suite
  python main_starter.py --all        # demo + test suite
        """,
    )
    parser.add_argument("--demo", action="store_true", help="Run single demo scenario")
    parser.add_argument("--test", action="store_true", help="Run full validation test suite")
    parser.add_argument("--all",  action="store_true", help="Run demo then full test suite")

    args = parser.parse_args()

    if args.demo:
        asyncio.run(run_demo())
    elif args.test:
        asyncio.run(run_tests())
    elif args.all:
        asyncio.run(run_all())
    else:
        asyncio.run(enhanced_main())
