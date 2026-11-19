import json
import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ---------------------------------------------------------------------------
# PAGE CONFIG & CONSTANTS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Career Venture Lab | TEAM-ROB (ROB-2)",
    page_icon="🤖",
    layout="wide",
)

TEAM_ID = "TEAM-ROB"
PATHWAY_ID = "ROB-2"
COURSE = "Precalculus"
BUSINESS_NAME = "Robotics Kit and Repair Studio"
PRIMARY_OFFERING = "Introductory robot kit"


def to_money(val) -> Decimal:
    """Convert numeric input to exact 2-decimal Decimal USD."""
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt_usd(val) -> str:
    d = to_money(val)
    sign = "-" if d < 0 else ""
    return f"{sign}${abs(d):,.2f}"


# ---------------------------------------------------------------------------
# DETERMINISTIC ROB ENGINE (HANDBOOK PP. 78-80)
# ---------------------------------------------------------------------------
def get_default_state() -> dict:
    return {
        "team_id": TEAM_ID,
        "course": COURSE,
        "pathway_id": PATHWAY_ID,
        "snapshot_id": "snap_ROB2_v1",
        "state_version": 1,
        "simulation_date": "2027-01-31",
        "base_period": "Monthly",
        "working_days": 20,
        "currency": "USD",
        "selected_level": "Advanced",
        "teacher_approved_skills": [
            "Rational Average Cost",
            "Composed Price-Demand-Profit Functions",
            "Seasonal Trigonometric / Growth Demand Modeling",
        ],
        "assumptions": [
            "Fictional teaching baseline defaults from Career Venture Lab Handbook (ROB-2).",
            "Simplified accrual model: immediate customer payment; taxes, interest, and depreciation disabled at baseline.",
            "Components are expensed when consumed on attempted kits; cash outflow occurs upon restock.",
        ],
        "sources": ["Career Venture Lab Student Handbook (November 2026), Pages 26 & 78-82"],
        "offerings": [
            {
                "offering_id": "OFF-ROB-01",
                "name": PRIMARY_OFFERING,
                "unit": "kit",
                "price": 120.00,
                "demand_rule": "q(p) = max(0, 2*D0 - (D0/p0)*p)",
                "capacity_rule": "floor(staff_hours / hours_per_unit)",
            }
        ],
        "funding": {
            "owner_contribution": 12000.00,
            "equipment_assets": 4000.00,
            "pre_opening_expense": 0.00,
            "opening_inventory_value": 3000.00,
            "opening_cash": 5000.00,
            "retained_earnings": 0.00,
            "loan_principal": 0.00,
            "interest": 0.00,
            "additional_capex": 0.00,
        },
        "inputs": {
            "base_price": 120.00,
            "D0": 40,
            "staff_hours": 90.0,
            "hours_per_unit": 3.0,
            "opening_stock_units": 100,
            "component_unit_cost": 30.00,
            "restock_units": 0,
            "defect_rate": 0.0,
            "ad_cost": 0.00,
            "refund_amount": 0.00,
            "random_seed": 2027,
        },
        "cost_lines": {
            "variable_per_unit": {
                "components_COGS": 30.00,
                "assembly_labor": 20.00,
                "packaging": 10.00,
                "warranty_consumables": 5.00,
            },
            "monthly_fixed": {
                "workspace": 250.00,
                "software": 100.00,
                "equipment_maintenance": 150.00,
                "admin": 100.00,
            },
        },
        "current_balances": {
            "cash": 5000.00,
            "stock_units": 100,
            "inventory_value": 3000.00,
            "equipment_assets": 4000.00,
            "debt": 0.00,
            "equity": 12000.00,
            "retained_earnings": 0.00,
        },
        "ledger": [],
        "executed_run_ids": [],
        "campaigns": [],
        "decisions": [],
    }


