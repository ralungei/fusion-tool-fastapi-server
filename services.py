from typing import Any
import httpx
import os
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

FUSION_API_BASE = "https://fa-eqiq-dev18-saasfademo1.ds-fa.oraclepdemos.com"
USER_AGENT = "fusion-fastapi-client/1.0"
FUSION_AUTH_READ = os.getenv("FUSION_AUTH_READ")
FUSION_AUTH_WRITE = os.getenv("FUSION_AUTH_WRITE")
FUSION_USER_ID = os.getenv("FUSION_USER_ID")

required_vars = {
    "FUSION_AUTH_READ": FUSION_AUTH_READ,
    "FUSION_AUTH_WRITE": FUSION_AUTH_WRITE,
    "FUSION_USER_ID": FUSION_USER_ID
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

FSCM_API_BASE = "/fscmRestApi/resources/11.13.18.05"
HCM_API_BASE = "/hcmRestApi/resources/11.13.18.05"
ITEMS_ENDPOINT = f"{FSCM_API_BASE}/itemsV2"
SUPPLIERS_ENDPOINT = f"{FSCM_API_BASE}/suppliers"
PURCHASE_REQUISITIONS_ENDPOINT = f"{FSCM_API_BASE}/purchaseRequisitions"
INVENTORY_ORGS_ENDPOINT = f"{FSCM_API_BASE}/inventoryOrganizations"
WORKERS_ENDPOINT = f"{HCM_API_BASE}/workers"

async def make_fusion_request(endpoint: str, method: str = "GET", data: dict = None, use_write_auth: bool = False) -> dict[str, Any] | None:
    """Make a request to the Oracle Fusion API with proper error handling."""
    auth_header = FUSION_AUTH_WRITE if use_write_auth else FUSION_AUTH_READ
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth_header
    }
    
    url = f"{FUSION_API_BASE}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data, timeout=30.0)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers, timeout=30.0)
            else:
                return None
                
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Generate curl command for debugging
            curl_cmd = f"curl -X {method.upper()} \\\n"
            curl_cmd += f"  '{url}' \\\n"
            for key, value in headers.items():
                curl_cmd += f"  -H '{key}: {value}' \\\n"
            if data and method.upper() in ["POST", "PUT"]:
                import json
                curl_cmd += f"  -d '{json.dumps(data, separators=(',', ':'))}'"
            else:
                curl_cmd = curl_cmd.rstrip(' \\\n')
            
            print(f"\n🚨 HTTP Error - Debug with this curl command:")
            print(f"{curl_cmd}\n")
            
            try:
                error_details = e.response.json()
                error_message = f"HTTP {e.response.status_code}: {error_details}"
                return {"error": error_message, "status_code": e.response.status_code}
            except:
                return {"error": f"HTTP {e.response.status_code}: {e.response.text}", "status_code": e.response.status_code}
        except Exception as e:
            return {"error": str(e), "status_code": None}

async def get_user_business_units() -> list[str]:
    """Get the business unit IDs that the user has access to from HCM API.
    
    Returns:
        List of business unit IDs as strings.
    """
    try:
        user_id = FUSION_USER_ID
        endpoint = f"{WORKERS_ENDPOINT}?q=PersonId={user_id}&expand=workRelationships.assignments"
        
        worker_data = await make_fusion_request(endpoint, use_write_auth=True)
        
        if not worker_data or not worker_data.get('items'):
            return []
        
        business_unit_ids = set()
        
        for worker in worker_data['items']:
            work_relationships = worker.get('workRelationships', [])
            for relationship in work_relationships:
                assignments = relationship.get('assignments', [])
                for assignment in assignments:
                    bu_id = assignment.get('BusinessUnitId')
                    if bu_id:
                        business_unit_ids.add(str(bu_id))
        
        return list(business_unit_ids)
        
    except Exception as e:
        return []

