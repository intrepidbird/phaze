from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import widgets, StringField, PasswordField, SubmitField, TextAreaField, RadioField, SelectMultipleField
from wtforms.validators import DataRequired
from sqlalchemy.orm import relationship, joinedload
import censusgeocode as cg
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecurefr'
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///db.sqlite'

db = SQLAlchemy()
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(128), unique = True, nullable = False)
    password = db.Column(db.String(128), nullable = False)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(128), nullable=False)
    charity_id = db.Column(db.Integer, db.ForeignKey('charity.id'), nullable=False)

class Charity(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(128), nullable = False)
    site = db.Column(db.String(128), unique = True, nullable = False)
    address = db.Column(db.String(128), nullable = False)
    number = db.Column(db.String(128), unique = True, nullable = False)
    description = db.Column(db.String(280), unique = True, nullable = False)
    orgtype = db.Column(db.String(128), nullable = False)
    keywords = relationship('Keyword', backref='charity', lazy=True)

db.init_app(app)
 
app.app_context().push()
db.create_all()

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class SignUpForm(FlaskForm):
    username = StringField('Username', validators = [DataRequired()])
    password = PasswordField('Password', validators = [DataRequired()])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators = [DataRequired()])
    password = PasswordField('Password', validators = [DataRequired()])
    submit = SubmitField('Log In')

class AddCharityForm(FlaskForm):
    name = StringField('Charity Name', validators=[DataRequired()])
    site = StringField('Website', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    number = StringField('Number', validators=[DataRequired()])
    description = TextAreaField('Page Content', validators=[DataRequired()])
    orgtype =  RadioField('Organization Type', choices=[('501(c)(1)','501(c)(1)'), ('501(c)(3)','501(c)(3)'), ('501(c)(4)','501(c)(4)'), ('501(c)(8)','501(c)(8)'), ('501(c)(10)','501(c)(10)'), ('501(c)(13)','501(c)(13)'), ('501(c)(19)','501(c)(19)'), ('501(c)(23)','501(c)(23)'), ('527', '527'), ('Other','Other')])
    keywords = MultiCheckboxField('Keywords',
                                   choices=[
                                       ('Disaster Relief', 'Disaster Relief'),
                                       ('Humanitarian Aid', 'Humanitarian Aid'),
                                       ('Refugee/Immigrant Assistance', 'Refugee/Immigrant Assistance'),
                                       ('Mental Health', 'Mental Health'),
                                       ('Education/Literacy', 'Education/Literacy'),
                                       ('Environment', 'Environment'),
                                       ('Human Rights', 'Human Rights'),
                                       ('Animal Welfare', 'Animal Welfare'),
                                       ('Poverty', 'Poverty'),
                                       ('Social Justice/Civil Rights', 'Social Justice/Civil Rights'),
                                       ('Hunger', 'Hunger'),
                                       ('Religious', 'Religious'),
                                       ('Healthcare', 'Healthcare'),
                                       ('Other', 'Other')
                                   ])
    submit = SubmitField('Add Charity')

@app.route('/signup', methods=["GET", "POST"])
def sign_up():
    form = SignUpForm()
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    elif form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('That username is already taken. Please choose a different one.', 'danger')
            return render_template('signup.html', signup_form=form)
        else:
            password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, password=password_hash)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('signup.html', signup_form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    elif form.validate_on_submit():
        user = User.query.filter_by(username = form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Incorrect username or password. Try again.', 'danger')
            return render_template('login.html', login_form=form)
    return render_template('login.html', login_form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route('/addcharity', methods=["GET", "POST"])
def addcharity():
    if current_user.is_authenticated:
        form = AddCharityForm()
        if form.validate_on_submit():
            charity = Charity(name=form.name.data, site=form.site.data, address=form.address.data, number=form.number.data, description=form.description.data, orgtype=form.orgtype.data, keywords=[Keyword(word=keyword, charity_id=current_user.id) for keyword in form.keywords.data])
            db.session.add(charity)
            db.session.commit()
            return redirect(url_for('index'))
        return render_template('addcharity.html', addcharity_form=form) 
    else:
        return redirect(url_for("login"))

@app.route("/directory")
def directory():
    keywords_list = [
        "Disaster Relief",
        "Humanitarian Aid",
        "Refugee/Immigrant Assistance",
        "Mental Health",
        "Education/Literacy",
        "Environment",
        "Human Rights",
        "Animal Welfare",
        "Poverty",
        "Social Justice/Civil Rights",
        "Hunger",
        "Religious,"
        "Healthcare,"
        "Other"
    ]
    keywords_dict = {keyword: keyword for keyword in keywords_list}
    selected_keyword = request.args.get('keyword', '')
    charities = Charity.query.all()
    if selected_keyword:
        charities = [charity for charity in charities if any(keyword.word == selected_keyword for keyword in charity.keywords)]
    return render_template('directory.html', charities=charities, keywords=keywords_dict)

@app.route('/map')
def map():
    charities = Charity.query.all() 
    for charity in charities:
        result = cg.onelineaddress(charity.address, returntype='locations')
        if result and len(result) > 0:
            location = result[0]['coordinates']
            charity.latitude = location['y']
            charity.longitude = location['x']
            charity.keywords_list = ', '.join([keyword.word for keyword in charity.keywords])
        else:
            print(f"No results found for {charity.address}")
    return render_template('map.html', charities=charities)

@app.route("/")
def index():
    return render_template("index.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
