from fastapi import FastAPI, HTTPException, Depends, Query
from api.entrypoints import schemas
from api.domain import commands
from api.bootstrap import bootstrap
from api.service_layer import messagebus
from api.entrypoints.auth_router import (
    auth_router,
    get_current_manager,
    get_current_customer,
)
from dataclasses import asdict
from api import views
import logging
import uvicorn
from fastapi import APIRouter

logger = logging.getLogger(__name__)
logger.info("Starting API")

tags_metadata = [
    {
        "name": "Manager",
        "description": "Operations related to Managers.",
    },
    {
        "name": "Customers",
        "description": "Operations related to Customers.",
    },
    {"name": "General", "description": "General operations"},
]


def get_bus() -> messagebus.MessageBus:
    return bootstrap()


app = FastAPI()
router = APIRouter()


@router.post(
    "/orders", response_model=schemas.OrderResponseBase, tags=["Customers"]
)
async def create_order(
    order: schemas.CreateOrder,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_customer=Depends(get_current_customer),
):
    cmd = commands.CreateOrder(**order.dict(), user_id=current_customer.id)
    result = await bus.handle(cmd)
    return result


@router.get(
    "/orders",
    response_model=schemas.GetOrdersResponse,
    tags=["Manager"],
)
async def get_order_for_managers(
    bus: messagebus.MessageBus = Depends(get_bus),
    page: int = Query(1, gt=0),
    page_size: int = Query(10, gt=0),
    current_manager=Depends(get_current_manager),
    filters: dict = Depends(schemas.OrderFilters),
):
    if filters:
        filters = filters.dict()
    cmd = commands.GetOrders(page=page, page_size=page_size, filters=filters)
    result = await bus.handle(cmd)
    if result:
        return schemas.GetOrdersResponse(
            orders=[schemas.DetailedOrderResponse(
                **asdict(order)) for order in result],
            page=page,
        )
    return schemas.GetOrdersResponse(orders=[], page=page)


@router.put(
    "/orders/{order_id}",
    response_model=schemas.OrderStatusUpdate,
    tags=["Manager"],
)
async def update_order_status(
    order_id: str,
    status_update: schemas.OrderStatusUpdate,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.UpdateOrderStatus(id=order_id, **status_update.dict())
    result = await bus.handle(cmd)
    return result


@router.get(
    "/orders/me",
    response_model=schemas.GetCustomerOrdersResponse,
    tags=["Customers"],
)
async def get_order_for_customer(
    bus: messagebus.MessageBus = Depends(get_bus),
    page: int = Query(1, gt=0),
    current_customer=Depends(get_current_customer),
):
    cmd = commands.GetOrdersForCustomer(page=page, user_id=current_customer.id)
    result = await bus.handle(cmd)
    # Create schema
    if result:
        result = [schemas.OrderResponseBase(
            **asdict(order)) for order in result]
        return schemas.GetCustomerOrdersResponse(page=page, orders=result)
    else:
        return schemas.GetCustomerOrdersResponse(page=page, orders=[])


@router.get(
    "/orders/{order_id}",
    response_model=schemas.OrderResponseBase,
    tags=["Manager"],
)
async def get_order(
    order_id: str,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.GetOrder(id=order_id)
    result = await bus.handle(cmd)
    return result


@router.put(
    "/orders/{order_id}/cancel",
    tags=["Customers"],
)
async def cancel_customer_order(
    order_id: str,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_customer=Depends(get_current_customer),
):
    cmd = commands.CancelOrder(order_id=order_id, user_id=current_customer.id)
    result_response = await bus.handle(cmd)
    if result_response is not None:
        result, response = result_response
        if result:
            return {"message": response}
        raise HTTPException(status_code=400, detail=response)


@router.post(
    "/products", response_model=schemas.ProductBase, tags=["Manager"]
)
async def create_product(
    product: schemas.CreateProduct,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.CreateProduct(**product.dict())
    result = await bus.handle(cmd)
    return result


@router.get(
    "/products/{product_id}",
    response_model=schemas.Product,
    tags=["Manager"],
)
async def get_product(
    product_id: str, bus: messagebus.MessageBus = Depends(get_bus)
):  # available to all
    cmd = commands.GetProduct(id=product_id)
    result = await bus.handle(cmd)
    return result


@router.put(
    "/products/{product_id}",
    response_model=schemas.Product,
    tags=["Manager"],
)
async def update_product(
    product_id: str,
    product_update: schemas.ProductUpdate,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.UpdateProduct(id=product_id, **product_update.dict())
    result = await bus.handle(cmd)
    return result


@router.delete(
    "/products/{product_id}",
    response_model=schemas.Product,
    tags=["Manager"],
)
async def delete_product(
    product_id: str,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.DeleteProduct(id=product_id)
    result = await bus.handle(cmd)
    return result


@router.post(
    "/products/{product_id}/variations",
    response_model=schemas.Variation,
    tags=["Manager"],
)
async def create_variation(
    product_id: str,
    variation: schemas.CreateVariation,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.CreateVariation(product_id=product_id, **variation.dict())
    result = await bus.handle(cmd)
    return result


@router.delete(
    "/products/{product_id}/variations/{variation_id}",
    response_model=schemas.SuccessResponse,
    tags=["Manager"],
)
async def delete_variation(
    product_id: str,
    variation_id: str,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.DeleteVariation(
        product_id=product_id, variation_id=variation_id)
    result = await bus.handle(cmd)
    return result


@router.put(
    "/products/{product_id}/variations/{variation_id}",
    tags=["Manager"],
)
async def update_variation(
    product_id: str,
    variation_id: str,
    variation_update: schemas.VariationUpdate,
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.UpdateVariation(
        product_id=product_id, variation_id=variation_id, **variation_update.dict()
    )
    result = await bus.handle(cmd)
    return result


@router.get(
    "/products", response_model=schemas.GetProductsResponse, tags=["Manager"]
)
async def get_products(
    page: int = Query(1, gt=0),
    bus: messagebus.MessageBus = Depends(get_bus),
    current_manager=Depends(get_current_manager),
):
    cmd = commands.GetAllProducts(page=page)
    result = await bus.handle(cmd)
    result = [asdict(product) for product in result]
    return schemas.GetProductsResponse(page=page, products=result)


@router.get(
    "/catalog", response_model=schemas.GetCatalogResponse, tags=["General"]
)
async def get_catalog(
    page: int = Query(1, gt=0),
    bus: messagebus.MessageBus = Depends(get_bus),
):
    result = await views.catalog(page=page, uow=bus.uow)
    return schemas.GetCatalogResponse(page=page, products=result)


@router.post(
    "/users", response_model=schemas.CreateUserResponse, tags=["Manager"]
)
async def create_user(
    user: schemas.CreateUser, bus: messagebus.MessageBus = Depends(get_bus)
):
    cmd = commands.CreateUser(**user.dict())
    result = await bus.handle(cmd)
    return result


@app.get("/healthcheck", tags=["Health"])
async def health(
    bus: messagebus.MessageBus = Depends(get_bus),
):  # available to all
    cmd = commands.HealthCheck()
    result = await bus.handle(cmd)
    if result:
        return {"message": "Healthy"}
    raise HTTPException(status_code=500, detail="Unhealthy")


app.include_router(auth_router)
app.include_router(router)


@app.get("/ping", tags=["Health"])
async def root():
    return "pong"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
