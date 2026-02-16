from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy 

app = Flask(__name__)

app.secret_key = 'super_geheim_wachtwoord_123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    lasten = db.relationship('Expense', backref='gebruiker', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'
    
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    omschrijving = db.Column(db.String(100), nullable=False)
    bedrag = db.Column(db.Float, nullable=False)
    categorie = db.Column(db.String(50), nullable=False)
    # Koppeling naar de User id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/')
def home():
    if session.get('logged_in') == True:
        user = User.query.filter_by(id=session['user_id']).first() 
        mijn_lasten = user.lasten 
        totaal = sum(l.bedrag for l in mijn_lasten)
        return render_template('back/home.html', data=user, lasten=mijn_lasten, totaal=totaal)
    else:
        return render_template('homepagina.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:

            session['logged_in'] = True
            session['user_id'] = user.id
            mijn_lasten = user.lasten 
            totaal = sum(l.bedrag for l in mijn_lasten)
            return render_template('back/home.html', data=user, lasten=mijn_lasten, totaal=totaal)
            
    return render_template('login_page.html')

@app.route('/logout')
def logout():
    # SESSIE LEEGMAKEN
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        
        nieuwe_gebruiker = User(email=email, password=password, first_name=first_name, last_name=last_name)
        db.session.add(nieuwe_gebruiker)
        db.session.commit()
        
        return redirect(url_for('login'))
        
    return render_template('register_page.html')

@app.route('/add_expense', methods=['POST'])
def add_expense():
    nieuwe_last = Expense(
        omschrijving=request.form.get('omschrijving'),
        bedrag=float(request.form.get('bedrag')),
        categorie=request.form.get('categorie'),
        user_id=session['user_id'] # De ID uit de sessie die we eerder bespraken
    )
    db.session.add(nieuwe_last)
    db.session.commit()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)