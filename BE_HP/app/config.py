import os
from dotenv import load_dotenv
from datetime import timedelta

class Config: 
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/mydatabase')
    MONGO_DB  = os.getenv("MONGO_DB", "Nuoc_HP")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-jwt")
    JSON_SORT_KEYS = False
    
    JWT_TOKEN_LOCATION = ["cookies", "headers"]
    JWT_COOKIE_SECURE = False  # Set to True in production with HTTPS
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SAMESITE = "Strict"  
    JWT_ACCESS_COOKIE_NAME = "access_token"
    JWT_REFRESH_COOKIE_NAME = "refresh_token"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_CSRF_PROTECT = False  # Tắt CSRF protection cho cookies

class MLConfig: 
    BASE_DIR = os.path.dirname(__file__)
    default_model_path = os.path.abspath(os.path.join(BASE_DIR, 'ml', 'lstm_autoencoder', 'pretrained_weights', 'lstm_ae.pth'))
    LSTM_AE_MODEL_PATH = os.getenv('LSTM_AE_MODEL_PATH', default_model_path)
    HISTORICAL_DATA_DAYS = 40
    LSTM_AE_CONFIG = {
        'input_size': int(os.getenv("LSTMAE_INPUT_SIZE", "1")),  
        'hidden_size': int(os.getenv("LSTMAE_HIDDEN_SIZE", "64")),
        'num_layers': int(os.getenv("LSTMAE_NUM_LAYERS", "2")),
        'dropout_ratio': float(os.getenv("LSTMAE_DROPOUT_RATIO", "0.1")),
        'seq_len': int(os.getenv("LSTMAE_SEQ_LEN", "6")),  
        'use_act': os.getenv("LSTMAE_USE_ACT", "true").lower() == "true",
    }

SWAGGER_CONFIG = {
    "headers": [], 
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ], 
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"     
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "APIs documentation", 
        "description": "API documentation for the BE_HP project",
        "version": "1.0.0"
    },
    "consumes": [
        "application/json"
    ],
    "produces": [
        "application/json"
    ],
}

