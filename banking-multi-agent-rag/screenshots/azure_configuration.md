# Azure Services Configuration Evidence

Generated: 2026-07-12 via az CLI

## Azure AI Foundry
- Resource  : demo-kernel
- Kind      : AIServices
- SKU       : S0
- Endpoint  : https://demo-kernel.cognitiveservices.azure.com/
- Location  : eastus

### Model Deployments
- text-embedding-3-small         model=text-embedding-3-small  version=1  capacity=1425
- gpt-4.1                        model=gpt-4.1  version=2025-04-14  capacity=10

## Azure SQL Database
- Server    : banking-sql-rag1.database.windows.net
- Admin     : sqladmin
- Location  : westus
- Database  : banking-db  status=Online  tier=Basic

### Firewall Rules
- AllowAzureServices         0.0.0.0 – 0.0.0.0
- AllowDevMachine            101.0.63.83 – 101.0.63.83

## Azure Blob Storage
- Account   : bankingrag851032
- SKU       : Standard_LRS
- Location  : westus
- Container : banking-policies
