from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


# ============ ACCOUNTS ============

@action(name="quickbooks_list_accounts", description="Get all QuickBooks accounts", app="quickbooks")
def list_accounts() -> list:
    """Get all QuickBooks accounts."""
    accounts = query_state("quickbooks", "account")
    return [{"account_id": acc["id"], **acc["json_data"]} for acc in accounts]


@action(name="quickbooks_get_account", description="Get a single QuickBooks account by ID", app="quickbooks")
def get_account(account_id: str) -> dict:
    """Get a QuickBooks account with all its data."""
    account = get_state(account_id)
    return {"account_id": account["id"], **account["json_data"]}


@action(name="quickbooks_create_account", description="Create a new QuickBooks account", app="quickbooks")
def create_account(name: str, account_type: str) -> dict:
    """Create a new QuickBooks account."""
    account_data = {
        "name": name,
        "account_type": account_type
    }
    return insert_state("quickbooks", "account", account_data)


# ============ CUSTOMERS ============

@action(name="quickbooks_list_customers", description="Get all QuickBooks customers", app="quickbooks")
def list_customers() -> list:
    """Get all QuickBooks customers."""
    customers = query_state("quickbooks", "customer")
    return [{"customer_id": cust["id"], **cust["json_data"]} for cust in customers]


@action(name="quickbooks_get_customer", description="Get a single QuickBooks customer by ID", app="quickbooks")
def get_customer(customer_id: str) -> dict:
    """Get a QuickBooks customer with all its data."""
    customer = get_state(customer_id)
    return {"customer_id": customer["id"], **customer["json_data"]}


@action(name="quickbooks_create_customer", description="Create a new QuickBooks customer", app="quickbooks")
def create_customer(company_name: str, display_name: str, primary_email: str = "", billing_address: str = "") -> dict:
    """Create a new QuickBooks customer."""
    customer_data = {
        "company_name": company_name,
        "display_name": display_name,
        "primary_email": primary_email,
        "billing_address": billing_address
    }
    return insert_state("quickbooks", "customer", customer_data)


# ============ VENDORS ============

@action(name="quickbooks_list_vendors", description="Get all QuickBooks vendors", app="quickbooks")
def list_vendors() -> list:
    """Get all QuickBooks vendors."""
    vendors = query_state("quickbooks", "vendor")
    return [{"vendor_id": v["id"], **v["json_data"]} for v in vendors]


@action(name="quickbooks_get_vendor", description="Get a single QuickBooks vendor by ID", app="quickbooks")
def get_vendor(vendor_id: str) -> dict:
    """Get a QuickBooks vendor with all its data."""
    vendor = get_state(vendor_id)
    return {"vendor_id": vendor["id"], **vendor["json_data"]}


@action(name="quickbooks_create_vendor", description="Create a new QuickBooks vendor", app="quickbooks")
def create_vendor(company_name: str, display_name: str) -> dict:
    """Create a new QuickBooks vendor."""
    vendor_data = {
        "company_name": company_name,
        "display_name": display_name
    }
    return insert_state("quickbooks", "vendor", vendor_data)


# ============ INVOICES ============

@action(name="quickbooks_list_invoices", description="Get all QuickBooks invoices", app="quickbooks")
def list_invoices() -> list:
    """Get all QuickBooks invoices."""
    invoices = query_state("quickbooks", "invoices")
    return [{"invoice_id": inv["id"], **inv["json_data"]} for inv in invoices]


@action(name="quickbooks_get_invoice", description="Get a single QuickBooks invoice by ID", app="quickbooks")
def get_invoice(invoice_id: str) -> dict:
    """Get a QuickBooks invoice with all its data."""
    invoice = get_state(invoice_id)
    return {"invoice_id": invoice["id"], **invoice["json_data"]}


@action(name="quickbooks_create_invoice", description="Create a new QuickBooks invoice", app="quickbooks")
def create_invoice(line_items: list = None) -> dict:
    """Create a new QuickBooks invoice with line items."""
    invoice_data = {
        "line_items": line_items or []
    }
    return insert_state("quickbooks", "invoices", invoice_data)


@action(name="quickbooks_add_line_item", description="Add a line item to an invoice", app="quickbooks")
def add_line_item(invoice_id: str, qty: float, amount: float, description: str, detail_type: str) -> dict:
    """Add a line item to an existing invoice."""
    invoice = get_state(invoice_id)
    line_item = {
        "qty": qty,
        "amount": amount,
        "description": description,
        "detail_type": detail_type
    }
    invoice["json_data"].setdefault("line_items", []).append(line_item)
    return update_state(invoice_id, invoice["json_data"])


# ============ PAYMENTS ============

@action(name="quickbooks_list_payments", description="Get all QuickBooks payments", app="quickbooks")
def list_payments() -> list:
    """Get all QuickBooks payments."""
    payments = query_state("quickbooks", "payment")
    return [{"payment_id": p["id"], **p["json_data"]} for p in payments]


@action(name="quickbooks_get_payment", description="Get a single QuickBooks payment by ID", app="quickbooks")
def get_payment(payment_id: str) -> dict:
    """Get a QuickBooks payment with all its data."""
    payment = get_state(payment_id)
    return {"payment_id": payment["id"], **payment["json_data"]}


@action(name="quickbooks_create_payment", description="Create a new QuickBooks payment", app="quickbooks")
def create_payment(total_amount: float, line_items: list = None) -> dict:
    """Create a new QuickBooks payment."""
    payment_data = {
        "total_amount": total_amount,
        "line_items": line_items or []
    }
    return insert_state("quickbooks", "payment", payment_data)
