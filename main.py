from email.policy import default
import gunicorn
from itsdangerous import URLSafeTimedSerializer, Serializer, URLSafeSerializer
from flask import Flask, render_template, url_for, request, redirect, flash, jsonify
from dotenv import load_dotenv
import os
from flask_mail import Mail, Message
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, URL, Email, ValidationError
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, func, Date
import random
from datetime import datetime, timedelta, date

load_dotenv()
app = Flask(__name__)
login_manager = LoginManager()
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
app.config["SECURITY_PASSWORD_SALT"]= os.environ.get("SECRET_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_TO_SEND =os.environ.get("EMAIL_USER")
MAIL_DEFAULT_SENDER = "noreply@flask.com"
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASSWORD")
Bootstrap5(app)
login_manager.init_app(app)
mail = Mail(app)

def generate_token(email):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=app.config["SECURITY_PASSWORD_SALT"])

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
    try:
        email = serializer.loads(
            token, salt=app.config["SECURITY_PASSWORD_SALT"], max_age=expiration
        )
        return email
    except Exception:
        return False

def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=MAIL_DEFAULT_SENDER,
    )
    mail.send(msg)
def check_is_confirmed(func):
    def decorated_function(*args, **kwargs):
        if current_user.is_confirmed is False:
            flash("Please confirm your account!", "warning")
            return redirect(url_for("accounts.inactive"))
        return func(*args, **kwargs)

    return decorated_function

class Base(DeclarativeBase):
    pass

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db= SQLAlchemy(model_class=Base)
db.init_app(app)
migrate = Migrate(app, db)

class Cards(db.Model):
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    dragon: Mapped[str] = mapped_column(String,nullable=False,unique=True)
    front_card_url: Mapped[str] = mapped_column(String,nullable=False)
    back_card_url: Mapped[str]= mapped_column(String,nullable=False)

class Dragons(db.Model):
    id: Mapped[int]= mapped_column(Integer,primary_key=True)
    name: Mapped[str] = mapped_column(String(100),unique=True)
    rarity: Mapped[str] = mapped_column(String(100))
    rarity_chance: Mapped[int] = mapped_column(Integer,)
    type: Mapped[str] = mapped_column(String(100))
    img: Mapped[str] =mapped_column(String(100),nullable=True)
    owned_by: Mapped[list["DragonsOwned"]] = relationship("DragonsOwned", back_populates="dragon_obj")

class User(db.Model,UserMixin):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(1000),unique=True)
    coins: Mapped[int] = mapped_column(Integer)
    last_login_reward = db.Column(Date)
    login_streak = db.Column(Integer, default=0)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)
    dragons: Mapped[list["DragonsOwned"]] = relationship("DragonsOwned", back_populates="user")


class DragonsOwned(db.Model):
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    dragon_id: Mapped[int] = mapped_column(ForeignKey("dragons.id"))
    bond_level: Mapped[int] = mapped_column(Integer, default=1)
    user: Mapped["User"] = relationship("User", back_populates="dragons")
    hunger: Mapped[int] = mapped_column(Integer,nullable=False, server_default="100")
    happiness: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    last_fed: Mapped[datetime] = mapped_column(DateTime,  nullable=True)
    last_played: Mapped[datetime] = mapped_column(DateTime,  nullable=True)
    sick: Mapped[str] = mapped_column(String(5), default="no")
    dragon_obj: Mapped["Dragons"] = relationship("Dragons", back_populates="owned_by")

class UserInventory(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    item_type: Mapped[str] = mapped_column(String(50))
    item_name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, default=1)

class Missions(db.Model):
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    dragon_id: Mapped[int] = mapped_column(ForeignKey("dragons.id"))
    dragon_on_mission: Mapped[str] = mapped_column(String(10),default="no")
    time_started: Mapped[datetime] = mapped_column(DateTime,  nullable=True)
    time_left: Mapped[float] = mapped_column(Float,nullable=True)
    region: Mapped[str] = mapped_column(String(50), nullable=True)

class PlantState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    planted_at = db.Column(db.DateTime)
    harvested = db.Column(db.Boolean, default=True)

class Shop(db.Model):
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    item: Mapped[str] = mapped_column(String(100), unique=True)
    item_price: Mapped[int] = mapped_column(Integer)

with app.app_context():
    db.create_all()

# with app.app_context():
#     new_item = Shop(item="egg",item_price=4000)
#     db.session.add(new_item)
#     db.session.commit()

with app.app_context():
    dragons = DragonsOwned.query.filter(
        (DragonsOwned.last_fed == None) | (DragonsOwned.last_played == None)).all()
    for dragon in dragons:
        if dragon.last_fed is None:
            dragon.last_fed = datetime.now()
        if dragon.last_played is None:
            dragon.last_played = datetime.now()
    db.session.commit()

