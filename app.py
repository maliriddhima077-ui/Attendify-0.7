import os
import csv
import io
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, make_response
)
from werkzeug.security import check_password_hash

from backend.database import (
    init_db, get_db_connection, seed_sample_data, reset_data,
    log_activity, get_recent_activities
)
from modules.student import (
    get_all_students, get_student_by_id, add_student,
    update_student, delete_student, get_student_profile_data,
    get_distinct_classes, get_distinct_divisions
)
from modules.attendance import (
    get_attendance_sheet, save_batch_attendance,
    get_attendance_history, get_attendance_analysis,
    get_distinct_subjects
)
from modules.performance import (
    get_all_performance, add_performance_record,
    update_performance_record, delete_performance_record,
    get_performance_analysis
)
from modules.dashboard import (
    get_dashboard_metrics, get_dashboard_charts_data,
    get_at_risk_students
)
from modules.reports import (
    generate_attendance_report, generate_performance_report,
    generate_student_dossier, generate_class_summary_report,
    get_system_settings
)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'attendify-secret-key-cs-college-project-2026')
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 1 day


def login_required(f):
    """Decorator to enforce session authentication on protected endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_scope():
    """
    Resolve the data-access scope for the current session user.
    - Principal -> ('', '') meaning unrestricted school-wide access.
    - Class Teacher -> (standard, division) restricting every query to 8A-style section.
    """
    if session.get('role') == 'Principal':
        return '', ''
    return session.get('standard', ''), session.get('division', '')


def is_principal():
    """True when the logged-in user holds the Principal role."""
    return session.get('role') == 'Principal'


def teacher_guard(f):
    """
    Decorator for detail-level routes (profile/edit/delete).
    Verifies the target record belongs to the teacher's assigned class.
    The wrapped function must accept (student_class, student_division) info via kwargs.
    Usage: decorate route, then call check_student_access(student_id) inside.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def check_student_access(student):
    """
    Ensure the current user may view/manage the given student record.
    Returns True when allowed; otherwise flashes an error and redirects.
    """
    if is_principal() or not student:
        return True
    t_standard, t_division = get_scope()
    if student.get('class_name') == t_standard and student.get('division') == t_division:
        return True
    flash("Access denied: this student does not belong to your assigned class.", "danger")
    return False


@app.context_processor
def inject_global_context():
    """Make common variables accessible to all templates."""
    settings = get_system_settings()
    return {
        'current_year': datetime.now().year,
        'system_settings': settings,
        'app_name': 'Attendify'
    }


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def index():
    """Root redirect."""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Administrator / Teacher authentication endpoint."""
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            standard_val = user['standard'] if user['standard'] else ''
            division_val = user['division'] if user['division'] else ''
            session['standard'] = standard_val
            session['division'] = division_val

            log_activity("User Login", f"User '{username}' logged in successfully.", user=user['full_name'])
            flash(f"Welcome back, {user['full_name']}!", "success")

            # Role-based redirect
            if user['role'] == 'Principal':
                next_url = request.args.get('next')
                return redirect(next_url or url_for('dashboard'))
            else:
                # Teacher - redirect to their class dashboard
                return redirect(url_for('teacher_dashboard'))
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Sign out user and destroy active session."""
    user_name = session.get('full_name', 'User')
    session.clear()
    flash(f"You have been signed out successfully.", "info")
    return redirect(url_for('login'))


# ==========================================
# DASHBOARD & ANALYTICS
# ==========================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main administrative analytics command center (Principal only)."""
    # Principal has school-wide access; Teachers redirect to their class dashboard
    if not is_principal():
        return redirect(url_for('teacher_dashboard'))

    metrics = get_dashboard_metrics()
    charts_data = get_dashboard_charts_data()
    at_risk_students = get_at_risk_students(threshold=75.0, limit=6)
    recent_activities = get_recent_activities(limit=6)

    return render_template(
        'dashboard.html',
        metrics=metrics,
        charts_data=charts_data,
        at_risk_students=at_risk_students,
        recent_activities=recent_activities
    )