def compute_monthly_step(
    state: dict,
    requested: int,
    month_label: str,
    run_id: str,
    capacity_override: int | None = None,
    ad_cost_override: float | None = None,
) -> dict:
    """Pure deterministic ROB monthly calculation matching Handbook pp. 79-80."""
    inp = state["inputs"]
    bal = state["current_balances"]
    v_lines = state["cost_lines"]["variable_per_unit"]
    f_lines = state["cost_lines"]["monthly_fixed"]

    price = to_money(inp["base_price"])
    comp_unit_cost = to_money(v_lines["components_COGS"])
    noncomp_unit_cost = to_money(
        v_lines["assembly_labor"] + v_lines["packaging"] + v_lines["warranty_consumables"]
    )
    var_per_unit = comp_unit_cost + noncomp_unit_cost  # $65.00 at baseline
    fixed_expense = to_money(sum(f_lines.values()))  # $600.00 at baseline

    ad_cost = to_money(ad_cost_override if ad_cost_override is not None else inp["ad_cost"])
    refund_amount = to_money(inp["refund_amount"])
    restock_units = int(inp["restock_units"])
    defect_rate = float(inp["defect_rate"])

    if capacity_override is not None:
        capacity = int(capacity_override)
        mode = "Fixture Override Mode"
    else:
        capacity = math.floor(float(inp["staff_hours"]) / float(inp["hours_per_unit"]))
        mode = "Normal Resource Mode"

    opening_stock = int(bal["stock_units"])
    available_stock = opening_stock + restock_units
    attempted = min(int(requested), capacity, available_stock)
    failed = math.floor(attempted * defect_rate)
    sold = attempted - failed
    unserved_demand = max(0, int(requested) - attempted)

    revenue = (price * Decimal(sold)) - refund_amount
    component_expense = comp_unit_cost * Decimal(attempted)
    noncomponent_expense = noncomp_unit_cost * Decimal(attempted)
    variable_expense = var_per_unit * Decimal(attempted)
    total_expense = variable_expense + fixed_expense + ad_cost
    operating_profit = revenue - total_expense

    # Cash rule for Robotics: component cash outflow occurs on restock; noncomponent paid on attempted
    restock_cash_outflow = comp_unit_cost * Decimal(restock_units)
    opening_cash = to_money(bal["cash"])
    closing_cash = (
        opening_cash
        + revenue
        - restock_cash_outflow
        - noncomponent_expense
        - fixed_expense
        - ad_cost
    )

    ending_stock = available_stock - attempted
    ending_inventory_value = comp_unit_cost * Decimal(ending_stock)

    return {
        "run_id": run_id,
        "month": month_label,
        "mode": mode,
        "requested": int(requested),
        "capacity": capacity,
        "attempted": attempted,
        "failed": failed,
        "sold": sold,
        "unserved_demand": unserved_demand,
        "revenue": float(revenue),
        "component_expense": float(component_expense),
        "noncomponent_expense": float(noncomponent_expense),
        "variable_expense": float(variable_expense),
        "fixed_expense": float(fixed_expense),
        "ad_cost": float(ad_cost),
        "total_expense": float(total_expense),
        "operating_profit": float(operating_profit),
        "opening_cash": float(opening_cash),
        "closing_cash": float(closing_cash),
        "opening_stock": opening_stock,
        "restock_units": restock_units,
        "ending_stock": ending_stock,
        "ending_inventory_value": float(ending_inventory_value),
        "state_version": state["state_version"],
    }