with app.app_context():
    sick_dragons = DragonsOwned.query.filter(
        (DragonsOwned.sick == None)).all()
    for dragon in sick_dragons:
        if dragon.sick is None:
            dragon.sick = "no"
    db.session.commit()

class Register(FlaskForm):
    username = StringField("Username",validators=[DataRequired()])
    email = StringField("Email",validators=[DataRequired(),Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    submit = SubmitField('Sign up!')

class SignIn(FlaskForm):
    username = StringField('Username',validators=[DataRequired()])
    password = PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField('Login ♡')

def daily_login():
    today = date.today()
    user_id = current_user.id
    if current_user.last_login_reward:
        if current_user.last_login_reward != today:
            yesterday = today - timedelta(days=1)
            if current_user.last_login_reward == yesterday:
                current_user.login_streak += 1
                if current_user.login_streak == 7:
                    egg = UserInventory.query.filter_by(user_id=user_id, item_type='Egg').first()
                    if egg and egg.quantity > 0:
                        egg.quantity += 1
                    else:
                        new_egg = UserInventory(user_id=user_id, item_type="Egg", item_name="dragon egg", quantity=1)
                        db.session.add(new_egg)
                    current_user.login_streak = 0
            else:
                current_user.login_streak = 1
            current_user.last_login_reward = today
        elif current_user.last_login_reward == today:
            return "Gotten daily reward already"
    else:
        current_user.last_login_reward = today
        current_user.login_streak = 0

    current_user.coins += 10 + (current_user.login_streak * 10)
    db.session.commit()


def get_random_dragon():
    all_dragons = Dragons.query.all()
    if not all_dragons:
        return None
    weighted_dragons = []
    for dragon in all_dragons:
        weighted_dragons.extend([dragon] * dragon.rarity_chance)
    selected_dragon = random.choice(weighted_dragons)

    existing = DragonsOwned.query.filter_by(
        user_id=current_user.id,
        dragon_id=selected_dragon.id
    ).first()

    if existing:
        existing.bond_level += 1
    else:
        new_owned = DragonsOwned(
            user_id=current_user.id,
            dragon_id=selected_dragon.id,
            bond_level=1
        )
        db.session.add(new_owned)
    db.session.commit()
    return selected_dragon

def hatch_egg(user_id):
    egg = UserInventory.query.filter_by(user_id=user_id, item_type='Egg').first()
    if egg and egg.quantity > 0:
        egg.quantity -= 1
        if egg.quantity == 0:
            db.session.delete(egg)

        new_dragon = get_random_dragon()

        existing = DragonsOwned.query.filter_by(user_id=user_id, dragon_id=new_dragon.id).first()
        if existing:
            existing.bond_level += 1
        else:
            new_ownership = DragonsOwned(user_id=user_id, dragon_id=new_dragon.id, bond_level=1)
            db.session.add(new_ownership)

        db.session.commit()
        return new_dragon
    return None

def get_user_egg_count(user_id):
    egg = UserInventory.query.filter_by(
        user_id=user_id,
        item_type="Egg",
    ).first()
    return egg.quantity if egg else 0

def get_user_food_count(user_id):
    food = UserInventory.query.filter_by(user_id=user_id,item_type="food").first()
    return food.quantity if food else 0

def get_user_seed_count(user_id):
    seed = UserInventory.query.filter_by(user_id=user_id,item_type="seed").first()
    return seed.quantity if seed else 0

def get_user_toy_count(user_id):
    toy = UserInventory.query.filter_by(user_id=user_id,item_type="toy").first()
    return toy.quantity if toy else 0

def get_user_meds_count(user_id):
    meds = UserInventory.query.filter_by(user_id=user_id,item_type="medicine").first()
    return meds.quantity if meds else 0

def feed(user_id,dragon_id):
    food = UserInventory.query.filter_by(user_id=user_id, item_type='food').first()
    dragon = db.session.execute(db.select(DragonsOwned).where(DragonsOwned.dragon_id==dragon_id)).scalar()
    if food and food.quantity > 0:
        food.quantity -= 1
        dragon.hunger = min(100, dragon.hunger + 20)
        dragon.last_fed = datetime.now()
        if food.quantity == 0:
            db.session.delete(food)
        db.session.commit()
        db.session.refresh(dragon)
        return "yes"
    return None

def play(user_id,dragon_id):
    toy = UserInventory.query.filter_by(user_id=user_id, item_type='toy').first()
    dragon = db.session.execute(db.select(DragonsOwned).where(DragonsOwned.dragon_id==dragon_id)).scalar()
    if toy and toy.quantity > 0:
        toy.quantity -= 1
        dragon.happiness = min(100, dragon.happiness + 20)
        dragon.last_played = datetime.now()
        if toy.quantity == 0:
            db.session.delete(toy)
        db.session.commit()
        return "yes"
    return None

def sick(dragon_id):
    dragon = db.session.execute(db.select(DragonsOwned).where(DragonsOwned.dragon_id == dragon_id)).scalar()
    if dragon.hunger == 0:
        dragon.sick = "yes"
        db.session.commit()

def cure(user_id,dragon_id):
    meds = UserInventory.query.filter_by(user_id=user_id, item_type='medicine').first()
    dragon = db.session.execute(db.select(DragonsOwned).where(DragonsOwned.dragon_id==dragon_id)).scalar()
    if meds and meds.quantity > 0:
        meds.quantity -= 1
        dragon.sick = "no"
        if meds.quantity == 0:
            db.session.delete(meds)
        db.session.commit()
        return "yes"
    return None

def plant(user_id):
    seed = UserInventory.query.filter_by(user_id=user_id, item_type='seed').first()
    if seed and seed.quantity > 0:
        seed.quantity -= 1
        if seed.quantity == 0:
            db.session.delete(seed)
        db.session.commit()
        return "yes"
    return None

def update_dragon_hunger(dragon):
    now = datetime.now()
    print(f"Before update: hunger={dragon.hunger}, last_fed={dragon.last_fed}")
    if dragon.last_fed is None:
        dragon.last_fed = now
        db.session.commit()
    elapsed = (now - dragon.last_fed).total_seconds()
    decay_rate_per_hour = 5
    decay = int(elapsed / 3600 * decay_rate_per_hour)
    new_hunger = max(0, dragon.hunger - decay)
    print(f"Elapsed: {elapsed}s → decay: {decay}, new hunger: {new_hunger}")
    if new_hunger != dragon.hunger:
        dragon.hunger = new_hunger
        db.session.commit()
    return dragon.hunger

def update_dragon_happiness(dragon):
    now = datetime.now()
    if dragon.last_played is None:
        dragon.last_played = now
        db.session.commit()
    elapsed = (now - dragon.last_played).total_seconds()
    decay_rate_per_hour = 5
    decay = int(elapsed / 3600 * decay_rate_per_hour)
    new_happiness = max(0, dragon.happiness - decay)
    if new_happiness != dragon.happiness:
        dragon.happiness = new_happiness
        db.session.commit()
    return dragon.happiness

def buy_item(user_id,item_id):
    food = UserInventory.query.filter_by(user_id=user_id, item_type='food').first()
    toy = UserInventory.query.filter_by(user_id=user_id, item_type='toy').first()
    egg = UserInventory.query.filter_by(user_id=user_id, item_type='Egg').first()
    seed = UserInventory.query.filter_by(user_id=user_id, item_type='seed').first()
    meds = UserInventory.query.filter_by(user_id=user_id, item_type='medicine').first()
    item_to_buy = db.session.execute(db.select(Shop).where(Shop.id == item_id)).scalar()
    if item_to_buy.item == "food":
        if food and food.quantity > 0:
            food.quantity += 1
        else:
            new_food = UserInventory(user_id=user_id, item_type="food",item_name="food",quantity=1)
            db.session.add(new_food)
    if item_to_buy.item == "meds":
        if meds and meds.quantity > 0:
            meds.quantity += 1
        else:
            new_meds = UserInventory(user_id=user_id, item_type="medicine",item_name="medicine",quantity=1)
            db.session.add(new_meds)
    if item_to_buy.item == "toy":
        if toy and toy.quantity > 0:
            toy.quantity += 1
        else:
            new_toy = UserInventory(user_id=user_id, item_type="toy",item_name="toy",quantity=1)
            db.session.add(new_toy)
    if item_to_buy.item == "egg":
        if egg and egg.quantity > 0:
            egg.quantity += 1
        else:
            new_egg = UserInventory(user_id=user_id, item_type="Egg",item_name="dragon egg",quantity=1)
            db.session.add(new_egg)
    if item_to_buy.item == "seed":
        if seed and seed.quantity > 0:
            seed.quantity += 1
        else:
            new_seed = UserInventory(user_id=user_id, item_type="seed",item_name="seed",quantity=1)
            db.session.add(new_seed)
    db.session.commit()

def sell_item(user_id,item_id):
    food = UserInventory.query.filter_by(user_id=user_id, item_type='food').first()
    toy = UserInventory.query.filter_by(user_id=user_id, item_type='toy').first()
    egg = UserInventory.query.filter_by(user_id=user_id, item_type='Egg').first()
    seed = UserInventory.query.filter_by(user_id=user_id, item_type='seed').first()
    meds = UserInventory.query.filter_by(user_id=user_id, item_type='medicine').first()
    item_to_sell = db.session.execute(db.select(Shop).where(Shop.id == item_id)).scalar()
    if item_to_sell.item == "food":
        if food and food.quantity > 0:
            food.quantity -= 1
            if food.quantity == 0:
                db.session.delete(food)
    if item_to_sell.item == "meds":
        if meds and meds.quantity > 0:
            meds.quantity -= 1
            if meds.quantity == 0:
                db.session.delete(meds)
    if item_to_sell.item == "toy":
        if toy and toy.quantity > 0:
            toy.quantity -= 1
            if toy.quantity == 0:
                db.session.delete(toy)
    if item_to_sell.item == "egg":
        if egg and egg.quantity > 0:
            egg.quantity -= 1
            if egg.quantity == 0:
                db.session.delete(egg)
    if item_to_sell.item == "seed":
        if seed and seed.quantity > 0:
            seed.quantity -= 1
            if seed.quantity == 0:
                db.session.delete(seed)
    db.session.commit()

def get_reward(user_id,level):
    user = db.session.execute(db.select(UserInventory).where(UserInventory.user_id == user_id)).scalar()
    food = UserInventory.query.filter_by(user_id=user_id, item_type='food').first()
    toy = UserInventory.query.filter_by(user_id=user_id, item_type='toy').first()
    egg = UserInventory.query.filter_by(user_id=user_id, item_type='Egg').first()
    reward = {}
    if level == "quick":
        chosen_number = random.randint(1, 2)
        add_food = chosen_number
        if food:
            food.quantity += add_food
        else:
            new_food = UserInventory(user_id=user_id, item_type="food",item_name="food",quantity=add_food)
            db.session.add(new_food)
        add_toy = 2 - chosen_number
        if toy:
            toy.quantity += add_toy
        else:
            new_toy = UserInventory(user_id=user_id, item_type="toy",item_name="toy",quantity=add_toy)
            db.session.add(new_toy)
        reward["food"] = add_food
        reward["toy"] = add_toy
    elif level == "medium":
        if random.random() < 0.2:
            if egg:
                egg.quantity += 1
            else:
                new_egg = UserInventory(user_id=user_id, item_type="Egg", item_name="dragon egg", quantity=1)
                db.session.add(new_egg)
            reward["egg"] = 1
        else:
            chosen_number = random.randint(1, 5)
            add_food = chosen_number
            if food and food.quantity > 0:
                food.quantity += add_food
            else:
                new_food = UserInventory(user_id=user_id, item_type="food", item_name="food", quantity=add_food)
                db.session.add(new_food)
            add_toy = 5 - chosen_number
            if toy:
                toy.quantity += add_toy
            else:
                new_toy = UserInventory(user_id=user_id, item_type="toy", item_name="toy", quantity=add_toy)
                db.session.add(new_toy)
            reward["food"] = add_food
            reward["toy"] = add_toy
    elif level == "long":
        if random.random() < 0.45:
            if egg and egg.quantity > 0:
                egg.quantity += 1
            else:
                new_egg = UserInventory(user_id=user_id, item_type="Egg", item_name="dragon egg", quantity=1)
                db.session.add(new_egg)
            reward["egg"] = 1
        else:
            chosen_number = random.randint(1, 8)
            add_food = chosen_number
            if food:
                food.quantity += add_food
            else:
                new_food = UserInventory(user_id=user_id, item_type="food", item_name="food", quantity=add_food)
                db.session.add(new_food)
            add_toy = 8 - chosen_number
            if toy:
                toy.quantity += add_toy
            else:
                new_toy = UserInventory(user_id=user_id, item_type="toy", item_name="toy", quantity=add_toy)
                db.session.add(new_toy)
            reward["food"] = add_food
            reward["toy"] = add_toy
    db.session.commit()
    return reward

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

@app.route("/support")
def support():
    return render_template('donation.html')

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/map")
def world_map():
    return render_template('map.html')

@app.route("/dragons")
def dragons():
    with app.app_context():
        all_dragons = db.session.execute(db.select(Cards).order_by(Cards.id)).scalars().all()
    return render_template('dragons.html',dragons=all_dragons)

@app.route("/login",methods=["GET","POST"])
def login():
    sign_in = SignIn()
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        result = db.session.execute(db.select(User).where(User.username == username))
        user = result.scalar()
        if not user:
            flash("Invalid credentials •︵• please try again!")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password,password):
            flash("Invalid credentials •︵• please try again!")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('user_home'))
    return render_template('sign-in.html',sign_in=sign_in)

