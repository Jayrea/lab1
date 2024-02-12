from flask import Flask, render_template, request, redirect, session, flash
from flask_session import Session
from sqlalchemy import create_engine , text
from sqlalchemy.orm import scoped_session, sessionmaker 
import hashlib
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DATABASE_URL = os.getenv("DATABASE_URL", "default_fallback_database_url")
engine = create_engine(DATABASE_URL)
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/search")
    return "Welcome! Please <a href='/login'>log in</a> or <a href='/register'>register</a>."

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            db.execute(text(f"INSERT INTO users (username, password) VALUES (:username, :password)"),
           {"username": username, "password": hashed_pw})
            db.commit()
            return redirect("/login")
        except Exception as e:
            db.rollback()
            return "Registration failed. Error: " + str(e)
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        user = db.execute(text("SELECT * FROM users WHERE username = :username AND password = :password"),
                          {"username": username, "password": hashed_pw}).fetchone()
        if user:
            session["user_id"] = user.id
            return redirect("/")
        else:
            return "Invalid username or password."
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/search", methods=["GET", "POST"])
def search():
    if "user_id" not in session:
        return redirect("/login")
    
    if request.method == "POST":
        query = request.form.get("query")
        query = "%" + query + "%"
        books = db.execute(text("SELECT * FROM books WHERE \
                            isbn LIKE :query OR \
                            title LIKE :query OR \
                            author LIKE :query"),
                            {"query": query}).fetchall()
        if not books:
            return render_template("search.html", message="No matches found.")
        return render_template("search.html", books=books)
    
    return render_template("search.html")

from flask import flash, redirect, render_template, request, session
from sqlalchemy import text

@app.route("/book/<isbn>", methods=["GET", "POST"])
def book(isbn):
    if "user_id" not in session:
        return redirect("/login")

    # Fetch the book details using the provided ISBN
    book = db.execute(text("SELECT * FROM books WHERE isbn = :isbn"), {"isbn": isbn}).fetchone()
    if book is None:
        return "Book not found."

    # Handle the review submission
    if request.method == "POST":
        user_id = session["user_id"]
        rating = request.form.get("rating")
        comment = request.form.get("comment")

        # Check if the user has already submitted a review for this book
        existing_review = db.execute(text("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id"),
                                     {"user_id": user_id, "book_id": book.id}).fetchone()
        if existing_review:
            flash("You've already submitted a review for this book.")
        else:
            # Insert the new review into the database
            db.execute(text("INSERT INTO reviews (user_id, book_id, comment, rating) VALUES (:user_id, :book_id, :comment, :rating)"),
                       {"user_id": user_id, "book_id": book.id, "comment": comment, "rating": rating})
            db.commit()
            flash("Your review has been submitted.")

    # Fetch all reviews for the book
    reviews = db.execute(text("SELECT reviews.*, users.username FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_id = :book_id"),
                         {"book_id": book.id}).fetchall()

    # Render the page with both book details and reviews
    return render_template("book.html", book=book, reviews=reviews)


if __name__ == "__main__":
    app.run(debug=True)
