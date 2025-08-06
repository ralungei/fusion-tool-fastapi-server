# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI server that provides REST API endpoints for interacting with Oracle Fusion Cloud ERP applications. It provides three main procurement endpoints:

- Product search and listing retrieval
- Supplier detail retrieval  
- Purchase requisition submission

## Development Commands

### Running the Development Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Production Server
```bash
python main.py
```

### Running Tests
```bash
python test_fusion.py
```

### Installing Dependencies
```bash
pip install fastapi uvicorn httpx python-dotenv pydantic
```

## Environment Configuration

The application requires three environment variables in a `.env` file:
- `FUSION_AUTH_READ` - Basic auth header for read operations
- `FUSION_AUTH_WRITE` - Basic auth header for write operations  
- `FUSION_USER_ID` - Oracle Fusion user ID for operations

Copy `.env.example` to `.env` and configure with actual Oracle Fusion credentials.

## Architecture

### Core Components

**main.py** - FastAPI application file containing:
- FastAPI server setup and configuration
- Three REST API endpoints: `/find_matching_listings`, `/retrieve_supplier_detail`, `/submit_purchase_requisition`
- Pydantic request models for data validation
- Error handling and response formatting

**services.py** - Business logic and Oracle Fusion API integration containing:
- Oracle Fusion API integration functions
- Data processing and formatting utilities
- All core business logic extracted from the original MCP implementation

**test_fusion.py** - Interactive test menu for manual testing of all service functions

### Key Functions

**make_fusion_request()** - Central HTTP client for all Oracle Fusion API calls
- Handles authentication with read/write auth headers
- Provides comprehensive error handling with curl debugging commands
- Supports GET, POST, PUT, DELETE methods

**get_user_business_units()** - Retrieves accessible business units for the authenticated user from HCM API

**enrich_sites_with_inventory_info()** - Enriches supplier sites with inventory organizations and delivery location data

**get_item_suppliers()** - Complex function that:
1. Gets suppliers for an item using self links
2. Filters sites by user's accessible business units
3. Enriches supplier data with inventory organization details
4. Returns supplier information with delivery locations

### Oracle Fusion API Integration

The server integrates with multiple Oracle Fusion REST APIs:
- **FSCM API** (Financial Supply Chain Management) - Items, suppliers, purchase requisitions, inventory orgs
- **HCM API** (Human Capital Management) - Worker/user business unit access

Key endpoints:
- `/fscmRestApi/resources/11.13.18.05/itemsV2` - Product search
- `/fscmRestApi/resources/11.13.18.05/suppliers` - Supplier management
- `/fscmRestApi/resources/11.13.18.05/purchaseRequisitions` - Purchase requisition creation
- `/hcmRestApi/resources/11.13.18.05/workers` - User business unit access

### FastAPI Endpoints

1. **POST /find_matching_listings** - Searches products with parallel API calls for multiple search terms, deduplicates results, and enriches with supplier/inventory data

2. **POST /retrieve_supplier_detail** - Fetches comprehensive supplier information including addresses, contacts, sites, and inventory organizations

3. **POST /submit_purchase_requisition** - Creates purchase requisitions by first creating a header, then adding line items

### Request Models

**ListingsRequest** - Validates product search requests with query terms and limit
**SupplierDetailRequest** - Validates supplier detail requests with supplier ID and optional BU ID
**PurchaseRequisitionRequest** - Validates purchase requisition requests with all required procurement fields

### Data Flow

1. HTTP requests are received by FastAPI endpoints with validated Pydantic models
2. Services authenticate using environment credentials
3. API calls are made to Oracle Fusion endpoints
4. Responses are enriched with related data (suppliers, inventory orgs, business units)
5. Results are formatted and returned as JSON responses with proper HTTP status codes

### Error Handling

- All API calls include comprehensive error handling
- Failed requests generate curl commands for debugging
- Missing environment variables cause startup failures
- Malformed responses are handled gracefully

## Oracle Fusion Concepts

**Business Units** - Organizational entities that control procurement access
**Inventory Organizations** - Physical locations where items can be delivered
**Supplier Sites** - Specific locations/addresses for suppliers with business unit associations
**Purchase Requisitions** - Internal requests for procurement that get converted to purchase orders