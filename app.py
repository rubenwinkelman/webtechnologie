from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy 
from werkzeug.security import check_password_hash, generate_password_hash
import json

# Initialiseer de Flask applicatie
app = Flask(__name__)

# Configuratie van de applicatie
# De secret_key beveiligt de sessie (cookies). In een echte app moet dit een veilige, verborgen string zijn.
app.secret_key = 'super_geheim_wachtwoord_123'
# Stel de database in op SQLite, dit maakt lokaal een bestand 'database.db' aan
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
# Zet waarschuwingen uit om geheugen te besparen
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiseer de database koppeling
db = SQLAlchemy(app)


# --- DATABASE MODELLEN ---
# Hier definiëren we hoe de tabellen in onze database eruit zien.

class User(db.Model):
    # Unieke ID voor elke gebruiker (Primary Key)
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    # E-mail moet uniek zijn, zodat twee gebruikers niet hetzelfde account kunnen aanmaken
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    salaris = db.Column(db.Float, default=0.0)
    # Koppeling (relatie) met de Expense tabel. Eén gebruiker kan meerdere lasten hebben.
    # lazy=True zorgt ervoor dat de lasten pas geladen worden als we ze opvragen.
    lasten = db.relationship('Expense', backref='gebruiker', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    omschrijving = db.Column(db.String(100), nullable=False)
    bedrag = db.Column(db.Float, nullable=False)
    categorie = db.Column(db.String(50), nullable=False)
    frequentie = db.Column(db.String(50), nullable=False, default='Maandelijks')
    # ForeignKey verwijst naar het ID van de gebruiker die deze last heeft aangemaakt
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Zorg ervoor dat de tabellen daadwerkelijk worden aangemaakt in de database
# Dit moet binnen de app_context gebeuren zodat Flask weet voor welke app de DB is.
with app.app_context():
    db.create_all()


# --- HULPFUNCTIES ---

def bereken_maandbedrag(last):
    """Rekent alle bedragen om naar een maandbasis, ongeacht de frequentie."""
    maand_bedrag = last.bedrag
    if last.frequentie == 'Kwartaal':
        maand_bedrag = last.bedrag / 3
    elif last.frequentie == 'Jaarlijks':
        maand_bedrag = last.bedrag / 12
    return maand_bedrag

def is_gehasht_wachtwoord(opgeslagen_wachtwoord):
    """Controleert of een wachtwoord in de database al is beveiligd (gehasht)."""
    return opgeslagen_wachtwoord.startswith('scrypt:') or opgeslagen_wachtwoord.startswith('pbkdf2:')

def controleer_wachtwoord(user, ingevoerd_wachtwoord):
    """Vergelijkt het ingevoerde wachtwoord met het wachtwoord in de database."""
    if is_gehasht_wachtwoord(user.password):
        # Gebruik de veilige check-functie van Werkzeug
        return check_password_hash(user.password, ingevoerd_wachtwoord)
    # Fallback voor onbeveiligde wachtwoorden (bijv. uit een oude versie van de app)
    return user.password == ingevoerd_wachtwoord


# --- ROUTES (PAGINA'S EN ACTIES) ---

@app.route('/')
def home():
    """De hoofdpagina / het dashboard."""
    # Controleer of de gebruiker is ingelogd
    if session.get('logged_in'):
        # Haal de huidige gebruiker op uit de database via het opgeslagen sessie-ID
        user = User.query.filter_by(id=session['user_id']).first()
        
        # Als de gebruiker (om wat voor reden dan ook) niet meer bestaat, log uit
        if not user:
            session.clear()
            return redirect(url_for('login'))
            
        mijn_lasten = user.lasten 
        totaal_per_maand = 0
        kosten_per_categorie = {}
        
        # NIEUW: Hier houden we per categorie het totaal en het aantal items bij
        categorie_info = {} 
        lasten_overzicht = []

        # Maak een lijst van recent gebruikte categorieën voor de dropdown in HTML
        recente_categorieen = []
        for last in reversed(mijn_lasten):
            if last.categorie not in recente_categorieen:
                recente_categorieen.append(last.categorie)

        # Loop door alle lasten om totalen te berekenen en lijsten te vullen
        for last in mijn_lasten:
            maand_bedrag = bereken_maandbedrag(last)
            totaal_per_maand += maand_bedrag

            lasten_overzicht.append({
                'id': last.id,
                'omschrijving': last.omschrijving,
                'categorie': last.categorie,
                'frequentie': last.frequentie,
                'bedrag': last.bedrag,
                'maand_bedrag': maand_bedrag
            })
            
            # Vul de data voor de Chart.js grafiek (totaal per categorie)
            if last.categorie in kosten_per_categorie:
                kosten_per_categorie[last.categorie] += maand_bedrag
            else:
                kosten_per_categorie[last.categorie] = maand_bedrag

            # NIEUW: Vul de data voor de gebundelde categorieën weergave
            if last.categorie not in categorie_info:
                categorie_info[last.categorie] = {'totaal': 0, 'aantal': 0}
            categorie_info[last.categorie]['totaal'] += maand_bedrag
            categorie_info[last.categorie]['aantal'] += 1

        # Bereid de data voor op JavaScript (JSON formaat)
        grafiek_labels = list(kosten_per_categorie.keys())
        grafiek_data = list(kosten_per_categorie.values())

        # Bepaal welke eigen categorieën de gebruiker als suggestie krijgt
        vaste_suggesties = ['Wonen', 'Abonnement', 'Boodschappen']
        eigen_invoer = [cat for cat in recente_categorieen if cat not in vaste_suggesties]
        max_twee_eigen = eigen_invoer[:2]

        # Laad de dashboard pagina en geef alle benodigde variabelen mee aan Jinja
        return render_template('back/home.html', 
                               data=user, 
                               lasten=mijn_lasten, 
                               lasten_overzicht=lasten_overzicht,
                               totaal=totaal_per_maand,
                               resterend=user.salaris - totaal_per_maand,
                               salaris=user.salaris,
                               grafiek_labels=json.dumps(grafiek_labels),
                               grafiek_data=json.dumps(grafiek_data),
                               eigen_categorieen=max_twee_eigen,
                               categorie_info=categorie_info) 
    else:
        # Als je niet bent ingelogd, zie je de publieke landingspagina
        return render_template('homepagina.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Verwerkt het inloggen."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Zoek de gebruiker op basis van e-mail
        user = User.query.filter_by(email=email).first()
        
        # Als gebruiker bestaat en wachtwoord klopt
        if user and controleer_wachtwoord(user, password):
            # Veiligheidsupgrade: als het wachtwoord nog niet gehasht is in de database, doe dat nu
            if not is_gehasht_wachtwoord(user.password):
                user.password = generate_password_hash(password)
                db.session.commit()

            # Zet de sessievariabelen om de gebruiker ingelogd te houden
            session['logged_in'] = True
            session['user_id'] = user.id
            return redirect(url_for('home'))
            
        # Foutieve inloggegevens
        return render_template('login_page.html', error='De ingevoerde gegevens kloppen niet.')
            
    # GET request: toon simpelweg het formulier
    return render_template('login_page.html', error=None)


@app.route('/logout')
def logout():
    """Logt de gebruiker uit door de sessie te wissen."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Verwerkt de registratie van een nieuwe gebruiker."""
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        
        # Controleer of het e-mailadres niet al bestaat
        bestaande_user = User.query.filter_by(email=email).first()
        if not bestaande_user:
            # Maak nieuw User object aan en hash het wachtwoord direct
            nieuwe_gebruiker = User(
                email=email,
                password=generate_password_hash(password),
                first_name=first_name,
                last_name=last_name
            )
            # Voeg toe aan database en sla op
            db.session.add(nieuwe_gebruiker)
            db.session.commit()
            return redirect(url_for('login'))
        else:
            # Foutmelding als e-mail al in de database zit
            return render_template('register_page.html', error='Dit e-mailadres wordt al gebruikt.')
            
    # GET request: toon registratie formulier
    return render_template('register_page.html', error=None)


# --- CRUD OPERATIES (Create, Read, Update, Delete) ---

@app.route('/add_expense', methods=['POST'])
def add_expense():
    """Voegt een nieuwe vaste last toe voor de ingelogde gebruiker."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    nieuwe_last = Expense(
        omschrijving=request.form.get('omschrijving'),
        bedrag=float(request.form.get('bedrag')),
        # strip() haalt spaties weg, capitalize() zorgt voor een hoofdletter (bijv ' auto' -> 'Auto')
        categorie=request.form.get('categorie').strip().capitalize(),
        frequentie=request.form.get('frequentie'),
        user_id=session['user_id'] # Koppel aan huidige gebruiker
    )
    db.session.add(nieuwe_last)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/edit_expense/<int:id>', methods=['POST'])
def edit_expense(id):
    """Bewerkt een specifieke bestaande last op basis van het ID."""
    if session.get('logged_in'):
        # Haal het specifieke object op uit de database
        last = Expense.query.get(id)
        # Veiligheidscheck: bestaat de last en behoort deze echt toe aan de huidige gebruiker?
        if last and last.user_id == session['user_id']:
            last.omschrijving = request.form.get('omschrijving')
            last.bedrag = float(request.form.get('bedrag'))
            last.categorie = request.form.get('categorie').strip().capitalize()
            last.frequentie = request.form.get('frequentie')
            db.session.commit() # Sla de wijzigingen op
            
    return redirect(url_for('home'))


@app.route('/delete/<int:id>')
def delete_expense(id):
    """Verwijdert een vaste last."""
    if session.get('logged_in'):
        last = Expense.query.get(id)
        # Extra veiligheidscheck voor het verwijderen (voorkomt dat iemand ID's raadt in de URL)
        if last and last.user_id == session['user_id']:
            db.session.delete(last)
            db.session.commit()
    return redirect(url_for('home'))


@app.route('/update_salaris', methods=['POST'])
def update_salaris():
    """Werkt het netto maandsalaris van de gebruiker bij."""
    if session.get('logged_in'):
        user = User.query.filter_by(id=session['user_id']).first()
        nieuw_salaris = request.form.get('salaris')
        
        if nieuw_salaris:
            user.salaris = float(nieuw_salaris)
            db.session.commit()
            
    return redirect(url_for('home'))


# Start de server als dit bestand direct wordt uitgevoerd (en niet geïmporteerd is)
if __name__ == "__main__":
    # debug=True zorgt ervoor dat de server automatisch herstart bij code-wijzigingen en toont duidelijke errors
    app.run(debug=True)