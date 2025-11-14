 *~Heart Disease Prediction System~* 

A web application built with Flask and Scikit-learn that predicts a user's risk of cardiovascular disease based on key health metrics. The app also provides personalized lifestyle insights based on the prediction.




 *~  FEATURES: ~*
 User Authentication:
  Secure user registration and login system (Flask-Login).

 ML Prediction:
 Uses a RandomForestClassifier model trained on the "Cardiovascular Disease dataset" to predict risk.

 Data-Driven Insights:
 Provides users with personalized, actionable lifestyle recommendations based on their inputs (e.g., high BMI, high blood pressure).

 Clean & Simple UI:
HTML, CSS, and Jinja2 templates for a smooth user experience.

Database Integration
SQLite database with Flask-Migrate for smooth migrations.






 Tech Stack:

Backend: Python, Flask, Flask-SQLAlchemy
Frontend:HTML, CSS, Jinja2
Machine Learning: Scikit-learn, Pandas, NumPy
Database: SQLite (via Flask-Migrate)
Model Storage:Joblib





INSTALLATION AND SETUP GUIDE(windows):
1. Clone repo:
git clone https://github.com/tameszn/Heart-disease-prediction-.git
cd Heart-disease-prediction

2. Create a virtual environment
python -m venv venv
venv\Scripts\activate

3. Installing dependencies
pip install -r requirements.txt

4. Setting up Database 
run the following commands:
  flask db init
  flask db migrate 
  flask db upgrade
  
5. Run
command:flask run
application starts at:
http://127.0.0.1:5000/
