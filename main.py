from email.policy import default
from flask import Flask, render_template, url_for, request, redirect, flash
from dotenv import load_dotenv
import os
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, URL, Email, ValidationError
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime
import random
from datetime import datetime,timedelta

app = Flask(__name__)
login_manager = LoginManager()
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
Bootstrap5(app)
login_manager.init_app(app)

class Base(DeclarativeBase):
    pass

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
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

class PlantState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    planted_at = db.Column(db.DateTime)
    harvested = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()

# with app.app_context():
#     new_item = UserInventory(user_id=1,item_type="seed",item_name="seed",quantity=3)
#     db.session.add(new_item)
#     db.session.commit()

with app.app_context():
    dragons = DragonsOwned.query.filter(
        (DragonsOwned.last_fed == None) | (DragonsOwned.last_played == None)).all()
    for dragon in dragons:
        if dragon.last_fed is None:
            dragon.last_fed = datetime.utcnow()
        if dragon.last_played is None:
            dragon.last_played = datetime.utcnow()
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

def get_user_toy_count(user_id):
    toy = UserInventory.query.filter_by(user_id=user_id,item_type="toy").first()
    return toy.quantity if toy else 0

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
        return "yes"
    return None

def play(user_id,dragon_id):
    toy = UserInventory.query.filter_by(user_id=user_id, item_type='toy').first()
    dragon = db.session.execute(db.select(DragonsOwned).where(DragonsOwned.dragon_id==dragon_id)).scalar()
    if toy and toy.quantity > 0:
        toy.quantity -= 1
        dragon.happiness = min(100, dragon.happiness + 20)
        dragon.last_play = datetime.now()
        if toy.quantity == 0:
            db.session.delete(toy)
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
    elapsed = (now - dragon.last_fed).total_seconds()
    decay_rate_per_hour = 5
    decay = int(elapsed / 3600 * decay_rate_per_hour)
    new_hunger = max(0, dragon.hunger - decay)
    if new_hunger != dragon.hunger:
        dragon.hunger = new_hunger
        db.session.commit()
    return dragon.hunger

def update_dragon_happiness(dragon):
    now = datetime.now()
    elapsed = (now - dragon.last_played).total_seconds()
    decay_rate_per_hour = 5
    decay = int(elapsed / 3600 * decay_rate_per_hour)
    new_happiness = max(0, dragon.happiness - decay)
    if new_happiness != dragon.happiness:
        dragon.happiness = new_happiness
        db.session.commit()
    return dragon.happiness

def get_reward(user_id,level):
    user = db.session.execute(db.select(UserInventory).where(UserInventory.user_id == user_id)).scalar()
    food = UserInventory.query.filter_by(user_id=user_id, item_type='food').first()
    toy = UserInventory.query.filter_by(user_id=user_id, item_type='toy').first()
    egg = UserInventory.query.filter_by(user_id=user_id, item_type='Egg').first()
    if level == "quick":
        chosen_number = random.randint(1, 2)
        add_food = chosen_number
        if food and food.quantity > 0:
            food.quantity += add_food
        else:
            new_food = UserInventory(user_id=user_id, item_type="food",item_name="food",quantity=add_food)
            db.session.add(new_food)
        add_toy = 2 - chosen_number
        if toy and toy.quantity > 0:
            toy.quantity += add_toy
        else:
            new_toy = UserInventory(user_id=user_id, item_type="toy",item_name="toy",quantity=add_toy)
            db.session.add(new_toy)
    elif level == "medium":
        if random.random() < 0.2:
            if egg and egg.quanity > 0:
                egg.quanity += 1
            else:
                new_egg = UserInventory(user_id=user_id, item_type="Egg", item_name="dragon egg", quantity=1)
                db.session.add(new_egg)
        else:
            chosen_number = random.randint(1, 5)
            add_food = chosen_number
            if food and food.quantity > 0:
                food.quantity += add_food
            else:
                new_food = UserInventory(user_id=user_id, item_type="food", item_name="food", quantity=add_food)
                db.session.add(new_food)
            add_toy = 5 - chosen_number
            if toy and toy.quantity > 0:
                toy.quantity += add_toy
            else:
                new_toy = UserInventory(user_id=user_id, item_type="toy", item_name="toy", quantity=add_toy)
                db.session.add(new_toy)
    elif level == "long":
        if random.random() < 0.45:
            if egg and egg.quanity > 0:
                egg.quanity += 1
            else:
                new_egg = UserInventory(user_id=user_id, item_type="Egg", item_name="dragon egg", quantity=1)
                db.session.add(new_egg)
        else:
            chosen_number = random.randint(1, 8)
            add_food = chosen_number
            if food and food.quantity > 0:
                food.quantity += add_food
            else:
                new_food = UserInventory(user_id=user_id, item_type="food", item_name="food", quantity=add_food)
                db.session.add(new_food)
            add_toy = 8 - chosen_number
            if toy and toy.quantity > 0:
                toy.quantity += add_toy
            else:
                new_toy = UserInventory(user_id=user_id, item_type="toy", item_name="toy", quantity=add_toy)
                db.session.add(new_toy)
        db.session.commit()

