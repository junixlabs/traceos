---
id: system.ecommerce.contexts
type: contexts
dimensions:
  - name: env
    values: [production, staging]
  - name: tenant
    values: [a, b]
    note: Tenant A is on the v2 gateway rollout; tenant B is not.
---

## Note

Context selects which assertion applies. It never forks the graph (INV-008).