async def enrich_sites_with_inventory_info(sites: list) -> list:
    """Enrich sites with inventory organizations and delivery location information.
    
    Args:
        sites: List of supplier sites
        
    Returns:
        List of enriched sites with inventory organizations and delivery locations
    """
    if not sites:
        return sites
        
    bu_groups = {}
    for site in sites:
        bu_id = site.get('ProcurementBUId')
        if bu_id:
            if bu_id not in bu_groups:
                bu_groups[bu_id] = []
            bu_groups[bu_id].append(site)
    
    import asyncio
    inv_tasks = []
    bu_id_list = list(bu_groups.keys())
    
    for bu_id in bu_id_list:
        inv_endpoint = f"{INVENTORY_ORGS_ENDPOINT}?q=ManagementBusinessUnitId={bu_id}"
        inv_tasks.append(make_fusion_request(inv_endpoint))
    
    inventory_orgs = {}
    if inv_tasks:
        inv_results = await asyncio.gather(*inv_tasks)
        for i, inv_data in enumerate(inv_results):
            if inv_data and inv_data.get("items"):
                inventory_orgs[bu_id_list[i]] = inv_data["items"]
    
    location_tasks = []
    org_ids = []
    
    for bu_id, orgs in inventory_orgs.items():
        for org in orgs:
            if org.get('InventoryFlag'):
                org_id = org.get('OrganizationId')
                if org_id:
                    detail_endpoint = f"{INVENTORY_ORGS_ENDPOINT}/{org_id}"
                    location_tasks.append(make_fusion_request(detail_endpoint))
                    org_ids.append(org_id)
    
    inventory_locations = {}
    if location_tasks:
        location_results = await asyncio.gather(*location_tasks)
        for i, org_detail in enumerate(location_results):
            if org_detail:
                inventory_locations[org_ids[i]] = org_detail
    
    enriched_sites = []
    for site in sites:
        enriched_site = site.copy()
        bu_id = site.get('ProcurementBUId')
        
        if bu_id and bu_id in inventory_orgs:
            enriched_site['inventory_organizations'] = inventory_orgs[bu_id]
            enriched_site['inventory_locations'] = inventory_locations
        
        enriched_sites.append(enriched_site)
    
    return enriched_sites

async def get_item_suppliers(item: dict) -> list:
    """Get suppliers for a specific item using the self link, including BU information.
    Filters sites to only show those belonging to business units the user has access to.
    
    Args:
        item: The item dictionary containing links
        
    Returns:
        List of supplier information with BU details or empty list if none found.
    """
    
    links = item.get("links", [])
    self_link = None
    
    for link in links:
        if link.get("rel") == "self":
            self_link = link.get("href")
            break
    
    if not self_link:
        return []
    
    
    user_business_units = await get_user_business_units()
    if not user_business_units:
        return []
    
    
    supplier_endpoint = f"{self_link}/child/ItemSupplierAssociation"
    
    
    if supplier_endpoint.startswith(FUSION_API_BASE):
        supplier_endpoint = supplier_endpoint[len(FUSION_API_BASE):]
    
    supplier_data = await make_fusion_request(supplier_endpoint)
    
    if not supplier_data or "items" not in supplier_data:
        return []
    
    
    import asyncio
    
    async def process_supplier(supplier):
        supplier_with_sites = supplier.copy()
        supplier_with_sites['sites'] = []
        
        supplier_party_id = supplier.get('SupplierId')  # Note: Field named 'SupplierId' but contains SupplierPartyId value
        
        if supplier_party_id:
            # Oracle supplier flow: SupplierPartyId (public ID) → search → SupplierId (internal ID for child endpoints)
            query = f"SupplierPartyId = '{supplier_party_id}'"
            search_endpoint = f"{SUPPLIERS_ENDPOINT}?q={query}"
            search_data = await make_fusion_request(search_endpoint)
            
            if search_data and search_data.get('items'):
                supplier_details = search_data['items'][0]
                actual_supplier_id = supplier_details.get('SupplierId')  # Now this is the real SupplierId
                supplier_with_sites['SupplierPartyId'] = supplier_details.get('SupplierPartyId')
                if actual_supplier_id:
                    
                    sites_endpoint = f"{SUPPLIERS_ENDPOINT}/{actual_supplier_id}/child/sites"
                    sites_data = await make_fusion_request(sites_endpoint)
                    
                    if sites_data and sites_data.get("items"):
                        
                        all_sites = sites_data["items"]
                        
                        
                        filtered_sites = [site for site in all_sites 
                                        if str(site.get('ProcurementBUId')) in user_business_units]
                        
                        if filtered_sites:
                            enriched_sites = await enrich_sites_with_inventory_info(filtered_sites)
                            
                            address_name = supplier.get('AddressName')
                            if address_name:
                                matching_sites = [site for site in enriched_sites 
                                                if site.get('SupplierSite') == address_name]
                                if matching_sites:
                                    supplier_with_sites['sites'] = matching_sites
                                else:
                                    
                                    supplier_with_sites['sites'] = enriched_sites[:3]
                            else:
                                
                                supplier_with_sites['sites'] = enriched_sites[:3]
        
        return supplier_with_sites if supplier_with_sites.get('sites') else None
    
    supplier_tasks = [process_supplier(supplier) for supplier in supplier_data["items"]]
    processed_suppliers = await asyncio.gather(*supplier_tasks)
    
    enriched_suppliers = [supplier for supplier in processed_suppliers if supplier is not None]
    
    return enriched_suppliers

