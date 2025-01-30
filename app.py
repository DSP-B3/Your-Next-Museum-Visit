import csv
import random
import os

from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap

from recommenders import RecSystem
from data import User


app = Flask(__name__)
rs = RecSystem()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/id/<key>")
def get_user_info(key: str):
    usr = User(key)
    return render_template("user.html", user=usr)


@app.route("/recommendations")
def recommendations():
    return render_template(
        "recommendations.html",
        perfect_matches=[],
        hidden_gems=[],
        local_spots=[],
        visited=None,
        user=None,
    )


@app.route("/recommendations/<key>")
def recommendations_id(key: str):
    usr = User(key)
    perfect_matches = rs.perfect_matches(usr)
    hidden_gems = rs.hidden_gems(usr)
    local_spots = rs.local_spots(usr)
    return render_template(
        "recommendations.html",
        perfect_matches=perfect_matches,
        hidden_gems=hidden_gems,
        local_spots=local_spots,
        visited=usr.previous_visits,
        user=usr,
    )


@app.route("/recommendations/login", methods=["GET"])
def recommendations_id_login():
    key = request.args.get("key")
    usr = User(key)
    perfect_matches = rs.perfect_matches(usr)
    hidden_gems = rs.hidden_gems(usr)
    local_spots = rs.local_spots(usr)
    return render_template(
        "recommendations.html",
        perfect_matches=perfect_matches,
        hidden_gems=hidden_gems,
        local_spots=local_spots,
        visited=usr.previous_visits,
        user=usr,
    )


@app.route("/recommendations/random")
def recommendations_random():
    user_id = random.choice(rs.all_users.PersonID)
    return recommendations_id(user_id)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/login")
def login():
    return render_template("login.html")
