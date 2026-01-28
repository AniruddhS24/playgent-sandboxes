from actions import action
from state_helpers import get_state, insert_state, update_state, query_state


# Account actions

@action(name="salesforce_list_accounts", description="Get all Salesforce accounts", app="salesforce")
def list_accounts() -> list:
    """Get all Salesforce accounts with full data."""
    accounts = query_state("salesforce", "account")
    return [{"account_id": a["id"], **a["json_data"]} for a in accounts]


@action(name="salesforce_get_account", description="Get a Salesforce account by ID", app="salesforce")
def get_account(account_id: str) -> dict:
    """Get a Salesforce account."""
    account = get_state(account_id)
    return {"account_id": account["id"], **account["json_data"]}


@action(name="salesforce_create_account", description="Create a new Salesforce account", app="salesforce")
def create_account(name: str, industry: str = "", account_type: str = "", phone: str = "", website: str = "") -> dict:
    """Create a new Salesforce account."""
    account_data = {
        "name": name,
        "industry": industry,
        "type": account_type,
        "phone": phone,
        "website": website,
        "rating": "",
        "revenue": 0,
        "employees": 0,
        "description": "",
        "address": {"street": "", "city": "", "state": "", "country": "", "postal_code": ""}
    }
    return insert_state("salesforce", "account", account_data)


@action(name="salesforce_update_account", description="Update a Salesforce account", app="salesforce")
def update_account(account_id: str, name: str = None, industry: str = None, phone: str = None, website: str = None) -> dict:
    """Update a Salesforce account."""
    account = get_state(account_id)
    if name is not None:
        account["json_data"]["name"] = name
    if industry is not None:
        account["json_data"]["industry"] = industry
    if phone is not None:
        account["json_data"]["phone"] = phone
    if website is not None:
        account["json_data"]["website"] = website
    return update_state(account_id, account["json_data"])


# Lead actions

@action(name="salesforce_list_leads", description="Get all Salesforce leads", app="salesforce")
def list_leads() -> list:
    """Get all Salesforce leads with full data."""
    leads = query_state("salesforce", "lead")
    return [{"lead_id": l["id"], **l["json_data"]} for l in leads]


@action(name="salesforce_get_lead", description="Get a Salesforce lead by ID", app="salesforce")
def get_lead(lead_id: str) -> dict:
    """Get a Salesforce lead."""
    lead = get_state(lead_id)
    return {"lead_id": lead["id"], **lead["json_data"]}


@action(name="salesforce_create_lead", description="Create a new Salesforce lead", app="salesforce")
def create_lead(first_name: str, last_name: str, company: str, email: str = "", phone: str = "", status: str = "Open") -> dict:
    """Create a new Salesforce lead."""
    lead_data = {
        "first_name": first_name,
        "last_name": last_name,
        "company": company,
        "email": email,
        "phone": phone,
        "status": status,
        "source": "",
        "rating": "",
        "industry": "",
        "address": {"street": "", "city": "", "state": "", "country": "", "postal_code": ""}
    }
    return insert_state("salesforce", "lead", lead_data)


@action(name="salesforce_update_lead", description="Update a Salesforce lead", app="salesforce")
def update_lead(lead_id: str, status: str = None, email: str = None, phone: str = None, rating: str = None) -> dict:
    """Update a Salesforce lead."""
    lead = get_state(lead_id)
    if status is not None:
        lead["json_data"]["status"] = status
    if email is not None:
        lead["json_data"]["email"] = email
    if phone is not None:
        lead["json_data"]["phone"] = phone
    if rating is not None:
        lead["json_data"]["rating"] = rating
    return update_state(lead_id, lead["json_data"])


# Opportunity actions

@action(name="salesforce_list_opportunities", description="Get all Salesforce opportunities", app="salesforce")
def list_opportunities() -> list:
    """Get all Salesforce opportunities with full data."""
    opps = query_state("salesforce", "opportunity")
    return [{"opportunity_id": o["id"], **o["json_data"]} for o in opps]


@action(name="salesforce_get_opportunity", description="Get a Salesforce opportunity by ID", app="salesforce")
def get_opportunity(opportunity_id: str) -> dict:
    """Get a Salesforce opportunity."""
    opp = get_state(opportunity_id)
    return {"opportunity_id": opp["id"], **opp["json_data"]}


@action(name="salesforce_create_opportunity", description="Create a new Salesforce opportunity", app="salesforce")
def create_opportunity(name: str, stage: str, amount: float = 0, account_id: str = "", close_date: str = "") -> dict:
    """Create a new Salesforce opportunity."""
    opp_data = {
        "name": name,
        "stage": stage,
        "amount": amount,
        "account_id": account_id,
        "close_date": close_date,
        "probability": 0,
        "next_step": "",
        "type": "",
        "source": "",
        "description": ""
    }
    return insert_state("salesforce", "opportunity", opp_data)


@action(name="salesforce_update_opportunity", description="Update a Salesforce opportunity", app="salesforce")
def update_opportunity(opportunity_id: str, stage: str = None, amount: float = None, probability: float = None, next_step: str = None) -> dict:
    """Update a Salesforce opportunity."""
    opp = get_state(opportunity_id)
    if stage is not None:
        opp["json_data"]["stage"] = stage
    if amount is not None:
        opp["json_data"]["amount"] = amount
    if probability is not None:
        opp["json_data"]["probability"] = probability
    if next_step is not None:
        opp["json_data"]["next_step"] = next_step
    return update_state(opportunity_id, opp["json_data"])
