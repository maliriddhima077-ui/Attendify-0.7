# Attendify — Smart Attendance & Academic Performance Analytics System

Attendify is a complete, full-stack, production-ready Attendance and Student Performance Analytics web application developed with Python (Flask), SQLite, HTML5, CSS3, JavaScript, Bootstrap 5, and Chart.js.

Built for college administrators, department heads, and faculty members, Attendify provides end-to-end management of student rosters, interactive attendance session capture, semester examination gradebooks, dynamic analytical dashboards, automated at-risk student detection (< 75% attendance), and high-resolution printable institutional dossiers.

---

## 🌟 Key Features

1. **Executive Dashboard**:
   - 6 Live KPI metric cards (Total Students, Present Today, Absent Today, Average Attendance %, Average Exam Performance %, At-Risk Count).
   - 5 Interactive Chart.js Visualizations (Attendance Overview Doughnut, Monthly Attendance Trend Line, Grade Distribution Bar, Comparative Subject Averages, and Attendance vs Performance Correlation).
   - Proactive At-Risk student radar (< 75% threshold).
   - Live system activity feed.

2. **Student Lifecycle Management (CRUD)**:
   - Enrolled student directory with multi-criteria filtering (Class, Division, Attendance Status, Grade) and instant table search.
   - Profile creation and modification with duplicate roll-number prevention.
   - Comprehensive 360° student profile dossier with personal credentials, attendance rates, radar charts, subject scores, and history logs.

3. **Interactive Attendance Management**:
   - Class attendance register by date, class, division, and subject.
   - Segmented status toggles (Present, Absent, Late).
   - One-click batch actions (*Mark All Present*, *Mark All Absent*, *Mark All Late*).
   - Live presence tally counter.
   - Atomic batch saving with SQLite upsert to prevent duplicates.

4. **Attendance Audit & Threshold Analytics**:
   - Granular historical attendance log with multi-parameter filtering.
   - Threshold categorization: Excellent (≥90%), Good (75–89%), Warning (60–74%), Critical (<60%).
   - Visual progress bars highlighting non-compliant students.

5. **Academic Performance & Gradebook**:
   - Examination marks entry (Internal max 40 + External max 60 = Total max 100).
   - Automatic percentage and standard letter grade calculation (A+, A, B+, B, C, D, F).
   - Performance analytics: Pass/Fail ratios, highest/lowest scores, subject averages.

6. **Institutional Report Generation & Print Support**:
   - 4 Printable Reports: Attendance Summary, Performance Dossier, Individual Student Dossier, and Class Batch Summary.
   - Clean printable layout (`@media print`) with official institutional letterheads and faculty/HOD/Dean signature blocks.
   - Instant CSV data roster exports.

7. **Modern UX & System Administration**:
   - Persistent Dark Mode / Light Mode toggle stored via `localStorage`.
   - Responsive mobile-friendly sidebar and navigation.
   - Flash notifications and modal delete confirmations.
   - Built-in Sample Data Seeder for instant demonstration.

---

## 👥 4-Member Team Workload & Module Breakdown

This project is structured into **4 equal, balanced, and independent modules** for a 4-member college engineering team:

| Team Member | Module Name | Core Responsibilities | Primary Files |
| :--- | :--- | :--- | :--- |
| **MEMBER 1** | **Student Management & Database Core** | SQLite schema, connection pooling, student CRUD, validation, search & 360° profile dossier | `modules/student.py`<br>`backend/database.py`<br>`templates/students.html`<br>`templates/student_profile.html` |
| **MEMBER 2** | **Attendance Management & Compliance** | Daily attendance register, segmented status toggles, atomic upsert, history audit & <75% threshold analytics | `modules/attendance.py`<br>`static/js/attendance.js`<br>`templates/attendance.html`<br>`templates/attendance_analysis.html` |
| **MEMBER 3** | **Performance & Visual Analytics** | Internal/External marks entry, automatic grading logic, Chart.js visual analytics & Attendance vs Performance correlation | `modules/performance.py`<br>`static/js/charts.js`<br>`templates/performance.html`<br>`templates/performance_analysis.html` |
| **MEMBER 4** | **Dashboard, Reports, UI/UX & Integration** | Executive dashboard, 6 KPI cards, printable institutional dossiers, Dark Mode, session auth & full integration | `app.py`<br>`modules/dashboard.py`<br>`modules/reports.py`<br>`templates/dashboard.html`<br>`templates/report_view.html` |

