# Reflective Report — Enhanced Banking Multi-Agent RAG System

**Student:** Akhil G. Gangwar  
**Course:** Azure Agentic AI — C4 Classroom  
**Date:** 12 July 2026  

---

## 1. Implementation Approach

### 1.1 Semantic Kernel Orchestration Design

The central design decision was how to coordinate the six specialised agents. I chose Semantic Kernel's `SequentialOrchestration` over a parallel or fan-out pattern for two reasons:

1. **Epistemic dependency**: Each downstream agent meaningfully depends on the upstream agent's output. The Fraud Analyst needs the Data Gatherer's transaction summary; the Risk Analyst needs the Fraud Analyst's risk rating. Sequential execution ensures context accumulates progressively.
2. **Auditability**: A sequential chain produces an ordered paper trail — each agent's contribution is timestamped and stored in `agent_contributions`. This is essential for regulatory traceability in banking.

The `SequentialOrchestration` abstraction in Semantic Kernel handles the message-passing between agents natively; I did not need to implement a custom routing layer, which simplified the codebase significantly.

### 1.2 Graceful Degradation Strategy

A core design principle was that the system should never fail completely due to an infrastructure dependency being unavailable. This was implemented at three layers:

- **Azure SQL unavailable** → `DataConnector.__init__` raises, caught in `EnhancedBankingSequentialOrchestration.__init__`, `self.data_connector` set to `None`, and three hardcoded sample profiles serve as fallback.
- **ChromaDB empty** → `_prepare_enhanced_context` returns a "No policy documents retrieved" string rather than crashing; agents still produce useful output from the customer profile alone.
- **Blob Storage empty** → `_load_enhanced_policies` calls `upload_sample_documents()` automatically, ensuring at least the five built-in policy files are always available.

This approach means the system can run in a pure "demo mode" with no Azure credentials other than the AI Foundry endpoint, which was invaluable during development.

### 1.3 Hybrid Search Implementation

The RAG pipeline uses ChromaDB's built-in embedding search augmented with keyword boosting (`+0.10` per matching query token found in the document). This hybrid approach was chosen because pure semantic search sometimes misses highly-specific banking terms (e.g., "DTI ratio", "BSA compliance") that are exact-string matches but may not rank highly on embedding distance alone. The keyword boost acts as a recall safety net without sacrificing semantic ranking.

---

## 2. Challenges Encountered and Solutions

### Challenge 1: Semantic Kernel API Evolution

**Problem:** The `SequentialOrchestration` and `InProcessRuntime` APIs changed substantially between Semantic Kernel 0.x and 1.x. Early documentation examples used deprecated patterns (e.g., `AgentGroupChat`) that no longer exist in SK 1.37.

**Solution:** Read the installed SDK source directly (`semantic_kernel/agents/`) rather than relying on online documentation. The correct import path is `from semantic_kernel.agents import ChatCompletionAgent, SequentialOrchestration` and the `InProcessRuntime` must be explicitly started with `runtime.start()` before invocation.

### Challenge 2: Async/Sync Boundary with ChromaDB

**Problem:** ChromaDB's Python client is synchronous, but the orchestration workflow is fully `async`. Calling `chroma_store.hybrid_search()` directly in an `async` function would block the event loop.

**Solution:** Wrapped all ChromaDB calls in `asyncio.to_thread()`, which runs the synchronous function in a thread-pool executor without blocking the event loop. This pattern also applies to `chunk_and_store_document()`.

### Challenge 3: Pydantic v2 / KernelBaseModel Compatibility

**Problem:** `KernelBaseModel` uses Pydantic v2 under the hood. Pydantic v2 does not support mutable default values like `datetime.now()` directly in field declarations — it raises a `PydanticSchemaGenerationError`.

**Solution:** Used `model_post_init` to set the `generated_at` field after model construction, and declared it as `Optional[datetime] = None` in the model body. This is the correct Pydantic v2 pattern for dynamic defaults.

### Challenge 4: Azure Security Classifier Blocking Inline Credentials

**Problem:** When scripting Azure resource creation, the Claude Code security classifier correctly flagged inline admin passwords and overly broad firewall rules (`0.0.0.0–255.255.255.255`) as policy violations.

**Solution:** This is a **correct** security block, not a false positive. The proper resolution for production is to use Azure Key Vault for secrets and limit firewall rules to specific known IP ranges. For the classroom project, the appropriate compromise is to create resources through the Azure Portal UI (where credentials are entered in a secure form field, not echoed to a shell) and restrict firewall rules to `AllowAzureServices` plus the specific developer machine IP.

---

## 3. Design Decisions and Trade-offs

