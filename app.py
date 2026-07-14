import os
import joblib
import numpy as np
import random
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# --- App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = '30052004'  # Change this!
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

CARDIO_FACTS = [
    "Fact: At least 30 minutes of moderate-intensity exercise (like brisk walking) 5 days a week can improve heart health.",
    "Habit: Reducing sodium (salt) in your diet is one of the most effective ways to lower high blood pressure.",
    "Insight: Quitting smoking can halve your risk of coronary heart disease within just one year.",
    "Habit: Aim for 7-9 hours of quality sleep per night. Poor sleep is linked to an increased risk of heart disease.",
    "Fact: Diets high in fruits, vegetables, and whole grains protect your heart. Aim for 5 portions of fruits and veggies daily.",
    "Insight: Knowing your numbers (blood pressure, cholesterol, blood sugar) is the first step to managing heart risk.",
    "Fact: Heart disease is not just a 'man's disease.' It is the leading cause of death for women worldwide.",
    "Habit: Managing stress through activities like meditation, yoga, or hobbies can help lower your risk.",
    "Insight: Your model uses Pulse Pressure (Systolic - Diastolic BP). A high pulse pressure (over 60) can be a risk indicator.",
    "Fact: The 'ap_hi' (Systolic) value in your model is the single most important predictor of cardiovascular risk."
]




# --- Login Manager Setup ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ML Model Loading ---
# Load the model *once* when the app starts
try:
    model = joblib.load('model.pkl')
    print("Model loaded successfully.")
except FileNotFoundError:
    print("Error: model.pkl not found. Make sure you've run Step 1.")
    model = None

# --- Database Models (Flask-SQLAlchemy) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    predictions = db.relationship('Prediction', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    result = db.Column(db.String(50), nullable=False)
    probability = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Store the input features for display
    age = db.Column(db.Integer, nullable=False)
    ap_hi = db.Column(db.Integer, nullable=False)
    ap_lo = db.Column(db.Integer, nullable=False)
    cholesterol = db.Column(db.Integer, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    pulsepressure = db.Column(db.Integer, nullable=False)


# --- Forms (Flask-WTF) ---
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class PredictionForm(FlaskForm):
    age = IntegerField('Age (in years)', validators=[DataRequired()])
    height = FloatField('Height (in cm)', validators=[DataRequired()])
    weight = FloatField('Weight (in kg)', validators=[DataRequired()])
    ap_hi = IntegerField('Systolic Blood Pressure (ap_hi)', validators=[DataRequired()])
    ap_lo = IntegerField('Diastolic Blood Pressure (ap_lo)', validators=[DataRequired()])
    cholesterol = SelectField('Cholesterol Level', 
                              choices=[(1, 'Normal'), (2, 'Above Normal'), (3, 'Excessive')],
                              coerce=int, validators=[DataRequired()])
    submit = SubmitField('Predict')


# --- Routes ---

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()                  #form object is created from the LOginForm class
    if form.validate_on_submit():       #processig the details of the user entered in the web-form
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('predictor'))
        else:
            flash('Login Unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/predictor', methods=['GET', 'POST'])
@login_required
def predictor():
    form = PredictionForm()
    if form.validate_on_submit() and model:
        # --- 1. Get data from form ---
        age = form.age.data
        height = form.height.data
        weight = form.weight.data
        ap_hi = form.ap_hi.data
        ap_lo = form.ap_lo.data
        cholesterol = form.cholesterol.data
        
        # --- 2. Apply Preprocessing (Clipping) ---
        # Note: Your script clips *after* reading, so we clip the user input
        weight = np.clip(weight, 20, 180)
        height = np.clip(height, 130, 220)
        ap_hi = np.clip(ap_hi, 60, 240)
        ap_lo = np.clip(ap_lo, 40, 130)

        #  Feature Engineering 
        bmi = weight / ((height / 100) ** 2 + 1e-6) 
        pulsepressure = ap_hi - ap_lo

      
        
        # ['age', 'ap_hi', 'ap_lo', 'cholesterol', 'bmi', 'pulsepressure']
        features = [[age, ap_hi, ap_lo, cholesterol, bmi, pulsepressure]]
        
        # --- 5. Predict ---
        prediction_raw = model.predict(features)[0]
        prediction_proba = model.predict_proba(features)[0][1] # Probability of class 1 (disease)

        result_text = "High Risk" if prediction_raw == 1 else "Low Risk"
        probability_percent = round(prediction_proba * 100, 2)

        # --- 6. Save to Database ---
        new_prediction = Prediction(
            result=result_text,
            probability=probability_percent,
            author=current_user,
            age=age,
            ap_hi=ap_hi,
            ap_lo=ap_lo,
            cholesterol=cholesterol,
            bmi=bmi,
            pulsepressure=pulsepressure
        )
        db.session.add(new_prediction)
        db.session.commit() 

        print(f'→ redirect to /loading/{new_prediction.id}')
        return redirect(url_for('loading', prediction_id=new_prediction.id))
        

    elif not model:
        flash('Prediction model is not loaded. Please contact the administrator.', 'danger')
        


       
    return render_template('predictor.html',title='Predictorpage', form=form,facts=CARDIO_FACTS)

@app.route("/loading/<int:prediction_id>")
@login_required
def loading(prediction_id):
    """
    Show the 8-second interstitial with rotating facts, then auto-redirect.
    """
    # Shuffle for variety (without mutating original constant)
    facts = random.sample(CARDIO_FACTS, k=len(CARDIO_FACTS))
    next_url = url_for("result", prediction_id=prediction_id)
    return render_template("loading.html", facts=facts, next_url=next_url)

    

@app.route('/result/<int:prediction_id>')
@login_required
def result(prediction_id):
    pred = Prediction.query.get_or_404(prediction_id)
    if pred.author != current_user:
        return redirect(url_for('index')) # Simple security

    # These are the feature importances from your script's output
    # (feature_importance_df)
    feature_importances = {
        'age': 0.281895,
        'ap_hi': 0.228966,
        'pulsepressure': 0.125678,
        'ap_lo': 0.126485,
        'bmi': 0.160136,
        'cholesterol': 0.076840
    }
    
    

    # Map cholesterol int back to string for display
    cholesterol_map = {1: 'Normal', 2: 'Above Normal', 3: 'Excessive'}
    pred.cholesterol_str = cholesterol_map.get(pred.cholesterol, 'Unknown')

    return render_template('result.html', title='Prediction Result', pred=pred, importances=feature_importances)


@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html', title='Lifestyle AI')


# --- Run the App ---
# Create database tables when the application starts
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
