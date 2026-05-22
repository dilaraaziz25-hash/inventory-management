from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockRecommendation(BaseModel):
    sku: str
    name: str
    trend: str
    unit_cost: float
    suggested_quantity: int
    line_total: float
    price_estimated: bool
    priority_score: float

class RestockRecommendationsResponse(BaseModel):
    budget: float
    recommendations: List[RestockRecommendation]
    total_cost: float
    remaining_budget: float

class RestockOrderItem(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_price: float

class SubmitRestockingRequest(BaseModel):
    items: List[RestockOrderItem]

RESTOCK_LEAD_TIME_DAYS = 14
TREND_WEIGHTS = {"increasing": 1.5, "stable": 1.0, "decreasing": 0.3}

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

@app.get("/api/restocking/recommendations", response_model=RestockRecommendationsResponse)
def get_restocking_recommendations(budget: float):
    """Recommend items to restock from the demand forecast within a budget.

    Joins forecasts with inventory for pricing. SKUs without an inventory match
    fall back to the average inventory unit_cost and are flagged with
    price_estimated=True. Items are ranked by a priority score (trend weight x
    shortage / reorder breach / forecast volume) and greedily selected.
    """
    if budget <= 0:
        raise HTTPException(status_code=400, detail="budget must be greater than 0")

    if not inventory_items:
        raise HTTPException(status_code=500, detail="No inventory data available")

    avg_unit_cost = sum(item["unit_cost"] for item in inventory_items) / len(inventory_items)
    inventory_by_sku = {item["sku"]: item for item in inventory_items}

    scored = []
    for forecast in demand_forecasts:
        sku = forecast["item_sku"]
        match = inventory_by_sku.get(sku)
        if match:
            unit_cost = float(match["unit_cost"])
            quantity_on_hand = int(match["quantity_on_hand"])
            reorder_point = int(match["reorder_point"])
            price_estimated = False
        else:
            unit_cost = round(avg_unit_cost, 2)
            quantity_on_hand = 0
            reorder_point = 0
            price_estimated = True

        forecasted = int(forecast["forecasted_demand"])
        shortage = max(0, forecasted - quantity_on_hand)
        reorder_breach = max(0, reorder_point - quantity_on_hand)
        trend_weight = TREND_WEIGHTS.get(forecast["trend"].lower(), 1.0)
        priority_score = trend_weight * (shortage + 2 * reorder_breach + 0.1 * forecasted)

        suggested_quantity = max(forecasted - quantity_on_hand, reorder_point)
        if suggested_quantity <= 0:
            suggested_quantity = forecasted

        scored.append({
            "sku": sku,
            "name": forecast["item_name"],
            "trend": forecast["trend"],
            "unit_cost": round(unit_cost, 2),
            "suggested_quantity": suggested_quantity,
            "price_estimated": price_estimated,
            "priority_score": round(priority_score, 2),
        })

    scored.sort(key=lambda r: r["priority_score"], reverse=True)

    remaining = budget
    recommendations: List[RestockRecommendation] = []
    for row in scored:
        qty = row["suggested_quantity"]
        cost = row["unit_cost"]
        if cost <= 0:
            continue
        line_total = qty * cost
        if line_total > remaining:
            qty = int(remaining // cost)
            if qty < 1:
                continue
            line_total = qty * cost
        recommendations.append(RestockRecommendation(
            sku=row["sku"],
            name=row["name"],
            trend=row["trend"],
            unit_cost=cost,
            suggested_quantity=qty,
            line_total=round(line_total, 2),
            price_estimated=row["price_estimated"],
            priority_score=row["priority_score"],
        ))
        remaining -= line_total

    total_cost = round(sum(r.line_total for r in recommendations), 2)
    return RestockRecommendationsResponse(
        budget=budget,
        recommendations=recommendations,
        total_cost=total_cost,
        remaining_budget=round(budget - total_cost, 2),
    )


@app.post("/api/restocking/orders", response_model=Order, status_code=201)
def submit_restocking_order(payload: SubmitRestockingRequest):
    """Submit a restocking order. Appends to the in-memory orders list.

    Restart of the server clears submitted orders (no disk persistence).
    """
    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required")

    existing_rst = [o for o in orders if o.get("order_number", "").startswith("RST-2025-")]
    next_seq = 1
    for o in existing_rst:
        try:
            seq = int(o["order_number"].split("-")[-1])
            next_seq = max(next_seq, seq + 1)
        except (ValueError, IndexError):
            continue

    next_id = 1
    for o in orders:
        try:
            next_id = max(next_id, int(o["id"]) + 1)
        except (ValueError, KeyError):
            continue

    now = datetime.now()
    order_date = now.isoformat(timespec="seconds")
    expected_delivery = (now + timedelta(days=RESTOCK_LEAD_TIME_DAYS)).isoformat(timespec="seconds")

    items_dicts = [item.model_dump() for item in payload.items]
    total_value = round(sum(i["quantity"] * i["unit_price"] for i in items_dicts), 2)

    new_order = {
        "id": str(next_id),
        "order_number": f"RST-2025-{next_seq:04d}",
        "customer": "Internal Restock",
        "items": items_dicts,
        "status": "Submitted",
        "order_date": order_date,
        "expected_delivery": expected_delivery,
        "total_value": total_value,
        "actual_delivery": None,
        "warehouse": None,
        "category": None,
        "source": "restock",
    }
    orders.append(new_order)
    return new_order


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
