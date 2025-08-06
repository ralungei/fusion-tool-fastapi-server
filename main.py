from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Union, List
from services import find_matching_listings, retrieve_supplier_detail, submit_purchase_requisition, retrieve_supplier_ratings

app = FastAPI(
    title="Fusion Procurement Tools",
    description="Oracle Fusion Cloud ERP procurement tools API",
    version="1.0.0"
)

class ListingsRequest(BaseModel):
    product_query_terms: Union[str, List[str]] = Field(
        description="Search terms - provide multiple variations for comprehensive results. For 'brake pads' use: ['brake', 'brake-pads', 'brake pads', 'brake pad'] to cover singular/plural and hyphenated forms"
    )
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

# @app.post("/find_matching_listings")
# async def find_matching_listings_endpoint(request: ListingsRequest):
#     """Search for products in Oracle Fusion catalog. Returns items with suppliers, pricing, inventory locations, and procurement details. Use this to find products for purchase requisitions or procurement analysis."""
#     try:
#         result = await find_matching_listings(
#             product_query_terms=request.product_query_terms,
#             limit=request.limit
#         )
#         return {"data": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/retrieve_supplier_detail")
# async def retrieve_supplier_detail_endpoint(request: SupplierDetailRequest):
#     """Get comprehensive supplier information including addresses, contacts, sites, and business unit relationships. Use this to understand supplier capabilities and delivery locations for procurement decisions."""
#     try:
#         result = await retrieve_supplier_detail(
#             supplier_id=request.supplier_id,
#             bu_id=request.bu_id
#         )
#         return {"data": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/submit_purchase_requisition")
# async def submit_purchase_requisition_endpoint(request: PurchaseRequisitionRequest):
#     """Create a purchase requisition in Oracle Fusion for procurement approval workflow. Requires item ID, quantity, business unit, delivery location, and delivery date. Always confirm details with user before submitting."""
#     try:
#         result = await submit_purchase_requisition(
#             listing_id=request.listing_id,
#             quantity=request.quantity,
#             procurement_bu_id=request.procurement_bu_id,
#             destination_org_id=request.destination_org_id,
#             deliver_to_location_id=request.deliver_to_location_id,
#             requested_delivery_date=request.requested_delivery_date
#         )
#         return {"data": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve_supplier_ratings")
async def retrieve_supplier_ratings_endpoint(request: SupplierRatingsRequest):
    """Get supplier performance ratings and feedback scores from Oracle database. Returns average rating, total reviews, and individual feedback entries. Use this to evaluate supplier quality before making procurement decisions."""
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