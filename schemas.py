from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

# --- Schemas de Categoría ---
class CategoryBase(BaseModel):
    name: str

class CategoryResponse(CategoryBase):
    category_id: int
    model_config = ConfigDict(from_attributes=True)

# --- Schemas de Almacén ---
class WarehouseBase(BaseModel):
    name: str
    location: Optional[str] = None

class WarehouseResponse(WarehouseBase):
    warehouse_id: int
    model_config = ConfigDict(from_attributes=True)

# --- Schemas de Stock ---
class StockResponse(BaseModel):
    stock_id: int
    warehouse_id: int
    available_stock: int
    reserve_stock: int
    last_update_time: Optional[datetime] = None
    warehouse: Optional[WarehouseResponse] = None
    model_config = ConfigDict(from_attributes=True)

class AvailableStockByClientResponse(BaseModel):
    product_id: int
    client_id: int
    client_country: str
    available_stock: int

# --- Schemas de Producto ---
class ProductBase(BaseModel):
    category_id: int
    name: str
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    stars: Decimal = Decimal("0.0")
    reviews: int = 0
    price: Decimal

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    stars: Optional[Decimal] = None
    reviews: Optional[int] = None
    price: Optional[Decimal] = None

class ProductResponse(ProductBase):
    product_id: int
    category: Optional[CategoryResponse] = None
    stocks: List[StockResponse] = []
    model_config = ConfigDict(from_attributes=True)

class PaginatedProductsResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    data: List[ProductResponse]

class ReservarStockRequest(BaseModel):
    product_id: int
    client_id: int
    cantidad: int

class ReservarStockResponse(BaseModel):
    exito: bool
    product_id: int
    available_stock: int  # stock restante tras la reserva
