from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import pdfplumber
import docx
import os
import re

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- UPLOAD FOLDER ----------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------- ALLOWED FILE TYPES ----------
ALLOWED_EXTENSIONS = {"pdf", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------- DATABASE CONNECTION ----------
conn = psycopg2.connect(
    dbname="resume_db",
    user="postgres",
    password="lucky04",  # change if needed
    host="localhost",
    port="5432"
)
cur = conn.cursor()


# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/upload")
        else:
            return "Invalid login"

    return render_template("login.html")


# ---------- TEXT EXTRACTION FUNCTION ----------
def extract_text(filepath):
    text = ""
    ext = os.path.splitext(filepath)[1].lower()

    try:
        # ---------- PDF ----------
        if ext == ".pdf":
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

        # ---------- DOCX ----------
        elif ext == ".docx":
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"

    except Exception as e:
        print("Error reading file:", e)

    return text


# ---------- UPLOAD & PARSE RESUME ----------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "admin" not in session:
        return redirect("/")

    if request.method == "POST":
        file = request.files["resume"]

        if file and allowed_file(file.filename):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            # ---------- EXTRACT TEXT ----------
            text = extract_text(filepath)

            if not text:
                return "Could not extract text from file."

            # ---------- NAME ----------
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            name = ""

            for line in lines[:5]:
                if len(line.split()) <= 4 and not any(char.isdigit() for char in line):
                    name = line
                    break

            # ---------- EMAIL ----------
            email = ""
            email_match = re.search(
                r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text
            )
            if email_match:
                email = email_match.group()

            # ---------- PHONE ----------
            phone = ""
            phone_match = re.search(r"\b\d{10}\b", text)
            if phone_match:
                phone = phone_match.group()

            # ---------- SKILLS ----------
            skill_keywords = [
                "python", "java", "flask", "django", "sql",
                "postgresql", "machine learning",
                "deep learning", "nlp",
                "html", "css", "javascript"
            ]

            skills_found = []
            text_lower = text.lower()

            for skill in skill_keywords:
                if skill in text_lower:
                    skills_found.append(skill)

            skills = ", ".join(skills_found)

            # ---------- INSERT INTO DATABASE ----------
            cur.execute(
                "INSERT INTO resumes (name, email, phone, skills) VALUES (%s, %s, %s, %s)",
                (name, email, phone, skills)
            )
            conn.commit()

            return redirect(url_for("resumes"))

        else:
            return "Only PDF and DOCX files are allowed!"

    return render_template("upload.html")


# ---------- VIEW ALL RESUMES ----------
@app.route("/resumes")
def resumes():
    if "admin" not in session:
        return redirect("/")

    cur.execute("SELECT name, email, phone, skills FROM resumes")
    data = cur.fetchall()
    return render_template("resumes.html", data=data)


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)

