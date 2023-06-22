from fastapi.exceptions import HTTPException


class Unauthorized(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Unauthorized")


class OrderNotFound(HTTPException):
    def __init__(self, order_id: str):
        super().__init__(status_code=404, detail=f"Order {order_id} not found")


class ProductNotFound(HTTPException):
    def __init__(self, product_id: str):
        super().__init__(
            status_code=404, detail=f"Product {product_id} not found"
        )


class InvalidOrderUpdate(HTTPException):
    def __init__(self, order_id: str, e: Exception):
        super().__init__(
            status_code=400,
            detail=f"Invalid order update {order_id}, exception is : {str(e)}",
        )


class InvalidProductUpdate(HTTPException):
    def __init__(self, product_id: str, e: Exception):
        super().__init__(
            status_code=400,
            detail=f"Invalid product update {product_id}, exception is : {str(e)}",
        )


class InvalidVariationUpdate(HTTPException):
    def __init__(self, variation_id: str, e: Exception):
        super().__init__(
            status_code=400,
            detail=f"Invalid variation update {variation_id}, exception is : {str(e)}",
        )


class UserNotFound(HTTPException):
    def __init__(self, user_id: str):
        super().__init__(status_code=404, detail=f"User {user_id} not found")


class InvalidOrderStatus(HTTPException):
    def __init__(self, status: str):
        super().__init__(
            status_code=400, detail=f"Invalid order status {status}"
        )


class OrderAlreadyCancelled(HTTPException):
    def __init__(self, order_id: str):
        super().__init__(
            status_code=400, detail=f"Order {order_id} is already cancelled"
        )


class OrderAlreadyCompleted(HTTPException):
    def __init__(self, order_id: str):
        super().__init__(
            status_code=400, detail=f"Order {order_id} is already completed"
        )


class VariationNotFound(HTTPException):
    def __init__(self, variation_id: str):
        super().__init__(
            status_code=404, detail=f"Variation {variation_id} not found"
        )


class InvalidPassword(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail=f"Invalid password")


class EntityAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail=f"Entity already exists")


class EntityDoesNotExist(Exception):
    def __init__(self, entity_id: str):
        super().__init__(f"Entity {entity_id} does not exist")