@app.route('/teacher-dashboard')
@login_required
def teacher_dashboard():
    """Teacher dashboard showing only their assigned class."""
    standard = session.get('standard')
    division = session.get('division')
    
    if not standard or not division:
        flash("Your assignment is not configured. Please contact the Administrator.", "danger")
        return redirect(url_for('logout'))
    
    # Get metrics filtered by this teacher's class
    metrics = get_dashboard_metrics(standard=standard, division=division)
    charts_data = get_dashboard_charts_data(standard=standard, division=division)
    at_risk_students = get_at_risk_students(threshold=75.0, limit=6, standard=standard, division=division)
    recent_activities = get_recent_activities(limit=6)
    
    return render_template(
        'teacher_dashboard.html',
        metrics=metrics,
        charts_data=charts_data,
        at_risk_students=at_risk_students,
        recent_activities=recent_activities,
        standard=standard,
        division=division
    )


# ==========================================
# STUDENT MANAGEMENT ROUTES
# ==========================================

@app.route('/students')
@login_required
def students_list():
    """Display student directory with filtering and search."""
    search = request.args.get('search', '')
    att_status = request.args.get('attendance_status', '')
    perf_grade = request.args.get('performance_grade', '')

    # Teachers are hard-locked to their assigned class section
    t_standard, t_division = get_scope()
    if t_standard:
        class_name = t_standard
        division = t_division
        classes = [t_standard]
        divisions = [t_division]
    else:
        class_name = request.args.get('class_name', '')
        division = request.args.get('division', '')
        classes = get_distinct_classes()
        divisions = get_distinct_divisions()

    students = get_all_students(
        search=search,
        class_name=class_name,
        division=division,
        attendance_status=att_status,
        performance_grade=perf_grade
    )

    return render_template(
        'students.html',
        students=students,
        classes=classes,
        divisions=divisions,
        search=search,
        selected_class=class_name,
        selected_division=division,
        selected_att_status=att_status,
        selected_grade=perf_grade
    )


@app.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student_view():
    """Add a new student profile."""
    from modules.student import build_roll_range_map

    t_standard, t_division = get_scope()
    if t_standard:
        # Teachers may only enroll students into their own class section
        classes = [t_standard]
        divisions = [t_division]
    else:
        classes = get_distinct_classes()
        divisions = get_distinct_divisions()

    # Frontend copy of every section's valid roll range (for live validation)
    roll_ranges = build_roll_range_map()

    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'roll': request.form.get('roll'),
            'class_name': t_standard or request.form.get('class_name'),
            'division': t_division or request.form.get('division'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'date_of_birth': request.form.get('date_of_birth'),
            'gender': request.form.get('gender'),
            'admission_date': request.form.get('admission_date')
        }

        success, msg, new_id = add_student(data)
        if success:
            flash(msg, "success")
            return redirect(url_for('student_profile', student_id=new_id))
        else:
            flash(msg, "danger")
            return render_template('add_student.html', classes=classes,
                                   divisions=divisions, form_data=data,
                                   roll_ranges=roll_ranges)

    return render_template('add_student.html', classes=classes,
                           divisions=divisions, form_data={},
                           roll_ranges=roll_ranges)


@app.route('/api/next-roll')
@login_required
def api_next_roll():
    """Suggest the first free roll number inside a section's valid range."""
    from modules.student import peek_next_roll, get_roll_range

    class_name = request.args.get('class_name', '')
    division = request.args.get('division', '')
    if not get_roll_range(class_name, division):
        return jsonify({'roll': None,
                        'message': 'Invalid class or division selected.'}), 400
    return jsonify({'roll': peek_next_roll(class_name, division)})


@app.route('/students/<int:student_id>')
@login_required
def student_profile(student_id):
    """360-degree student analytical profile."""
    profile_data = get_student_profile_data(student_id)
    if not profile_data:
        flash("Student not found.", "danger")
        return redirect(url_for('students_list'))

    if not check_student_access(profile_data['student']):
        return redirect(url_for('students_list'))

    return render_template('student_profile.html', profile=profile_data)


@app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student_view(student_id):
    """Edit student profile."""
    from modules.student import build_roll_range_map

    student = get_student_by_id(student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for('students_list'))

    if not check_student_access(student):
        return redirect(url_for('students_list'))

    t_standard, t_division = get_scope()
    if t_standard:
        classes = [t_standard]
        divisions = [t_division]
    else:
        classes = get_distinct_classes()
        divisions = get_distinct_divisions()

    roll_ranges = build_roll_range_map()

    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'roll': request.form.get('roll'),
            'class_name': t_standard or request.form.get('class_name'),
            'division': t_division or request.form.get('division'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'date_of_birth': request.form.get('date_of_birth'),
            'gender': request.form.get('gender'),
            'admission_date': request.form.get('admission_date'),
            'status': request.form.get('status', 'Active')
        }

        success, msg = update_student(student_id, data)
        if success:
            flash(msg, "success")
            return redirect(url_for('student_profile', student_id=student_id))
        else:
            flash(msg, "danger")
            return render_template('edit_student.html', student=data, student_id=student_id,
                                   classes=classes, divisions=divisions, roll_ranges=roll_ranges)

    return render_template('edit_student.html', student=student, student_id=student_id,
                           classes=classes, divisions=divisions, roll_ranges=roll_ranges)