async def find_matching_listings(product_query_terms, limit: int = 10) -> str:
    """Find matching product listings in Oracle Fusion based on search terms.
    
    Args:
        product_query_terms: Either a single search term (str) or list of search terms to match against ItemNumber and ItemDescription
        limit: Maximum number of items to return (default: 10)
        
    Returns:
        A formatted string with the matching product listings and suppliers.
    """
    
    # Convert single string to list for uniform processing
    if isinstance(product_query_terms, str):
        search_terms = [product_query_terms]
    else:
        search_terms = product_query_terms
    
    # Oracle Fusion OR doesn't work properly, so make multiple parallel requests
    import asyncio
    
    # Create individual queries for each term with case variations
    query_tasks = []
    for term in search_terms:
        # Get unique case variations
        variations = [term, term.lower(), term.upper()]
        unique_variations = list(dict.fromkeys(variations))
        
        for variation in unique_variations:
            query_param = f"ItemNumber LIKE '{variation}%'"
            endpoint = f"{ITEMS_ENDPOINT}?q={query_param}&limit={limit}"
            query_tasks.append(make_fusion_request(endpoint))
    
    # Execute all queries in parallel
    results = await asyncio.gather(*query_tasks)
    
    # Check for errors in results and collect error details
    errors = []
    for idx, data in enumerate(results):
        if data and "error" in data:
            errors.append(f"Query {idx}: {data.get('error')}")
    
    if errors:
        error_detail = "; ".join(errors)
        search_terms_str = ", ".join(search_terms) if len(search_terms) > 1 else search_terms[0]
        return json.dumps({
            "error": f"Failed to fetch products for '{search_terms_str}'",
            "details": error_detail,
            "auth_configured": bool(FUSION_AUTH_READ),
            "user_id_configured": bool(FUSION_USER_ID)
        })
    
    # Combine all items and remove duplicates (by ItemId + OrganizationId combination)
    all_items = []
    seen_combinations = set()
    
    for data in results:
        if data and data.get("items"):
            for item in data["items"]:
                item_id = item.get("ItemId")
                org_id = item.get("OrganizationId")
                combination_key = f"{item_id}_{org_id}"
                
                if combination_key not in seen_combinations:
                    all_items.append(item)
                    seen_combinations.add(combination_key)
    
    # Create a mock data structure like the original API response
    data = {"items": all_items} if all_items else None
    
    if not data:
        search_terms_str = ", ".join(search_terms) if len(search_terms) > 1 else search_terms[0]
        return json.dumps({
            "error": f"No results found for query: {search_terms_str}",
            "total_queries": len(query_tasks),
            "successful_queries": len([r for r in results if r and not r.get("error")])
        })
    
    
    items = data.get("items", [])
    if not items:
        search_terms_str = ", ".join(search_terms) if len(search_terms) > 1 else search_terms[0]
        return f"No products found matching: {search_terms_str}"
    
    
    from collections import defaultdict
    grouped_items = defaultdict(list)
    
    for item in items:
        item_number = item.get('ItemNumber')
        grouped_items[item_number].append(item)
    
    import asyncio
    supplier_tasks = [get_item_suppliers(item) for item in items]
    suppliers_results = await asyncio.gather(*supplier_tasks)
    
    item_suppliers_map = {}
    for item, suppliers in zip(items, suppliers_results):
        item_key = f"{item.get('ItemNumber')}_{item.get('OrganizationId')}"
        item_suppliers_map[item_key] = suppliers
    
    results = []
    for item_number, item_list in grouped_items.items():
        group_data = format_grouped_item_summary(item_number, item_list, item_suppliers_map)
        if group_data:
            results.append(group_data)
    
    if not results:
        return json.dumps({"error": "No products found with valid inventory organizations for procurement.", "products": []})
    
    return json.dumps({"products": results}, indent=2)

