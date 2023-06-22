import argparse
from api.adapters.orm import create_tables, drop_tables
from api.config import get_sync_postgres_uri
from api.utils.hashoor import hash_password
from sqlalchemy import select
from api.adapters.orm import user, product, variation, order, order_item
from api.domain.enums import UserRole, OrderStatus, ConsumeLocation
from sqlalchemy import text
import random
import uuid
from sqlalchemy import create_engine
import asyncio
import time


def main(drop=True, create=False):
    # This is mostly for postgres
    time.sleep(5)
    connection_string = get_sync_postgres_uri()

    engine = create_engine(connection_string)
    # Wait for postgres to be up.
    if drop:
        drop_tables(engine)
        print("Tables dropped.")
    # Tables are always created. They are not recreated if they already exist.
    create_tables(engine)
    print("Tables created.")
    if create:
        create_initial_data(engine)
        print("Intial data created.")

    engine.dispose()


def create_initial_data(engine):
    conn = engine.connect()
    trans = conn.begin()
    try:
        # Create a manager
        manager_id = str(uuid.uuid4())
        conn.execute(
            user.insert(),
            {
                "id": manager_id,
                "email": "manager@example.com",
                "password": hash_password("test"),
                "role": UserRole.MANAGER.value,
            },
        )

        # Create a customer
        customer_id = str(uuid.uuid4())
        conn.execute(
            user.insert(),
            {
                "id": customer_id,
                "email": "customer@example.com",
                "password": hash_password("test"),
                "role": UserRole.CUSTOMER.value,
            },
        )

        # Catalog dictionary
        product_catalog = [
            {
                "name": "Latte",
                "variations": ["Pumpkin Spice", "Vanilla", "Hazelnut"],
            },
            {"name": "Cappuccino", "variations": ["Small", "Medium", "Large"]},
            {
                "name": "Iced Drinks",
                "variations": ["Smoothie", "Iced Coffee", "Iced Macchiato"],
            },
            {"name": "Tea", "variations": []},
            {
                "name": "Hot Chocolate",
                "variations": ["Small", "Medium", "Large"],
            },
            {
                "name": "Donuts",
                "variations": ["Glazed", "Jelly", "Boston Cream"],
            },
        ]

        # Create each product and variations
        product_ids = []
        for p in product_catalog:
            product_id = str(uuid.uuid4())
            conn.execute(
                product.insert(),
                {
                    "id": product_id,
                    "name": p["name"],
                    "description": f"This is a description for {p['name']}",
                    "price": round(random.uniform(10.0, 100.0), 2),
                },
            )
            for v in p["variations"]:
                conn.execute(
                    variation.insert(),
                    {
                        "id": str(uuid.uuid4()),
                        "name": v,
                        "price": round(random.uniform(10.0, 100.0), 2),
                        "product_id": product_id,
                    },
                )
            product_ids.append(product_id)

        # Create orders for the customer using the products created above
        order_ids = []
        for product_id in product_ids:
            variation_exists = conn.execute(
                select(variation).where(variation.c.product_id == product_id)
            ).fetchone()
            if variation_exists is not None:
                order_id = str(uuid.uuid4())
                order_ids.append(order_id)
                conn.execute(
                    order.insert(),
                    {
                        "id": order_id,
                        "status": OrderStatus.WAITING,
                        "consume_location": ConsumeLocation.IN_HOUSE,
                        "total_cost": variation_exists.price,
                        "user_id": customer_id,
                    },
                )
                conn.execute(
                    order_item.insert(),
                    {
                        "id": str(uuid.uuid4()),
                        "quantity": 1,
                        "unit_price": variation_exists.price,
                        "product_id": product_id,
                        "variation_id": variation_exists.id,
                        "order_id": order_id,
                    },
                )
        trans.commit()
    except Exception as e:
        print(e)
        trans.rollback()
    finally:
        conn.close()


async def create_initial_data_async(conn):
    # Wait for postgres
    # Create a manager
    manager_id = str(uuid.uuid4())
    await conn.execute(
        user.insert(),
        {
            "id": manager_id,
            "email": "manager@example.com",
            "password": hash_password("test"),
            "role": UserRole.MANAGER.value,
        },
    )

    # Create a customer
    customer_id = str(uuid.uuid4())
    await conn.execute(
        user.insert(),
        {
            "id": customer_id,
            "email": "customer@example.com",
            "password": hash_password("test"),
            "role": UserRole.CUSTOMER.value,
        },
    )
    # Catalog dictionary
    product_catalog = [
        {
            "name": "Latte",
            "variations": ["Pumpkin Spice", "Vanilla", "Hazelnut"],
        },
        {"name": "Cappuccino", "variations": ["Small", "Medium", "Large"]},
        {
            "name": "Iced Drinks",
            "variations": ["Smoothie", "Iced Coffee", "Iced Macchiato"],
        },
        {"name": "Tea", "variations": []},
        {"name": "Hot Chocolate", "variations": ["Small", "Medium", "Large"]},
        {"name": "Donuts", "variations": ["Glazed", "Jelly", "Boston Cream"]},
    ]
    # Create each product and variations
    product_ids = []
    for p in product_catalog:
        product_id = str(uuid.uuid4())
        await conn.execute(
            product.insert(),
            {
                "id": product_id,
                "name": p["name"],
                "description": f"This is a description for {p['name']}",
                "price": round(random.uniform(10.0, 100.0), 2),
            },
        )
        for v in p["variations"]:
            await conn.execute(
                variation.insert(),
                {
                    "id": str(uuid.uuid4()),
                    "name": v,
                    "price": round(random.uniform(10.0, 100.0), 2),
                    "product_id": product_id,
                },
            )
        product_ids.append(product_id)

    # Create orders for the customer using the products created above
    order_ids = []
    for product_id in product_ids:
        result = await conn.execute(
            select(variation).where(variation.c.product_id == product_id)
        )
        variation_exists = result.fetchone()
        if variation_exists is not None:
            order_id = str(uuid.uuid4())
            order_ids.append(order_id)
            await conn.execute(
                order.insert(),
                {
                    "id": order_id,
                    "status": OrderStatus.WAITING,
                    "consume_location": ConsumeLocation.IN_HOUSE,
                    "total_cost": variation_exists.price,
                    "user_id": customer_id,
                },
            )
            await conn.execute(
                order_item.insert(),
                {
                    "id": str(uuid.uuid4()),
                    "quantity": 1,
                    "unit_price": variation_exists.price,
                    "product_id": product_id,
                    "variation_id": variation_exists.id,
                    "order_id": order_id,
                },
            )

    # Save results to test folder as json
    db_dict = {}

    for table_name in [
        "users",
        "products",
        "variations",
        "orders",
        "order_items",
    ]:
        result = await conn.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        db_dict[table_name] = [dict(row._mapping) for row in rows]
    import json

    with open("tests/e2e/db_dict.json", "w") as f:
        json.dump(db_dict, f, indent=4, sort_keys=True, default=str)
        print("Saved db_dict to tests/e2e/db_dict.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage database tables.")
    parser.add_argument(
        "--drop", action="store_true", help="Drop tables if given"
    )
    parser.add_argument(
        "--create", action="store_true", help="Create tables if given"
    )
    args = parser.parse_args()

    main(drop=args.drop, create=args.create)
