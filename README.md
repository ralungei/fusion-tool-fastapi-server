# Oracle Fusion FastAPI Server

A FastAPI server that provides REST API endpoints for interacting with Oracle Fusion Cloud ERP applications.

## Setup

1. Copy environment file and configure credentials:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your Oracle Fusion credentials:

   - `FUSION_AUTH_READ` - Basic auth header for read operations
   - `FUSION_AUTH_WRITE` - Basic auth header for write operations  
   - `FUSION_USER_ID` - User ID for operations

3. Install dependencies:
   ```bash
   pip install fastapi uvicorn httpx python-dotenv pydantic
   ```

## Available API Endpoints

### Health Check
- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint

### Procurement Tools
- `POST /find_matching_listings` - Search for products by item number with supplier and inventory organization details
- `POST /retrieve_supplier_detail` - Get detailed supplier information including sites and delivery locations  
- `POST /submit_purchase_requisition` - Create purchase requisitions for procurement

## API Documentation

Once the server is running, visit:
- `http://localhost:8000/docs` - Interactive Swagger UI documentation
- `http://localhost:8000/redoc` - ReDoc documentation

## Usage

### Development Server
Run the server with auto-reload for development:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Server
Run the server directly:

```bash
python main.py
```

### Example API Calls

#### Find Matching Listings
```bash
curl -X POST "http://localhost:8000/find_matching_listings" \
     -H "Content-Type: application/json" \
     -d '{
       "product_query_terms": "brake pad",
       "limit": 10
     }'
```

#### Retrieve Supplier Detail
```bash
curl -X POST "http://localhost:8000/retrieve_supplier_detail" \
     -H "Content-Type: application/json" \
     -d '{
       "supplier_id": "12345",
       "bu_id": "67890"
     }'
```

#### Submit Purchase Requisition
```bash
curl -X POST "http://localhost:8000/submit_purchase_requisition" \
     -H "Content-Type: application/json" \
     -d '{
       "listing_id": "12345",
       "quantity": 5,
       "procurement_bu_id": "67890",
       "destination_org_id": "111",
       "deliver_to_location_id": "222",
       "requested_delivery_date": "2024-12-31"
     }'
```