async def retrieve_supplier_detail(supplier_id: str, bu_id: str = None) -> str:
    """Retrieve detailed information for a specific supplier including addresses, contacts, and sites.
    
    Args:
        supplier_id: The supplier ID (SupplierPartyId) to get details for
        bu_id: Optional Business Unit ID to filter sites and organizations
        
    Returns:
        A formatted string with comprehensive supplier information.
    """
    
    query = f"SupplierPartyId = '{supplier_id}'"
    search_endpoint = f"{SUPPLIERS_ENDPOINT}?q={query}"
    search_data = await make_fusion_request(search_endpoint)
    
    if not search_data or not search_data.get('items'):
        return f"Unable to find supplier with SupplierPartyId: {supplier_id}"
    
    
    actual_supplier_id = search_data['items'][0].get('SupplierId')
    
    
    endpoint = f"{SUPPLIERS_ENDPOINT}/{actual_supplier_id}"
    supplier_data = await make_fusion_request(endpoint)
    
    if not supplier_data:
        return f"Unable to fetch details for supplier ID: {supplier_id}"
    
    
    addresses_endpoint = f"{SUPPLIERS_ENDPOINT}/{actual_supplier_id}/child/addresses"
    contacts_endpoint = f"{SUPPLIERS_ENDPOINT}/{actual_supplier_id}/child/contacts"  
    sites_endpoint = f"{SUPPLIERS_ENDPOINT}/{actual_supplier_id}/child/sites"
    
    
    import asyncio
    
    
    addresses_task = make_fusion_request(addresses_endpoint)
    contacts_task = make_fusion_request(contacts_endpoint)
    sites_task = make_fusion_request(sites_endpoint)
    
    addresses_data, contacts_data, sites_data = await asyncio.gather(
        addresses_task, contacts_task, sites_task
    )
    
    
    sites_list = sites_data.get("items", []) if sites_data else []
    if bu_id and sites_list:
        sites_list = [site for site in sites_list if str(site.get('ProcurementBUId')) == str(bu_id)]
    
    
    inventory_orgs = {}
    if sites_list:
        unique_bu_ids = set()
        for site in sites_list:
            if site.get('ProcurementBUId'):
                unique_bu_ids.add(site['ProcurementBUId'])
        
        
        inv_tasks = []
        bu_id_list = list(unique_bu_ids)
        for bu_id in bu_id_list:
            inv_endpoint = f"{INVENTORY_ORGS_ENDPOINT}?q=ManagementBusinessUnitId={bu_id}"
            inv_tasks.append(make_fusion_request(inv_endpoint))
        
        
        if inv_tasks:
            inv_results = await asyncio.gather(*inv_tasks)
            for i, inv_data in enumerate(inv_results):
                if inv_data and inv_data.get("items"):
                    inventory_orgs[bu_id_list[i]] = inv_data["items"]
    
    
    inventory_locations = {}
    if inventory_orgs:
        location_tasks = []
        org_ids = []
        
        for bu_id, orgs in inventory_orgs.items():
            for org in orgs:
                if org.get('InventoryFlag'):  
                    org_id = org.get('OrganizationId')
                    if org_id:
                        
                        detail_endpoint = f"{INVENTORY_ORGS_ENDPOINT}/{org_id}"
                        location_tasks.append(make_fusion_request(detail_endpoint))
                        org_ids.append(org_id)
        
        
        if location_tasks:
            location_results = await asyncio.gather(*location_tasks)
            for i, org_detail in enumerate(location_results):
                if org_detail:
                    inventory_locations[org_ids[i]] = org_detail
    
    return format_supplier_detail(
        supplier_data, 
        addresses_data.get("items", []) if addresses_data else [],
        contacts_data.get("items", []) if contacts_data else [],
        sites_list,
        inventory_orgs,
        bu_id,
        inventory_locations
    )

