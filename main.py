
from itertools import product
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Literal
from typing import Pattern
from motor.motor_asyncio import AsyncIOMotorClient
import gridfs
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from fastapi import File, UploadFile
from io import BytesIO
from pydantic import BaseModel, Field, conint, confloat, constr
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware



# FastAPI app initialization
app = FastAPI()

# MongoDB connection setup
client = AsyncIOMotorClient("mongodb+srv://bismaawan003:0000@cluster0.rm3gu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["petiverse"] # Database name
products_collection = db["products"]
users_collection = db["users"]
orders_collection = db["orders"]
cart_collection = db["cart"]

# Pydantic models for request/response validation
class Product(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., max_length=1000)
    price: float = Field(..., gt=0, lt=100000)
    category: str= Field(...,min_length=1, max_length=50)
    stock: conint = Field(default=0, ge=0)
    images: List[str]
    availability: Literal["in stock","out of stock","preorder"]
    seller_id: str

    class Config:
        schema_extra={
            "example": {
                "name": "Golden Retriever",
                "description": "a sturdy, muscular dog of medium size, famous for the dense, lustrous coat of gold that gives the breed its name. The broad head, with its friendly and intelligent eyes, short ears, and straight muzzle, is a breed hallmark.",
                "price": 10000,
                "stock": 15,
                "availability": "in stock",
                "category": "dog",
                "image": "https://www.google.com/imgres?q=golden%20retriever%20details&imgurl=https%3A%2F%2Fwww.dailypaws.com%2Fthmb%2FDQfQglzyKWlVSlsDwKPprF2iMSg%3D%2F1500x0%2Ffilters%3Ano_upscale()%3Amax_bytes(150000)%3Astrip_icc()%2Fgolden-retriever-177213599-2000-a30830f4d2b24635a5d01b3c5c64b9ef.jpg&imgrefurl=https%3A%2F%2Fwww.dailypaws.com%2Fgolden-retriever-dog-breed-7491294&docid=WkKCC-IjPWkGAM&tbnid=UBtZKt7A0vEEAM&vet=12ahUKEwjRmJHsjoyNAxWoVaQEHSPQOLgQM3oECH0QAA..i&w=1500&h=1000&hcb=2&ved=2ahUKEwjRmJHsjoyNAxWoVaQEHSPQOLgQM3oECH0QAA",
                "seller_id": "507f1f77bcf86cd799439015"
            }
        }

class User(BaseModel):
    username: str
    email: str
    password: str
    role: str # buyer/seller

class Pet(BaseModel):
    name: str
    age: int
    breed: str
    category: str
    description: Optional[str]= None
    images: List[str]
    owner_id: str

    class Config:
        schema_extra = {
            "example": {
                "name": "Whiskers",
                "age": 2,
                "breed": "Siamese",
                "category": "cat",
                "images": ["https://example.com/cat1.jpg"],
                "owner_id": "507f1f77bcf86cd799439012"
            }
        }

class Order(BaseModel):
    product_ids: List[str]
    user_id: str
    quantity: List[int]
    total_amount: float
    shipping_address: str
    status: Literal["pending", "shipped", "delivered","canceled"]
    class Config:
        schema_extra = {
            "example": {
                "product_ids": ["507f1f77bcf86cd799439013", "507f1f77bcf86cd799439014"],
                "user_id": "507f1f77bcf86cd799439015",
                "quantities": [1, 2],
                "total_amount": 25000,
                "shipping_address": "123 Pet Street, Dogville",
                "status": "pending"
            }
        }

class CartItem(BaseModel):
    product_id: str
    user_id: str
    quantity: int

class ImageModel(BaseModel):
    image: str

class ProductResponse(BaseModel):
    product: dict

class Review(BaseModel):
    product_id: str
    user_id:str
    rating: int
    comment: Optional[str]= None
    created_at: Optional[datetime]= None
    class Config:
        schema_extra = {
            "example": {
                "product_id": "507f1f77bcf86cd799439016",
                "user_id": "507f1f77bcf86cd799439017",
                "rating": 5,
                "comment": "Excellent pet! Very friendly."
            }
        }

class Post(BaseModel):
    title: str
    content: str
    images: List[str]
    user_id: str
    created_at: Optional[datetime]= None

class category(BaseModel):
    name: str
    description: Optional[str]= None
    class Config:
        schema_extra = {
            "example": {
                "name": "dogs",
                "description": "All dog breeds and accessories"
            }
        }


# Helper function to convert ObjectId to string
def serialize_object_id(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError("ObjectId must be of type ObjectId.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change in production)
    allow_methods=["GET", "POST", "PUT", "DELETE"],
)

#pet api
@app.get("/pets")
async def get_all_pets():
    pets = await db["pets"].find().to_list(length=100)
    return {"pets":pets}

# ------------------------ Product APIs ------------------------

@app.post("/products")
async def create_product(product: Product):
    product_dict = product.dict()
    result = await products_collection.insert_one(product_dict)
    return {"id": str(result.inserted_id), "message": "Product added successfully!"}

@app.get("/products")
async def get_products(skip: int = 0, limit: int = 10):
    products = await products_collection.find().skip(skip).limit(limit).to_list()
    return {"products": products}

@app.put("/products/{product_id}")
async def update_product(product_id: str, product: Product):
    updated_product = await products_collection.update_one(
        {"_id": ObjectId(product_id)}, {"$set": product.dict()}
    )
    if updated_product.modified_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product updated successfully!"}

@app.delete("/products/{product_id}")
async def delete_product(product_id: str):
    result = await products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully!"}


# ------------------------ Order APIs ------------------------

@app.post("/orders")
async def create_order(order: Order):
    order_dict = order.dict()
    result = await orders_collection.insert_one(order_dict)
    return {"id": str(result.inserted_id), "message": "Order placed successfully!"}

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order": order}

@app.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order canceled successfully!"}

#----------------------------Category Management----------------------------
class Category(BaseModel):
    name : str
    description : Optional[str] = None

@app.post("/categories")
async def create_category(category: Category):
    category_dict = category.dict()
    result = await db["categories"].insert_one(category_dict)
    return {"id": str(result.inserted_id), "message": "Category Added Successfully"}

@app.get("/categories")
async def get_categories():
    categories = await db["categories"].find().to_list(length = 100)
    return {"categories": categories}

@app.get("/categories/{category_id}")
async def get_category(category_id: str):
    category = await db["categories"].find_one({"_id":ObjectId(category_id)})
    if category is None:
        raise HTTPException(status_code=404, detail= "Category not found")
    return {"category": category}

@app.put("/categories/{category_id}")
async def update_category(category_id: str, category: Category):
    updated_category = await db["categories"].update_one({"_id": ObjectId(category_id)}, {"$set": category.dict()})
    if updated_category.modified_count == 0:
        raise HTTPException(status_code = 404, detail= "Category not found")
    return {"message": "Category updated successfully!"}

@app.delete("/categories/{category_id}")
async def delete_category(category_id= str):
    result = await db["categories"].delete_one({"_id":ObjectId(category_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code= 404, detail= "Category not found")
    return {"message": "Category deleted successfully1"}


#------------------------Product Api With Image Upload-------------------------
fs = AsyncIOMotorGridFSBucket(db)

@app.post("/products/with-image")
async def create_product_with_image(product: Product, images: List[UploadFile]):
    images_ids = []
    for image in images:
        image_data = await image.read()
        gridfs_file = await fs.upload_from_stream(image.filename, image_data)
        images_ids.append(str(gridfs_file))

    product_dict["images"]= images_ids
    result = await products_collection.insert_one(product_dict)
    return {"_id": str(result.inserted_id),"message": "Product added successfully!"}

@app.get("/products/{product_id}")
async def get_products(product_id: str):
    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if product is None:
        raise HTTPException(status_code= 404, detail= "Product not found")
    return {"product": product}

# Fetch images from gridfs
    product_images = []
    for image_id in product["images"]:
        gridfs_file = fs.get(ObjectId(image_id))
        product_images.append({"image": gridfs_file.read()})
    product["images"] = product_images
    return {"product": product}

#------------------------Advance Product Search------------------------
@app.get("/search/products")
async def search_products(
    name: Optional[str] = Query(None),
    category: Optional[str]= Query(None),
    price_min: Optional[float]= Query(None),
    price_max: Optional[float]= Query(None)
):
    search_query = {}
    if name: search_query["name"]= {"$regex": name, "$options":"i"}
    if category: search_query["category"]= category
    if price_min and price_max:
        search_query["price"]= {"$gte": price_min, "$lte": price_max}
    elif price_min: search_query["price"]= {"$gte": price_min}
    elif price_max: search_query["price"]= {"$lte": price_max}

    products= await db["products"].find(search_query).to_list(length=100)
    return {"products": products}

#--------------------------rating and Reviews-----------------------=-----
@app.post("/reviews")
async def create_reviews(review: Review):
    review_dict = review.dict()
    result = await db["reviews"].insert_one(review_dict)
    return {"id": str(result.inserted_id), "message": "Review added successfully!"}

@app.get("/reviews/{product_id}")
async def get_reviews(product_id: str):
    reviews= await db["reviews"].find({"product_id": product_id}).to_list(length=100)
    return {"reviews": reviews}