def send_dragon(user_id,dragon_id):
    pass

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

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
        starting_egg = UserInventory(user_id=new_user.id, item_type="Egg", item_name="Dragon Egg", quantity=1)
        db.session.add(starting_egg)
        db.session.commit()
        login_user(new_user)
        return render_template('user-home.html',username=username)
    return render_template('register.html',sign_up=sign_up)

@app.route("/yourhome")
@login_required
def user_home():
    return render_template("user-home.html")

@app.route("/missions",methods=["POST","GET"])
@login_required
def missions():
    user_id = current_user.id
    busy_dragon_ids = db.session.execute(
        db.select(Missions.dragon_id)
        .where(Missions.user_id == current_user.id)
        .where(Missions.dragon_on_mission == "yes")
    ).scalars().all()
    available_dragons = db.session.execute(
        db.select(DragonsOwned)
        .where(DragonsOwned.user_id == current_user.id)
        .where(DragonsOwned.id.notin_(busy_dragon_ids))
        .join(Dragons)
    ).scalars().all()
    user_dragons = [{"id": d.id, "name": d.dragon_obj.name} for d in available_dragons]

    region = request.form.get("region")
    print(region)
    dragon_sent_id = request.form.get("dragon_id")
    print(dragon_sent_id)
    if region == "farm" or region == "mushroom-forest":
        pass

    return render_template('missions.html',user_dragons=user_dragons)

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
    return render_template('inventory.html')

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
        dragon_owned = db.session.execute(db.select(DragonsOwned).where(DragonsOwned.dragon_id == caring_for .id)).scalar()
        if action == "feed":
            food = feed(user_id=current_user.id,dragon_id= dragon_owned.dragon_id)
            if food:
                flash(f"{caring_for .name} loved that!")
                update_dragon_hunger(dragon_owned)
                return render_template('care-for.html',care=dragon_owned, dragon=caring_for,show_script = True,action_done="feed")
            else:
                flash("You have no food!")
        if action == "play":
            toy = play(user_id=current_user.id,dragon_id= dragon_owned.dragon_id)
            if toy:
                flash(f"{caring_for .name} had so much fun!")
                update_dragon_happiness(dragon_owned)
                return render_template('care-for.html',care=dragon_owned, dragon=caring_for,show_script = True, action_done="play")
            else:
                flash("You need a toy!")
        return render_template('care-for.html',care=dragon_owned, dragon=caring_for,show_script=True)
    who = request.args.get("dragon")
    dragon_info = db.session.execute(db.select(Dragons).where(Dragons.name == who)).scalar()
    dragon_owned = db.session.execute(db.select(DragonsOwned).where(DragonsOwned.dragon_id == dragon_info.id)).scalar()
    update_dragon_hunger(dragon_owned)
    update_dragon_happiness(dragon_owned)
    return render_template('care-for.html',care=dragon_owned, dragon=dragon_info, show_script=True)

@app.route("/farm",methods=["GET","POST"])
@login_required
def farm():
    now = datetime.utcnow()
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
        time_left = max(0, 30 - time_since_planted)
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
            if time_since_planted >= 30:
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
        time_since_planted = (datetime.utcnow() - state.planted_at).total_seconds()
        if time_since_planted >= 30:
            button_text = "Harvest"
            time_left = 0
        else:
            button_text = None
            time_left = 30 - time_since_planted
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
