# Bike Factory

You run a bike supply chain for one year (52 weeks). Parts flow
Tier 2 Supplier → Tier 1 Supplier → Components → Assembly → Warehouse →
Stores A, B and C. One part becomes one bike. Customers buy at the stores;
whoever finds an empty shelf leaves.

**Goal:** CHF 1M profit (Easy: 800k) while serving ≥ 95% of customers.

**Each week:** queue actions, then `advance()`. Queued actions apply at the
start of the next simulated week.

| Action | Effect |
|---|---|
| `order(site, qty)` | The site's upstream ships `qty` units (after the site's lead time). Tier 2 (Easy: Tier 1) buys raw parts at CHF 150 each. |
| `expand(site)` | +20% capacity, +8% holding cost. CHF 8k, warehouse 12k. Not on Easy. |
| `probe(site)` | CHF 500. May reveal a hidden rule at that site. |
| `note(text)` | Record the hypothesis you are testing. |

**Money:** a bike sells for CHF 450. Shipping costs CHF 4 per unit and leg;
holding stock costs every week; there is a fixed weekly overhead.

**Read:** `observe()`, `observe_site(site)`, `score()`. The world has hidden
rules; you only see their effects until you discover them.
