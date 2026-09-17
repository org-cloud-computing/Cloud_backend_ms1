import math
from typing import Optional, List
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from database import get_db, engine
import requests

models.Base.metadata.create_all(bind=engine)

NODE_API_URL = "https://okj8uulv98.execute-api.us-east-1.amazonaws.com/ms2/clientes"

app = FastAPI(
    title="MS1 - Catálogo e Inventario Amazon",
    description="Microservicio transaccional para productos, categorías y control de inventario por almacén/país.",
    version="1.0.0",
    docs_url="/ms1/docs",
    openapi_url="/ms1/openapi.json",
    redoc_url="/ms1/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Método Auxiliar: Resolver País del Cliente por ID ---
def get_client_country_by_id(client_id: int) -> str:
    """
    Consulta el país del cliente consumiendo el endpoint de la API en Node.js.
    """
    response = requests.get(f"{NODE_API_URL}/{client_id}/pais", timeout=5)

    if response.status_code == 404:
        return "Perú"  # Fallback si el cliente no existe

    response.raise_for_status()
    data = response.json()
    return data.get("pais", "Perú")


# --- 1. HEALTH CHECK ---
# CAMBIO: Agregado prefijo /ms1 al health check
@app.get("/ms1", tags=["Health Check"])
def health_check():
    return {"status": "ok", "service": "MS1 - SQL 1 (PostgreSQL)"}


# --- 2. GET PRODUCT (Listado General Paginado) ---
# CAMBIO: Cambiado a /ms1/products (se agrega /ms1 y se remueve barra final)
@app.get("/ms1/products", response_model=schemas.PaginatedProductsResponse, tags=["Productos"])
def get_products(
    page: int = Query(1, ge=1, description="Número de página"),
    limit: int = Query(20, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)
    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total > 0 else 1,
        "data": products
    }


# --- 3. GET PRODUCT BY ID ---
# CAMBIO: Cambiado a /ms1/products/{product_id}
@app.get("/ms1/products/{product_id}", response_model=schemas.ProductResponse, tags=["Productos"])
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return product


# --- 4. GET PRODUCT BY CATEGORY_ID ---
# CAMBIO: Cambiado a /ms1/products/category/{category_id}
@app.get("/ms1/products/category/{category_id}", response_model=schemas.PaginatedProductsResponse, tags=["Productos"])
def get_products_by_category(
    category_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(models.Product.category_id == category_id)
    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total > 0 else 1,
        "data": products
    }


# --- 5. GET PRODUCT BY STRING IN NAME ---
# CAMBIO: Cambiado a /ms1/products/search/by-name
@app.get("/ms1/products/search/by-name", response_model=schemas.PaginatedProductsResponse, tags=["Productos"])
def get_products_by_name(
    name: str = Query(..., min_length=1, description="Subcadena a buscar en el nombre del producto"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product).filter(models.Product.name.ilike(f"%{name}%"))
    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total > 0 else 1,
        "data": products
    }


# --- 6. GET PRODUCT BY PRICE (Rango o Precio Máximo) ---
# CAMBIO: Cambiado a /ms1/products/filter/by-price
@app.get("/ms1/products/filter/by-price", response_model=schemas.PaginatedProductsResponse, tags=["Productos"])
def get_products_by_price(
    min_price: Optional[Decimal] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Precio máximo"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)

    total = query.count()
    offset = (page - 1) * limit
    products = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total > 0 else 1,
        "data": products
    }


# --- 7. GET CATEGORIES ---
# CAMBIO: Cambiado a /ms1/categories (se agrega /ms1 y se remueve barra final)
@app.get("/ms1/categories", response_model=List[schemas.CategoryResponse], tags=["Categorías"])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()


# --- 8. GET AVAILABLE STOCK BY PRODUCT_ID AND CLIENT COUNTRY ---
# CAMBIO: Cambiado a /ms1/stock/available
@app.get("/ms1/stock/available", response_model=schemas.AvailableStockByClientResponse, tags=["Stock e Inventario"])
def get_available_stock_by_client_country(
    product_id: int = Query(..., description="ID del producto"),
    client_id: int = Query(..., description="ID del cliente"),
    db: Session = Depends(get_db)
):
    client_country = get_client_country_by_id(client_id)

    # Consulta de stock disponible filtrado por el país en la ubicación del almacén
    total_stock = (
        db.query(func.coalesce(func.sum(models.Stock.available_stock), 0))
        .join(models.Warehouse, models.Stock.warehouse_id == models.Warehouse.warehouse_id)
        .filter(models.Stock.product_id == product_id)
        .filter(models.Warehouse.location.ilike(f"%{client_country}%"))
        .scalar()
    )

    return {
        "product_id": product_id,
        "client_id": client_id,
        "client_country": client_country,
        "available_stock": total_stock
    }

@app.patch("/ms1/stock/reservar", response_model=schemas.ReservarStockResponse, tags=["Stock e Inventario"])
def reservar_stock(payload: schemas.ReservarStockRequest, db: Session = Depends(get_db)):
    client_country = get_client_country_by_id(payload.client_id)

    # Bloqueo de fila para evitar condiciones de carrera entre checkouts concurrentes
    stock_row = (
        db.query(models.Stock)
        .join(models.Warehouse, models.Stock.warehouse_id == models.Warehouse.warehouse_id)
        .filter(models.Stock.product_id == payload.product_id)
        .filter(models.Warehouse.location.ilike(f"%{client_country}%"))
        .with_for_update()
        .first()
    )

    if not stock_row or stock_row.available_stock < payload.cantidad:
        raise HTTPException(status_code=409, detail="Stock insuficiente para reservar")

    stock_row.available_stock -= payload.cantidad
    stock_row.reserve_stock += payload.cantidad
    db.commit()
    db.refresh(stock_row)

    return {
        "exito": True,
        "product_id": payload.product_id,
        "available_stock": stock_row.available_stock
    }

@app.patch("/ms1/stock/liberar", response_model=schemas.ReservarStockResponse, tags=["Stock e Inventario"])
def liberar_stock(payload: schemas.ReservarStockRequest, db: Session = Depends(get_db)):
    client_country = get_client_country_by_id(payload.client_id)
    stock_row = (
        db.query(models.Stock)
        .join(models.Warehouse, models.Stock.warehouse_id == models.Warehouse.warehouse_id)
        .filter(models.Stock.product_id == payload.product_id)
        .filter(models.Warehouse.location.ilike(f"%{client_country}%"))
        .with_for_update()
        .first()
    )
    if not stock_row:
        raise HTTPException(404, "Stock no encontrado")

    stock_row.available_stock += payload.cantidad
    stock_row.reserve_stock = max(0, stock_row.reserve_stock - payload.cantidad)
    db.commit()
    db.refresh(stock_row)

    return {"exito": True, "product_id": payload.product_id, "available_stock": stock_row.available_stock}


# --- ENDPOINTS EXTRAS (CRUD COMPLETO Y ALMACENES) ---

# CAMBIO: Cambiado a /ms1/warehouses (se remueve barra final)
@app.get("/ms1/warehouses", response_model=List[schemas.WarehouseResponse], tags=["Extras - Almacenes"])
def get_warehouses(db: Session = Depends(get_db)):
    return db.query(models.Warehouse).all()

# CAMBIO: Cambiado a /ms1/products (se remueve barra final)
@app.post("/ms1/products", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED, tags=["Extras - CRUD"])
def create_product(product_data: schemas.ProductCreate, db: Session = Depends(get_db)):
    new_product = models.Product(**product_data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

# CAMBIO: Cambiado a /ms1/products/{product_id}
@app.put("/ms1/products/{product_id}", response_model=schemas.ProductResponse, tags=["Extras - CRUD"])
def update_product(product_id: int, product_data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    update_dict = product_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

# CAMBIO: Cambiado a /ms1/products/{product_id}
@app.delete("/ms1/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Extras - CRUD"])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(product)
    db.commit()
    return None
