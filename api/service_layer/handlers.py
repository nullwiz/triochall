from dataclasses import asdict
from typing import Tuple
from api.domain import events, models, commands, enums
from api.utils.hashoor import hash_password, verify_password
from api.adapters import notifications
from api.adapters import redis_eventpublisher
from api.service_layer import unit_of_work
import uuid
from api.utils.exceptions import (
    OrderNotFound,
    ProductNotFound,
    UserNotFound,
    VariationNotFound,
    InvalidPassword,
    Unauthorized,
    InvalidOrderUpdate,
    InvalidProductUpdate,
    InvalidVariationUpdate,
)


# Order - Main use case, we could have composition of different handlers aswell.
# Order - Main use case, we could have composition of different handlers as well.
async def create_order_handler(
    cmd: commands.CreateOrder, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        order_items = []
        total_cost = 0
        order_id = str(uuid.uuid4())
        for item in cmd.order_items:
            product = await uow.products.get(item["product_id"])
            if product is None:
                raise ProductNotFound(item["product_id"])

            variation = None
            unit_price = product.price

            if "variation_id" in item and item["variation_id"] is not None:
                variation = await uow.variations.get(item["variation_id"])
                if variation is None:
                    raise VariationNotFound(item["variation_id"])
                unit_price += variation.price

            total_cost += unit_price * item["quantity"]
            order_items.append(
                models.OrderItem(
                    quantity=item["quantity"],
                    product_id=item["product_id"],
                    variation_id=item.get("variation_id", None),
                    unit_price=unit_price,
                    order_id=order_id,
                )
            )

        cmd_as_dict = asdict(cmd)
        cmd_as_dict.pop("order_items", None)
        cmd_as_dict["id"] = order_id
        order = models.Order(
            order_items=order_items, total_cost=total_cost, **cmd_as_dict
        )
        await uow.orders.add(order)
        await uow.commit()
        return order


async def get_orders_handler(
    cmd: commands.GetOrders, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        orders = await uow.orders.get_all(cmd.page, cmd.page_size, cmd.filters)
        return orders


async def update_order_status_handler(
    cmd: commands.UpdateOrderStatus, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        order = await uow.orders.get(cmd.id)
        if order is None:
            raise OrderNotFound(cmd.id)
        try:
            order_items = []
            for i in order.order_items:
                product = await uow.products.get(i.product_id)
                variation = await uow.variations.get(i.variation_id)
                order_items.append(
                    {
                        "name": product.name + " with " + variation.name,
                        "quantity": i.quantity,
                        "price": i.unit_price,
                    }
                )
            order.change_status(cmd.status, order.order_items)
        except ValueError as e:
            raise InvalidOrderUpdate(order_id=cmd.id, e=e)
        await uow.commit()
        await redis_eventpublisher.publish(
            channel="orders", event="OrderStatusUpdated", data=asdict(order)
        )
        return order


async def get_order_handler(
    cmd: commands.GetOrder, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        order = await uow.orders.get(cmd.id)
        if order is None:
            raise OrderNotFound(cmd.id)
        return order


async def handle_order_change_event(
    event: events.OrderStatusChanged,
    notifications: notifications.AbstractNotifications,
    uow: unit_of_work.AbstractUnitOfWork,
):
    user = await uow.users.get(event.user_id)
    if user is not None:
        await notifications.publish(user.email, event)


async def handle_push_notification(
    event: events.OrderStatusChanged,
    notifications: notifications.AbstractNotifications,
    uow: unit_of_work.AbstractUnitOfWork,
):
    # This is added as an example.
    pass


async def handle_order_created_event(
    event: events.OrderCreated,
    uow: unit_of_work.AbstractUnitOfWork,
    notifications: notifications.AbstractNotifications,
):
    user = await uow.users.get(event.user_id)
    if user is not None:
        await notifications.publish(user.email, event)


async def cancel_order_handler(
    cmd: commands.CancelOrder, uow: unit_of_work.AbstractUnitOfWork
) -> Tuple[bool, str]:
    async with uow:
        order = await uow.orders.get(cmd.order_id)
        if order is None:
            raise OrderNotFound(cmd.order_id)
        if order.user_id != cmd.user_id:
            raise Unauthorized
        # Order cant by cancelled if its already cancelled or delivered
        if order.status == enums.OrderStatus.CANCELLED:
            return (False, "Order already cancelled")
        if order.status == enums.OrderStatus.DELIVERED:
            return (False, "Order already delivered")
        order.change_status(enums.OrderStatus.CANCELLED, order.order_items)
        await uow.commit()
        order_data = asdict(order)
        # Enums to string for event
        order_data["consume_location"] = order_data["consume_location"].value
        order_data["status"] = order_data["status"].value
        await redis_eventpublisher.publish(
            channel="orders",
            event="OrderCancelled",
            data=order_data,
        )
        return (True, "Order cancelled successfully")


# Products
async def show_product_handler(
    cmd: commands.GetProduct, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        product = await uow.products.get(cmd.id)
        if product is None:
            raise ProductNotFound(cmd.id)
        return product


async def create_product_handler(
    cmd: commands.CreateProduct, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        # create Product instance without variations
        product = models.Product(
            name=cmd.name, description=cmd.description, price=cmd.price
        )

        # create Variation instances and add them to the product
        for variation in cmd.variations:
            var = models.Variation(**variation, product_id=product.id)
            if var is None:
                raise VariationNotFound(variation["id"])
            product.variations.append(var)

        await uow.products.add(product)
        await uow.commit()

        return product


async def update_product_handler(
    cmd: commands.UpdateProduct, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        product = await uow.products.get(cmd.id)
        if product is None:
            raise ProductNotFound(cmd.id)

        original_price = product.price
        if cmd.variations:
            await product_variations(cmd, product, uow)

        update_product_attributes(cmd, product)

        await uow.products.update(product)
        # If price difers 50% send notification that is cheap
        if product.price * 2 < original_price:
            await redis_eventpublisher.publish(
                channel="products",
                event="ProductDiscount",
                data={
                    "event": "ProductDiscount",
                },
            )
        await uow.commit()
        return product


async def product_variations(cmd, product, uow):
    for v in cmd.variations:
        var = await uow.variations.get(v["id"])
        if var is None:
            raise VariationNotFound(v["id"])
        if var not in product.get_active_variations():
            product.variations.append(var)
        else:
            for attr, value in v.items():
                if value is not None:
                    setattr(var, attr, value)


def update_product_attributes(cmd, product):
    attrs_to_update = asdict(cmd)
    attrs_to_update.pop("variations", None)
    for attr, value in attrs_to_update.items():
        if value is not None:
            setattr(product, attr, value)


async def delete_product_handler(
    cmd: commands.DeleteProduct, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        product = await uow.products.get(cmd.id)
        if product is None:
            raise ProductNotFound(cmd.id)
        await uow.products.delete(product)
        await uow.commit()
        return product


async def get_product_handler(
    cmd: commands.GetProduct, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        product = await uow.products.get(cmd.id)
        if product is None:
            raise ProductNotFound(cmd.id)
        return product


async def get_all_products_handler(
    cmd: commands.GetAllProducts, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        products = await uow.products.get_all(cmd.page)
        if products is None:
            return []
        return products


async def get_orders_for_customer_handler(
    cmd: commands.GetOrdersForCustomer, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        orders = await uow.orders.get_all(
            cmd.page, filters={"user_id": cmd.user_id}
        )
        return orders


async def get_catalog_handler(
    cmd: commands.GetCatalog, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        products = await uow.products.get_all(cmd.page)
        if products is None:
            return []
        return products


# Variations
async def create_variation_handler(
    cmd: commands.CreateVariation, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        variation = models.Variation(**asdict(cmd))
        product = await uow.products.get(cmd.product_id)
        if product is None:
            raise ProductNotFound(cmd.product_id)
        for v in product.variations:
            if v.name == variation.name:
                raise InvalidVariationUpdate(
                    variation_id=v.id,
                    e=Exception(
                        "Variation name already exists with id %s" % v.id
                    ),
                )
        product.add_variation(variation=variation)
        await uow.products.update(product)
        await uow.commit()
        return variation


async def delete_variation_handler(
    cmd: commands.DeleteVariation, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        product = await uow.products.get(cmd.product_id)
        if product is None:
            raise ProductNotFound(cmd.product_id)
        product.remove_variation(id=cmd.variation_id)
        await uow.products.update(product)
        await uow.commit()
        return product


async def update_variation_handler(
    cmd: commands.UpdateVariation, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        product = await uow.products.get(cmd.product_id)
        if product is None:
            raise ProductNotFound(cmd.product_id)
        variation = product.get_variation_by_id(cmd.variation_id)
        if variation is None:
            raise VariationNotFound(cmd.variation_id)
        # Check if variation name already exists
        for v in product.get_active_variations():
            if v.name == cmd.name and v.id != cmd.variation_id:
                raise InvalidVariationUpdate(
                    variation_id=v.id,
                    e="Variation name already exists with id " + v.id,
                )
        try:
            variation.name = cmd.name if cmd.name else variation.name
            variation.price = cmd.price if cmd.price else variation.price
            product.add_variation(variation=variation)
        except ValueError as e:
            raise InvalidProductUpdate(order_id=cmd.id, e=e)
        await uow.variations.update(variation)
        await uow.commit()
        return variation


# Users


async def create_user_handler(
    cmd: commands.CreateUser, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        cmd_dict = asdict(cmd)
        cmd_dict["role"] = cmd_dict["role"].value.upper()
        cmd_dict["password"] = hash_password(cmd_dict["password"])
        user = models.User(**cmd_dict)
        await uow.users.add(user)
        await uow.commit()
        return user


async def authenticate_user_handler(
    cmd: commands.AuthenticateUser, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        user = await uow.users.get_by_email(cmd.email)
        if user is None:
            raise UserNotFound(cmd.email)
        if not verify_password(cmd.password, user.password):
            raise InvalidPassword
        return user


async def get_user_by_email_handler(
    cmd: commands.GetUserByEmail, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        user = await uow.users.get_by_email(cmd.email)
        if user is None:
            raise UserNotFound(cmd.email)
        return user


# General
async def healthcheck_handler(
    cmd: commands.HealthCheck, uow: unit_of_work.AbstractUnitOfWork
):
    async with uow:
        try:
            await uow.health_check()
        except Exception:
            return False
        return True


# POC
async def notify_order_sale_handler(
    cmd: commands.NotifyOrderSale,
    uow: unit_of_work.AbstractUnitOfWork,
    notifications: notifications.AbstractNotifications,
):
    async with uow:
        await notifications.publish("test@example.com", events.OrderSale())
        return "OK"


EVENT_HANDLERS = {
    events.OrderStatusChanged: [
        handle_order_change_event,
        handle_push_notification,
    ],
    events.OrderCreated: [handle_order_created_event],
}

COMMAND_HANDLERS = {
    commands.HealthCheck: healthcheck_handler,
    commands.CreateOrder: create_order_handler,
    commands.CreateProduct: create_product_handler,
    commands.CancelOrder: cancel_order_handler,
    commands.GetOrdersForCustomer: get_orders_for_customer_handler,
    commands.GetOrders: get_orders_handler,
    commands.GetProduct: get_product_handler,
    commands.GetAllProducts: get_all_products_handler,
    commands.UpdateProduct: update_product_handler,
    commands.CreateVariation: create_variation_handler,
    commands.DeleteVariation: delete_variation_handler,
    commands.UpdateVariation: update_variation_handler,
    commands.CreateUser: create_user_handler,
    commands.GetUserByEmail: get_user_by_email_handler,
    commands.DeleteProduct: delete_product_handler,
    commands.AuthenticateUser: authenticate_user_handler,
    commands.GetCatalog: get_catalog_handler,
    commands.GetOrder: get_order_handler,
    commands.CreateOrder: create_order_handler,
    commands.UpdateOrderStatus: update_order_status_handler,
    commands.NotifyOrderSale: notify_order_sale_handler,
}
