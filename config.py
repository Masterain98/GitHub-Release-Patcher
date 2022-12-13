import os
import random
import string

# MySQL Settings
MYSQL_HOST = os.getenv('MYSQL_HOST')
try:
    MYSQL_PORT = int(os.getenv('MYSQL_PORT'))
except TypeError:
    print("MYSQL_PORT is not set, use default port 3306")
    MYSQL_PORT = 3306
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
except TypeError:
    print("ACCESS_TOKEN_EXPIRE_MINUTES is not set, use default value 30")
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Default user settings
INIT_PASSWORD = os.getenv('INIT_PASSWORD')

# Default settings for None values
if INIT_PASSWORD is None:
    print("INIT_PASSWORD is not set, use default password")
    INIT_PASSWORD = "ghrp-admin"
if SECRET_KEY is None:
    SECRET_KEY = ''.join(random.choices(string.ascii_letters, k=64))
    print(f"{SECRET_KEY} is generated as your JWT secret key")
if ALGORITHM is None:
    ALGORITHM = "HS256"
    print(f"{ALGORITHM} is set as your JWT algorithm")
