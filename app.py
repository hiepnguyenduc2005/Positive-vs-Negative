import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from transformers import pipeline

from helpers import apology, login_required

classifier = pipeline("sentiment-analysis")

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///analysis.db")

TEXTS = ["I love Villanova so much.", "I hate reading about Criminology.","My name is Roger.", "I am so busy for the mid-term exam.", "Finally, we have the Fall Break."]
OPTIONS = ["Positive", "Negative"]

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    users = db.execute("SELECT * FROM users WHERE id = ?;", session["user_id"])
    totalTexts = users[0]["totalTexts"]

    positive = db.execute(
        """SELECT text FROM history WHERE user_id = ? AND label = "POSITIVE" ORDER BY score DESC LIMIT 5;""", session["user_id"],
    )

    negative = db.execute(
        """SELECT text FROM history WHERE user_id = ? AND label = "NEGATIVE" ORDER BY score DESC LIMIT 5;""", session["user_id"],
    )

    posNumber = db.execute(
        """SELECT COUNT (*) FROM history WHERE user_id = ? AND label = "POSITIVE";""", session["user_id"],
    )

    posPercent = posNumber[0]["COUNT (*)"] / totalTexts * 100
    posPercent = round(posPercent, 2)

    negNumber = db.execute(
        """SELECT COUNT (*) FROM history WHERE user_id = ? AND label = "NEGATIVE";""", session["user_id"],
    )
    negPercent = negNumber[0]["COUNT (*)"] / totalTexts * 100
    negPercent = round(negPercent, 2)

    return render_template("index.html", totalTexts = totalTexts, positive = positive, negative = negative, posPercent = posPercent, negPercent = negPercent)                                                                                                                                                                                                                                                                 

@app.route("/test", methods=["GET", "POST"])
@login_required
def test():
    """Test with users' input"""
    if request.method == "POST":
        # Ensure text/option is exists
        if not (request.form.get("text")):
            return apology("missing text")
        if not (request.form.get("guess")):
            return apology("missing guess")
        text = request.form.get("text")
        guess = request.form.get("guess").upper()
        result = classifier(text)[0]
        respond = (guess == result["label"])
        score = round(result["score"], 4)
        storage = {}
        if text.endswith(".") or text.endswith("!") or text.endswith("?"):
            text = text[:-1]
        words = text.split(" ")
        for i in words:
            if i.endswith(","):
                i = i[:-1]
            if classifier(i)[0]["label"] == result["label"] and classifier(i)[0]["score"] >= 0.995:
                storage[i] = round(classifier(i)[0]["score"], 5)
        if respond:
            flash("Correct! Text analysis added!")
        else:
            flash("Wrong! Text analysis added!")

        keyList = list(storage.keys())
        if len(keyList) == 0:
            keyWords = "NONE"
        else:
            keyWords = ', '.join(keyList)

        # Execute an addition
        db.execute(
            "INSERT INTO history(user_id, text, guess, label, score, keyWords) VALUES(?, ?, ?, ?, ?, ?);",
            session["user_id"],
            text,
            guess,
            result["label"],
            score,
            keyWords
        )

        # Update user's total
        db.execute(
            "UPDATE users SET totalTexts = totalTexts + 1 WHERE id = ?;", session["user_id"]
        )
        return render_template("test.html", text = text, guess = guess, result = result, score = score, respond = respond, options = OPTIONS, storage = storage, keyWords = keyWords)

    else:
        return render_template("test.html", options = OPTIONS)

@app.route("/about")
def about():
    """About the project"""
    return render_template("about.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC;", session["user_id"]
    )
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/sample", methods=["GET", "POST"])
def sample():
    """Get example"""
    if request.method == "POST":
        # Ensure text/option is exists
        if not (request.form.get("text")):
            return apology("missing text")
        if not (request.form.get("guess")):
            return apology("missing guess")
        text = request.form.get("text")
        guess = request.form.get("guess").upper()
        result = classifier(text)[0]
        respond = (guess == result["label"])
        score = round(result["score"], 4)
        storage = {}
        words = text[:-1].split(" ")
        for i in words:
            if classifier(i)[0]["label"] == result["label"] and classifier(i)[0]["score"] >= 0.995:
                storage[i] = round(classifier(i)[0]["score"], 5)
        if respond:
            flash("Correct!")
        else:
            flash("Wrong!")

        return render_template("sample.html", texts = TEXTS, text = text, guess = guess, result = result, score = score, respond = respond, options = OPTIONS, storage = storage)

    else:
        return render_template("sample.html", texts = TEXTS, options = OPTIONS)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?;", request.form.get("username")
        )

        # Ensure username not in database
        username = request.form.get("username")
        if len(rows) != 0:
            return apology(
                f"The username '{username}' already exists. Please choose another name."
            )

        password = request.form.get("password")
        password_cf = request.form.get("confirmation")

        # Ensure first password and second password are matched
        if password != password_cf:
            return apology("passwords do not match")

        # Insert username into database
        id = db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?);",
            username,
            generate_password_hash(password),
        )

        # Remember which user has logged in
        session["user_id"] = id

        flash("Registered!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/remove", methods=["POST"])
@login_required
def remove():
    """Remove texts from history"""
    id = request.form.get("id")
    if id:
        flash("Text analysis removed!")
        db.execute("DELETE FROM history WHERE id = ?", id)
        db.execute(
            "UPDATE users SET totalTexts = totalTexts - 1 WHERE id = ?;", session["user_id"]
        )
    return redirect("/history")
    