@app.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
def delete_student_view(student_id):
    """Delete a student and cascading records."""
    student = get_student_by_id(student_id)
    if not check_student_access(student):
        return redirect(url_for('students_list'))

    success, msg = delete_student(student_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('students_list'))


# ==========================================
# ATTENDANCE MANAGEMENT ROUTES
# ==========================================

@app.route('/attendance')
@login_required
def attendance_view():
    """Attendance marking sheet."""
    t_standard, t_division = get_scope()
    if t_standard:
        classes = [t_standard]
        divisions = [t_division]
    else:
        classes = get_distinct_classes()
        divisions = get_distinct_divisions()
    subjects = get_distinct_subjects()

    selected_class = t_standard or request.args.get('class_name', classes[0] if classes else 'FYCS')
    selected_div = t_division or request.args.get('division', divisions[0] if divisions else 'A')
    selected_sub = request.args.get('subject', subjects[0] if subjects else 'Computer Science')
    selected_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))

    students_sheet = get_attendance_sheet(selected_class, selected_div, selected_sub, selected_date)

    return render_template(
        'attendance.html',
        classes=classes,
        divisions=divisions,
        subjects=subjects,
        selected_class=selected_class,
        selected_division=selected_div,
        selected_subject=selected_sub,
        selected_date=selected_date,
        students_sheet=students_sheet
    )


@app.route('/attendance/save', methods=['POST'])
@login_required
def save_attendance():
    """Process and save batch attendance form submission."""
    date_str = request.form.get('date')
    subject = request.form.get('subject')
    class_name = request.form.get('class_name')
    division = request.form.get('division')

    # Teachers may only save attendance for their own assigned section
    t_standard, t_division = get_scope()
    if t_standard and (class_name != t_standard or division != t_division):
        flash("Access denied: you can only manage attendance for your assigned class.", "danger")
        return redirect(url_for('attendance_view'))

    attendance_dict = {}
    for key, value in request.form.items():
        if key.startswith('attendance_'):
            s_id = key.replace('attendance_', '')
            attendance_dict[s_id] = value

    # Verify every submitted student actually belongs to the target class
    conn = get_db_connection()
    placeholders = ','.join('?' for _ in attendance_dict)
    valid_rows = conn.execute(
        f'SELECT id FROM students WHERE id IN ({placeholders}) AND class_name = ? AND division = ?',
        list(attendance_dict.keys()) + [class_name, division]
    ).fetchall() if attendance_dict else []
    conn.close()
    valid_ids = {str(r['id']) for r in valid_rows}
    attendance_dict = {k: v for k, v in attendance_dict.items() if k in valid_ids}

    success, msg, count = save_batch_attendance(
        date_str=date_str,
        subject=subject,
        class_name=class_name,
        division=division,
        attendance_dict=attendance_dict
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for(
        'attendance_view',
        class_name=class_name,
        division=division,
        subject=subject,
        date=date_str
    ))


@app.route('/attendance/history')
@login_required
def attendance_history():
    """Comprehensive attendance history log with multi-filters."""
    t_standard, t_division = get_scope()
    if t_standard:
        classes = [t_standard]
        divisions = [t_division]
    else:
        classes = get_distinct_classes()
        divisions = get_distinct_divisions()
    subjects = get_distinct_subjects()

    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    subject = request.args.get('subject', '')
    status = request.args.get('status', '')
    search = request.args.get('search', '')

    class_name = t_standard or request.args.get('class_name', '')
    division = t_division or request.args.get('division', '')

    history_records = get_attendance_history(
        date_from=date_from,
        date_to=date_to,
        class_name=class_name,
        division=division,
        subject=subject,
        status=status,
        search=search
    )

    return render_template(
        'attendance_history.html',
        records=history_records,
        classes=classes,
        divisions=divisions,
        subjects=subjects,
        date_from=date_from,
        date_to=date_to,
        selected_class=class_name,
        selected_division=division,
        selected_subject=subject,
        selected_status=status,
        search=search
    )