> 📖 **Full Viva & Presentation Guide**: See [TEAM_GUIDE.md](file:///C:/Users/Riddhima%20Mali/.gemini/antigravity/scratch/attendance_report_system/TEAM_GUIDE.md) for 2–3 minute spoken presentation scripts and 20+ viva questions with model answers.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python 3, Flask 3.x, Jinja2 |
| **Database Engine** | SQLite3 (`school.db`) with `PRAGMA foreign_keys = ON` |
| **Security & Session** | Werkzeug password hashing, Flask Sessions |
| **Frontend UI / Layout** | HTML5, Modern Custom CSS3, Bootstrap 5.3.3 |
| **Iconography** | Bootstrap Icons, Font Awesome 6 |
| **Data Visualizations** | Chart.js 4.4.x |
| **Export Formats** | CSV, Print-to-PDF ready views |

---

## 📁 Project Architecture & Structure

```
attendance_report_system/
│
├── app.py                      # Flask application factory, controllers, auth decorator & routes
├── requirements.txt            # Python dependencies
├── README.md                   # Complete documentation, setup guide & viva questions
├── school.db                   # SQLite database (auto-generated on startup)
│
├── backend/
│   ├── __init__.py             # Backend package initialization
│   └── database.py             # SQLite connection helper, schema creation, activity logging & sample seeder
│
├── modules/
│   ├── __init__.py             # Domain modules export
│   ├── student.py              # Student lifecycle CRUD & profile analytics aggregation
│   ├── attendance.py           # Attendance sheets, batch upsert, history filters & compliance calculations
│   ├── performance.py          # Marks entry, grade computation & performance distributions
│   ├── dashboard.py            # Dashboard KPI calculations & Chart.js series aggregations
│   └── reports.py              # Institutional report compilers (Attendance, Performance, Dossier, Batch)
│
├── templates/
│   ├── base.html               # Master layout: collapsible sidebar, top navbar, alerts & theme switchers
│   ├── login.html              # Modern login interface
│   ├── dashboard.html          # Main dashboard with 6 KPI cards, 5 charts, risk list & activity feed
│   ├── students.html           # Student roster with multi-filter, instant search & modals
│   ├── add_student.html        # New student registration form
│   ├── edit_student.html       # Edit student record form
│   ├── student_profile.html    # 360° student profile with doughnut & bar charts
│   ├── attendance.html         # Class attendance register with batch toggles
│   ├── attendance_history.html # Historical log with date/class/subject filters
│   ├── attendance_analysis.html# Dedicated compliance analytics with progress meters
│   ├── performance.html        # Gradebook roster with search & filters
│   ├── add_performance.html    # Marks entry form with live preview calculation
│   ├── edit_performance.html   # Edit exam marks record
│   ├── performance_analysis.html# Pass/Fail stats, subject averages & grade distribution
│   ├── reports.html            # Report configuration center
│   ├── report_view.html        # Official institutional letterhead printable report
│   ├── settings.html           # Institution settings & demo data tools
│   ├── 404.html                # Friendly 404 not found page
│   └── 500.html                # 500 internal server error page
│
└── static/
    ├── css/
    │   └── style.css           # Design system, CSS variables for dark mode & print styles
    └── js/
        ├── main.js             # Theme switcher, mobile sidebar toggle, live search
        ├── dashboard.js        # Chart.js initialization for 5 interactive charts
        ├── attendance.js       # Register batch toggles and live presence tally
        └── charts.js           # Student profile & performance analytics chart handlers
```

---

## 🚀 Quick Setup & Installation Guide

### Prerequisites
- Python 3.9 or higher installed on your system.

### Step 1: Navigate to the Project Directory
```bash
cd "C:\Users\Riddhima Mali\.gemini\antigravity\scratch\attendance_report_system"
```

### Step 2: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
python app.py
```

### Step 4: Open in Web Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Administrator Credentials

| Field | Demo Credential |
| :--- | :--- |
| **Username** | `admin` |
| **Password** | `admin123` |

*(On initial startup, the database is auto-initialized and pre-seeded with sample students, attendance, and exam marks for immediate demonstration)*.

---

## 🗄️ Database Design & Schema

### 1. `users` Table
- Stores administrator and faculty credentials with hashed passwords (`werkzeug.security`).
- `id` (INTEGER PK), `username` (TEXT UNIQUE), `password_hash` (TEXT), `full_name` (TEXT), `role` (TEXT), `created_at` (TIMESTAMP).

### 2. `students` Table
- Stores enrolled student records.
- `id` (INTEGER PK), `name` (TEXT), `roll` (TEXT), `class_name` (TEXT), `division` (TEXT), `email` (TEXT), `phone` (TEXT), `date_of_birth` (TEXT), `gender` (TEXT), `admission_date` (TEXT), `status` (TEXT), `created_at` (TIMESTAMP).
- **Constraint**: `UNIQUE(roll, class_name, division)` prevents duplicate roll numbers in the same class batch.

### 3. `attendance` Table
- Tracks daily subject-wise session attendance.
- `id` (INTEGER PK), `student_id` (INTEGER FK), `date` (TEXT), `status` (TEXT CHECK in 'Present', 'Absent', 'Late'), `subject` (TEXT), `created_at` (TIMESTAMP).
- **Constraint**: `UNIQUE(student_id, date, subject)` and `FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE`.

### 4. `performance` Table
- Stores internal assessment and external examination scores.
- `id` (INTEGER PK), `student_id` (INTEGER FK), `subject` (TEXT), `internal_marks` (REAL, max 40), `external_marks` (REAL, max 60), `total_marks` (REAL, max 100), `percentage` (REAL), `grade` (TEXT), `semester` (TEXT), `created_at` (TIMESTAMP).
- **Constraint**: `FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE`.

### 5. `activity_log` Table
- Audits administrative actions (logins, enrollments, attendance entries, marks updates).
- `id` (INTEGER PK), `action_type` (TEXT), `description` (TEXT), `user` (TEXT), `created_at` (TIMESTAMP).

### 6. `settings` Table
- Holds institutional name, academic year, contact details, and attendance warning threshold.

---

## 📊 Core Calculation Logic

### 1. Attendance Percentage Formula
$$\text{Attendance \%} = \left(\frac{\text{Present Classes}}{\text{Total Conducted Classes}}\right) \times 100$$

- **Excellent**: $\ge 90\%$
- **Good**: $75\% - 89.9\%$
- **Warning**: $60\% - 74.9\%$
- **Critical**: $< 60\%$ (Flagged on Risk Radar)

### 2. Grading System Formula
- **90% – 100%**: Grade `A+` (Outstanding)
- **80% – 89.9%**: Grade `A` (Excellent)
- **70% – 79.9%**: Grade `B+` (Very Good)
- **60% – 69.9%**: Grade `B` (Good)
- **50% – 59.9%**: Grade `C` (Satisfactory)
- **40% – 49.9%**: Grade `D` (Pass)
- **Below 40%**: Grade `F` (Fail)

---

## 🎓 College Viva Q&A Guide

**Q1: Why was Flask and SQLite chosen instead of a heavyweight framework?**
> *Answer*: Flask is lightweight, beginner-friendly, modular, and adheres to WSGI standards without boilerplate bloat. SQLite requires zero server configuration, stores data in a portable self-contained file (`school.db`), and supports standard SQL, transactions, and foreign key cascades.

**Q2: How are duplicate attendance records prevented?**
> *Answer*: The database enforces a `UNIQUE(student_id, date, subject)` constraint. In the application backend, we utilize SQLite's `INSERT ... ON CONFLICT(student_id, date, subject) DO UPDATE SET status = excluded.status` upsert logic, allowing faculty to mark or revise attendance without duplicating rows.

**Q3: How do Chart.js charts receive dynamic data from SQLite?**
> *Answer*: The backend aggregates metric counts using SQL `GROUP BY` and conditional `SUM(CASE WHEN...)` statements, formats the results into structured Python dictionaries, and injects them securely into Jinja2 templates via `tojson`. Chart.js initializes asynchronously using these dynamic payloads.

**Q4: How does dark mode persistence work across browser refreshes?**
> *Answer*: The JavaScript theme manager listens for the toggle event, alters the `data-bs-theme` attribute on the root `<html>` element, and writes the selected state (`dark` or `light`) into browser `localStorage`. When the theme changes, a custom DOM event triggers Chart.js instances to re-render using adjusted grid and text colors.

**Q5: How are SQL injection vulnerabilities prevented?**
> *Answer*: All database queries in `database.py` and domain modules use parameterized queries with `?` placeholders, ensuring user inputs are treated strictly as data literals and never executed as raw SQL commands.

---

## 🧪 Demonstration & Testing Checklist

- [x] Application launches without error on `python app.py`.
- [x] Login with demo credentials (`admin` / `admin123`).
- [x] Dashboard loads with 6 metric cards, 5 charts, at-risk table, and activity feed.
- [x] Enrolled Students directory displays roster with live search and filter options.
- [x] Add a new student and verify profile creation.
- [x] Open a student profile and inspect 360° analytics and charts.
- [x] Mark class attendance using batch toggles ("Mark All Present") and save to SQLite.
- [x] Verify Attendance Log and Compliance Analytics update in real time.
- [x] Record examination marks in Gradebook and verify automatic percentage and grade calculation.
- [x] Generate and test Printable Institutional Reports (print layout and signature blocks).
- [x] Toggle Dark/Light mode and verify clean color transitions.
- [x] Export students and attendance logs to CSV.

---

## 📄 License
This project is developed as an educational Computer Science project and is open source for academic demonstration and enhancement.
