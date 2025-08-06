import asyncio
from fusion import find_matching_listings, retrieve_supplier_detail, submit_purchase_requisition


async def test_menu():
    """Interactive test menu for Fusion MCP functions."""
    while True:
        print("\n" + "="*50)
        print("FUSION MCP TEST MENU")
        print("="*50)
        print("1. Search single term")
        print("2. Search with multiple terms")
        print("3. Search brake pad terms list")
        print("4. Retrieve supplier detail")
        print("5. Submit purchase requisition")
        print("0. Exit")
        print("="*50)
        
        choice = input("Select option: ").strip()
        
        if choice == "0":
            print("Exiting...")
            break
        elif choice == "1":
            term = input("Enter search term: ").strip()
            if term:
                print(f"\nSearching for: {term}")
                result = await find_matching_listings(term, 10)
                print(result)
        elif choice == "2":
            terms_input = input("Enter terms separated by comma: ").strip()
            if terms_input:
                terms = [t.strip() for t in terms_input.split(",")]
                print(f"\nSearching for: {terms}")
                result = await find_matching_listings(terms, 10)
                print(result)
        elif choice == "3":
            brake_terms = ["brake pad", "brake pads", "brake-pad", "brake", "pad"]
            print(f"\nSearching brake pad terms: {brake_terms}")
            result = await find_matching_listings(brake_terms, 10)
            print(result)
        elif choice == "4":
            supplier_id = input("Enter Supplier Party ID: ").strip()
            bu_id = input("Enter BU ID (optional, press Enter to skip): ").strip()
            if supplier_id:
                print(f"\nRetrieving supplier details for: {supplier_id}")
                result = await retrieve_supplier_detail(supplier_id, bu_id if bu_id else None)
                print(result)
        elif choice == "5":
            print("\nPurchase Requisition - Enter details:")
            listing_id = input("Item ID: ").strip()
            quantity = input("Quantity: ").strip()
            procurement_bu_id = input("Procurement BU ID: ").strip()
            destination_org_id = input("Destination Org ID: ").strip()
            deliver_to_location_id = input("Deliver To Location ID: ").strip()
            delivery_date = input("Delivery Date (YYYY-MM-DD, optional): ").strip()
            
            if all([listing_id, quantity, procurement_bu_id, destination_org_id, deliver_to_location_id]):
                try:
                    result = await submit_purchase_requisition(
                        listing_id,
                        int(quantity),
                        procurement_bu_id,
                        destination_org_id,
                        deliver_to_location_id,
                        delivery_date if delivery_date else None
                    )
                    print(result)
                except ValueError:
                    print("Error: Quantity must be a number")
            else:
                print("Error: All required fields must be filled")
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    asyncio.run(test_menu())