def format_supplier_detail(supplier: dict, addresses: list = None, contacts: list = None, sites: list = None, inventory_orgs: dict = None, filter_bu_id: str = None, inventory_locations: dict = None) -> str:
    """Format supplier details with addresses, contacts, sites, inventory organizations and locations into a readable summary."""
    
    fields = {
        "Supplier Party ID": supplier.get('SupplierPartyId', 'N/A'),
        "Supplier Name": supplier.get('Supplier', 'N/A'),
        "Supplier Number": supplier.get('SupplierNumber', 'N/A'), 
        "Status": supplier.get('Status', 'N/A'),
        "Business Relationship": supplier.get('BusinessRelationship', 'N/A'),
        "DUNS Number": supplier.get('DUNSNumber', 'N/A'),
        "Year Established": supplier.get('YearEstablished', 'N/A'),
        "Country": supplier.get('TaxpayerCountry', 'N/A'),
        "Annual Revenue": f"${supplier.get('CurrentFiscalYearPotentialRevenue', 'N/A'):,}" if supplier.get('CurrentFiscalYearPotentialRevenue') else 'N/A'
    }
    
    formatted_lines = [f"{key}: {value}" for key, value in fields.items()]
    
    
    if filter_bu_id:
        formatted_lines.append(f"\n📍 Filtered by Business Unit ID: {filter_bu_id}")
    
    
    if addresses:
        formatted_lines.append("\nAddresses:")
        for addr in addresses[:35]:
            address_info = []
            if addr.get('AddressLine1'): address_info.append(addr.get('AddressLine1'))
            if addr.get('City'): address_info.append(addr.get('City'))
            if addr.get('State'): address_info.append(addr.get('State'))
            if addr.get('PostalCode'): address_info.append(addr.get('PostalCode'))
            if addr.get('Country'): address_info.append(addr.get('Country'))
            
            address_name = addr.get('AddressName', 'Unknown')
            address_line = f"  • {address_name}: {', '.join(address_info) if address_info else 'N/A'}"
            formatted_lines.append(address_line)
    else:
        formatted_lines.append("\nAddresses: No addresses found")
    
    
    if contacts:
        formatted_lines.append("\nContacts:")
        
        useful_contacts = [c for c in contacts if c.get('Email') or c.get('PhoneNumber')]
        
        for contact in useful_contacts[:5]:
            name = f"{contact.get('FirstName', '')} {contact.get('LastName', '')}".strip()
            email = contact.get('Email', 'N/A')
            phone = contact.get('PhoneNumber', 'N/A') 
            job_title = contact.get('JobTitle', 'N/A')
            
            contact_line = f"  • {name or 'N/A'} ({job_title}) - Email: {email}, Phone: {phone}"
            formatted_lines.append(contact_line)
    else:
        formatted_lines.append("\nContacts: No contacts found")
    
    
    if sites:
        formatted_lines.append("\nSites:")
        for site in sites[:5]:
            site_name = site.get('SupplierSite', 'N/A')
            bu_name = site.get('ProcurementBU', 'N/A')
            bu_id = site.get('ProcurementBUId', 'N/A')
            
            
            purposes = []
            if site.get('SitePurposePurchasingFlag'): purposes.append('Purchasing')
            if site.get('SitePurposePayFlag'): purposes.append('Payment')
            if site.get('SitePurposePrimaryPayFlag'): purposes.append('Primary Pay')
            purpose_text = ', '.join(purposes) if purposes else 'N/A'
            
            
            site_status = 'Active' if not site.get('InactiveDate') else 'Inactive'
            
            site_line = f"  • Site: {site_name}\n    Business Unit: {bu_name}\n    BU ID: {bu_id}\n    Purpose: {purpose_text}\n    Status: {site_status}"
            formatted_lines.append(site_line)
            
            
            if inventory_orgs and bu_id in inventory_orgs:
                formatted_lines.append("    Destination Organizations (Available Inventory Orgs):")
                for org in inventory_orgs[bu_id]:
                    if org.get('InventoryFlag'):
                        org_id = org.get('OrganizationId', 'N/A')
                        org_name = org.get('OrganizationName', 'N/A')
                        org_code = org.get('OrganizationCode', 'N/A')
                        formatted_lines.append(f"      - Organization: {org_name}\n        ID: {org_id}\n        Code: {org_code}")
                        
                        
                        if inventory_locations and org_id in inventory_locations:
                            org_details = inventory_locations[org_id]
                            location_id = org_details.get('LocationId', 'N/A')
                            if location_id != 'N/A':
                                formatted_lines.append(f"        Deliver To Location ID: {location_id}")
                            else:
                                formatted_lines.append("        Deliver To Location ID: Not available")
                        else:
                            formatted_lines.append("        Deliver To Location ID: Not available")
    else:
        formatted_lines.append("\nSites: No sites found")
    
    return "\n".join(formatted_lines)