def commit_step_to_ledger(state: dict, step_result: dict) -> tuple[bool, str]:
    """Commit an approved step to the dated ledger with duplicate run_id protection."""
    run_id = step_result["run_id"]
    if run_id in state["executed_run_ids"]:
        return False, f"Duplicate run_id '{run_id}' rejected: transaction already recorded."

    new_version = state["state_version"] + 1
    step_result["state_version"] = new_version
    step_result["committed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    state["ledger"].append(step_result)
    state["executed_run_ids"].append(run_id)
    state["state_version"] = new_version
    state["snapshot_id"] = f"snap_ROB2_v{new_version}"
    state["simulation_date"] = f"{step_result['month']}-28"

    # Update persistent balances
    state["current_balances"]["cash"] = step_result["closing_cash"]
    state["current_balances"]["stock_units"] = step_result["ending_stock"]
    state["current_balances"]["inventory_value"] = step_result["ending_inventory_value"]
    state["current_balances"]["retained_earnings"] = round(
        state["current_balances"]["retained_earnings"] + step_result["operating_profit"], 2
    )
    state["current_balances"]["equity"] = round(
        state["funding"]["owner_contribution"] + state["current_balances"]["retained_earnings"], 2
    )
    return True, f"Committed {run_id} (State advanced to v{new_version})."


def validate_and_load_snapshot(raw_json: str) -> tuple[bool, str, dict | None]:
    """Validate team_id, schema, nonnegative numbers, and state_version on import."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return False, f"Invalid JSON format: {exc}", None

    required_keys = [
        "team_id",
        "course",
        "pathway_id",
        "snapshot_id",
        "state_version",
        "inputs",
        "cost_lines",
        "current_balances",
        "ledger",
    ]
    missing = [k for k in required_keys if k not in data]
    if missing:
        return False, f"Missing required snapshot fields: {', '.join(missing)}", None

    if data.get("team_id") != TEAM_ID:
        return (
            False,
            f"Team ID mismatch: expected '{TEAM_ID}', got '{data.get('team_id')}'. Import rejected.",
            None,
        )

    if data.get("pathway_id") != PATHWAY_ID:
        return (
            False,
            f"Pathway mismatch: expected '{PATHWAY_ID}', got '{data.get('pathway_id')}'. Import rejected.",
            None,
        )

    if int(data.get("state_version", 0)) < 1:
        return False, "Invalid state_version: must be >= 1.", None

    if data["current_balances"].get("stock_units", 0) < 0:
        return False, "Negative stock units detected. Import rejected.", None

    return True, f"Snapshot '{data['snapshot_id']}' (v{data['state_version']}) validated.", data


# ---------------------------------------------------------------------------
# INITIALIZE SESSION STATE
# ---------------------------------------------------------------------------
if "biz_state" not in st.session_state:
    st.session_state.biz_state = get_default_state()

state = st.session_state.biz_state

# ---------------------------------------------------------------------------
# HEADER & STAGE ROADMAP BANNER
# ---------------------------------------------------------------------------
st.title(f"🤖 Career Venture Lab — {BUSINESS_NAME}")
st.caption(
    f"**Team ID:** `{state['team_id']}` | **Pathway:** `{state['pathway_id']}` | "
    f"**Course:** `{state['course']}` | **Approved Level:** `{state['selected_level']}` | "
    f"**Snapshot:** `{state['snapshot_id']}` (`v{state['state_version']}`)"
)

with st.expander("📌 Stage 1 Build Status & Module Roadmap (Plain-Language Guide)", expanded=False):
    st.markdown(
        """
        - **Stage 1 (Active Now):** Overview, Inputs & Funding, Operations & Monthly Engine, Precalculus Math Skills & Levels Panel, Durable Save/Load JSON, and Fixture Tests.
        - **Stage 2 (Not Yet Implemented):** Departmental AI Assistant Tab (Finance, Operations, Marketing, Reviewer), Full Report Center, Costed Marketing Studio.
        - **Stage 3 (Not Yet Implemented):** Snapshot Practice Assessment & Cross-Course Connections Panel.
        - **Stage 4 (Optional / Not Yet Implemented):** Fictional Demonstration Storefront.
        """
    )

# ---------------------------------------------------------------------------
# NAVIGATION TABS (STAGE 1)
# ---------------------------------------------------------------------------
tabs = st.tabs(
    [
        "1. Overview & Ledger",
        "2. Inputs & Funding",
        "3. Operations & Monthly Run",
        "4. Math Skills & Levels (Precalculus)",
        "5. Save / Load & Fixture Tests",
    ]
)

# ===========================================================================
# TAB 1: OVERVIEW & LEDGER
# ===========================================================================
with tabs[0]:
    st.subheader("Business Health Snapshot (Actual Recorded State)")
    st.info(
        "**Plain-Language Summary:** Your **Cash** is spendable money in the bank. Your **Inventory** is the dollar value of unassembled robot parts sitting on your shelves. "
        "Your **Ledger** below is your chronological receipt book—only transactions you explicitly approve are recorded here."
    )

    bal = state["current_balances"]
    inp = state["inputs"]
    cap_now = math.floor(inp["staff_hours"] / inp["hours_per_unit"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Spendable Cash", fmt_usd(bal["cash"]))
    c2.metric("Parts Stock on Hand", f"{bal['stock_units']} sets", fmt_usd(bal["inventory_value"]))
    c3.metric("Monthly Build Ceiling", f"{cap_now} kits/mo", f"{inp['staff_hours']} hrs ÷ {inp['hours_per_unit']} hrs/kit")
    c4.metric("Total Assets", fmt_usd(bal["cash"] + bal["inventory_value"] + bal["equipment_assets"]))
    c5.metric("Owner Equity", fmt_usd(bal["equity"]), f"Retained: {fmt_usd(bal['retained_earnings'])}")

    st.divider()
    st.subheader("Chronological Event Ledger (Actual Recorded Transactions)")
    if not state["ledger"]:
        st.warning("No monthly simulation rounds committed yet. Preview and approve a run in Tab 3 or run the Fixture Tests in Tab 5.")
    else:
        df_ledger = pd.DataFrame(state["ledger"])
        st.dataframe(df_ledger, use_container_width=True)

        # Daily / Monthly / Yearly Aggregation View
        view_horizon = st.radio(
            "Aggregation View (Derived from Dated Ledger):",
            ["Monthly (Observed Simulated)", "Yearly Summary", "Daily Modeled Allocation (20 Working Days/Mo)"],
            horizontal=True,
        )
        if view_horizon == "Yearly Summary":
            df_yr = df_ledger.copy()
            df_yr["year"] = df_yr["month"].str.slice(0, 4)
            agg = df_yr.groupby("year", as_index=False)[
                ["requested", "attempted", "failed", "sold", "revenue", "total_expense", "operating_profit"]
            ].sum()
            st.dataframe(agg, use_container_width=True)
        elif view_horizon.startswith("Daily"):
            st.caption("⚠️ Daily values below are **modeled allocations** (monthly totals ÷ 20 working days), not observed daily sales.")
            df_day = df_ledger[["month", "sold", "revenue", "total_expense", "operating_profit"]].copy()
            for col in ["sold", "revenue", "total_expense", "operating_profit"]:
                df_day[f"daily_alloc_{col}"] = (df_day[col] / state["working_days"]).round(2)
            st.dataframe(df_day, use_container_width=True)

        csv_bytes = df_ledger.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Export Ledger as CSV",
            data=csv_bytes,
            file_name=f"{TEAM_ID}_{PATHWAY_ID}_ledger_v{state['state_version']}.csv",
            mime="text/csv",
        )

# ===========================================================================
# TAB 2: INPUTS & FUNDING
# ===========================================================================
with tabs[1]:
    st.subheader("Editable Business Assumptions & Startup Capital")
    st.caption("All baseline numbers are fictional teaching assumptions from Handbook Page 78. Changes update scenarios immediately; ledger balances update only when a round is approved.")

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("#### Pricing, Demand & Production Limits")
        inp["base_price"] = st.number_input("Base Kit Price ($/kit)", min_value=1.0, value=float(inp["base_price"]), step=5.0)
        inp["D0"] = st.number_input("Baseline Monthly Demand D0 (kits/mo)", min_value=0, value=int(inp["D0"]), step=1)
        inp["staff_hours"] = st.number_input("Monthly Staff Build Hours", min_value=0.0, value=float(inp["staff_hours"]), step=5.0)
        inp["hours_per_unit"] = st.number_input("Build Hours per Kit", min_value=0.1, value=float(inp["hours_per_unit"]), step=0.5)
        inp["defect_rate"] = st.slider("Build Defect Rate (0.00 = 0%, 0.20 = 20%)", 0.0, 1.0, float(inp["defect_rate"]), 0.01)
        inp["restock_units"] = st.number_input("New Parts Sets Purchased This Month (Restock)", min_value=0, value=int(inp["restock_units"]), step=5)
        inp["ad_cost"] = st.number_input("Own-Business Advertising Expense ($)", min_value=0.0, value=float(inp["ad_cost"]), step=25.0)

    with col_right:
        st.markdown("#### Per-Kit Variable Costs & Monthly Fixed Costs")
        v_lines = state["cost_lines"]["variable_per_unit"]
        v_lines["components_COGS"] = st.number_input("Components COGS ($/attempted kit)", min_value=0.0, value=float(v_lines["components_COGS"]), step=1.0)
        v_lines["assembly_labor"] = st.number_input("Assembly Labor ($/attempted kit)", min_value=0.0, value=float(v_lines["assembly_labor"]), step=1.0)
        v_lines["packaging"] = st.number_input("Packaging ($/attempted kit)", min_value=0.0, value=float(v_lines["packaging"]), step=1.0)
        v_lines["warranty_consumables"] = st.number_input("Warranty & Rework Consumables ($/attempted kit)", min_value=0.0, value=float(v_lines["warranty_consumables"]), step=1.0)
        total_v = sum(v_lines.values())
        st.success(f"**Total Variable Cost per Attempted Kit:** {fmt_usd(total_v)}")

        f_lines = state["cost_lines"]["monthly_fixed"]
        f_lines["workspace"] = st.number_input("Workspace Rent ($/mo)", min_value=0.0, value=float(f_lines["workspace"]), step=25.0)
        f_lines["software"] = st.number_input("Software ($/mo)", min_value=0.0, value=float(f_lines["software"]), step=25.0)
        f_lines["equipment_maintenance"] = st.number_input("Equipment Maintenance ($/mo)", min_value=0.0, value=float(f_lines["equipment_maintenance"]), step=25.0)
        f_lines["admin"] = st.number_input("Admin & Insurance ($/mo)", min_value=0.0, value=float(f_lines["admin"]), step=25.0)
        total_f = sum(f_lines.values())
        st.success(f"**Total Monthly Fixed Cost:** {fmt_usd(total_f)}")

    st.divider()
    st.markdown("#### Startup Opening Balance Sheet (Handbook Page 78)")
    fnd = state["funding"]
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Owner Contribution (Equity)", fmt_usd(fnd["owner_contribution"]))
    b2.metric("Tools & Test Equipment", fmt_usd(fnd["equipment_assets"]))
    b3.metric("Opening Parts Inventory (100 sets)", fmt_usd(fnd["opening_inventory_value"]))
    b4.metric("Post-Startup Spendable Cash", fmt_usd(fnd["opening_cash"]))

    if st.button("🔄 Reset Entire Simulation to Opening Baseline State"):
        st.session_state.biz_state = get_default_state()
        st.rerun()

# ===========================================================================
# TAB 3: OPERATIONS & MONTHLY RUN (HUMAN-IN-THE-LOOP APPROVAL)
# ===========================================================================
with tabs[2]:
    st.subheader("Operations Planner & Monthly Simulation Step")
    st.info(
        "**How Robotics Fulfillment Works (Plain Language):** Your team can only build kits up to your lowest bottleneck: "
        "**(1) Customer Requests**, **(2) Staff Build Capacity** (`floor(staff_hours ÷ hours_per_unit)`), or **(3) Available Parts Sets** (`opening_stock + restock`). "
        "If any attempted kits fail quality checks (`defect_rate`), you still pay the $65/kit build cost, but those broken kits earn $0 revenue."
    )

    col_sim1, col_sim2, col_sim3 = st.columns(3)
    with col_sim1:
        sim_month = st.text_input("Simulation Month (YYYY-MM)", value="2027-01")
    with col_sim2:
        sim_run_id = st.text_input("Unique Run ID (Duplicate Protection)", value=f"RUN-{sim_month}-v{state['state_version']}")
    with col_sim3:
        sim_requested = st.number_input("Requested Kits This Month", min_value=0, value=int(state["inputs"]["D0"]), step=1)

    preview = compute_monthly_step(state, requested=sim_requested, month_label=sim_month, run_id=sim_run_id)

    st.markdown("#### Scenario Preview (Not Yet Committed to Ledger)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Build Capacity / Attempted", f"{preview['capacity']} / {preview['attempted']} kits", f"Unserved Demand: {preview['unserved_demand']}")
    m2.metric("Failed / Sold Kits", f"{preview['failed']} failed / {preview['sold']} sold")
    m3.metric("Revenue / Operating Profit", fmt_usd(preview["revenue"]), f"Profit: {fmt_usd(preview['operating_profit'])}")
    m4.metric("Projected Closing Cash / Stock", fmt_usd(preview["closing_cash"]), f"Stock: {preview['ending_stock']} sets")

    # Bottleneck diagnostic
    cap_limit = preview["capacity"]
    stock_limit = preview["opening_stock"] + preview["restock_units"]
    if preview["attempted"] == 0:
        bottleneck = "Zero demand or zero capacity/stock."
    elif cap_limit <= sim_requested and cap_limit <= stock_limit:
        bottleneck = f"Staff Build Hours ({cap_limit} kits max)"
    elif stock_limit <= sim_requested and stock_limit <= cap_limit:
        bottleneck = f"Component Parts Inventory ({stock_limit} sets available)"
    else:
        bottleneck = f"Customer Demand ({sim_requested} kits requested)"
    st.write(f"**Active Bottleneck:** {bottleneck} | **Stock Cover After Month:** {preview['ending_stock']} sets ({fmt_usd(preview['ending_inventory_value'])})")

    # Transfer check prompt
    student_prediction = st.text_input(
        "Transfer Check (Required Before Approving): Predict what happens to profit and cash if you approve this step:",
        placeholder="e.g., Selling 30 kits at $120 yields $3,600 revenue minus $2,550 total expense = $1,050 profit...",
    )

    if st.button("✅ Student Approval: Commit Step to Ledger & Advance State", type="primary"):
        if not student_prediction.strip():
            st.error("Please enter your brief prediction above before approving the simulation step.")
        else:
            ok, msg = commit_step_to_ledger(state, preview)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

# ===========================================================================
# TAB 4: MATH SKILLS & LEVELS PANEL (PRECALCULUS)
# ===========================================================================
with tabs[3]:
    st.subheader("Math Skills & Challenge Level Panel — Precalculus (ROB-2)")
    level = st.selectbox(
        "Selected Challenge Level (Teacher Approval Required to Change):",
        ["Foundation", "Applied", "Advanced"],
        index=["Foundation", "Applied", "Advanced"].index(state["selected_level"]),
    )
    state["selected_level"] = level

    p0 = float(state["inputs"]["base_price"])
    D0 = float(state["inputs"]["D0"])
    v = float(sum(state["cost_lines"]["variable_per_unit"].values()))
    F = float(sum(state["cost_lines"]["monthly_fixed"].values()))
    cap = math.floor(float(state["inputs"]["staff_hours"]) / float(state["inputs"]["hours_per_unit"]))

    if level == "Foundation":
        st.markdown("### Foundation Mode: Rational Average Cost Function $A(s)$")
        st.info(
            "**Plain-Language Meaning:** Even if you build 1 kit, you still pay $600 in monthly rent/software, making that 1 kit cost $665! "
            "As you build more kits up to your 30-kit limit, that $600 fixed cost gets shared across more kits, pulling average cost down toward $65/kit."
        )
        st.latex(r"C(s) = F + v \cdot s = 600 + 65s \quad 	ext{and} \quad A(s) = rac{C(s)}{s} = rac{F}{s} + v, \quad 0 < s \le 	ext{capacity}")
        st.markdown(
            f"- **Practical Domain:** $0 < s \le {cap}$ kits (at $s = 0$, $A(0)$ is **undefined** — vertical asymptote at $s = 0$)
"
            f"- **Horizontal Behavior:** As $s$ grows large, $A(s)$ approaches the horizontal asymptote $y = {fmt_usd(v)}$/kit
"
            f"- **At Full Capacity ($s = {cap}$):** $A({cap}) = \frac{{{F:.0f}}}{{{cap}}} + {v:.0f} = {fmt_usd(F/cap + v)}$ per kit"
        )

        s_vals = np.linspace(1, max(2, cap), 100)
        a_vals = F / s_vals + v
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s_vals, y=a_vals, mode="lines", name="Average Cost A(s)", line=dict(color="#1f77b4", width=3)))
        fig.add_hline(y=v, line_dash="dash", line_color="#d62728", annotation_text=f"Horizontal Asymptote y = ${v:.0f}")
        fig.add_vline(x=cap, line_dash="dot", line_color="#2ca02c", annotation_text=f"Capacity Limit s = {cap}")
        fig.update_layout(
            title=f"ROB-2 Average Cost Curve A(s) | Team {TEAM_ID} | Snapshot {state['snapshot_id']}",
            xaxis_title="Completed Kits (s)",
            yaxis_title="Average Cost per Kit ($ USD)",
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

        df_avg = pd.DataFrame({
            "Kits (s)": [0, 1, 5, 10, 15, 20, 25, cap],
            "Total Cost C(s) ($)": [F] + [round(F + v * k, 2) for k in [1, 5, 10, 15, 20, 25, cap]],
            "Average Cost A(s) ($/kit)": ["UNDEFINED (Vertical Asymptote)"] + [round(F / k + v, 2) for k in [1, 5, 10, 15, 20, 25, cap]],
        })
        st.dataframe(df_avg, use_container_width=True)

    elif level == "Applied":
        st.markdown("### Applied Mode: Composed Price-Demand-Profit Functions")
        st.info(
            "**Plain-Language Meaning:** Raising your price lowers customer demand $q(p)$. Because your workshop can only build 30 kits max, "
            "any price low enough to attract more than 30 buyers hits a flat ceiling (`s(p) = min(capacity, q(p))`). That creates a sharp corner (breakpoint) in your profit curve!"
        )
        b_slope = D0 / p0
        p_break = p0 * (2.0 - cap / D0) if D0 > 0 else 0.0
        st.latex(r"q(p) = \max\left(0, 2D_0 - rac{D_0}{p_0}pight), \quad s(p) = \min(	ext{capacity}, q(p)), \quad P(p) = p\cdot s(p) - (F + v\cdot s(p))")
        st.markdown(
            f"- **Price Domain:** $\$0 \le p \le {fmt_usd(2*p0)}$ | **Demand Slope:** $-{b_slope:.5f}$ kits per dollar
"
            f"- **Capacity Breakpoint Price:** $p = {fmt_usd(p_break)}$ (below this price, sales are capped at {cap} kits)
"
            f"- **Continuous vs. Integer Rule:** Graphs below show continuous models; actual ledger transactions round completed sales down to whole kits."
        )

        test_price = st.slider("Interactive Price Explorer ($/kit):", 0.0, float(2 * p0), float(p0), 5.0)
        q_cont = max(0.0, 2 * D0 - b_slope * test_price)
        s_cont = min(float(cap), q_cont)
        s_int = math.floor(s_cont)
        prof_cont = test_price * s_cont - (F + v * s_cont)
        prof_int = test_price * s_int - (F + v * s_int)

        k1, k2, k3 = st.columns(3)
        k1.metric("Unconstrained Demand q(p)", f"{q_cont:.2f} kits")
        k2.metric("Realized Sales s(p) (Continuous / Integer)", f"{s_cont:.2f} / {s_int} kits")
        k3.metric("Profit (Continuous / Whole-Kit)", f"{fmt_usd(prof_cont)} / {fmt_usd(prof_int)}")

        p_grid = np.linspace(0, 2 * p0, 200)
        q_grid = np.maximum(0, 2 * D0 - b_slope * p_grid)
        s_grid = np.minimum(cap, q_grid)
        r_grid = p_grid * s_grid
        c_grid = F + v * s_grid
        prof_grid = r_grid - c_grid

        fig = make_subplots(rows=1, cols=2, subplot_titles=("Demand q(p) vs. Capped Sales s(p)", "Composed Revenue, Cost & Profit P(p)"))
        fig.add_trace(go.Scatter(x=p_grid, y=q_grid, name="Demand q(p)", line=dict(dash="dash", color="#7f7f7f")), row=1, col=1)
        fig.add_trace(go.Scatter(x=p_grid, y=s_grid, name="Capped Sales s(p)", line=dict(color="#1f77b4", width=3)), row=1, col=1)
        fig.add_vline(x=p_break, line_dash="dot", line_color="#ff7f0e", row=1, col=1)

        fig.add_trace(go.Scatter(x=p_grid, y=r_grid, name="Revenue R(p)", line=dict(color="#2ca02c")), row=1, col=2)
        fig.add_trace(go.Scatter(x=p_grid, y=c_grid, name="Cost C(s(p))", line=dict(color="#d62728")), row=1, col=2)
        fig.add_trace(go.Scatter(x=p_grid, y=prof_grid, name="Profit P(p)", line=dict(color="#9467bd", width=3)), row=1, col=2)
        fig.add_hline(y=0, line_color="black", line_width=1, row=1, col=2)
        fig.update_layout(height=430, title=f"ROB-2 Composed Functions | Team {TEAM_ID} | Snapshot {state['snapshot_id']}")
        st.plotly_chart(fig, use_container_width=True)

    else:  # Advanced
        st.markdown("### Advanced Mode: Seasonal Trigonometric Demand or Exponential Growth Target")
        ext_choice = st.radio(
            "Select ONE Teacher-Approved Precalculus Extension:",
            [
                "Trigonometric Seasonal Model: D(t) = D0 * (1 + 0.20 * sin(2*pi*(t-1)/12))",
                "Exponential Growth Target Model: D(t) = D0 * (1 + r)^(t-1)",
            ],
        )

        if ext_choice.startswith("Trigonometric"):
            st.info(
                "**Plain-Language Meaning:** School robotics clubs order more kits in spring (Month 4 peak = +20%) and fewer in autumn (Month 10 dip = -20%). "
                "Even when demand jumps to 48 kits in Month 4, your 30-kit workshop limit clips actual sales at 30 kits—meaning 18 orders go unfulfilled unless you add capacity."
            )
            st.latex(r"D(t) = D_0 \left(1 + 0.20 \sin\left(rac{2\pi(t-1)}{12}ight)ight), \quad S(t) = \min(	ext{capacity}, \lfloor D(t) floor)")
            months = np.arange(1, 13)
            d_t = D0 * (1.0 + 0.20 * np.sin(2 * np.pi * (months - 1) / 12.0))
            s_t = np.minimum(cap, np.floor(d_t))
            lost_t = np.maximum(0, np.floor(d_t) - s_t)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=months, y=d_t, mode="lines+markers", name="Modeled Seasonal Demand D(t)", line=dict(color="#1f77b4", width=3)))
            fig.add_trace(go.Bar(x=months, y=s_t, name="Realized Sales S(t) (Clipped at Capacity)", marker_color="rgba(44, 160, 44, 0.55)"))
            fig.add_hline(y=cap, line_dash="dash", line_color="#d62728", annotation_text=f"Capacity Ceiling = {cap} kits")
            fig.update_layout(
                title=f"12-Month Seasonal Demand vs. Realized Sales (Assumed ±20% Amplitude) | {TEAM_ID}",
                xaxis_title="Month Index (t = 1..12; Peak at t=4, Min at t=10)",
                yaxis_title="Robotics Kits",
                height=420,
            )
            st.plotly_chart(fig, use_container_width=True)

            df_season = pd.DataFrame({
                "Month (t)": months,
                "Modeled Demand D(t)": np.round(d_t, 2),
                "Floored Demand": np.floor(d_t).astype(int),
                "Realized Sales S(t)": s_t.astype(int),
                "Lost Demand (Unserved)": lost_t.astype(int),
            })
            st.dataframe(df_season, use_container_width=True)
        else:
            st.info(
                "**Plain-Language Meaning:** If marketing grows monthly kit requests by a steady percentage rate $r$, logarithms tell us the exact month $t$ when demand hits your 30-kit capacity ceiling."
            )
            r_rate = st.slider("Assumed Monthly Demand Growth Rate (r):", 0.01, 0.25, 0.05, 0.01)
            start_d = st.number_input("Starting Month 1 Demand:", min_value=1, value=20, step=1)
            months = np.arange(1, 13)
            d_growth = start_d * ((1 + r_rate) ** (months - 1))
            s_growth = np.minimum(cap, np.floor(d_growth))
            t_cap = 1 + math.log(cap / start_d) / math.log(1 + r_rate) if cap > start_d else 1.0
            st.write(f"**Exact Logarithmic Capacity Crossing:** $t = 1 + \frac{{\ln({cap}/{start_d})}}{{\ln(1+{r_rate:.2f})}} = {t_cap:.2f}$ months")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=months, y=d_growth, mode="lines+markers", name="Exponential Demand D(t)"))
            fig.add_trace(go.Bar(x=months, y=s_growth, name="Realized Sales S(t)"))
            fig.add_hline(y=cap, line_dash="dash", line_color="#d62728", annotation_text=f"Capacity = {cap}")
            fig.update_layout(title=f"Exponential Growth vs. Capacity Ceiling | {TEAM_ID}", xaxis_title="Month (t)", yaxis_title="Kits", height=400)
            st.plotly_chart(fig, use_container_width=True)

    st.text_area(
        "Required Student Interpretation & Limitation Note:",
        placeholder="Explain what happens at the domain boundaries/asymptotes and why continuous formulas differ from whole-kit ledger sales...",
    )

# ===========================================================================
# TAB 5: SAVE / LOAD JSON & FIXTURE TESTS
# ===========================================================================
with tabs[4]:
    st.subheader("Durable Save / Load JSON & Handbook Fixture Tests")
    col_sl1, col_sl2 = st.columns(2)

    with col_sl1:
        st.markdown("#### Export Approved Snapshot JSON")
        st.caption("Use this JSON file as your durable save state and attach it to your departmental Gems/Skills.")
        snapshot_json_str = json.dumps(state, indent=2)
        st.download_button(
            "💾 Download Snapshot JSON",
            data=snapshot_json_str.encode("utf-8"),
            file_name=f"{TEAM_ID}_{PATHWAY_ID}_{state['snapshot_id']}.json",
            mime="application/json",
        )

    with col_sl2:
        st.markdown("#### Import / Restore Snapshot JSON")
        uploaded = st.file_uploader("Upload saved snapshot JSON", type=["json"])
        if uploaded is not None:
            raw_txt = uploaded.read().decode("utf-8")
            valid, message, loaded_data = validate_and_load_snapshot(raw_txt)
            if valid and loaded_data is not None:
                st.success(message)
                if st.button("Restore This Snapshot into Active Session"):
                    st.session_state.biz_state = loaded_data
                    st.rerun()
            else:
                st.error(message)

    st.divider()
    st.markdown("### Automated Acceptance & Fixture Replay (Handbook Page 80)")
    st.warning("⚠️ **Fixture Test Mode:** Replays `sample_data/monthly_fixture.csv` using explicit `capacity_override` values to verify ledger math against the handbook answer key.")

    if st.button("▶️ Run 3-Month ROB Fixture Replay & Verification"):
        test_state = get_default_state()
        fixture_rows = [
            {"month": "2027-01", "requested": 40, "capacity_override": 30, "ad_cost": 0, "exp_sold": 30, "exp_rev": 3600, "exp_exp": 2550, "exp_prof": 1050, "exp_cash": 6950, "exp_stock": 70},
            {"month": "2027-02", "requested": 44, "capacity_override": 30, "ad_cost": 100, "exp_sold": 30, "exp_rev": 3600, "exp_exp": 2650, "exp_prof": 950, "exp_cash": 8800, "exp_stock": 40},
            {"month": "2027-03", "requested": 36, "capacity_override": 22, "ad_cost": 0, "exp_sold": 22, "exp_rev": 2640, "exp_exp": 2030, "exp_prof": 610, "exp_cash": 10070, "exp_stock": 18},
        ]
        results_rows = []
        all_pass = True
        for r in fixture_rows:
            step = compute_monthly_step(
                test_state,
                requested=r["requested"],
                month_label=r["month"],
                run_id=f"FIX-{r['month']}",
                capacity_override=r["capacity_override"],
                ad_cost_override=r["ad_cost"],
            )
            commit_step_to_ledger(test_state, step)
            passed = (
                step["sold"] == r["exp_sold"]
                and abs(step["revenue"] - r["exp_rev"]) < 0.01
                and abs(step["total_expense"] - r["exp_exp"]) < 0.01
                and abs(step["operating_profit"] - r["exp_prof"]) < 0.01
                and abs(step["closing_cash"] - r["exp_cash"]) < 0.01
                and step["ending_stock"] == r["exp_stock"]
            )
            all_pass = all_pass and passed
            results_rows.append({
                "Month": r["month"],
                "Sold (Actual / Exp)": f"{step['sold']} / {r['exp_sold']}",
                "Revenue": f"${step['revenue']:,.0f} / ${r['exp_rev']:,.0f}",
                "Total Expense": f"${step['total_expense']:,.0f} / ${r['exp_exp']:,.0f}",
                "Profit": f"${step['operating_profit']:,.0f} / ${r['exp_prof']:,.0f}",
                "Closing Cash": f"${step['closing_cash']:,.0f} / ${r['exp_cash']:,.0f}",
                "Ending Stock": f"{step['ending_stock']} / {r['exp_stock']}",
                "Status": "PASS" if passed else "FAIL",
            })
        st.dataframe(pd.DataFrame(results_rows), use_container_width=True)
        if all_pass:
            st.success("✅ ALL 3 FIXTURE MONTHS PASSED EXACTLY!")
        else:
            st.error("❌ One or more fixture checks failed.")
