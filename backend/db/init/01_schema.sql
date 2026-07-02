CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY,
  reference TEXT NOT NULL,
  category TEXT NOT NULL,
  price NUMERIC(12, 2) NOT NULL,
  cost NUMERIC(12, 2) NOT NULL,
  safety_stock INTEGER NOT NULL,
  current_stock INTEGER NOT NULL,
  created_at DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  region TEXT NOT NULL,
  segment TEXT NOT NULL,
  tenant_id TEXT NOT NULL DEFAULT 'tenant_demo'
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  order_date DATE NOT NULL,
  quantity INTEGER NOT NULL,
  revenue NUMERIC(12, 2) NOT NULL,
  cost NUMERIC(12, 2) NOT NULL,
  tenant_id TEXT NOT NULL DEFAULT 'tenant_demo'
);

CREATE TABLE IF NOT EXISTS production_batches (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  line TEXT NOT NULL,
  produced_at DATE NOT NULL,
  volume INTEGER NOT NULL,
  defects INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_movements (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  movement_type TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  happened_at DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  punctuality_rate NUMERIC(5, 2) NOT NULL,
  lead_time_days INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS supplier_delays (
  id INTEGER PRIMARY KEY,
  supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  delivery_date DATE NOT NULL,
  delay_days INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS shipments (
  id INTEGER PRIMARY KEY,
  route TEXT NOT NULL,
  carrier TEXT NOT NULL,
  shipped_at DATE NOT NULL,
  cost NUMERIC(12, 2) NOT NULL,
  delay_days INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS returns (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  returned_at DATE NOT NULL,
  quantity INTEGER NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS costs (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  period TEXT NOT NULL,
  cost_type TEXT NOT NULL,
  amount NUMERIC(12, 2) NOT NULL
);
