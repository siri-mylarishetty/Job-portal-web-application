from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# -------------------- Flask app & DB config --------------------

# note: template_folder="template" because your folder is named "template"
app = Flask(__name__, template_folder="template")
app.secret_key = "dev_secret_key_for_job_portal"  # you can change this

# XAMPP MySQL (MariaDB) config
# User: root
# Host: localhost
# Password: (empty, XAMPP default)
# Database: job_portal
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:@localhost/job_portal"
# If you later set a password, e.g. 'siri123', use:
# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:siri123@localhost/job_portal"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------- Models --------------------


class Employer(db.Model):
    __tablename__ = "employer"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    contact_email = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)  # plain text for demo only

    jobs = db.relationship("Job", backref="employer", lazy=True)


class Applicant(db.Model):
    __tablename__ = "applicant"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    resume_text = db.Column(db.Text, nullable=True)

    applications = db.relationship("Application", backref="applicant", lazy=True)


class Job(db.Model):
    __tablename__ = "job"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employer_id = db.Column(db.Integer, db.ForeignKey("employer.id"), nullable=False)

    applications = db.relationship("Application", backref="job", lazy=True)


class Application(db.Model):
    __tablename__ = "application"

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey("applicant.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    cover_letter = db.Column(db.Text)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- Routes --------------------


@app.route("/")
def index():
    """Home page: show latest 5 jobs."""
    jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    # home template name in your project
    return render_template("intex.html", jobs=jobs)


# ---- Applicant registration ----
@app.route("/register_applicant", methods=["GET", "POST"])
def register_applicant():
    if request.method == "POST":
        name = request.form["full_name"]
        email = request.form["email"]
        resume_text = request.form.get("resume_text", "")

        if not name or not email:
            flash("Name and email are required.")
            return redirect(url_for("register_applicant"))

        applicant = Applicant(full_name=name, email=email, resume_text=resume_text)
        db.session.add(applicant)
        db.session.commit()

        flash(f"Applicant registered successfully. Your applicant ID: {applicant.id}")
        return redirect(url_for("index"))

    return render_template("register_applicant.html")


# ---- Employer registration ----
@app.route("/register_employer", methods=["GET", "POST"])
def register_employer():
    if request.method == "POST":
        company = request.form["company_name"]
        email = request.form["contact_email"]
        password = request.form["password"]

        if not company or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register_employer"))

        emp = Employer(company_name=company, contact_email=email, password=password)
        db.session.add(emp)
        db.session.commit()

        flash(f"Employer registered successfully. Your employer ID: {emp.id}")
        return redirect(url_for("index"))

    return render_template("register_employer.html")


# ---- Employer posts a job ----
@app.route("/post_job", methods=["GET", "POST"])
def post_job():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        location = request.form.get("location", "")
        employer_id = request.form["employer_id"]

        if not title or not description or not employer_id:
            flash("Title, description and employer ID are required.")
            return redirect(url_for("post_job"))

        emp = Employer.query.get(employer_id)
        if not emp:
            flash("Employer ID not found. Please check and try again.")
            return redirect(url_for("post_job"))

        job = Job(title=title, description=description, location=location, employer=emp)
        db.session.add(job)
        db.session.commit()

        flash("Job posted successfully.")
        return redirect(url_for("index"))

    return render_template("post_job.html")


# ---- List all jobs ----
@app.route("/jobs")
def jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template("jobs.html", jobs=jobs)


# ---- Job detail page ----
@app.route("/job/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template("job_detail.html", job=job)


# ---- Apply for a job ----
@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply(job_id):
    job = Job.query.get_or_404(job_id)

    if request.method == "POST":
        applicant_id = request.form["applicant_id"]
        cover_letter = request.form.get("cover_letter", "")

        applicant = Applicant.query.get(applicant_id)
        if not applicant:
            flash("Applicant ID not found. Please register first.")
            return redirect(url_for("register_applicant"))

        existing = Application.query.filter_by(
            applicant_id=applicant_id, job_id=job_id
        ).first()
        if existing:
            flash("You have already applied for this job.")
            return redirect(url_for("jobs"))

        appn = Application(
            applicant_id=applicant.id, job_id=job.id, cover_letter=cover_letter
        )
        db.session.add(appn)
        db.session.commit()

        flash("Application submitted successfully.")
        return redirect(url_for("jobs"))

    return render_template("apply.html", job=job)


# ---- Employer dashboard ----
@app.route("/employer/<int:employer_id>/dashboard")
def employer_dashboard(employer_id):
    emp = Employer.query.get_or_404(employer_id)
    jobs = Job.query.filter_by(employer_id=employer_id).order_by(
        Job.created_at.desc()
    ).all()

    job_applications = {}
    for j in jobs:
        job_applications[j.id] = Application.query.filter_by(job_id=j.id).all()

    return render_template(
        "employer_dashboard.html",
        employer=emp,
        jobs=jobs,
        job_applications=job_applications,
    )


# -------------------- CLI command to init DB --------------------


@app.cli.command("init-db")
def init_db():
    """Create all tables in the MySQL database."""
    db.create_all()
    print("Database initialized (tables created).")


# -------------------- Run app --------------------

if __name__ == "__main__":
    app.run(debug=True)