@app.route('/attendance/analysis')
@login_required
def attendance_analysis():
    """Dedicated attendance analytics dashboard with progress meters."""
    t_standard, t_division = get_scope()
    if t_standard:
        classes = [t_standard]
        divisions = [t_division]
    else:
        classes = get_distinct_classes()
        divisions = get_distinct_divisions()
    subjects = get_distinct_subjects()

    subject = request.args.get('subject', '')
    class_name = t_standard or request.args.get('class_name', '')
    division = t_division or request.args.get('division', '')

    analysis_data = get_attendance_analysis(
        class_name=class_name,
        division=division,
        subject=subject
    )

    return render_template(
        'attendance_analysis.html',
        analysis=analysis_data,
        classes=classes,
        divisions=divisions,
        subjects=subjects,
        selected_class=class_name,
        selected_division=division,
        selected_subject=subject
    )


# ==========================================
# PERFORMANCE MANAGEMENT ROUTES
# ==========================================

@app.route('/performance')
@login_required
def performance_list():
    """Academic gradebook displaying all student marks."""
    t_standard, t_division = get_scope()
    if t_standard:
        classes = [t_standard]
    else:
        classes = get_distinct_classes()
    subjects = get_distinct_subjects()

    semester = request.args.get('semester', '')
    subject = request.args.get('subject', '')
    search = request.args.get('search', '')

    class_name = t_standard or request.args.get('class_name', '')
    division = t_division or ''

    records = get_all_performance(
        class_name=class_name,
        division=division,
        semester=semester,
        subject=subject,
        search=search
    )

    return render_template(
        'performance.html',
        records=records,
        classes=classes,
        subjects=subjects,
        selected_class=class_name,
        selected_semester=semester,
        selected_subject=subject,
        search=search
    )


@app.route('/performance/add', methods=['GET', 'POST'])
@login_required
def add_performance_view():
    """Record student exam & internal assessment scores."""
    t_standard, t_division = get_scope()
    students = get_all_students(class_name=t_standard or None, division=t_division or None)
    subjects = get_distinct_subjects()
    semesters = ["Term 1 (Midterm)", "Term 2 (Final)", "Unit Test 1", "Unit Test 2", "Annual Exam"]
    prefilled_student_id = request.args.get('student_id', type=int)

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        subject = request.form.get('subject')
        internal_marks = request.form.get('internal_marks')
        external_marks = request.form.get('external_marks')
        semester = request.form.get('semester')

        # Teachers may only record marks for their own class students
        allowed = True
        if t_standard:
            st = get_student_by_id(student_id)
            if not st or st['class_name'] != t_standard or st['division'] != t_division:
                flash("Access denied: you can only record marks for students in your assigned class.", "danger")
                allowed = False

        success, msg, new_id = (False, "Access denied.", None)
        if allowed:
            success, msg, new_id = add_performance_record(
                student_id=student_id,
                subject=subject,
                internal_marks=internal_marks,
                external_marks=external_marks,
                semester=semester
            )

        if success:
            flash(msg, "success")
            return redirect(url_for('performance_list'))
        else:
            flash(msg, "danger")

    return render_template(
        'add_performance.html',
        students=students,
        subjects=subjects,
        semesters=semesters,
        prefilled_student_id=prefilled_student_id
    )


