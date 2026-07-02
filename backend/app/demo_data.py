from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def create_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    _create_schema(connection)
    _seed_data(connection)
    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE products (
          id INTEGER PRIMARY KEY,
          reference TEXT NOT NULL,
          category TEXT NOT NULL,
          price REAL NOT NULL,
          cost REAL NOT NULL,
          safety_stock INTEGER NOT NULL,
          current_stock INTEGER NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE customers (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          region TEXT NOT NULL,
          segment TEXT NOT NULL
        );

        CREATE TABLE orders (
          id INTEGER PRIMARY KEY,
          customer_id INTEGER NOT NULL,
          product_id INTEGER NOT NULL,
          order_date TEXT NOT NULL,
          quantity INTEGER NOT NULL,
          revenue REAL NOT NULL,
          cost REAL NOT NULL,
          FOREIGN KEY(customer_id) REFERENCES customers(id),
          FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE production_batches (
          id INTEGER PRIMARY KEY,
          product_id INTEGER NOT NULL,
          line TEXT NOT NULL,
          produced_at TEXT NOT NULL,
          volume INTEGER NOT NULL,
          defects INTEGER NOT NULL,
          FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE inventory_movements (
          id INTEGER PRIMARY KEY,
          product_id INTEGER NOT NULL,
          movement_type TEXT NOT NULL,
          quantity INTEGER NOT NULL,
          happened_at TEXT NOT NULL,
          FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE suppliers (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          punctuality_rate REAL NOT NULL,
          lead_time_days INTEGER NOT NULL
        );

        CREATE TABLE supplier_delays (
          id INTEGER PRIMARY KEY,
          supplier_id INTEGER NOT NULL,
          product_id INTEGER NOT NULL,
          delivery_date TEXT NOT NULL,
          delay_days INTEGER NOT NULL,
          FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
          FOREIGN KEY(product_id) REFERENCES products(id)
        );

        CREATE TABLE shipments (
          id INTEGER PRIMARY KEY,
          route TEXT NOT NULL,
          carrier TEXT NOT NULL,
          shipped_at TEXT NOT NULL,
          cost REAL NOT NULL,
          delay_days INTEGER NOT NULL
        );

        CREATE TABLE returns (
          id INTEGER PRIMARY KEY,
          product_id INTEGER NOT NULL,
          customer_id INTEGER NOT NULL,
          returned_at TEXT NOT NULL,
          quantity INTEGER NOT NULL,
          reason TEXT NOT NULL,
          FOREIGN KEY(product_id) REFERENCES products(id),
          FOREIGN KEY(customer_id) REFERENCES customers(id)
        );

        CREATE TABLE costs (
          id INTEGER PRIMARY KEY,
          product_id INTEGER NOT NULL,
          period TEXT NOT NULL,
          cost_type TEXT NOT NULL,
          amount REAL NOT NULL,
          FOREIGN KEY(product_id) REFERENCES products(id)
        );
        """
    )


def _seed_data(connection: sqlite3.Connection) -> None:
    products = [
        (1, "AX-100", "Acier", 120.0, 78.0, 180, 92, "2025-02-12"),
        (2, "BX-220", "Composite", 210.0, 151.0, 90, 260, "2025-04-02"),
        (3, "CX-310", "Electronique", 340.0, 240.0, 55, 38, "2025-05-18"),
        (4, "DX-450", "Plastique", 75.0, 49.0, 240, 410, "2024-11-24"),
        (5, "EX-510", "Mecanique", 480.0, 360.0, 40, 33, "2025-07-09"),
        (6, "FX-700", "Assemblage", 155.0, 118.0, 120, 74, "2024-09-17"),
    ]
    customers = [
        (1, "Boden Industrie", "Nord", "PME"),
        (2, "Alpine Equipements", "Est", "ETI"),
        (3, "Delta Machines", "Ouest", "PME"),
        (4, "Hexa Supply", "Sud", "Grand compte"),
        (5, "Nova Process", "Nord", "PME"),
    ]
    suppliers = [
        (1, "ForgeNord", 0.82, 9),
        (2, "Polymeris", 0.93, 6),
        (3, "MicroFlux", 0.74, 14),
        (4, "LogiMetal", 0.88, 11),
    ]

    connection.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?)", products)
    connection.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)
    connection.executemany("INSERT INTO suppliers VALUES (?, ?, ?, ?)", suppliers)

    order_rows = []
    cost_rows = []
    batch_rows = []
    movement_rows = []
    delay_rows = []
    shipment_rows = []
    return_rows = []

    order_id = 1
    cost_id = 1
    batch_id = 1
    movement_id = 1
    delay_id = 1
    shipment_id = 1
    return_id = 1

    month_starts = [date(2026, month, 1) for month in range(1, 7)]
    demand_pattern = {
        1: [92, 88, 78, 70, 61, 54],
        2: [36, 42, 48, 55, 62, 70],
        3: [18, 24, 31, 39, 47, 52],
        4: [120, 126, 132, 136, 140, 144],
        5: [12, 16, 19, 23, 28, 34],
        6: [58, 56, 53, 50, 47, 43],
    }

    for month_index, month_start in enumerate(month_starts):
        for product in products:
            product_id, reference, category, price, unit_cost, *_ = product
            quantity = demand_pattern[product_id][month_index]
            customer_id = ((product_id + month_index) % len(customers)) + 1
            margin_pressure = 1 - (0.015 * month_index if product_id in {1, 6} else 0)
            revenue = round(quantity * price * margin_pressure, 2)
            cost = round(quantity * unit_cost * (1 + 0.01 * month_index), 2)
            order_rows.append(
                (
                    order_id,
                    customer_id,
                    product_id,
                    (month_start + timedelta(days=4 + product_id)).isoformat(),
                    quantity,
                    revenue,
                    cost,
                )
            )
            order_id += 1

            cost_rows.append(
                (
                    cost_id,
                    product_id,
                    month_start.strftime("%Y-%m"),
                    "production",
                    round(quantity * unit_cost * (0.09 + month_index * 0.004), 2),
                )
            )
            cost_id += 1

            defects = int(quantity * (0.025 + (0.018 if product_id in {3, 5} else 0) + month_index * 0.003))
            batch_rows.append(
                (
                    batch_id,
                    product_id,
                    f"Ligne {((product_id + month_index) % 3) + 1}",
                    (month_start + timedelta(days=11 + product_id)).isoformat(),
                    quantity * 9,
                    defects,
                )
            )
            batch_id += 1

            movement_rows.append(
                (
                    movement_id,
                    product_id,
                    "sortie",
                    quantity,
                    (month_start + timedelta(days=8 + product_id)).isoformat(),
                )
            )
            movement_id += 1

            supplier_id = ((product_id + 1) % len(suppliers)) + 1
            delay = max(0, (supplier_id * 2 + month_index) % 9 - 3)
            if supplier_id == 3:
                delay += 4
            delay_rows.append(
                (
                    delay_id,
                    supplier_id,
                    product_id,
                    (month_start + timedelta(days=17)).isoformat(),
                    delay,
                )
            )
            delay_id += 1

        routes = [
            ("Lille -> Lyon", "TransHexa", 1280 + month_index * 90, 1),
            ("Nantes -> Lille", "NordCargo", 980 + month_index * 130, 0),
            ("Marseille -> Paris", "MistralLog", 1420 + month_index * 170, 2),
            ("Lyon -> Strasbourg", "RhineMove", 760 + month_index * 55, 0),
        ]
        for route, carrier, cost, delay in routes:
            shipment_rows.append(
                (
                    shipment_id,
                    route,
                    carrier,
                    (month_start + timedelta(days=20)).isoformat(),
                    float(cost),
                    delay + (1 if month_index >= 4 and "Marseille" in route else 0),
                )
            )
            shipment_id += 1

        if month_index >= 2:
            for product_id in (3, 5, 6):
                return_rows.append(
                    (
                        return_id,
                        product_id,
                        ((product_id + month_index) % len(customers)) + 1,
                        (month_start + timedelta(days=24)).isoformat(),
                        2 + month_index,
                        "defaut qualite" if product_id in {3, 5} else "non-conformite",
                    )
                )
                return_id += 1

    connection.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", order_rows)
    connection.executemany("INSERT INTO costs VALUES (?, ?, ?, ?, ?)", cost_rows)
    connection.executemany("INSERT INTO production_batches VALUES (?, ?, ?, ?, ?, ?)", batch_rows)
    connection.executemany("INSERT INTO inventory_movements VALUES (?, ?, ?, ?, ?)", movement_rows)
    connection.executemany("INSERT INTO supplier_delays VALUES (?, ?, ?, ?, ?)", delay_rows)
    connection.executemany("INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?)", shipment_rows)
    connection.executemany("INSERT INTO returns VALUES (?, ?, ?, ?, ?, ?)", return_rows)
    connection.commit()