@app.route("/inactive")
@login_required
def inactive():
    if current_user.is_confirmed:
        return redirect(url_for("user_home"))
    return render_template("accounts/inactive.html")

@app.route("/resend")
@login_required
def resend_confirmation():
    if current_user.is_confirmed:
        flash("Your account has already been confirmed.", "success")
        return redirect(url_for("user_home"))
    token = generate_token(current_user.email)
    confirm_url = url_for("confirm_email", token=token, _external=True)
    html = render_template("accounts/confirm_email.html", confirm_url=confirm_url)
    subject = "Please confirm your email"
    send_email(current_user.email, subject, html)
    flash("A new confirmation email has been sent.", "success")
    return redirect(url_for("inactive"))

@app.route("/register",methods=["GET","POST"])
def register():
    sign_up = Register()
    if sign_up.validate_on_submit():
        username = sign_up.username.data
        email = sign_up.email.data
        password = sign_up.password.data
        username_exists = db.session.execute(db.select(User).where(User.username == username)).scalar()
        email_exists = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if email_exists:
            flash("You've already begun your adventure with that email! Please log in.")
            return redirect(url_for('login'))
        elif username_exists:
            flash("˙◠˙ Username taken! ˙◠˙")
            return redirect(url_for('register'))

        hash_salted_password = generate_password_hash(password,method='pbkdf2:sha256',salt_length=8)
        new_user = User(username=username,email=email,password=hash_salted_password,coins=100)
        db.session.add(new_user)
        db.session.commit()

        token = generate_token(new_user.email)
        confirm_url = url_for("confirm_email", token=token, _external=True)
        html = render_template("accounts/confirm_email.html", confirm_url=confirm_url)
        subject = "Please confirm your email"
        send_email(new_user.email, subject, html)
        flash("A confirmation email has been sent via email.", "success")
        starting_egg = UserInventory(user_id=new_user.id, item_type="Egg", item_name="Dragon Egg", quantity=1)
        db.session.add(starting_egg)
        db.session.commit()
        login_user(new_user)
        return render_template('user-home.html',username=username,token=token)
    return render_template('register.html',sign_up=sign_up)

