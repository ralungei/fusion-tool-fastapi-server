from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Union, List
from services import find_matching_listings, retrieve_supplier_detail, submit_purchase_requisition, retrieve_supplier_ratings

app = FastAPI(
    title="Fusion Procurement Tools",
    description="Oracle Fusion Cloud ERP procurement tools API",
    version="1.0.0"
)

class ListingsRequest(BaseModel):
    product_query_terms: Union[str, List[str]]
    limit: int = 10

class SupplierDetailRequest(BaseModel):
    supplier_id: str
    bu_id: Union[str, None] = None

class PurchaseRequisitionRequest(BaseModel):
    listing_id: str
    quantity: int
    procurement_bu_id: str
    destination_org_id: str
    deliver_to_location_id: str
    requested_delivery_date: Union[str, None] = None

class SupplierRatingsRequest(BaseModel):
    supplier_id: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Fusion Procurement Tools API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/find_matching_listings")
async def find_matching_listings_endpoint(request: ListingsRequest):
    """Find matching product listings in Oracle Fusion based on search terms"""
    try:
        result = await find_matching_listings(
            product_query_terms=request.product_query_terms,
            limit=request.limit
        )
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve_supplier_detail")
async def retrieve_supplier_detail_endpoint(request: SupplierDetailRequest):
    """Retrieve detailed information for a specific supplier"""
    try:
        result = await retrieve_supplier_detail(
            supplier_id=request.supplier_id,
            bu_id=request.bu_id
        )
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit_purchase_requisition")
async def submit_purchase_requisition_endpoint(request: PurchaseRequisitionRequest):
    """Submit a purchase requisition for a specific item"""
    try:
        result = await submit_purchase_requisition(
            listing_id=request.listing_id,
            quantity=request.quantity,
            procurement_bu_id=request.procurement_bu_id,
            destination_org_id=request.destination_org_id,
            deliver_to_location_id=request.deliver_to_location_id,
            requested_delivery_date=request.requested_delivery_date
        )
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve_supplier_ratings")
async def retrieve_supplier_ratings_endpoint(request: SupplierRatingsRequest):
    """Retrieve supplier ratings and feedback from Oracle database"""
    try:
        result = await retrieve_supplier_ratings(
            supplier_id=request.supplier_id
        )
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)