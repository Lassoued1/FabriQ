TRUNCATE
  costs,
  returns,
  shipments,
  supplier_delays,
  inventory_movements,
  production_batches,
  orders,
  suppliers,
  customers,
  products
RESTART IDENTITY CASCADE;

INSERT INTO products (id, reference, category, price, cost, safety_stock, current_stock, created_at) VALUES
  (1, 'AX-100', 'Acier', 120.00, 78.00, 180, 92, DATE '2025-02-12'),
  (2, 'BX-220', 'Composite', 210.00, 151.00, 90, 260, DATE '2025-04-02'),
  (3, 'CX-310', 'Electronique', 340.00, 240.00, 55, 38, DATE '2025-05-18'),
  (4, 'DX-450', 'Plastique', 75.00, 49.00, 240, 410, DATE '2024-11-24'),
  (5, 'EX-510', 'Mecanique', 480.00, 360.00, 40, 33, DATE '2025-07-09'),
  (6, 'FX-700', 'Assemblage', 155.00, 118.00, 120, 74, DATE '2024-09-17');

-- Customers 1-3 belong to tenant_demo, 4-5 to tenant_acme (multi-tenant demo).
INSERT INTO customers (id, name, region, segment, tenant_id) VALUES
  (1, 'Boden Industrie',   'Nord',  'PME',          'tenant_demo'),
  (2, 'Alpine Equipements','Est',   'ETI',           'tenant_demo'),
  (3, 'Delta Machines',    'Ouest', 'PME',           'tenant_demo'),
  (4, 'Hexa Supply',       'Sud',   'Grand compte',  'tenant_acme'),
  (5, 'Nova Process',      'Nord',  'PME',           'tenant_acme');

INSERT INTO suppliers (id, name, punctuality_rate, lead_time_days) VALUES
  (1, 'ForgeNord', 0.82, 9),
  (2, 'Polymeris', 0.93, 6),
  (3, 'MicroFlux', 0.74, 14),
  (4, 'LogiMetal', 0.88, 11);

WITH months(month_index, month_start) AS (
  VALUES
    (0, DATE '2026-01-01'),
    (1, DATE '2026-02-01'),
    (2, DATE '2026-03-01'),
    (3, DATE '2026-04-01'),
    (4, DATE '2026-05-01'),
    (5, DATE '2026-06-01')
),
demand(product_id, quantities) AS (
  VALUES
    (1, ARRAY[92, 88, 78, 70, 61, 54]),
    (2, ARRAY[36, 42, 48, 55, 62, 70]),
    (3, ARRAY[18, 24, 31, 39, 47, 52]),
    (4, ARRAY[120, 126, 132, 136, 140, 144]),
    (5, ARRAY[12, 16, 19, 23, 28, 34]),
    (6, ARRAY[58, 56, 53, 50, 47, 43])
),
order_source AS (
  SELECT
    ROW_NUMBER() OVER (ORDER BY m.month_index, p.id) AS id,
    ((p.id + m.month_index) % 5) + 1 AS customer_id,
    p.id AS product_id,
    m.month_start + (4 + p.id) AS order_date,
    d.quantities[m.month_index + 1] AS quantity,
    p.price,
    p.cost,
    m.month_index
  FROM months m
  JOIN products p ON TRUE
  JOIN demand d ON d.product_id = p.id
)
-- tenant_id on orders follows the customer's tenant.
INSERT INTO orders (id, customer_id, product_id, order_date, quantity, revenue, cost, tenant_id)
SELECT
  id,
  customer_id,
  product_id,
  order_date,
  quantity,
  ROUND(quantity * price * CASE WHEN product_id IN (1, 6) THEN 1 - (0.015 * month_index) ELSE 1 END, 2),
  ROUND(quantity * cost * (1 + 0.01 * month_index), 2),
  CASE WHEN customer_id IN (4, 5) THEN 'tenant_acme' ELSE 'tenant_demo' END
FROM order_source;

WITH months(month_index, month_start) AS (
  VALUES
    (0, DATE '2026-01-01'),
    (1, DATE '2026-02-01'),
    (2, DATE '2026-03-01'),
    (3, DATE '2026-04-01'),
    (4, DATE '2026-05-01'),
    (5, DATE '2026-06-01')
),
demand(product_id, quantities) AS (
  VALUES
    (1, ARRAY[92, 88, 78, 70, 61, 54]),
    (2, ARRAY[36, 42, 48, 55, 62, 70]),
    (3, ARRAY[18, 24, 31, 39, 47, 52]),
    (4, ARRAY[120, 126, 132, 136, 140, 144]),
    (5, ARRAY[12, 16, 19, 23, 28, 34]),
    (6, ARRAY[58, 56, 53, 50, 47, 43])
)
INSERT INTO costs (id, product_id, period, cost_type, amount)
SELECT
  ROW_NUMBER() OVER (ORDER BY m.month_index, p.id),
  p.id,
  TO_CHAR(m.month_start, 'YYYY-MM'),
  'production',
  ROUND(d.quantities[m.month_index + 1] * p.cost * (0.09 + m.month_index * 0.004), 2)
FROM months m
JOIN products p ON TRUE
JOIN demand d ON d.product_id = p.id;

