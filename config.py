import os
import binascii

DEBUG = False

# Generate a random secret key
SECRET_KEY = 'e040cec8b0f2f050c14643973a8db06abe4b2a50ff554d62'

root = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(root, 'sqlite3.db')
