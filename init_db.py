# init_db.py
from app import app, db
from flask_sqlalchemy import SQLAlchemy  

with app.app_context():
    db.create_all()
    print("Database succesvol aangemaakt!")