WITH months(month_index, month_start) AS (
  VALUES
    (0, DATE '2026-01-01'),
    (1, DATE '2026-02-01'),
    (2, DATE '2026-03-01'),
    (3, DATE '2026-04-01'),
    (4, DATE '2026-05-01'),
    (5, DATE '2026-06-01')
),
demand(product_id, quantities) AS (
  VALUES
    (1, ARRAY[92, 88, 78, 70, 61, 54]),
    (2, ARRAY[36, 42, 48, 55, 62, 70]),
    (3, ARRAY[18, 24, 31, 39, 47, 52]),
    (4, ARRAY[120, 126, 132, 136, 140, 144]),
    (5, ARRAY[12, 16, 19, 23, 28, 34]),
    (6, ARRAY[58, 56, 53, 50, 47, 43])
)
INSERT INTO production_batches (id, product_id, line, produced_at, volume, defects)
SELECT
  ROW_NUMBER() OVER (ORDER BY m.month_index, p.id),
  p.id,
  'Ligne ' || (((p.id + m.month_index) % 3) + 1),
  m.month_start + (11 + p.id),
  d.quantities[m.month_index + 1] * 9,
  FLOOR(d.quantities[m.month_index + 1] * (0.025 + CASE WHEN p.id IN (3, 5) THEN 0.018 ELSE 0 END + m.month_index * 0.003))::integer
FROM months m
JOIN products p ON TRUE
JOIN demand d ON d.product_id = p.id;

WITH months(month_index, month_start) AS (
  VALUES
    (0, DATE '2026-01-01'),
    (1, DATE '2026-02-01'),
    (2, DATE '2026-03-01'),
    (3, DATE '2026-04-01'),
    (4, DATE '2026-05-01'),
    (5, DATE '2026-06-01')
),
demand(product_id, quantities) AS (
  VALUES
    (1, ARRAY[92, 88, 78, 70, 61, 54]),
    (2, ARRAY[36, 42, 48, 55, 62, 70]),
    (3, ARRAY[18, 24, 31, 39, 47, 52]),
    (4, ARRAY[120, 126, 132, 136, 140, 144]),
    (5, ARRAY[12, 16, 19, 23, 28, 34]),
    (6, ARRAY[58, 56, 53, 50, 47, 43])
)
INSERT INTO inventory_movements (id, product_id, movement_type, quantity, happened_at)
SELECT
  ROW_NUMBER() OVER (ORDER BY m.month_index, p.id),
  p.id,
  'sortie',
  d.quantities[m.month_index + 1],
  m.month_start + (8 + p.id)
FROM months m
JOIN products p ON TRUE
JOIN demand d ON d.product_id = p.id;

WITH months(month_index, month_start) AS (
  VALUES
    (0, DATE '2026-01-01'),
    (1, DATE '2026-02-01'),
    (2, DATE '2026-03-01'),
    (3, DATE '2026-04-01'),
    (4, DATE '2026-05-01'),
    (5, DATE '2026-06-01')
),
source AS (
  SELECT
    ROW_NUMBER() OVER (ORDER BY m.month_index, p.id) AS id,
    ((p.id + 1) % 4) + 1 AS supplier_id,
    p.id AS product_id,
    m.month_start + 17 AS delivery_date,
    m.month_index
  FROM months m
  JOIN products p ON TRUE
)
INSERT INTO supplier_delays (id, supplier_id, product_id, delivery_date, delay_days)
SELECT
  id,
  supplier_id,
  product_id,
  delivery_date,
  GREATEST(0, ((supplier_id * 2 + month_index) % 9) - 3) + CASE WHEN supplier_id = 3 THEN 4 ELSE 0 END
FROM source;

WITH months(month_index, month_start) AS (
  VALUES
    (0, DATE '2026-01-01'),
    (1, DATE '2026-02-01'),
    (2, DATE '2026-03-01'),
    (3, DATE '2026-04-01'),
    (4, DATE '2026-05-01'),
    (5, DATE '2026-06-01')
),
routes(route, carrier, base_cost, monthly_delta, base_delay) AS (
  VALUES
    ('Lille -> Lyon', 'TransHexa', 1280, 90, 1),
    ('Nantes -> Lille', 'NordCargo', 980, 130, 0),
    ('Marseille -> Paris', 'MistralLog', 1420, 170, 2),
    ('Lyon -> Strasbourg', 'RhineMove', 760, 55, 0)
)
INSERT INTO shipments (id, route, carrier, shipped_at, cost, delay_days)
SELECT
  ROW_NUMBER() OVER (ORDER BY m.month_index, r.route),
  r.route,
  r.carrier,
  m.month_start + 20,
  r.base_cost + (m.month_index * r.monthly_delta),
  r.base_delay + CASE WHEN m.month_index >= 4 AND r.route LIKE 'Marseille%' THEN 1 ELSE 0 END
FROM months m
JOIN routes r ON TRUE;

WITH months(month_index, month_start) AS (
  VALUES
    (2, DATE '2026-03-01'),
    (3, DATE '2026-04-01'),
    (4, DATE '2026-05-01'),
    (5, DATE '2026-06-01')
),
return_products(product_id) AS (
  VALUES (3), (5), (6)
)
INSERT INTO returns (id, product_id, customer_id, returned_at, quantity, reason)
SELECT
  ROW_NUMBER() OVER (ORDER BY m.month_index, rp.product_id),
  rp.product_id,
  ((rp.product_id + m.month_index) % 5) + 1,
  m.month_start + 24,
  2 + m.month_index,
  CASE WHEN rp.product_id IN (3, 5) THEN 'defaut qualite' ELSE 'non-conformite' END
FROM months m
JOIN return_products rp ON TRUE;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fabriq_readonly') THEN
    CREATE ROLE fabriq_readonly LOGIN PASSWORD 'fabriq_readonly';
  END IF;
END
$$;

ALTER ROLE fabriq_readonly WITH LOGIN PASSWORD 'fabriq_readonly';
GRANT CONNECT ON DATABASE fabriq TO fabriq_readonly;
GRANT USAGE ON SCHEMA public TO fabriq_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fabriq_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO fabriq_readonly;
