import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug_security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

login_manager = LoginManager
login_manager.init.app(app)
login_manager.login_view = "login"

app.config['SQLALCHEMYURI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.column(db.Integer, primary_key = True)
    username = db.column(db.String(80), Unique = True, nullable = False)
    password = db.column(generate_password_hash (db.String(80)),Unique = True, nullable = False)

class User(UserMixin):
    def __init__ (self,id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id in users else None

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods = ['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get['username']
        password = request.form.get['password']
        user_data = users.get(username)
        if user_data and check_password_hash(user_data['password'], password):
            user_obj = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
        return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return f'Welcome, {username}'
    return render_template('dashboard.html')

@app.route('logout')
def logout():
    logout_user()
    return redirect (url_for('landing.html'))

if __name__ == '__main__':
    app.run(debug = True, port = 8000)
