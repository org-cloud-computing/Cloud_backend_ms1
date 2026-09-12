from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, ForeignKey, UniqueConstraint, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class Warehouse(Base):
    __tablename__ = "warehouse"

    warehouse_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    location = Column(String(255), nullable=True)

    stocks = relationship("Stock", back_populates="warehouse")

class Category(Base):
    __tablename__ = "category"

    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)

    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "product"

    product_id = Column(BigInteger, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("category.category_id", ondelete="RESTRICT"), nullable=False)
    name = Column(String(255), nullable=False)
    image_url = Column(Text, nullable=True)
    product_url = Column(Text, unique=True, nullable=True)
    stars = Column(Numeric(2, 1), default=0.0)
    reviews = Column(Integer, default=0)
    price = Column(Numeric(10, 2), nullable=False)

    category = relationship("Category", back_populates="products")
    stocks = relationship("Stock", back_populates="product", cascade="all, delete-orphan")

class Stock(Base):
    __tablename__ = "stock"

    stock_id = Column(BigInteger, primary_key=True, index=True)
    product_id = Column(BigInteger, ForeignKey("product.product_id", ondelete="CASCADE"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouse.warehouse_id", ondelete="RESTRICT"), nullable=False)
    available_stock = Column(Integer, nullable=False, default=0)
    reserve_stock = Column(Integer, nullable=False, default=0)
    last_update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="stocks")
    warehouse = relationship("Warehouse", back_populates="stocks")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_product_warehouse"),
    )