| Decision | Alternative Considered | Rationale for Choice |
|----------|----------------------|----------------------|
| Sequential orchestration | Parallel fan-out | Context accumulation; auditability |
| ChromaDB (local) | Azure AI Search | Zero cost for student project; no additional Azure quota needed |
| Local blob simulator | Azure Blob Storage | Eliminates a dependency during development; trivial to swap |
| Hardcoded sample profiles | Pure SQL-only profiles | Enables demo mode without Azure SQL; reduces barrier to entry |
| `asyncio.to_thread` for ChromaDB | Synchronous wrapper | Keeps the entire orchestration layer properly async |
| `model_post_init` for timestamps | `default_factory` | Required for Pydantic v2 / KernelBaseModel compatibility |

---

## 4. System Strengths

1. **Zero-crash guarantee**: Three-tier fallback (SQL → sample profiles, Blob → local sim, ChromaDB → empty context) means the system always produces a report, even in degraded mode.
2. **Full observability**: Every agent interaction is logged with timestamps, duration, and content. The `processing_metrics` dict in every report provides per-agent timing for performance analysis.
3. **Policy-grounded responses**: The hybrid RAG search ensures agent recommendations are anchored to actual banking policy documents, not just LLM priors.
4. **Clean separation of concerns**: Infrastructure (connectors, ChromaDB, state) is entirely isolated from orchestration logic, making it easy to swap any component.

---

## 5. Suggestions for Improvement

### Suggestion 1: Parallel Sub-Task Execution Within the Sequential Pipeline

The current sequential pipeline runs each agent fully before starting the next. A significant latency improvement could be achieved by running the middle three agents (Fraud, Loan, Support) in parallel after the Data Gatherer completes, then passing all three results to the Risk Analyst. This would reduce total processing time from ~6×(agent latency) to ~3×(agent latency) for a typical query.

Implementation: Replace `SequentialOrchestration` with a custom orchestrator using `asyncio.gather` for the parallel segment.

### Suggestion 2: Persistent Customer Profile Cache with Invalidation

Currently, customer profiles are re-fetched from Azure SQL on every run of `enhanced_main()`. In production, customer data changes infrequently (daily at most). Implementing a Redis or Azure Cache for Redis layer with a 24-hour TTL and event-driven invalidation (triggered by new transactions) would eliminate the SQL round-trip for the majority of requests and improve latency by 0.5–2 seconds per analysis.

### Suggestion 3: Structured Agent Output Parsing

Agents currently return free-text markdown. A production system should enforce structured JSON output from each agent using Semantic Kernel's `OpenAI Structured Outputs` feature (available in GPT-4.1). This would allow downstream agents and the synthesis coordinator to reliably parse specific fields (e.g., `fraud_risk_rating`, `loan_eligibility_decision`) rather than relying on text extraction heuristics.

---

## 6. Lessons Learned

1. **Read the installed SDK, not the web docs** — SDK APIs evolve faster than documentation. Grepping the installed package source (`pip show semantic-kernel` → location) is the most reliable reference.

2. **Design for degradation from day one** — Adding fallback logic late is painful because it requires restructuring existing code. Designing every data dependency with an explicit fallback path at the start made the final implementation clean.

3. **Sequential agent output accumulation is a feature, not a limitation** — I initially considered parallel agents as "faster and better." In practice, the sequential pattern produced dramatically more coherent final reports because each agent had full context from all prior agents. The Synthesis Coordinator's output quality was visibly superior when it had Fraud + Loan + Support + Risk analysis to integrate.

4. **Pydantic v2 has important differences from v1** — Several patterns that work in Pydantic v1 (mutable defaults, `validator` decorators, `orm_mode`) require different approaches in v2. Understanding the v2 migration guide saved significant debugging time.

5. **Azure security controls are there for good reason** — The security classifier blocking the open firewall rule and inline password was initially frustrating, but upon reflection those are exactly the controls that prevent real incidents. Incorporating security best practices (Key Vault, scoped firewall rules, environment variables) from the start, rather than as a retrofit, is the professional standard.

---

## 7. Conclusion

This project produced a functioning multi-agent banking AI system that integrates Azure AI Foundry, Semantic Kernel orchestration, ChromaDB vector search, and Azure SQL data retrieval into a coherent sequential analysis pipeline. The most valuable technical insight was that sequential agent architectures, when designed with clear epistemic dependencies between agents, produce qualitatively better outputs than parallel architectures for complex, context-dependent analytical tasks. The most valuable engineering insight was that resilient fallback design and security-first credential handling are not optional extras — they are the foundation of trustworthy AI systems in regulated industries like banking.
