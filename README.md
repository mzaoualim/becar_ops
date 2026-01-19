# Bécar – Operational Controller Cockpit (Streamlit Demo)

A **password‑protected Streamlit demo** inspired by the *Contrôleur opérationnel (Bécar inc.)* role.

What it demonstrates:

- Operational KPIs (**cost/hour, cost/m³, cost/km**)
- Profitability & variance analysis (activity/contract/team/equipment)
- Asset optimization recommendations
- CAPA‑style action plan (who/what/when/status) + traceability
- MIR / maintenance system readiness (import template + quality checks + KPIs)

> ⚠️ The app uses **synthetic data by default**. Do not upload confidential data unless you have explicit permission and it is anonymized.

## Run locally

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows (cmd)
.venv\Scripts\activate.bat

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# Set password (recommended)
# Windows PowerShell:
#   $env:APP_PASSWORD = "your_password"
# macOS/Linux:
#   export APP_PASSWORD="your_password"

streamlit run app.py
```

## Deploy to Streamlit Community Cloud

See `docs/DEPLOY_GUIDE.md`.

## Folder structure

- `app.py` – main Streamlit app
- `src/` – data generation, KPIs, quality checks, exports, i18n, auth
- `data/` – sample synthetic datasets + CSV templates
- `docs/` – demo script + deploy guide + real data guide
