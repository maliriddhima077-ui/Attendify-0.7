"""Database layer for the Attendify school attendance and performance system.

Handles SQLite connection management, schema initialization, sample data
seeding, activity logging, and academic grade calculations.
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'school.db')


def get_db_connection():
    """Create and return a database connection with dictionary row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initialize database tables and create default administrator if not present."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users table (School Administrators & Teachers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Teacher',
            standard TEXT,
            division TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # 2. Students table (School Students Roster)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll TEXT NOT NULL,
            class_name TEXT NOT NULL,
            division TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            date_of_birth TEXT,
            gender TEXT NOT NULL,
            admission_date TEXT,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(roll, class_name, division)
        );
    ''')

    # 3. Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
            subject TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            UNIQUE(student_id, date, subject)
        );
    ''')

    # 4. Performance / School Examination Marks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            internal_marks REAL NOT NULL,
            external_marks REAL NOT NULL,
            total_marks REAL NOT NULL,
            percentage REAL NOT NULL,
            grade TEXT NOT NULL,
            semester TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
        );
    ''')

    # 5. Activity Log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            user TEXT NOT NULL DEFAULT 'Admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # 6. School Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institution_name TEXT NOT NULL DEFAULT 'St. Xavier Primary School',
            attendance_threshold REAL NOT NULL DEFAULT 75.0,
            academic_year TEXT NOT NULL DEFAULT '2025-2026',
            contact_email TEXT DEFAULT 'principal@stxavierschool.edu',
            department TEXT DEFAULT 'Primary School Wing'
        );
    ''')

    # ------------------------------------------------------------
    # Schema migration: add standard/division columns to users table
    # (needed for databases created before role-based auth existed)
    # ------------------------------------------------------------
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if 'standard' not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN standard TEXT")
    if 'division' not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN division TEXT")

    # Roll numbers encode Class+Division, so a roll alone must be unique
    # across the entire school (stronger than the composite UNIQUE above).
    cursor.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS uq_students_roll
        ON students (roll)
    ''')

    # Permanent occupancy register for strict no-reuse of roll numbers.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roll_ledger (
            roll TEXT PRIMARY KEY
        )
    ''')

    # Upgrade legacy administrator account to Principal role
    cursor.execute('''
        UPDATE users SET role = 'Principal', standard = NULL, division = NULL
        WHERE username = 'admin' AND role != 'Principal'
    ''')

    # Insert default admin (Principal) user if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name,
                               role, standard, division)
            VALUES (?, ?, ?, ?, NULL, NULL)
        ''', ('admin', hashed_pw, 'Principal / Admin', 'Principal'))

    # Insert/sync demo Class Teacher accounts — one teacher per class section.
    # Primary school: Standards 1-6 x Divisions A & B = 12 sections.
    # Uses upsert so assignment changes propagate to existing installs.
    teacher_pw = generate_password_hash('teach123')
    teacher_names = [
        'Anita Deshmukh', 'Sunita Rao',
        'Farida Khan', 'Geeta Patil',
        'Rakesh Menon', 'Shalini Verma',
        'Manoj Jadhav', 'Priyanka Shetty',
        'Vikas Yadav', 'Neha Kulkarni',
        'Sameer Shaikh', 'Lata Hegde',
    ]
    t_idx = 0
    for std in range(1, 7):
        for division in ('A', 'B'):
            t_username = f"teacher{std}{division.lower()}"
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, role,
                                   standard, division)
                VALUES (?, ?, ?, 'Teacher', ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    full_name = excluded.full_name,
                    role = 'Teacher',
                    standard = excluded.standard,
                    division = excluded.division
            ''', (t_username, teacher_pw, teacher_names[t_idx],
                  f'Class {std}', division))
            t_idx += 1

    # Insert default settings if not exists
    cursor.execute("SELECT id FROM settings WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO settings (
                id, institution_name, attendance_threshold,
                academic_year, contact_email, department
            )
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            1, 'St. Xavier Primary School', 75.0, '2025-2026',
            'principal@stxavierschool.edu', 'Primary School Wing'
        ))

    conn.commit()

    # Automatically seed sample data if empty
    cursor.execute("SELECT COUNT(*) as count FROM students")
    count = cursor.fetchone()['count']
    if count == 0:
        seed_sample_data(conn)
    conn.close()


