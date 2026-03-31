from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy 
import json

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
    salaris = db.Column(db.Float, default=0.0)
    lasten = db.relationship('Expense', backref='gebruiker', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    omschrijving = db.Column(db.String(100), nullable=False)
    bedrag = db.Column(db.Float, nullable=False)
    categorie = db.Column(db.String(50), nullable=False)
    frequentie = db.Column(db.String(50), nullable=False, default='Maandelijks')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if session.get('logged_in'):
        user = User.query.filter_by(id=session['user_id']).first()
        if not user:
            session.clear()
            return redirect(url_for('login'))
            
        mijn_lasten = user.lasten 
        totaal_per_maand = 0
        kosten_per_categorie = {}

        # Lijst om unieke categorieën in de juiste volgorde (meest recent) op te slaan
        recente_categorieen = []
        for last in reversed(mijn_lasten):
            if last.categorie not in recente_categorieen:
                recente_categorieen.append(last.categorie)

        for last in mijn_lasten:
            maand_bedrag = last.bedrag
            if last.frequentie == 'Kwartaal':
                maand_bedrag = last.bedrag / 3
            elif last.frequentie == 'Jaarlijks':
                maand_bedrag = last.bedrag / 12
            
            totaal_per_maand += maand_bedrag
            
            if last.categorie in kosten_per_categorie:
                kosten_per_categorie[last.categorie] += maand_bedrag
            else:
                kosten_per_categorie[last.categorie] = maand_bedrag

        grafiek_labels = list(kosten_per_categorie.keys())
        grafiek_data = list(kosten_per_categorie.values())

        # LOGICA: Maximaal 3 vaste suggesties en 2 eigen categorieën
        vaste_suggesties = ['Wonen', 'Abonnement', 'Boodschappen']
        
        # Filter de vaste suggesties eruit (zodat ze niet dubbel in de lijst komen)
        eigen_invoer = [cat for cat in recente_categorieen if cat not in vaste_suggesties]
        
        # Pak maximaal de eerste 2 (omdat we de lijst omdraaiden met 'reversed', zijn dit de meest recente)
        max_twee_eigen = eigen_invoer[:2]

        return render_template('back/home.html', 
                               data=user, 
                               lasten=mijn_lasten, 
                               totaal=totaal_per_maand,
                               salaris=user.salaris,
                               grafiek_labels=json.dumps(grafiek_labels),
                               grafiek_data=json.dumps(grafiek_data),
                               eigen_categorieen=max_twee_eigen)
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
            return redirect(url_for('home'))
            
    return render_template('login_page.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        
        bestaande_user = User.query.filter_by(email=email).first()
        if not bestaande_user:
            nieuwe_gebruiker = User(email=email, password=password, first_name=first_name, last_name=last_name)
            db.session.add(nieuwe_gebruiker)
            db.session.commit()
        
        return redirect(url_for('login'))
        
    return render_template('register_page.html')

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    ingevulde_categorie = request.form.get('categorie').strip().capitalize()

    nieuwe_last = Expense(
        omschrijving=request.form.get('omschrijving'),
        bedrag=float(request.form.get('bedrag')),
        categorie=ingevulde_categorie,
        frequentie=request.form.get('frequentie'),
        user_id=session['user_id']
    )
    db.session.add(nieuwe_last)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/update_salaris', methods=['POST'])
def update_salaris():
    if session.get('logged_in'):
        user = User.query.filter_by(id=session['user_id']).first()
        nieuw_salaris = request.form.get('salaris')
        
        if nieuw_salaris:
            user.salaris = float(nieuw_salaris)
            db.session.commit()
            
    return redirect(url_for('home'))

@app.route('/delete/<int:id>')
def delete_expense(id):
    if session.get('logged_in'):
        last = Expense.query.get(id)
        if last and last.user_id == session['user_id']:
            db.session.delete(last)
            db.session.commit()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)