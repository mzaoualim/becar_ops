# Using real (anonymized) data

You can replace synthetic data with a CSV extract **only if** you have permission.

## Recommended minimal extract for Ops Runs

- date
- subsidiary
- activity
- contract
- team
- equipment_id
- hours_operated
- km_driven
- m3_moved
- revenue
- fuel_cost
- labor_cost
- maintenance_cost
- overhead_cost
- downtime_hours

No names, phone numbers, driver IDs, or addresses are required.

## MIR events (optional)

- equipment_id
- event_date
- event_type (preventive/corrective)
- labor_hours
- parts_cost
- downtime_hours

## Mapping
The app can auto‑normalize common column names, but the safest approach is to use the templates in `data/`.
