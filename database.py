import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv


# Load variables from the .env file
load_dotenv()

# Get the cloud URL, or fall back to localhost if the .env is missing
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://root:@localhost/museamigo_db"
)

# The Engine is the core interface to the database
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# The SessionLocal class will be used to create actual database sessions for your API requests
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your database models (tables)
Base = declarative_base()

# Dependency function to get a database session for your FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()