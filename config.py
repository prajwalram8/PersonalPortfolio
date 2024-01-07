import os
import binascii

DEBUG = False

# Generate a random secret key
SECRET_KEY = binascii.hexlify(os.urandom(24)).decode()

root = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(root, 'sqlite3.db')