@app.route("/confirm/<token>")
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash("The confirmation link is invalid or has expired.", "danger")
        return redirect(url_for("inactive"))

    user = User.query.filter_by(email=email).first_or_404()

    if user.is_confirmed:
        flash("Account already confirmed. Please log in.", "info")
        return redirect(url_for("login"))

    user.is_confirmed = True
    user.confirmed_on = datetime.now()
    user.coins += 100
    db.session.commit()
    flash("You have confirmed your account. Thanks! You earned 100 coins!", "success")
    return redirect(url_for("login"))

@app.route("/yourhome")
@login_required
def user_home():
    token = None
    if not current_user.is_confirmed:
        token = generate_token(current_user.email)
        confirm_url = url_for("confirm_email", token=token, _external=True)
        html = render_template("accounts/confirm_email.html", confirm_url=confirm_url)
        subject = "Please confirm your email"
        send_email(current_user.email, subject, html)
        flash("A confirmation email has been sent.", "success")
    user_id = current_user.id
    daily_login()
    user = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
    return render_template("user-home.html", user =user, token=token)

@app.route("/missions",methods=["POST","GET"])
@login_required
def missions():
    user_id = current_user.id
    busy_dragon_ids = db.session.execute(
        db.select(Missions.dragon_id)
        .where(Missions.user_id == current_user.id)
        .where(Missions.dragon_on_mission == "yes")
    ).scalars().all()
    sick_dragon_ids = db.session.execute(
        db.select(DragonsOwned.dragon_id)
        .where(DragonsOwned.user_id == current_user.id)
        .where(DragonsOwned.sick == "yes")
    ).scalars().all()
    sick_dragons = db.session.execute(
        db.select(Dragons)
        .select_from(DragonsOwned)
        .where(DragonsOwned.user_id == user_id)
        .where(DragonsOwned.dragon_id.in_(sick_dragon_ids)).join(Dragons)).scalars().all()

    users_dragons_free = (db.session.execute(
        db.select(DragonsOwned)
        .where(DragonsOwned.user_id == user_id)
        .where(DragonsOwned.dragon_id.notin_(busy_dragon_ids)))).scalars().all()

    dragons_names = db.session.execute(
        db.select(Dragons)
        .select_from(DragonsOwned)
        .where(DragonsOwned.user_id == user_id)
        .where(DragonsOwned.dragon_id.notin_(busy_dragon_ids))
        .where(DragonsOwned.dragon_id.notin_(sick_dragon_ids))
        .join(Dragons)).scalars().all()

    free_dragons_json = []
    for drag in dragons_names:
        name = {
            'name': drag.name,
            'id':drag.id,
        }
        free_dragons_json.append(name)

    busy_dragons = db.session.execute(
        db.select(Dragons)
        .select_from(DragonsOwned)
        .where(DragonsOwned.user_id == user_id)
        .where(DragonsOwned.dragon_id.in_(busy_dragon_ids)).join(Dragons)).scalars().all()

    if request.method == "POST":
        region = request.form.get("region")
        dragon_sent_id = int(request.form.get("dragon_id"))

        dragon_sent = db.session.execute(
            db.select(Missions).where(
                Missions.user_id == user_id,
                Missions.dragon_id == dragon_sent_id
            )
        ).scalar()

        if not dragon_sent:
            dragon_sent = Missions(
                user_id=user_id,
                dragon_id=dragon_sent_id,
                dragon_on_mission="yes",
                time_started=datetime.now(),
                region=region,
            )
            db.session.add(dragon_sent)
        else:
            dragon_sent.dragon_on_mission = "yes"
            dragon_sent.time_started = datetime.now()
            dragon_sent.region = region

        db.session.commit()
        return redirect(url_for('missions'))

    return render_template('missions.html',user_dragons=free_dragons_json,
                           busy_dragons=busy_dragons,sick_dragons=sick_dragons)

