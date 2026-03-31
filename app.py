from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy 

# Maak de Flask-app aan; deze vormt het startpunt van de hele website.
app = Flask(__name__)

# De secret key gebruikt Flask om sessiegegevens veilig te ondertekenen.
app.secret_key = 'super_geheim_wachtwoord_123'

# Hier configureren we waar de SQLite-database staat en dat we geen extra tracking willen.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy koppelt onze Python-modellen aan de database.
db = SQLAlchemy(app)

# Dit model stelt een gebruiker van de applicatie voor.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    # Via deze relatie kunnen we alle vaste lasten van een gebruiker opvragen.
    lasten = db.relationship('Expense', backref='gebruiker', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'
    
# Dit model bewaart elke vaste last die een gebruiker toevoegt.
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    omschrijving = db.Column(db.String(100), nullable=False)
    bedrag = db.Column(db.Float, nullable=False)
    categorie = db.Column(db.String(50), nullable=False)
    # Koppeling naar de User id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# De home-route toont afhankelijk van de sessie een publieke pagina of het persoonlijke dashboard.
@app.route('/')
def home():
    if session.get('logged_in') == True:
        # Haal de ingelogde gebruiker op en bereken het totaal van alle lasten.
        user = User.query.filter_by(id=session['user_id']).first() 
        mijn_lasten = user.lasten 
        totaal = sum(l.bedrag for l in mijn_lasten)
        return render_template('back/home.html', data=user, lasten=mijn_lasten, totaal=totaal)
    else:
        return render_template('homepagina.html')

# De login-route verwerkt zowel het formulier tonen als het inloggen zelf.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Lees de ingevulde waarden uit het loginformulier.
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Zoek de gebruiker op basis van het opgegeven e-mailadres.
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:

            # Bewaar in de sessie dat deze gebruiker succesvol is ingelogd.
            session['logged_in'] = True
            session['user_id'] = user.id
            mijn_lasten = user.lasten 
            totaal = sum(l.bedrag for l in mijn_lasten)
            return render_template('back/home.html', data=user, lasten=mijn_lasten, totaal=totaal)
            
    return render_template('login_page.html')

# Met logout verwijderen we alle sessie-informatie van de huidige gebruiker.
@app.route('/logout')
def logout():
    # SESSIE LEEGMAKEN
    session.clear()
    return redirect(url_for('login'))

# Via register kan een nieuwe gebruiker een account aanmaken.
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Lees alle velden uit het registratieformulier.
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        
        # Maak een nieuw User-object en sla dit op in de database.
        nieuwe_gebruiker = User(email=email, password=password, first_name=first_name, last_name=last_name)
        db.session.add(nieuwe_gebruiker)
        db.session.commit()
        
        return redirect(url_for('login'))
        
    return render_template('register_page.html')

# Deze route voegt een nieuwe vaste last toe voor de ingelogde gebruiker.
@app.route('/add_expense', methods=['POST'])
def add_expense():
    # Maak van de formulierdata een nieuw Expense-object.
    nieuwe_last = Expense(
        omschrijving=request.form.get('omschrijving'),
        bedrag=float(request.form.get('bedrag')),
        categorie=request.form.get('categorie'),
        user_id=session['user_id'] # De ID uit de sessie die we eerder bespraken
    )
    # Sla de nieuwe vaste last direct op in de database op.
    db.session.add(nieuwe_last)
    db.session.commit()
    return redirect(url_for('home'))

# Start de Flask development-server wanneer dit bestand direct wordt uitgevoerd.
if __name__ == "__main__":
    app.run(debug=True)
