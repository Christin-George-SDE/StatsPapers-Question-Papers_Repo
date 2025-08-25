import os
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_file, Response
)
from io import BytesIO
from pymongo import MongoClient


# --- Load environment variables ---

MONGO_URI = os.getenv("MONGO_URI")

# --- Flask setup ---
app = Flask(__name__)
app.secret_key = "super_secret_key"  # change in production

# --- MongoDB setup ---

client = MongoClient(MONGO_URI)
db = client["question_papers"]
collection = db["Q_P"]

# --- Authentication ---
VALID_USERNAME = "MscStat"
VALID_PASSWORD = "Stat123@"


@app.route("/")
def home():
    return render_template("index.html", login=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session["user"] = username
            return redirect(url_for("uploader"))
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

    return render_template("contribute.html", login=True)


@app.route("/uploader", methods=["GET", "POST"])
def uploader():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        semester = request.form.get("semester")
        subject = request.form.get("paper") 
        subject = subject.replace(" ", "_") 
        year = request.form.get("year") 
        month = request.form.get("month") 
        file = request.files.get("pdfFile")

        if not (semester and subject and year and month and file):
            flash("Please fill all fields and upload a file", "error")
            return redirect(url_for("uploader"))

        if not file.filename.endswith(".pdf"):
            flash("Only PDF files allowed", "error")
            return redirect(url_for("uploader"))

        # Check if already exists
        existing = collection.find_one({
            "semester": f"{semester}_sem",
            "subject": subject,
            "filename": f"{year}_{month}.pdf"            
        })
        if existing:
            flash(f"A file for {year}_{month} already exists", "warning")
            return redirect(url_for("uploader"))

        # Save file to MongoDB
        file_data = file.read()
        doc = {
            "semester": f"{semester}_sem",
            "subject": subject,
            "filename": f"{year}_{month}.pdf",
            "content": file_data
        }
        collection.insert_one(doc)

        flash("File uploaded successfully!", "success")
        return redirect(url_for("uploader"))

    return render_template("contribute.html", login=False)


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


# --- List PDFs from MongoDB ---
@app.route("/pdfs")
def list_pdfs():
    global query
    query = request.args.get("query")
    

    pdf_files = list(collection.find(eval(query), {"_id": 1, "filename": 1,
                                             "semester": 1, "subject": 1,
                                             "year": 1, "month": 1}))

    return render_template("pdf_view.html", pdf_files=[pdf['filename'] for pdf in pdf_files])


# --- Serve a PDF directly from MongoDB ---
@app.route("/pdfs/<filename>")
def serve_pdf(filename):
    global query
    query = eval(query)
    query['filename'] = filename
    print(query)

    doc = collection.find_one(query)
    if not doc:
        return "File not found", 404

    return Response(
        doc["content"],
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={doc['filename']}"}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