@app.route("/claim_reward", methods=["POST","GET"])
@login_required
def claim_reward():
    reward = None
    dragons_back = None
    dragons_still_busy = None
    user_id = current_user.id
    dragons_busy = db.session.execute(
        db.select(Missions)
        .where(Missions.user_id == current_user.id)
        .where(Missions.dragon_on_mission == "yes")
    ).scalars().all()
    print(f"dragons on mission: {dragons_busy}")
    reward = []
    dragons_back = []
    dragons_still_busy = []
    for mission in dragons_busy:
        if mission.region == "farm" or mission.region == "mushroom-forest":
            now = datetime.now()
            time_elapsed = (now - mission.time_started).total_seconds()
            if time_elapsed > 2000:
                mission.dragon_on_mission = "no"
                dragon_back = db.session.execute(
                    db.select(Dragons).where(Dragons.id == mission.dragon_id)
                ).scalar()
                new_reward = get_reward(user_id, "quick")
                db.session.commit()
                dragons_back.append(dragon_back)
                reward.append(new_reward)
        elif mission.region == "pond" or mission.region == "sleeping-forest":
            now = datetime.now()
            time_elapsed = (now - mission.time_started).total_seconds()
            if time_elapsed > 3600:
                mission.dragon_on_mission = "no"
                dragon_back = db.session.execute(
                    db.select(Dragons).where(Dragons.id == mission.dragon_id)
                ).scalar()
                new_reward = get_reward(user_id, "medium")
                db.session.commit()
                dragons_back.append(dragon_back)
                reward.append(new_reward)
        elif mission.region == "wishing-well" or mission.region == "crystal-peaks":
            now = datetime.now()
            time_elapsed = (now - mission.time_started).total_seconds()
            if time_elapsed > 7200:
                mission.dragon_on_mission = "no"
                dragon_back = db.session.execute(
                    db.select(Dragons).where(Dragons.id == mission.dragon_id)
                ).scalar()
                new_reward = get_reward(user_id, "long")
                db.session.commit()
                dragons_back.append(dragon_back)
                reward.append(new_reward)
        elif mission.region == "open-field":
            now = datetime.now()
            time_elapsed = (now - mission.time_started).total_seconds()
            if time_elapsed > 3600:
                mission.dragon_on_mission = "no"
                dragon_back = db.session.execute(
                    db.select(Dragons).where(Dragons.id == mission.dragon_id)
                ).scalar()
                new_happy = 100
                new_hunger = 100
                dragon_to_update = db.session.execute(
                    db.select(DragonsOwned).where(DragonsOwned.dragon_id == mission.dragon_id)).scalar()
                dragon_to_update.hunger = new_hunger
                dragon_to_update.happiness = new_happy
                new_reward = None
                db.session.commit()
                dragons_back.append(dragon_back)
                reward.append(new_reward)
    for mission in dragons_busy:
        now = datetime.now()
        time_elapsed = (now - mission.time_started).total_seconds()
        required_time = 0
        if mission.region in ["farm", "mushroom-forest"]:
            required_time = 2000
        elif mission.region in ["pond", "sleeping-forest","open-field"]:
            required_time = 3600
        elif mission.region in ["wishing-well", "crystal-peaks"]:
            required_time = 7200

        time_left = max(0, int(required_time - time_elapsed))

        if time_left > 0:
            dragon = db.session.execute(
                db.select(Dragons).where(Dragons.id == mission.dragon_id)
            ).scalar()
            dragons_still_busy.append({
                "name": dragon.name,
                "time_left": time_left,
            })
    return render_template('claim-reward.html',rewards=reward,dragon_back=dragons_back,
                           dragons_busy=dragons_still_busy)


