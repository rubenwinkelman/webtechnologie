# init_db.py
from app import app, db
from flask_sqlalchemy import SQLAlchemy  

# Binnen de app-context heeft Flask toegang tot de juiste configuratie en database.
with app.app_context():
    # Maak alle tabellen aan die in de modellen van app.py zijn gedefinieerd.
    db.create_all()
    # Laat in de terminal zien dat het aanmaken is afgerond.
    print("Database succesvol aangemaakt!")