def log_activity(action_type, description, user='Admin'):
    """Record an administrative or teacher action into the activity log."""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO activity_log (action_type, description, user)
            VALUES (?, ?, ?)
        ''', (action_type, description, user))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Error logging activity: {e}")


def get_recent_activities(limit=8):
    """Retrieve the most recent school activity logs."""
    conn = get_db_connection()
    logs = conn.execute('''
        SELECT * FROM activity_log
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    return logs


def calculate_grade(percentage):
    """Compute standard school letter grade based on percentage."""
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B+'
    elif percentage >= 60:
        return 'B'
    elif percentage >= 50:
        return 'C'
    elif percentage >= 40:
        return 'D'
    else:
        return 'F'


def seed_sample_data(existing_conn=None):
    """Populate realistic sample data for a primary school (Standards 1-6, Divisions A & B)."""
    conn = existing_conn if existing_conn else get_db_connection()
    cursor = conn.cursor()

    # Clear existing data first
    cursor.execute("DELETE FROM attendance;")
    cursor.execute("DELETE FROM performance;")
    cursor.execute("DELETE FROM students;")
    cursor.execute("DELETE FROM activity_log;")

    # 1. Primary School Students — Standards 1 to 6, Divisions A & B (3 per section)
    #    Roll numbers encode the section:
    #      Class c, Division A -> c*1000 + seat        (e.g. 3001, 3002, 3003)
    #      Class c, Division B -> c*1000 + 100 + seat  (e.g. 3101, 3102, 3103)
    student_names = [
        ("Aarav Sharma", "Male"), ("Ananya Deshmukh", "Female"), ("Rohan Verma", "Male"),
        ("Diya Patel", "Female"), ("Kabir Mehta", "Male"), ("Sneha Kulkarni", "Female"),
        ("Vihaan Gupta", "Male"), ("Isha Joshi", "Female"), ("Aditya Rao", "Male"),
        ("Meera Nambiar", "Female"), ("Aryan Saxena", "Male"), ("Tanvi Bhat", "Female"),
        ("Pooja Nair", "Female"), ("Siddharth Malhotra", "Male"), ("Kavya Reddy", "Female"),
        ("Devansh Sen", "Male"), ("Arjun Nair", "Male"), ("Riya Kapoor", "Female"),
        ("Vivaan Joshi", "Male"), ("Saanvi Kulkarni", "Female"), ("Atharv Deshpande", "Male"),
        ("Myra Chauhan", "Female"), ("Kiaan Pandya", "Male"), ("Aadhya Menon", "Female"),
        ("Reyansh Kotecha", "Male"), ("Pari Naik", "Female"), ("Advik Rane", "Male"),
        ("Anvi Desai", "Female"), ("Prisha Kamble", "Female"), ("Daksh Pawar", "Male"),
        ("Sara Shaikh", "Female"), ("Om Thakkar", "Male"), ("Navya Pillai", "Female"),
        ("Veer Malhotra", "Male"), ("Kiara Fernandes", "Female"), ("Ritvik Suresh", "Male"),
    ]

    sample_students = []
    roll_to_seat = {}
    name_index = 0
    for std in range(1, 7):                      # Standards 1 .. 6
        for division in ('A', 'B'):              # Two divisions only
            birth_year_base = 2020 - std         # Ages ~6 to ~12
            admission_year = 2026 - std
            base = std * 1000 + (0 if division == 'A' else 100)
            for seat in range(1, 4):             # 3 students per section
                full_name, gender = student_names[name_index]
                roll = str(base + seat)          # e.g. Class 3-B -> 3101..3103

                first = full_name.split()[0].lower()
                email = f"{first}.{roll}@gmail.com"
                phone_digits = str(9000000000 + name_index * 137911 + std)
                phone = f"+91 {phone_digits[:5]} {phone_digits[5:]}"
                dob_month = (name_index % 12) + 1
                dob_day = ((name_index * 7) % 27) + 1
                date_of_birth = f"{birth_year_base}-{dob_month:02d}-{dob_day:02d}"
                sample_students.append((
                    full_name, roll, f"Class {std}", division,
                    email, phone,
                    date_of_birth, gender,
                    f"{admission_year}-06-15"
                ))
                roll_to_seat[roll] = seat
                name_index += 1

    cursor.executemany('''
        INSERT INTO students (
            name, roll, class_name, division, email, phone,
            date_of_birth, gender, admission_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_students)

    # Rebuild the permanent roll ledger from the freshly seeded roster
    # (seeding is a full reset of the school dataset).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roll_ledger (
            roll TEXT PRIMARY KEY
        )
    ''')
    cursor.execute('DELETE FROM roll_ledger;')
    cursor.execute('INSERT INTO roll_ledger (roll) SELECT roll FROM students;')

    # Fetch inserted student records
    cursor.execute("SELECT id, roll FROM students ORDER BY id ASC")
    students = cursor.fetchall()

    # Primary School Subjects
    school_subjects = [
        "Mathematics", "English", "Environmental Studies",
        "Hindi", "Computer Science", "Art & Craft"
    ]

    today = datetime.now().date()
    dates = []
    current = today - timedelta(days=28)
    while current <= today:
        if current.weekday() < 5:  # Monday to Friday school days
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    attendance_records = []
    for st in students:
        s_id = st['id']
        roll = st['roll']
        seat = roll_to_seat.get(roll, 1)         # Seat position within section

        if seat == 3:
            weights = [0.55, 0.35, 0.10]         # At risk (<60%)
        elif seat == 2:
            weights = [0.70, 0.22, 0.08]         # Warning (<75%)
        else:
            weights = [0.90, 0.07, 0.03]         # Good (88-96%)

        for dt in dates:
            for sub in school_subjects[:4]:      # Track daily core subjects
                status = random.choices(['Present', 'Absent', 'Late'], weights=weights, k=1)[0]
                attendance_records.append((s_id, dt, status, sub))

    cursor.executemany('''
        INSERT OR REPLACE INTO attendance (student_id, date, status, subject)
        VALUES (?, ?, ?, ?)
    ''', attendance_records)

    # Performance Records for School Terms (Midterm / Term 1)
    performance_records = []
    for st in students:
        s_id = st['id']
        roll = st['roll']
        seat = roll_to_seat.get(roll, 1)         # Seat position within section

        if seat == 1:
            base_score = 86                      # High achievers (A / A+)
        elif seat == 2:
            base_score = 72                      # Good / Average
        else:
            base_score = 48                      # Needs improvement

        for sub in school_subjects:
            jitter = random.randint(-10, 8)
            target_pct = max(28, min(98, base_score + jitter))

            # Periodic / Internal Assessment (max 40) + Term Exam (max 60) = 100
            internal = round(target_pct * 0.40 * (random.uniform(0.92, 1.05)), 1)
            internal = max(5.0, min(40.0, internal))

            external = round(target_pct * 0.60 * (random.uniform(0.92, 1.05)), 1)
            external = max(10.0, min(60.0, external))

            total = round(internal + external, 1)
            pct = round((total / 100.0) * 100, 1)
            grade = calculate_grade(pct)
            semester = "Term 1 (Midterm)"

            performance_records.append((s_id, sub, internal, external, total, pct, grade, semester))

    cursor.executemany('''
        INSERT INTO performance (
            student_id, subject, internal_marks, external_marks,
            total_marks, percentage, grade, semester
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', performance_records)

    sample_activities = [
        ("System", "Primary school academic session 2025-2026 configured successfully",
         "Principal"),
        ("Student Admission",
         "Admitted 36 students across Standards 1 to 6 (Divisions A & B)", "Admin"),
        ("Attendance", "Daily morning roll call recorded for Class 3-A", "Class Teacher"),
        ("Examinations", "Term 1 Midterm Assessment marks compiled", "Exam Coordinator"),
        ("Report Cards", "Generated Student Progress Report Cards for Term 1",
         "Class Teacher")
    ]
    cursor.executemany('''
        INSERT INTO activity_log (action_type, description, user)
        VALUES (?, ?, ?)
    ''', sample_activities)

    conn.commit()
    if not existing_conn:
        conn.close()


def reset_data():
    """Safely reset all school records while preserving admin user."""
    conn = get_db_connection()
    conn.execute("DELETE FROM attendance;")
    conn.execute("DELETE FROM performance;")
    conn.execute("DELETE FROM students;")
    conn.execute("DELETE FROM activity_log;")
    conn.execute('''
        INSERT INTO activity_log (action_type, description, user)
        VALUES ('System', 'All school academic records were reset by Administrator', 'Admin')
    ''')
    conn.commit()
    conn.close()