@app.route("/mydragons")
@login_required
def user_dragons():
    user_id = current_user.id
    owned_dragons = db.session.execute(
        db.select(DragonsOwned).where(DragonsOwned.user_id == user_id)
    ).scalars().all()
    dragon_names = [d.dragon_obj.name for d in owned_dragons if d.dragon_obj]
    if dragon_names:
        return render_template("user-dragons.html", dragons=dragon_names)
    else:
        flash("You don't have any dragons yet, hatch your egg!", "warning")
        return render_template("user-dragons.html", dragons=None)

@app.route("/inventory")
@login_required
def inventory():
    user_id = current_user.id
    users_food_count = get_user_food_count(user_id)
    users_toy_count = get_user_toy_count(user_id)
    users_seed_count = get_user_seed_count(user_id)
    users_egg_count = get_user_egg_count(user_id)
    users_meds_count = get_user_meds_count(user_id)
    user = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
    coins = user.coins
    return render_template('inventory.html', eggs=users_egg_count,food=users_food_count,
                           toy=users_toy_count,seed=users_seed_count,coins=coins,meds=users_meds_count)

@app.route("/inventory/eggs",methods =["GET","POST"])
@login_required
def inventory_eggs():
    user_id = current_user.id
    num_eggs = get_user_egg_count(user_id)
    if request.method == "POST":
        dragon = hatch_egg(user_id)
        if dragon:
            flash(f"You hatched a {dragon.rarity} dragon: {dragon.name}!", "success")
            new_dragon = Missions(user_id=user_id,dragon_id=dragon.id,dragon_on_mission="no")
            db.session.add(new_dragon)
            db.session.commit()
            return render_template('eggs_owned.html', eggs=num_eggs, dragon=dragon)
        else:
            flash("You don't have any eggs to hatch!", "warning")
    num_eggs = get_user_egg_count(user_id)
    return render_template('eggs_owned.html',eggs=num_eggs,dragon=None)

