from flask import Flask, render_template 
from flask_sqlalchemy import SQLAlchemy 

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Een 'Model' is eigenlijk een tabel in je database
class Gebruiker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gebruikersnaam = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<Gebruiker {self.gebruikersnaam}>'


@app.route('/')
def home():
    return render_template('homepagina.html')

@app.route('/login')
def login():
    return render_template('login_page.html')

