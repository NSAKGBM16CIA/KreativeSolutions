from flask import Flask, render_template, request, redirect, url_for, make_response, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, login_required, LoginManager
from fpdf import FPDF
from stripe.api_resources.quote import Quote
import os
from forms import SignupForm, User
from dotenv import load_dotenv
from datetime import datetime



app = Flask(__name__, template_folder='../templates', static_folder='../static')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exterior_cleaners.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
load_dotenv()

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    address = db.Column(db.String(120))
    roof_area = db.Column(db.Float)
    tile_type = db.Column(db.String(50))
    cleaning_method = db.Column(db.String(50))
    treatment_type = db.Column(db.String(50))
    drainage_type = db.Column(db.String(50))
    estimated_date = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Customer {self.name}>'


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    roof_area = db.Column(db.Float, nullable=False)
    tile_type = db.Column(db.String(50), nullable=False)
    cleaning_method = db.Column(db.String(50), nullable=False)
    treatment_type = db.Column(db.String(50), nullable=False)
    drainage_type = db.Column(db.String(50), nullable=False)
    estimated_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Job('{self.customer_name}', '{self.address}', '{self.roof_area}', '{self.tile_type}', '{self.cleaning_method}', '{self.treatment_type}', '{self.drainage_type}', '{self.estimated_date}')"



class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    job_duration = db.Column(db.Float)
    total_cost = db.Column(db.Float)
    image_url = db.Column(db.String(200))
    notes = db.Column(db.Text)

    customer = db.relationship('Customer', backref='reports')

    def __repr__(self):
        return f'<Report {self.id}>'


class PricingTier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    max_roof_area = db.Column(db.Float)
    max_job_duration = db.Column(db.Float)

    def __repr__(self):
        return f'<PricingTier {self.name}>'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)


class QuoteForm(db.Model):
    __tablename__ = 'quote_form'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    roof_area = db.Column(db.Float, nullable=False)
    tile_type = db.Column(db.String(50), nullable=False)
    cleaning_method = db.Column(db.String(50), nullable=False)
    treatment_type = db.Column(db.String(50), nullable=False)
    drainage_type = db.Column(db.String(50), nullable=False)
    date_of_cleaning = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<QuoteForm {self.customer_name}>'

    def validate_on_submit(self):
        pass


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(50))
    order_date = db.Column(db.DateTime)


db.create_all()

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'password':
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
            return render_template('login.html', error=error)
    else:
        return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        user = User(email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Thanks for signing up! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    quotes_price = Quote.query.filter_by(user_id=current_user.id)
    orders = Order.query.filter_by(user_id=current_user.id)

    return render_template('dashboard.html', quotes=quotes_price, orders=orders)


@app.route('/quotes', methods=['GET', 'POST'])
@login_required
def quotes():
    form = QuoteForm()

    if form.validate_on_submit():
        new_quote = Quote(
            user_id=current_user.id,
            address=form.address.data,
            roof_area=form.roof_area.data,
            tile_type=form.tile_type.data,
            cleaning_method=form.cleaning_method.data,
            treatment_type=form.treatment_type.data,
            drainage_type=form.drainage_type.data,
            estimated_date=form.date_of_cleaning.data
        )

        db.session.add(new_quote)
        db.session.commit()

        flash('Your quote has been saved.', 'success')
        return redirect(url_for('quotes'))

    quotes_data = Quote.query.filter_by(user_id=current_user.id)

    return render_template('quotes.html', form=form, quotes=quotes_data)



@app.route('/googlemaps')
def googlemaps():
    user_id = session.get('user_id')
    user_data = User.query.filter_by(id=user_id).first()
    return render_template('googlemaps.html', user=user_data)



@app.route('/pricing', methods=['GET', 'POST'])
def pricing():
    tiers = PricingTier.query.all()

    if request.method == 'POST':
        roof_area = float(request.form['roof_area'])
        job_duration = float(request.form['job_duration'])
        tier_name = request.form['tier_name']

        tier = PricingTier.query.filter_by(name=tier_name).first()

        if roof_area <= tier.max_roof_area and job_duration <= tier.max_job_duration:
            price = tier.price
        else:
            price = 'N/A'

        return render_template('pricing.html', tiers=tiers, price=price, tier_name=tier_name)

    return render_template('pricing.html', tiers=tiers, price='', tier_name='')




@app.route('/report/<int:customer_id>/<int:job_id>')
def report(customer_id, job_id):
    customer = Customer.query.get(customer_id)
    job = Job.query.get(job_id)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(40, 10, 'Customer Report')
    pdf.ln()
    pdf.cell(40, 10, f'Name: {customer.name}')
    pdf.ln()
    pdf.cell(40, 10, f'Address: {customer.address}')
    pdf.ln()
    pdf.cell(40, 10, f'Roof area: {job.roof_area} sq. m')
    pdf.ln()
    pdf.cell(40, 10, f'Tile type: {job.tile_type}')
    pdf.ln()
    pdf.cell(40, 10, f'Cleaning method: {job.cleaning_method}')
    pdf.ln()
    pdf.cell(40, 10, f'Treatment type: {job.treatment_type}')
    pdf.ln()
    pdf.cell(40, 10, f'Drainage type: {job.drainage_type}')
    pdf.ln()
    pdf.cell(40, 10, f'Estimated date of cleaning: {job.estimated_date}')
    pdf.ln()
    pdf.output("report.pdf")

    response = make_response(open("report.pdf", "rb").read())
    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename='report.pdf')
    return response



if __name__ == '__main__':
    app.run(debug=True)