@app.route('/performance/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_performance_view(record_id):
    """Edit existing exam marks record."""
    conn = get_db_connection()
    record = conn.execute('''
        SELECT p.*, s.name as student_name, s.roll, s.class_name, s.division 
        FROM performance p 
        JOIN students s ON p.student_id = s.id 
        WHERE p.id = ?
    ''', (record_id,)).fetchone()
    conn.close()

    if not record:
        flash("Performance record not found.", "danger")
        return redirect(url_for('performance_list'))

    if not check_student_access(dict(record)):
        return redirect(url_for('performance_list'))

    subjects = get_distinct_subjects()
    semesters = ["Term 1 (Midterm)", "Term 2 (Final)", "Unit Test 1", "Unit Test 2", "Annual Exam"]

    if request.method == 'POST':
        subject = request.form.get('subject')
        internal_marks = request.form.get('internal_marks')
        external_marks = request.form.get('external_marks')
        semester = request.form.get('semester')

        success, msg = update_performance_record(
            record_id=record_id,
            subject=subject,
            internal_marks=internal_marks,
            external_marks=external_marks,
            semester=semester
        )

        if success:
            flash(msg, "success")
            return redirect(url_for('performance_list'))
        else:
            flash(msg, "danger")

    return render_template(
        'edit_performance.html',
        record=dict(record),
        subjects=subjects,
        semesters=semesters
    )


@app.route('/performance/<int:record_id>/delete', methods=['POST'])
@login_required
def delete_performance_view(record_id):
    """Delete a marks entry."""
    conn = get_db_connection()
    record = conn.execute('''
        SELECT p.*, s.class_name, s.division
        FROM performance p
        JOIN students s ON p.student_id = s.id
        WHERE p.id = ?
    ''', (record_id,)).fetchone()
    conn.close()

    if not check_student_access(dict(record) if record else None):
        return redirect(url_for('performance_list'))

    success, msg = delete_performance_record(record_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('performance_list'))


@app.route('/performance/analysis')
@login_required
def performance_analysis():
    """Dedicated academic performance analytics dashboard."""
    t_standard, t_division = get_scope()
    if t_standard:
        classes = [t_standard]
    else:
        classes = get_distinct_classes()
    subjects = get_distinct_subjects()
    semesters = ["Term 1 (Midterm)", "Term 2 (Final)", "Unit Test 1", "Unit Test 2", "Annual Exam"]

    semester = request.args.get('semester', '')
    subject = request.args.get('subject', '')
    class_name = t_standard or request.args.get('class_name', '')
    division = t_division or ''

    analysis_data = get_performance_analysis(
        class_name=class_name or None,
        division=division or None,
        semester=semester,
        subject=subject
    )

    return render_template(
        'performance_analysis.html',
        analysis=analysis_data,
        classes=classes,
        subjects=subjects,
        semesters=semesters,
        selected_class=class_name,
        selected_semester=semester,
        selected_subject=subject
    )


# ==========================================
# REPORT GENERATION & PRINT VIEW ROUTES
# ==========================================

@app.route('/reports')
@login_required
def reports_hub():
    """Report configuration center."""
    t_standard, t_division = get_scope()
    if t_standard:
        classes = [t_standard]
        divisions = [t_division]
        students = get_all_students(class_name=t_standard, division=t_division)
    else:
        classes = get_distinct_classes()
        divisions = get_distinct_divisions()
        students = get_all_students()
    subjects = get_distinct_subjects()
    semesters = ["Term 1 (Midterm)", "Term 2 (Final)", "Unit Test 1", "Unit Test 2", "Annual Exam"]

    return render_template(
        'reports.html',
        classes=classes,
        divisions=divisions,
        subjects=subjects,
        students=students,
        semesters=semesters
    )


@app.route('/reports/attendance')
@login_required
def report_attendance():
    """Generate printable attendance report."""
    t_standard, t_division = get_scope()
    class_name = t_standard or request.args.get('class_name')
    division = t_division or request.args.get('division')
    subject = request.args.get('subject')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    report_data = generate_attendance_report(
        class_name=class_name,
        division=division,
        subject=subject,
        date_from=date_from,
        date_to=date_to
    )
    return render_template('report_view.html', report=report_data)


@app.route('/reports/performance')
@login_required
def report_performance():
    """Generate printable performance analysis report."""
    t_standard, t_division = get_scope()
    class_name = t_standard or request.args.get('class_name')
    division = t_division or request.args.get('division')
    semester = request.args.get('semester')
    subject = request.args.get('subject')

    report_data = generate_performance_report(
        class_name=class_name or None,
        division=division or None,
        semester=semester,
        subject=subject
    )
    return render_template('report_view.html', report=report_data)


@app.route('/reports/student/<int:student_id>')
@login_required
def report_student(student_id):
    """Generate printable single-student comprehensive dossier."""
    profile_data = get_student_profile_data(student_id)
    if not profile_data:
        flash("Student dossier could not be generated.", "danger")
        return redirect(url_for('reports_hub'))

    if not check_student_access(profile_data['student']):
        return redirect(url_for('reports_hub'))

    report_data = generate_student_dossier(student_id)
    return render_template('report_view.html', report=report_data)


@app.route('/reports/class-summary')
@login_required
def report_class_summary():
    """Generate printable class batch summary report."""
    t_standard, t_division = get_scope()
    class_name = t_standard or request.args.get('class_name', 'FYCS')
    division = t_division or request.args.get('division')

    report_data = generate_class_summary_report(class_name=class_name, division=division)
    return render_template('report_view.html', report=report_data)


# ==========================================
# CSV EXPORT ROUTES
# ==========================================

@app.route('/reports/export/students-csv')
@login_required
def export_students_csv():
    """Export student roster to CSV (scoped to teacher's class when applicable)."""
    t_standard, t_division = get_scope()
    students = get_all_students(
        class_name=t_standard or None,
        division=t_division or None
    )
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Student ID', 'Full Name', 'Roll Number', 'Class', 'Division', 'Email', 'Phone', 'Gender', 'Attendance %', 'Performance %', 'Grade', 'Status'])
    
    for s in students:
        cw.writerow([
            s['id'], s['name'], s['roll'], s['class_name'], s['division'],
            s['email'], s['phone'], s['gender'], f"{s['attendance_pct']}%",
            f"{s['performance_pct']}%" if s['performance_pct'] is not None else 'N/A',
            s['performance_grade'], s.get('status', 'Active')
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=attendify_students_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@app.route('/reports/export/attendance-csv')
@login_required
def export_attendance_csv():
    """Export attendance history records to CSV (scoped for teachers)."""
    t_standard, t_division = get_scope()
    records = get_attendance_history(
        limit=5000,
        class_name=t_standard or None,
        division=t_division or None
    )
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Record ID', 'Date', 'Roll Number', 'Student Name', 'Class', 'Division', 'Subject', 'Attendance Status'])
    
    for r in records:
        cw.writerow([
            r['id'], r['date'], r['roll'], r['student_name'],
            r['class_name'], r['division'], r['subject'], r['status']
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=attendify_attendance_log.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# ==========================================
# SETTINGS & SAMPLE DATA MANAGEMENT
# ==========================================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_view():
    """Manage institution settings and demo data. Principal access only."""
    if not is_principal():
        flash("Access denied: only the Principal can modify system settings.", "danger")
        return redirect(url_for('teacher_dashboard') if session.get('role') != 'Principal' else url_for('dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_settings':
            name = request.form.get('institution_name', '').strip()
            threshold = float(request.form.get('attendance_threshold', 75.0))
            year = request.form.get('academic_year', '').strip()
            dept = request.form.get('department', '').strip()
            email = request.form.get('contact_email', '').strip()

            conn = get_db_connection()
            conn.execute('''
                UPDATE settings
                SET institution_name = ?, attendance_threshold = ?, academic_year = ?, department = ?, contact_email = ?
                WHERE id = 1
            ''', (name, threshold, year, dept, email))
            conn.commit()
            conn.close()

            log_activity("Settings Updated", "Updated institutional configuration parameters.")
            flash("System settings updated successfully.", "success")

        elif action == 'seed_demo':
            seed_sample_data()
            flash("Demo dataset loaded successfully with realistic students, attendance, and exam marks!", "success")

        elif action == 'reset_data':
            reset_data()
            flash("All student records, attendance, and performance logs have been cleared.", "warning")

        return redirect(url_for('settings_view'))

    settings = get_system_settings()
    return render_template('settings.html', settings=settings)


# ==========================================
# API JSON ENDPOINTS
# ==========================================

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """JSON API for dashboard metrics (scoped to teacher's class)."""
    t_standard, t_division = get_scope()
    return jsonify(get_dashboard_metrics(standard=t_standard or None, division=t_division or None))


@app.route('/api/chart-data')
@login_required
def api_chart_data():
    """JSON API providing structured Chart.js series (scoped for teachers)."""
    t_standard, t_division = get_scope()
    return jsonify(get_dashboard_charts_data(standard=t_standard or None, division=t_division or None))


# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error page."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Custom 500 error page."""
    return render_template('500.html', error=str(e)), 500


# ==========================================
# APPLICATION STARTUP
# ==========================================

if __name__ == '__main__':
    # Initialize SQLite database and tables automatically on startup
    init_db()
    print("==================================================================")
    print(" Attendify — Primary School Attendance & Performance System")
    print(" Standards 1-6 | Divisions A & B")
    print(" Server running at: http://127.0.0.1:10000")
    print(" Principal Login:      admin      / admin123")
    print(" Class Teacher (3-A):  teacher3a  / teach123")
    print("==================================================================")
    app.run(debug=True, host='127.0.0.1', port=7070)
