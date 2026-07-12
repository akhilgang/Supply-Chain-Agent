# Test Results — Enhanced Banking Multi-Agent RAG System

Run date: 2026-07-12  
Environment: Azure AI Foundry (GPT-4.1) + Azure SQL (`banking-db`) + ChromaDB (local)

---

## Test Suite: `python main_starter.py --test`

Full output: [test_run_20260712_193423.txt](test_run_20260712_193423.txt)

| Test | Customer | Query Type | Risk Score | Risk Tier | Agents | Time |
|------|----------|-----------|-----------|----------|--------|------|
| financial_planning | 12345 | Investment / retirement | 0.250 | LOW | 6/6 | ~38s |
| loan_application | 67890 | Home improvement loan | 0.470 | MEDIUM | 6/6 | ~38s |
| fraud_report | 11111 | Suspected fraud | 0.620 | HIGH | 6/6 | ~36s |
| credit_inquiry | 12345 | Credit limit increase | 0.250 | LOW | 6/6 | ~39s |
| account_management | 67890 | Moving abroad | 0.450 | MEDIUM | 6/6 | ~41s |

**Result: 5 passed, 0 failed**  
Average processing time: 38.4 s

---

## ChromaDB RAG Verification

Full output: [chromadb_verification.txt](chromadb_verification.txt)

### Collection document counts (post-ingestion)

| Collection | Documents |
|-----------|----------|
| fraud_detection | 15 |
| loan_policies | 15 |
| customer_support | 0 |
| risk_assessment | 0 |
| transaction_monitoring | 0 |
| compliance | 0 |
| **TOTAL** | **30** |

> Note: `determine_collection()` (provided in chroma_manager.py) routes documents
> based on keyword matching. The 5 sample policy files were routed to
> `fraud_detection` and `loan_policies`; other collections would be populated
> by uploading domain-specific documents named for those categories.

### Sample hybrid_search result (score = 0.888)
```
Query  : "loan eligibility credit score income requirements"
Source : loan_eligibility_framework.md  (collection: loan_policies)
Excerpt: # Loan Eligibility Framework
         ## Comprehensive Credit Assessment
         ### Income Requirements:
         | Tier | Minimum Income | Debt ...
```

---

## Azure SQL Verification

Full output: [azure_sql_verification.txt](azure_sql_verification.txt)

Connection to `banking-sql-rag1.database.windows.net / banking-db`: **OK**

| Customer | Income | Transactions retrieved |
|----------|--------|----------------------|
| 12345 | $75,000 | 4 (Salary, Mortgage, Investment, Utilities) |
| 67890 | $45,000 | 4 (Salary, Rent, Car Payment, Student Loan) |
| 11111 | $28,000 | 4 (Salary, Rent, Credit Card, Overdraft Fee) |

---

## Runtime Log

Full log: [run_log.txt](run_log.txt)  
Key log entries showing all three services exercised:

```
INFO - Azure SQL connection verified successfully.
INFO - Indexed 'fraud_detection_policy_v2.md' → collection 'fraud_detection' (1 chunks)
INFO - Indexed 'loan_eligibility_framework.md' → collection 'loan_policies' (1 chunks)
INFO - Indexed 'customer_support_protocols.md' → collection 'fraud_detection' (1 chunks)
INFO - Indexed 'risk_assessment_framework.md' → collection 'loan_policies' (2 chunks)
INFO - Indexed 'transaction_monitoring_guide.md' → collection 'fraud_detection' (1 chunks)
INFO - Banking documents indexed in ChromaDB.
```