def format_grouped_item_summary(item_number: str, item_list: list, item_suppliers_map: dict) -> dict:
    """Format a grouped item summary as dictionary for JSON output."""
    if not item_list:
        return {"item_name": item_number, "error": "No data available"}
    first_item = item_list[0]
    product_data = {
        "item_name": item_number,
        "item_id": first_item.get('ItemId'),
        "description": first_item.get('ItemDescription'),
        "primary_uom": first_item.get('PrimaryUOMValue'),
        "item_class": first_item.get('ItemClass'),
        "status": first_item.get('ItemStatusValue'),
        "purchasable": first_item.get('PurchasableFlag'),
        "organizations": []
    }
    
    # Process each organization - only show inventory organizations (InventoryFlag: True)
    for item in item_list:
        org_id = item.get('OrganizationId')
        org_code = item.get('OrganizationCode')
        list_price = item.get('ListPrice')
        
        item_key = f"{item_number}_{org_id}"
        suppliers = item_suppliers_map.get(item_key, [])
        
        # Check if organization has inventory flag
        has_inventory_flag = False
        org_name = None
        for supplier in suppliers:
            sites = supplier.get('sites', [])
            for site in sites:
                inventory_orgs = site.get('inventory_organizations', [])
                for inv_org in inventory_orgs:
                    if str(inv_org.get('OrganizationId')) == str(org_id):
                        if inv_org.get('InventoryFlag'):
                            has_inventory_flag = True
                        org_name = inv_org.get('OrganizationName')
                        break
                if org_name:
                    break
            if org_name:
                break
        
        if not has_inventory_flag:
            continue
        
        # Get procurement BU info
        procurement_bu_id = None
        procurement_bu_name = None
        for supplier in suppliers:
            sites = supplier.get('sites', [])
            for site in sites:
                if site.get('ProcurementBUId'):
                    procurement_bu_id = site.get('ProcurementBUId')
                    procurement_bu_name = site.get('ProcurementBU')
                    break
            if procurement_bu_id:
                break
        
        # Process suppliers
        supplier_list = []
        for supplier in suppliers[:2]:  # Limit to first 2 suppliers
            supplier_data = {
                "supplier_name": supplier.get('SupplierName'),
                "supplier_party_id": supplier.get('SupplierPartyId'),
                "sites": []
            }
            
            sites = supplier.get('sites', [])
            for site in sites[:2]:  # Limit to first 2 sites
                site_data = {
                    "site_name": site.get('SupplierSite'),
                    "business_unit": site.get('ProcurementBU'),
                    "site_purpose": []
                }
                
                if site.get('SitePurposePurchasingFlag'):
                    site_data["site_purpose"].append('Purchasing')
                if site.get('SitePurposePayFlag'):
                    site_data["site_purpose"].append('Payment')
                
                # Get delivery locations
                delivery_locations = []
                inventory_orgs = site.get('inventory_organizations', [])
                inventory_locations = site.get('inventory_locations', {})
                
                for inv_org in inventory_orgs:
                    if inv_org.get('InventoryFlag') and str(inv_org.get('OrganizationId')) == str(org_id):
                        org_id_inv = inv_org.get('OrganizationId')
                        if inventory_locations and org_id_inv in inventory_locations:
                            org_details = inventory_locations[org_id_inv]
                            location_id = org_details.get('LocationId')
                            if location_id:
                                delivery_locations.append({
                                    "organization_name": inv_org.get('OrganizationName'),
                                    "deliver_to_location_id": location_id
                                })
                
                # If no delivery locations for specific org, get all inventory orgs
                if not delivery_locations:
                    for inv_org in inventory_orgs:
                        if inv_org.get('InventoryFlag'):
                            org_id_inv = inv_org.get('OrganizationId')
                            if inventory_locations and org_id_inv in inventory_locations:
                                org_details = inventory_locations[org_id_inv]
                                location_id = org_details.get('LocationId')
                                if location_id:
                                    delivery_locations.append({
                                        "organization_name": inv_org.get('OrganizationName'),
                                        "deliver_to_location_id": location_id
                                    })
                
                site_data["delivery_locations"] = delivery_locations[:3]  # Limit to 3
                supplier_data["sites"].append(site_data)
            
            supplier_list.append(supplier_data)
        
        org_data = {
            "organization_code": org_code,
            "organization_name": org_name,
            "procurement_bu_id": procurement_bu_id,
            "procurement_bu_name": procurement_bu_name,
            "destination_organization_id": org_id,
            "list_price": list_price,
            "suppliers": supplier_list
        }
        
        product_data["organizations"].append(org_data)
    
    if not product_data["organizations"]:
        return None
    
    return product_data

