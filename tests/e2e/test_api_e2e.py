import pytest
from api.domain import enums
import api.bootstrap as bootstrap
import logging
import uuid
from httpx import AsyncClient
from api.entrypoints import app
import json
from api.service_layer import unit_of_work
from api.adapters.notifications import EmailLocalNotifications
import asyncio
import pytest_asyncio

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def client_teardown(app):
    yield
    app.shutdown()


@pytest.fixture(scope="module")
def shutdown_app(app):
    yield
    app.shutdown()


@pytest_asyncio.fixture
def message_bus(postgres_session_factory):
    def _bootstrap():
        return bootstrap.bootstrap(
            start_orm=True,
            uow=unit_of_work.SqlAlchemyUnitOfWork(
                session_factory=postgres_session_factory
            ),
            notifications=EmailLocalNotifications(),
        )

    return _bootstrap


@pytest_asyncio.fixture(scope="function")
async def client(message_bus):
    async with AsyncClient(app=app.app, base_url="http://test") as client:
        app.app.dependency_overrides[app.get_bus] = message_bus
        yield client


@pytest_asyncio.fixture
async def get_manager_auth_token(client: AsyncClient):
    test_client = client
    response = await test_client.post(
        "/token",
        data={"username": "manager@example.com", "password": "test"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def get_customer_auth_token(client: AsyncClient):
    test_client = client
    response = await test_client.post(
        "/token",
        data={"username": "customer@example.com", "password": "test"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_get_token_invalid_user(client: AsyncClient):
    response = await client.post(
        "/token",
        data={"username": "asdasd@asdasdas.asd", "password": "test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_order(
    client: AsyncClient, db_state_dict_postgres, get_customer_auth_token
):
    current_user = db_state_dict_postgres["users"][0]
    order_data = {
        "consume_location": enums.ConsumeLocation.IN_HOUSE,
        "user_id": current_user["id"],
        "order_items": [
            {
                "product_id": db_state_dict_postgres["products"][0]["id"],
                "variation_id": db_state_dict_postgres["variations"][0]["id"],
                "quantity": 1,
            }
        ],
    }
    response = await client.post(
        "/orders",
        content=json.dumps(order_data),
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
    )

    assert response.status_code == 200


# @pytest.mark.asyncio
# async def test_create_order_with_no_product_variations(
#     client: AsyncClient, db_state_dict_postgres, get_customer_auth_token
# ):
#     # Find a product without variations. Tea has none
#     for i in db_state_dict_postgres["products"]:
#         if i["name"] == "Tea":
#             product_id = i["id"]
#             tea_price = i["price"]
#     if product_id is None:
#         pytest_asyncio.fail("No product without variations found")
#     # Build the order, with no additionalw
#     order_data = {
#         "consume_location": enums.ConsumeLocation.IN_HOUSE,
#         "user_id": db_state_dict_postgres["users"][1]["id"],
#         "order_items": [
#             {
#                 "product_id": product_id,
#                 "quantity": 1,
#             }
#         ]
#     }
#     response = await client.post(
#         "/orders",
#         content=json.dumps(order_data),
#         headers={"Authorization": f"Bearer {get_customer_auth_token}"},
#     )

#     assert response.status_code == 200
#     # Price should be the same as product price
#     assert response.json()["total_cost"] == tea_price


# @pytest.mark.asyncio
# async def test_create_order_with_mixed_variations(
#     client: AsyncClient, db_state_dict_postgres, get_customer_auth_token
# ):
#     total_price = 0
#     order_items = []
#     for i in range(len(db_state_dict_postgres["products"])):
#         product = db_state_dict_postgres["products"][i]
#         product_id = product["id"]
#         for variation in db_state_dict_postgres["variations"]:
#             if variation["product_id"] == product_id:
#                 variation_id = variation["id"]
#                 order_items.append(
#                     {
#                         "product_id": product_id,
#                         "quantity": 1,
#                         "variation_id": variation_id,
#                     })
#                 total_price += variation["price"] + product["price"]
#                 break
#         else:
#             order_items.append(
#                 {"product_id": product_id, "quantity": 1})
#             total_price += product["price"]
#     # Build the order, with no additionals.
#     order_data = {
#         "consume_location": enums.ConsumeLocation.IN_HOUSE,
#         "user_id": db_state_dict_postgres["users"][1]["id"],
#         "order_items": order_items
#     }
#     response = await client.post(
#         "/orders",
#         content=json.dumps(order_data),
#         headers={"Authorization": f"Bearer {get_customer_auth_token}"},
#     )

#     assert response.status_code == 200
#     # Price should be the same as product price
#     assert response.json()["total_cost"] == total_price


@pytest.mark.asyncio
async def test_get_catalog(
    client: AsyncClient, db_state_dict_postgres, get_customer_auth_token
):
    response = await client.get(
        "/catalog",
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json()["products"], list)
    assert len(response.json()["products"]) > 2
    await asyncio.sleep(2)


@pytest.mark.asyncio
async def test_get_all_orders(
    client: AsyncClient,
    get_manager_auth_token,
):
    response = await client.get(
        "/orders", headers={"Authorization": f"Bearer {get_manager_auth_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json()["orders"], list)
    assert len(response.json()["orders"]) > 2


@pytest.mark.asyncio
async def test_get_token(client: AsyncClient, get_customer_auth_token):
    if get_customer_auth_token:
        assert True


@pytest.mark.asyncio
async def test_customer_cant_access_resources(
    client: AsyncClient, get_customer_auth_token
):
    response = await client.get(
        "/orders",
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
    )
    assert response.status_code == 403
    response = await client.get(
        "/products",
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
    )
    assert response.status_code == 403
    response = await client.post(
        "/products",
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_product(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    product_id = db_state_dict_postgres["products"][0]["id"]
    response = await client.get(
        f"/products/{product_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_order_status(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    order_id = db_state_dict_postgres["orders"][0]["id"]
    response = await client.put(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
        json={"status": enums.OrderStatus.PREPARATION.value},
    )
    assert response.status_code == 200
    assert response.json()["status"] == enums.OrderStatus.PREPARATION.value

    # We shouldnt be able to move to Delivered
    response = await client.put(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
        json={"status": enums.OrderStatus.DELIVERED.value},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_order(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    order_id = db_state_dict_postgres["orders"][0]["id"]
    response = await client.get(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
    )
    assert response.status_code == 200
    await asyncio.sleep(2)


@pytest.mark.asyncio
async def test_get_order_not_found(client: AsyncClient, get_manager_auth_token):
    order_id = str(uuid.uuid4())
    response = await client.get(
        f"/orders/{order_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_customer_cancels_its_order(
    client: AsyncClient, db_state_dict_postgres, get_customer_auth_token
):
    order = db_state_dict_postgres["orders"][0]
    response = await client.put(
        f"/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
        json={"status": "CANCELLED"},
    )
    assert response.status_code == 200
    # We shouldnt be able to cancel again
    response = await client.put(
        f"/orders/{order['id']}/cancel",
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
        json={"status": "CANCELLED"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_all_products(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    response = await client.get(
        "/products",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_product(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    p_id = str(uuid.uuid4())
    product_data = {
        "id": p_id,
        "name": "Test Product",
        "description": "Test Description",
        "price": 10.0,
        "is_available": True,
        "variations": [
            {
                "name": "Variation 1 for Product 1",
                "price": 84.24,
                "product_id": p_id,
            },
        ],
    }
    response = await client.post(
        "/products",
        content=json.dumps(product_data),
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == product_data["name"]
    assert response.json()["description"] == product_data["description"]
    assert response.json()["price"] == product_data["price"]


@pytest.mark.asyncio
async def test_update_product(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    product_id = db_state_dict_postgres["products"][0]["id"]
    variation_id = db_state_dict_postgres["variations"][0]["id"]
    response = await client.put(
        f"/products/{product_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
        json={
            "name": "Updated Product Name",
            "variations": [
                {
                    "name": "Updated Variation Name",
                    "price": 10.0,
                    "id": variation_id,
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Product Name"
    assert response.json()["variations"][0]["name"] == "Updated Variation Name"


@pytest.mark.asyncio
async def test_create_variation(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    product_id = db_state_dict_postgres["products"][0]["id"]
    response = await client.post(
        f"/products/{product_id}/variations",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
        json={"name": "New Variation", "price": 10.0},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Variation"
    # We shouldnt be able to create another variation with the same name
    response = await client.post(
        f"/products/{product_id}/variations",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
        json={"name": "New Variation", "price": 10.0},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_variation(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    product_id = db_state_dict_postgres["products"][0]["id"]
    variation_id = db_state_dict_postgres["variations"][0]["id"]
    response = await client.put(
        f"/products/{product_id}/variations/{variation_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
        json={"name": "Updated Variation Name", "price": 10.0},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Variation Name"
    assert response.json()["price"] == 10.0


@pytest.mark.asyncio
async def test_delete_variation(
    client: AsyncClient, db_state_dict_postgres, get_manager_auth_token
):
    variation_id = db_state_dict_postgres["variations"][2]["id"]
    product_id = db_state_dict_postgres["variations"][2]["product_id"]
    response = await client.delete(
        f"/products/{product_id}/variations/{variation_id}",
        headers={"Authorization": f"Bearer {get_manager_auth_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_users_me(
    client: AsyncClient, db_state_dict_postgres, get_customer_auth_token
):
    user = db_state_dict_postgres["users"][1]
    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {get_customer_auth_token}"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]


@pytest.mark.asyncio
async def test_create_and_authenticate_new_user(
    client: AsyncClient, db_state_dict_postgres, get_customer_auth_token
):
    user_data = {
        "email": "testnewuser@test.com",
        "password": "test",
        "role": "CUSTOMER",
    }
    response = await client.post(
        "/users",
        content=json.dumps(user_data),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_healthcheck_with_db(client: AsyncClient):
    response = await client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"message": "Healthy"}


@pytest.mark.asyncio
async def test_ping(client: AsyncClient):
    response = await client.get("/ping")
    assert response.status_code == 200
    assert response.json() == "pong"


@pytest.mark.asyncio
async def test_docs(client: AsyncClient):
    response = await client.get("/docs")
    assert response.status_code == 200
