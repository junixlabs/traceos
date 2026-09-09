---
id: system.ecommerce
type: system
name: E-Commerce Platform
domains: [order, payment, inventory, notification]
staleness_window_days: 90
---

## Boundary

Everything in this repository. The payment gateway, the email provider and the fraud
analyst are outside it — none of their behavior can be changed by editing this repo
(spec §3.1).
