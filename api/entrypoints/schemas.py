from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from api.domain.enums import OrderStatus, ConsumeLocation, UserRole


class IDModel(BaseModel):
    id: str


class Variation(IDModel):
    name: str
    price: float


class VariationBase(BaseModel):
    name: str
    price: float


class VariationUpdate(VariationBase):
    name: Optional[str] = None
    price: Optional[float] = None


class CreateVariation(VariationBase):
    pass


class ProductBase(BaseModel):
    name: str
    price: float
    description: str
    variations: List[Variation] | None = []


class ProductBaseOptional(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    variations: Optional[List[Variation]] = []


class Product(ProductBase, IDModel):
    pass


class ProductUpdate(ProductBaseOptional):
    pass


class OrderItemBase(BaseModel):
    quantity: int
    product_id: str
    variation_id: Optional[str] = None


class OrderItem(OrderItemBase):
    unit_price: float


class CustomerOrderItem(OrderItemBase):
    pass


class CreateOrder(BaseModel):
    consume_location: ConsumeLocation
    order_items: List[CustomerOrderItem]


class CreateProduct(BaseModel):
    name: str
    price: float
    description: str
    variations: List[VariationBase]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderUpdate(IDModel, OrderStatusUpdate):
    user_id: str


class CreateUser(BaseModel):
    email: EmailStr
    password: str
    role: UserRole


class GetCatalog(BaseModel):
    page: int = 1

    @validator("page")
    def validate_page(cls, v):
        if v < 1:
            raise ValueError("Page must be greater than 0.")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None


class User(IDModel):
    email: str
    role: UserRole


class OrderFilters(BaseModel):
    status: Optional[OrderStatus]
    consume_location: Optional[ConsumeLocation]
    user_id: Optional[str]


class OrderResponseBase(BaseModel):
    id: str
    total_cost: float
    consume_location: ConsumeLocation
    status: OrderStatus
    order_items: List[OrderItem]


class DetailedOrderResponse(OrderResponseBase):
    created_at: datetime
    updated_at: datetime


class GetOrdersResponse(BaseModel):
    orders: List[DetailedOrderResponse]
    page: int = 1


class GetCustomerOrdersResponse(BaseModel):
    orders: List[OrderResponseBase]
    page: int = 1


class GetProductsResponse(BaseModel):
    products: List[Product]
    page: int = 1


class DeleteProductResponse(IDModel):
    status: str


class CreateUserResponse(User):
    pass


class CatalogItem(Product):
    pass


class GetCatalogResponse(BaseModel):
    page: int = 1
    products: List[CatalogItem]


class ResponseData(BaseModel):
    message: str
    status_code: int


class SuccessResponse(ResponseData):
    message: str = "The data was stored successfully."
    status_code: int = 200


class ErrorResponse(ResponseData):
    message: str = "Invalid or malformatted data."
    status_code: int = 400


class ServerErrorResponse(ResponseData):
    message: str = "Unexpeted errors."
    status_code: int = 500
