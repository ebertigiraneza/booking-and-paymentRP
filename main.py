from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from importlib import import_module
import uvicorn
from contextlib import asynccontextmanager
from shared.databases import database, Base, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    Base.metadata.create_all(bind=engine) 
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

# Autorise les requêtes CORS si nécessaire
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import dynamique des sous-applications
services = {
    "authentification": {"prefix": "/auth", "router_name": "router"},
    "wallet": {"prefix": "/wallet", "router_name": "router"},
    "booking":{"prefix": "/booking", "router_name": "router"},
    "payment":{"prefix": "/payment", "router_name": "router"}
}

for name, config in services.items():
    module = import_module(f"{name}.main")
    router = getattr(module, config["router_name"])
    app.include_router(router, prefix=config["prefix"])
    print(f"Included {name} at {config['prefix']}")

@app.get("/")
def read_root():
    return {"message": "API Gateway", "services": list(services.keys())}

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Booking and Payment System API",
        version="1.0",
        routes=app.routes,
    )
    
    # Configuration pour regrouper les docs par service
    openapi_schema["tags"] = [
        {"name": "Authentication", "description": "User authentication endpoints"},
        {"name": "Wallet", "description": "Wallet management endpoints"},
        {"name": "Booking", "description": "Booking endpoints"},
        {"name": "Payement", "description": "Payment endpoints"}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    