@app.route("/carefor",methods=["GET","POST"])
@login_required
def care_for():
    if request.method == "POST":
        action = request.form.get("action")
        which_dragon = request.form.get("dragon")
        caring_for = db.session.execute(db.select(Dragons).where(Dragons.name == which_dragon)).scalar()
        dragon_owned = db.session.execute(db.select(DragonsOwned).where
                                          (DragonsOwned.dragon_id == caring_for.id)).scalar()
        lower_drag_name = caring_for.name.lower()
        sick_dragon = db.session.execute(
            db.select(DragonsOwned)
            .where(DragonsOwned.user_id == current_user.id)
            .where(DragonsOwned.sick == "yes")
            .where(DragonsOwned.dragon_id == caring_for.id)
        ).scalar()
        print(f"DRAGON SICK STATUS:, {sick_dragon} : {sick_dragon.sick}")
        if action == "feed":
            food = feed(user_id=current_user.id,dragon_id= dragon_owned.dragon_id)
            if food:
                flash(f"{caring_for.name} loved that!")
                db.session.refresh(dragon_owned)
                return render_template('care-for.html',care=dragon_owned,
                                       dragon=caring_for,show_script = True,action_done="feed",name=lower_drag_name)
            else:
                flash("You have no food!")
        if action == "play":
            toy = play(user_id=current_user.id,dragon_id= dragon_owned.dragon_id)
            if toy:
                flash(f"{caring_for.name} had so much fun!")
                db.session.refresh(dragon_owned)
                return render_template('care-for.html',care=dragon_owned,
                                       dragon=caring_for,show_script = True, action_done="play",name=lower_drag_name)
            else:
                flash("You need a toy!")
        if action == "medicine":
            meds = cure(user_id=current_user.id,dragon_id=dragon_owned.dragon_id)
            if meds:
                flash(f"{caring_for.name} feels much better!")
                db.session.refresh(dragon_owned)
                return render_template('care-for.html',care=dragon_owned,
                                       dragon=caring_for,show_script = True,action_done="medicine",name=lower_drag_name)
            else:
                flash("You have no medicine!")
        db.session.refresh(dragon_owned)
        print(f"DRAGON SICK STATUS:, {sick_dragon} : {sick_dragon.sick}")
        return render_template('care-for.html', care=dragon_owned,
                               dragon=caring_for, show_script=True,
                               action_done=action, name=lower_drag_name,sick = sick_dragon)
    who = request.args.get("dragon")
    dragon_info = db.session.execute(
        db.select(Dragons).where(func.lower(Dragons.name) == who.lower())
    ).scalar()
    dragon_owned = db.session.execute(db.select(DragonsOwned).where
                                      (DragonsOwned.dragon_id == dragon_info.id)).scalar()
    update_dragon_hunger(dragon_owned)
    update_dragon_happiness(dragon_owned)
    sick(dragon_owned.dragon_id)
    db.session.refresh(dragon_owned)
    print(f"DRAGON SICK STATUS:, {dragon_owned.sick}")
    return render_template('care-for.html',care=dragon_owned,
                           dragon=dragon_info, show_script=True,name=who)

