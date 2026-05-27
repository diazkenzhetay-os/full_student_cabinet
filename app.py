from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "student_secret_key"

GROUP_NAME = "ПОР-2"

TEACHERS = {
    "Гулдана Толепбергенова": {
        "password": "12345",
        "name": "Гулдана Толепбергенова",
        "subjects": ["Базы данных"]
    },
    "Мадина Нурлыхановна": {
        "password": "12345",
        "name": "Мадина Нурлыхановна",
        "subjects": ["ООП", "Алгоритмизация и программирование"]
    }
}


def get_db():
    return sqlite3.connect("database.db")


def letter_grade(score):
    score = int(score)
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 65:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            teacher_name TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject_id INTEGER,
            score INTEGER DEFAULT 65
        )
    """)

    students = [
        "Абдрашев Амир",
        "Байрахим Айлин",
        "Енотов Сергей",
        "Жумабай Айгерим",
        "Нусупбеков Дастан",
        "Калиаскарова Гульмира",
        "Мустафина Алина",
        "Нурланов Диас",
        "Серикбаев Аян",
        "Тулегенова Аружан"
    ]

    for student in students:
        c.execute("SELECT id FROM students WHERE full_name=?", (student,))
        if not c.fetchone():
            c.execute(
                "INSERT INTO students (full_name, password) VALUES (?, ?)",
                (student, generate_password_hash("12345"))
            )

    for teacher, info in TEACHERS.items():
        for subject in info["subjects"]:
            c.execute("SELECT id FROM subjects WHERE name=? AND teacher_name=?", (subject, teacher))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO subjects (name, teacher_name) VALUES (?, ?)",
                    (subject, teacher)
                )

    conn.commit()

    c.execute("SELECT id FROM students")
    students_db = c.fetchall()

    c.execute("SELECT id FROM subjects")
    subjects_db = c.fetchall()

    for student in students_db:
        for subject in subjects_db:
            c.execute(
                "SELECT id FROM grades WHERE student_id=? AND subject_id=?",
                (student[0], subject[0])
            )
            if not c.fetchone():
                c.execute(
                    "INSERT INTO grades (student_id, subject_id, score) VALUES (?, ?, ?)",
                    (student[0], subject[0], random.randint(45, 100))
                )

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in TEACHERS and password == TEACHERS[username]["password"]:
            session.clear()
            session["teacher"] = username
            session["teacher_name"] = TEACHERS[username]["name"]
            return redirect("/admin")

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, full_name, password FROM students WHERE full_name=?", (username,))
        student = c.fetchone()
        conn.close()

        if student and check_password_hash(student[2], password):
            session.clear()
            session["student_id"] = student[0]
            session["student_name"] = student[1]
            return redirect("/profile")

        return "Неверный логин или пароль"

    return render_template("login.html")


@app.route("/profile")
def profile():
    if "student_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT subjects.name, grades.score
        FROM grades
        JOIN subjects ON grades.subject_id = subjects.id
        WHERE grades.student_id=?
        ORDER BY subjects.name
    """, (session["student_id"],))

    grades = c.fetchall()
    conn.close()

    avg = round(sum([g[1] for g in grades]) / len(grades), 2) if grades else 0

    return render_template(
        "profile.html",
        grades=grades,
        avg=avg,
        letter_grade=letter_grade,
        group_name=GROUP_NAME
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "teacher" not in session:
        return redirect("/login")

    teacher = session["teacher"]

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_grade":
            grade_id = request.form["grade_id"]
            score = request.form["score"]

            c.execute("""
                SELECT subjects.teacher_name
                FROM grades
                JOIN subjects ON grades.subject_id = subjects.id
                WHERE grades.id=?
            """, (grade_id,))

            owner = c.fetchone()

            if owner and owner[0] == teacher:
                c.execute("UPDATE grades SET score=? WHERE id=?", (score, grade_id))

        elif action == "add_student":
            full_name = request.form["full_name"]

            try:
                c.execute(
                    "INSERT INTO students (full_name, password) VALUES (?, ?)",
                    (full_name, generate_password_hash("12345"))
                )

                student_id = c.lastrowid

                c.execute("SELECT id FROM subjects")
                all_subjects = c.fetchall()

                for subject in all_subjects:
                    c.execute(
                        "INSERT INTO grades (student_id, subject_id, score) VALUES (?, ?, ?)",
                        (student_id, subject[0], random.randint(45, 100))
                    )

            except sqlite3.IntegrityError:
                pass

        elif action == "add_subject":
            subject_name = request.form["subject_name"]

            try:
                c.execute(
                    "INSERT INTO subjects (name, teacher_name) VALUES (?, ?)",
                    (subject_name, teacher)
                )

                subject_id = c.lastrowid

                c.execute("SELECT id FROM students")
                all_students = c.fetchall()

                for student in all_students:
                    c.execute(
                        "INSERT INTO grades (student_id, subject_id, score) VALUES (?, ?, ?)",
                        (student[0], subject_id, random.randint(45, 100))
                    )

            except sqlite3.IntegrityError:
                pass

        conn.commit()

    c.execute("""
        SELECT grades.id, students.full_name, subjects.name, grades.score
        FROM grades
        JOIN students ON grades.student_id = students.id
        JOIN subjects ON grades.subject_id = subjects.id
        WHERE subjects.teacher_name=?
        ORDER BY subjects.name, students.full_name
    """, (teacher,))

    data = c.fetchall()

    c.execute("SELECT name FROM subjects WHERE teacher_name=? ORDER BY name", (teacher,))
    teacher_subjects = [row[0] for row in c.fetchall()]

    conn.close()

    return render_template(
        "admin.html",
        data=data,
        teacher_name=session["teacher_name"],
        group_name=GROUP_NAME,
        teacher_subjects=teacher_subjects,
        letter_grade=letter_grade
    )


@app.route("/journal")
def journal():
    if "teacher" not in session:
        return redirect("/login")

    teacher = session["teacher"]

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id, full_name FROM students ORDER BY full_name")
    students = c.fetchall()

    c.execute("SELECT id, name FROM subjects WHERE teacher_name=? ORDER BY name", (teacher,))
    subjects = c.fetchall()

    journal_data = []

    for student_id, full_name in students:
        row = {
            "full_name": full_name,
            "grades": [],
            "avg": 0
        }

        scores = []

        for subject_id, subject_name in subjects:
            c.execute(
                "SELECT score FROM grades WHERE student_id=? AND subject_id=?",
                (student_id, subject_id)
            )

            result = c.fetchone()
            score = result[0] if result else 0

            scores.append(score)
            row["grades"].append(score)

        row["avg"] = round(sum(scores) / len(scores), 2) if scores else 0
        journal_data.append(row)

    conn.close()

    return render_template(
        "journal.html",
        students=journal_data,
        subjects=subjects,
        teacher_name=session["teacher_name"],
        group_name=GROUP_NAME,
        letter_grade=letter_grade
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)