async def submit_purchase_requisition(listing_id: str, quantity: int, procurement_bu_id: str, destination_org_id: str, deliver_to_location_id: str, requested_delivery_date: str = None) -> str:
    """Submit a purchase requisition for a specific item.
    
    Args:
        listing_id: The item ID (ItemId) from find_matching_listings
        quantity: Quantity to requisition
        procurement_bu_id: The business unit ID (RequisitioningBUId) from supplier sites
        destination_org_id: The destination organization ID from inventory organizations
        deliver_to_location_id: The delivery location ID (DeliverToLocationId) from inventory org details
        requested_delivery_date: Optional delivery date in YYYY-MM-DD format (defaults to 7 days from now)
        
    Returns:
        A formatted string with the requisition details and status.
    """
    try:
        
        header_data = {
            "PreparerId": int(FUSION_USER_ID),
            "RequisitioningBUId": int(procurement_bu_id),
            "Description": f"Purchase requisition for item {listing_id}",
            "ExternallyManagedFlag": False
        }
        
        header_response = await make_fusion_request(
            PURCHASE_REQUISITIONS_ENDPOINT, 
            method="POST", 
            data=header_data,
            use_write_auth=True
        )
        
        if not header_response:
            return "Failed to create purchase requisition header"
        
        
        requisition_id = header_response.get('RequisitionHeaderId')
        if not requisition_id:
            return f"Header created but no requisition ID returned: {header_response}"
        
        
        line_endpoint = f"{PURCHASE_REQUISITIONS_ENDPOINT}/{requisition_id}/child/lines"
        
        
        from datetime import datetime, timedelta
        if requested_delivery_date:
            delivery_date = requested_delivery_date
        else:
            delivery_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        line_data = {
            "LineNumber": 1,
            "LineTypeId": 1,  
            "ItemId": int(listing_id),
            "Quantity": quantity,
            "UOM": "Ea",  
            "DestinationOrganizationId": int(destination_org_id),
            "DeliverToLocationId": int(deliver_to_location_id),
            "RequestedDeliveryDate": delivery_date,
            "DestinationTypeCode": "EXPENSE",
            "RequesterId": int(FUSION_USER_ID)
        }
        
        line_response = await make_fusion_request(
            line_endpoint,
            method="POST",
            data=line_data,
            use_write_auth=True
        )
        
        if not line_response:
            return f"Header created (ID: {requisition_id}) but failed to create requisition line"
        
        
        if isinstance(line_response, dict) and "error" in line_response:
            error_msg = line_response["error"]
            return f"Header created (ID: {requisition_id}) but failed to create requisition line.\nError: {error_msg}"
        
        
        return format_requisition_response(header_response, line_response)
        
    except Exception as e:
        return f"Error creating purchase requisition: {str(e)}"

def format_requisition_response(header: dict, line: dict = None) -> str:
    """Format the purchase requisition response into a readable summary."""
    requisition_id = header.get('RequisitionHeaderId', 'N/A')
    description = header.get('Description', 'N/A')
    preparer_id = header.get('PreparerId', 'N/A')
    bu_id = header.get('RequisitioningBUId', 'N/A')
    
    formatted_lines = [
        f"Purchase Requisition Header Created Successfully",
        f"Requisition ID: {requisition_id}",
        f"Description: {description}",
        f"Preparer ID: {preparer_id}",
        f"Business Unit ID: {bu_id}"
    ]
    
    if line:
        line_number = line.get('LineNumber', 'N/A')
        item_id = line.get('ItemId', 'N/A')
        quantity = line.get('Quantity', 'N/A')
        uom = line.get('UOM', 'N/A')
        dest_org_id = line.get('DestinationOrganizationId', 'N/A')
        deliver_to_location_id = line.get('DeliverToLocationId', 'N/A')
        delivery_date = line.get('RequestedDeliveryDate', 'N/A')
        
        formatted_lines.extend([
            "",
            f"Line Details:",
            f"  • Line Number: {line_number}",
            f"  • Item ID: {item_id}",
            f"  • Quantity: {quantity}",
            f"  • Unit of Measure: {uom}",
            f"  • Destination Organization ID: {dest_org_id}",
            f"  • Deliver To Location ID: {deliver_to_location_id}",
            f"  • Requested Delivery Date: {delivery_date}"
        ])
    
    return "\n".join(formatted_lines)