@app.route("/store",methods=["GET","POST"])
@login_required
def store():
    user_id = current_user.id
    user = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
    user_coins = user.coins
    items = db.session.execute(db.select(Shop)).scalars().all()
    users_food_count = get_user_food_count(user_id)
    users_toy_count = get_user_toy_count(user_id)
    users_seed_count = get_user_seed_count(user_id)
    users_egg_count = get_user_egg_count(user_id)
    users_meds_count = get_user_meds_count(user_id)
    if request.method == "POST":
        item_id = int(request.form.get("item_id"))
        action = request.form.get("action")
        item = db.session.execute(db.select(Shop).where(Shop.id == item_id)).scalar()
        if action == "buy":
            if user_coins > item.item_price:
                user_coins -= item.item_price
                user_coins_update = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
                user_coins_update.coins = user_coins
                db.session.commit()
                buy_item(user_id, item_id)
            else:
                flash("You don't have enough coins!")
        if action == "sell":
            if item.item == "food":
                if users_food_count > 0:
                    sell_item(user_id, item_id)
                    user_coins_update = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
                    user_coins_update.coins = user_coins
                    db.session.commit()
                    user_coins += item.item_price
                else:
                    flash("You don't have any food!")
            elif item.item == "toy":
                if users_toy_count > 0:
                    sell_item(user_id, item_id)
                    user_coins += item.item_price
                    user_coins_update = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
                    user_coins_update.coins = user_coins
                    db.session.commit()
                else:
                    flash("You don't have any toys!")
            elif item.item == "seed":
                if users_seed_count > 0:
                    sell_item(user_id, item_id)
                    user_coins += item.item_price
                    user_coins_update = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
                    user_coins_update.coins = user_coins
                    db.session.commit()
                else:
                    flash("You don't have any seeds!")
            elif item.item == "egg":
                if users_egg_count > 0:
                    sell_item(user_id, item_id)
                    user_coins += item.item_price
                    user_coins_update = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
                    user_coins_update.coins = user_coins
                    db.session.commit()
                else:
                    flash("You don't have any eggs!")
            elif item.item == "medicine":
                if users_meds_count > 0:
                    sell_item(user_id, item_id)
                    user_coins += item.item_price
                    user_coins_update = db.session.execute(db.select(User).where(User.id == user_id)).scalar()
                    user_coins_update.coins = user_coins
                    db.session.commit()
                else:
                    flash("You don't have any eggs!")
        db.session.commit()
        return redirect(url_for('store'))
    return render_template('store.html',items=items,user_coins=user_coins)


@app.route("/farm",methods=["GET","POST"])
@login_required
def farm():
    now = datetime.now()
    state = db.session.execute(
        db.select(PlantState).where(PlantState.user_id == current_user.id)
    ).scalar()
    if not state:
        state = PlantState(user_id=current_user.id, harvested=True)
        db.session.add(state)
        db.session.commit()
    time_left = None
    time_since_planted = 0
    if state.planted_at:
        time_since_planted = (now - state.planted_at).total_seconds()
        time_left = max(0, 18000 - time_since_planted)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "Plant" and state.harvested:
            if plant(user_id=current_user.id):
                state.planted_at = now
                state.harvested = False
                db.session.commit()
            else:
                flash("You don't have any seeds!")

        elif action == "Harvest" and not state.harvested:
            time_since_planted = (now - state.planted_at).total_seconds()
            if time_since_planted >= 18000:
                state.harvested = True
                state.planted_at = None
                new_item = UserInventory(
                    user_id=current_user.id,
                    item_type="food",
                    item_name="food",
                    quantity=3
                )
                db.session.add(new_item)
                db.session.commit()
    if state.planted_at and not state.harvested:
        time_since_planted = (datetime.now() - state.planted_at).total_seconds()
        if time_since_planted >= 30:
            button_text = "Harvest"
            time_left = 0
        else:
            button_text = None
            time_left = 18000 - time_since_planted
    else:
        button_text = "Plant"
        time_left = None
    return render_template("farm.html", button_text=button_text, timer=time_left)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
