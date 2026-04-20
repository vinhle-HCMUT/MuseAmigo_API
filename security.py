from passlib.context import CryptContext

# This tells Passlib to use the bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This function takes a plain password and returns the scrambled hash
def get_password_hash(password: str):
    return pwd_context.hash(password)

# We will use this later for the Login endpoint!
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)