# Career Venture Lab — TEAM-ROB (Pathway ROB-2: Precalculus, Advanced)

**Business:** Robotics Kit and Repair Studio (`ROB-2`)  
**Course:** Precalculus | **Approved Level:** Advanced | **Team ID:** `TEAM-ROB`

## Stage 1 Status
- **Implemented (Stage 1):** Overview, Inputs & Funding, Deterministic Operations & Monthly Ledger Engine, Precalculus Math Skills & Levels Panel (Foundation, Applied, Advanced), Durable Save/Load JSON & CSV Export, Fixture Test Runner (`sample_data/monthly_fixture.csv`), and Automated Unit Tests (`tests/test_rob_stage1.py`).
- **Scheduled for Later Stages (Not Yet Implemented):** Stage 2 (Departmental AI Assistant Tab, Full Report Center, Costed Marketing Studio), Stage 3 (Snapshot Practice Assessment & Cross-Course Panel), Stage 4 (Optional Storefront).

## Local Setup & Verification
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run automated mathematical and ledger acceptance tests:
   ```bash
   pytest -v
   ```
3. Launch the Streamlit application locally:
   ```bash
   streamlit run app.py
   ```

## Render Deployment Command
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```
*(Note: Render disks are ephemeral by default. Always export your `snapshot.json` via the Save/Load panel before closing or redeploying.)*
