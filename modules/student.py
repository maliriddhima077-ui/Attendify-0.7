# ==============================================================================
# MODULE 1: STUDENT MANAGEMENT & DATABASE MODULE (Member 1)
# Responsibilities: Student CRUD, Data Validation, Search/Filter, Profile Analytics
# ==============================================================================

import re
from backend.database import get_db_connection, log_activity, calculate_grade

# Indian mobile numbers: exactly 10 digits, starting with 6/7/8/9
_PHONE_DIGITS_RE = re.compile(r'^[6-9]\d{9}$')


def normalize_indian_phone(raw):
    """
    Normalize any user-entered value to canonical '+91 XXXXX XXXXX' format.
    Accepts '9876543210', '98765 43210', '+919876543210', '+91 98765 43210'.
    Returns None when the number is not a valid 10-digit Indian mobile.
    """
    if not raw:
        return None
    digits = re.sub(r'\D', '', str(raw))
    # Strip a leading country code if the user pasted it in
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    if not _PHONE_DIGITS_RE.match(digits):
        return None
    return f"+91 {digits[:5]} {digits[5:]}"


# ==============================================================================
# ROLL NUMBER SYSTEM
# Every roll number encodes the student's Class and Division:
#   Class c, Division A -> (c*1000 + 1)   to (c*1000 + 99)    e.g. 3001-3099
#   Class c, Division B -> (c*1000 + 101) to (c*1000 + 199)   e.g. 3101-3199
# ==============================================================================

SCHOOL_CLASSES = [f'Class {i}' for i in range(1, 7)]      # Standards 1-6
SCHOOL_DIVISIONS = ['A', 'B']                              # Exactly two divisions


def _class_number(class_name):
    """'Class 3' -> 3, else None."""
    m = re.match(r'^Class\s+(\d+)$', str(class_name or '').strip())
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 6 else None


def get_roll_range(class_name, division):
    """
    Return (low, high) valid roll bounds for a class section,
    or None when the class/division combination does not exist.
        Class 1 A -> (1001, 1099) ... Class 6 B -> (6101, 6199)
    """
    c = _class_number(class_name)
    if c is None or division not in SCHOOL_DIVISIONS:
        return None
    base = c * 1000 + (0 if division == 'A' else 100)
    return base + 1, base + 99


def build_roll_range_map():
    """Frontend-friendly dict: 'Class 1|A': [1001, 1099], ..."""
    result = {}
    for cls in SCHOOL_CLASSES:
        for div in SCHOOL_DIVISIONS:
            lo, hi = get_roll_range(cls, div)
            result[f'{cls}|{div}'] = [lo, hi]
    return result


def _ensure_roll_ledger(conn):
    """
    Permanent occupancy register. Once a roll number has EVER been assigned
    to a saved student, it is recorded here forever — deleting the student
    does NOT release the number (strict no-reuse rule).
    """
    conn.execute('''
        CREATE TABLE IF NOT EXISTS roll_ledger (
            roll TEXT PRIMARY KEY
        )
    ''')


def _roll_is_occupied(conn, roll_str, exclude_student_id=None):
    """True when the roll is held by a current student OR burned in the ledger."""
    row = conn.execute(
        'SELECT 1 FROM students WHERE roll = ?'
        + (' AND id != ?' if exclude_student_id else ''),
        (roll_str, exclude_student_id) if exclude_student_id else (roll_str,)
    ).fetchone()
    if row:
        return True
    return bool(conn.execute(
        'SELECT 1 FROM roll_ledger WHERE roll = ?', (roll_str,)
    ).fetchone())


def peek_next_roll(class_name, division):
    """
    Non-consuming look at the first FREE roll number inside the section's
    range. A number is occupied if any current student holds it OR it was
    ever assigned in the past (roll_ledger). Opening forms never reserve.
    """
    rng = get_roll_range(class_name, division)
    if not rng:
        return ''
    lo, hi = rng

    conn = get_db_connection()
    _ensure_roll_ledger(conn)
    taken = {row['r'] for row in conn.execute('''
        SELECT CAST(roll AS INTEGER) AS r FROM students
        WHERE CAST(roll AS INTEGER) BETWEEN ? AND ?
    ''', (lo, hi)).fetchall()}
    taken |= {row['r'] for row in conn.execute('''
        SELECT CAST(roll AS INTEGER) AS r FROM roll_ledger
        WHERE CAST(roll AS INTEGER) BETWEEN ? AND ?
    ''', (lo, hi)).fetchall()}
    conn.close()

    for candidate in range(lo, hi + 1):
        if candidate not in taken:
            return str(candidate)
    return ''                      # Section has no free numbers left


def generate_next_roll(class_name, division):
    """Assign the next free roll number within this section's range."""
    suggestion = peek_next_roll(class_name, division)
    if not suggestion:
        raise ValueError(
            f'No free roll numbers left in {class_name} Division {division}.'
        )
    return suggestion


def validate_roll_for_section(roll, class_name, division, exclude_student_id=None):
    """
    Strict backend validation applied before every save/update.
    Returns (ok: bool, error_message: str).

    Check 1 - Correct series : the number must lie inside the exact fixed,
               exclusive range of the selected Class and Division.
    Check 2 - Availability   : the number must not already belong to any
               other student, nor have been assigned historically
               (permanently burned in the ledger).
    Both checks must pass or the student is not saved.
    """
    rng = get_roll_range(class_name, division)
    if not rng:
        return False, 'Please select a valid Class (1-6) and Division (A/B).'
    lo, hi = rng

    roll_str = str(roll or '').strip()
    if not roll_str.isdigit():
        return False, ('Roll number must contain digits only '
                       '(no letters, spaces or symbols).')

    value = int(roll_str)
    if not (lo <= value <= hi):
        return False, (f'Invalid roll number {roll_str} for '
                       f'{class_name} - Division {division}. '
                       f'{roll_str} belongs to another class/division series. '
                       f'The only allowed roll numbers for this section are '
                       f'{lo}-{hi}.')

    conn = get_db_connection()
    _ensure_roll_ledger(conn)
    occupied = _roll_is_occupied(conn, roll_str, exclude_student_id)
    conn.close()

    if occupied:
        return False, (f'Roll number {roll_str} is already assigned to another '
                       f'student. Please choose an available roll number from '
                       f'the valid series.')
    return True, ''


def get_all_students(search=None, class_name=None, division=None, attendance_status=None, performance_grade=None, standard=None):
    """
    Retrieve all students with real-time calculated attendance percentage,
    average performance percentage, and overall grade.
    If standard is provided, filters by class_name (e.g. 'Class 8').
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT 
            s.*,
            COUNT(DISTINCT a.id) as total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) as late_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
            AVG(p.percentage) as avg_performance
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        LEFT JOIN performance p ON s.id = p.student_id
        WHERE 1=1
    '''
    params = []

    if standard and standard.strip():
        query += ' AND s.class_name = ?'
        params.append(standard.strip())

    if class_name and class_name.strip():
        query += ' AND s.class_name = ?'
        params.append(class_name.strip())

    if division and division.strip():
        query += ' AND s.division = ?'
        params.append(division.strip())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += ' AND (s.name LIKE ? OR s.roll LIKE ? OR s.email LIKE ? OR s.phone LIKE ?)'
        params.extend([term, term, term, term])

    query += ' GROUP BY s.id ORDER BY s.class_name ASC, s.roll ASC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    students = []
    for row in rows:
        st = dict(row)
        total = st['total_classes'] or 0
        present = st['present_count'] or 0
        late = st['late_count'] or 0
        absent = st['absent_count'] or 0

        # Calculate effective attendance %: (Present + 0.5 * Late) / Total or standard (Present / Total) * 100
        # Requirement formula: (Present Classes / Total Classes) * 100
        att_pct = round((present / total * 100), 1) if total > 0 else 0.0
        st['attendance_pct'] = att_pct

        if att_pct >= 90:
            st['attendance_category'] = 'Excellent'
            st['attendance_badge'] = 'success'
        elif att_pct >= 75:
            st['attendance_category'] = 'Good'
            st['attendance_badge'] = 'info'
        elif att_pct >= 60:
            st['attendance_category'] = 'Warning'
            st['attendance_badge'] = 'warning'
        else:
            st['attendance_category'] = 'Critical'
            st['attendance_badge'] = 'danger'

        perf_avg = round(st['avg_performance'], 1) if st['avg_performance'] is not None else None
        st['performance_pct'] = perf_avg
        st['performance_grade'] = calculate_grade(perf_avg) if perf_avg is not None else 'N/A'

        # Filter by attendance status if requested
        if attendance_status and attendance_status.strip():
            if st['attendance_category'].lower() != attendance_status.strip().lower():
                continue

        # Filter by performance grade if requested
        if performance_grade and performance_grade.strip():
            if st['performance_grade'] != performance_grade.strip():
                continue

        students.append(st)

    return students


def get_student_by_id(student_id):
    """Fetch single student record by primary key."""
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(student) if student else None


def add_student(data):
    """
    Validate and insert a new student. The roll number must belong to the
    selected Class/Division range (1001-1099 ... 6101-6199) and be unique;
    when left blank it is auto-assigned as the next free number in range.
    Returns (success: bool, message: str, student_id: int/None)
    """
    name = (data.get('name') or '').strip()
    class_name = (data.get('class_name') or '').strip()
    division = (data.get('division') or '').strip()
    email = (data.get('email') or '').strip()
    gender = (data.get('gender') or '').strip()
    dob = (data.get('date_of_birth') or '').strip() or None
    admission_date = (data.get('admission_date') or '').strip() or None

    # Validations
    if not name or not class_name or not division or not email or not gender:
        return False, "Please fill in all required fields (Name, Class, Division, Email, Gender).", None

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "Please enter a valid email address.", None

    # Phone must be a valid 10-digit Indian mobile number
    phone_norm = normalize_indian_phone(data.get('phone'))
    if not phone_norm:
        return False, "Please enter a valid 10-digit Indian mobile number (e.g. 9876543210).", None

    # Roll number: validate user entry, or auto-assign the next free slot
    roll = (data.get('roll') or '').strip()
    if roll:
        ok, err = validate_roll_for_section(roll, class_name, division)
        if not ok:
            return False, err, None
    else:
        roll = generate_next_roll(class_name, division)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO students (
                name, roll, class_name, division, email, phone,
                date_of_birth, gender, admission_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, roll, class_name, division, email, phone_norm,
              dob, gender, admission_date))
        new_id = cursor.lastrowid          # capture BEFORE any other statements

        # Burn this roll permanently: even if the student is deleted later,
        # the number can never be assigned to anyone else.
        _ensure_roll_ledger(cursor)
        cursor.execute('INSERT OR IGNORE INTO roll_ledger (roll) VALUES (?)', (roll,))

        conn.commit()
        conn.close()

        log_activity("Student Added",
                     f"Enrolled new student: {name} (Roll: {roll}, {class_name}-{division})")
        return True, f"Student registered successfully with Roll Number {roll}.", new_id
    except Exception as e:
        conn.close()
        if 'UNIQUE' in str(e):
            return False, (f"Roll number {roll} is already assigned to another "
                           f"student. Please choose an available roll number "
                           f"from the valid series."), None
        return False, f"Database error: {str(e)}", None


def update_student(student_id, data):
    """
    Validate and update an existing student record.
    The roll number is system-generated and can never be changed here.
    Returns (success: bool, message: str)
    """
    name = (data.get('name') or '').strip()
    class_name = (data.get('class_name') or '').strip()
    division = (data.get('division') or '').strip()
    email = (data.get('email') or '').strip()
    gender = (data.get('gender') or '').strip()
    dob = (data.get('date_of_birth') or '').strip() or None
    admission_date = (data.get('admission_date') or '').strip() or None
    status = (data.get('status') or 'Active').strip()

    if not name or not class_name or not division or not email or not gender:
        return False, "Please fill in all required fields."

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "Please enter a valid email address."

    # Phone must be a valid 10-digit Indian mobile number
    phone_norm = normalize_indian_phone(data.get('phone'))
    if not phone_norm:
        return False, "Please enter a valid 10-digit Indian mobile number (e.g. 9876543210)."

    conn = get_db_connection()
    cursor = conn.cursor()

    # Roll number is immutable: always keep the stored value
    existing = cursor.execute(
        'SELECT roll FROM students WHERE id = ?', (student_id,)
    ).fetchone()
    if not existing:
        conn.close()
        return False, "Student not found."
    roll = existing['roll']

    # A roll number encodes its section: reject class/division changes that
    # would leave the stored roll outside the new section's valid range.
    rng = get_roll_range(class_name, division)
    if rng and roll.isdigit():
        lo, hi = rng
        if not (lo <= int(roll) <= hi):
            conn.close()
            return False, (f'Roll number {roll} does not belong to '
                           f'{class_name} - Division {division}. '
                           f'The valid range for that section is {lo}-{hi}. '
                           'Roll numbers cannot be moved between sections.')

    try:
        cursor.execute('''
            UPDATE students 
            SET name = ?, class_name = ?, division = ?, email = ?, 
                phone = ?, date_of_birth = ?, gender = ?, admission_date = ?, status = ?
            WHERE id = ?
        ''', (name, class_name, division, email, phone_norm,
              dob, gender, admission_date, status, student_id))
        conn.commit()
        conn.close()

        log_activity("Student Updated", f"Updated student profile: {name} ({roll})")
        return True, "Student details updated successfully."
    except Exception as e:
        conn.close()
        return False, f"Database error: {str(e)}"


def delete_student(student_id):
    """
    Delete a student and all related attendance/performance records.
    The roll number is deliberately NOT released: it stays burned in
    roll_ledger and can never be assigned to any future student.
    """
    student = get_student_by_id(student_id)
    if not student:
        return False, "Student not found."

    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM performance WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        # NOTE: roll_ledger row intentionally kept — strict no-reuse rule.
        conn.commit()
        conn.close()

        log_activity("Student Deleted", f"Removed student: {student['name']} ({student['roll']})")
        return True, f"Student '{student['name']}' was successfully deleted."
    except Exception as e:
        conn.close()
        return False, f"Failed to delete student: {str(e)}"


def get_student_profile_data(student_id):
    """
    Compile complete 360-degree analytics dossier for a student.
    Includes profile info, attendance breakdown, subject-wise attendance,
    subject-wise performance, grades, and historical logs.
    """
    student = get_student_by_id(student_id)
    if not student:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Attendance Aggregates
    cursor.execute('''
        SELECT 
            COUNT(*) as total_classes,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
            SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) as late_count
        FROM attendance
        WHERE student_id = ?
    ''', (student_id,))
    att_agg = dict(cursor.fetchone())
    total_att = att_agg['total_classes'] or 0
    present_att = att_agg['present_count'] or 0
    absent_att = att_agg['absent_count'] or 0
    late_att = att_agg['late_count'] or 0

    att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0.0

    # 2. Subject-wise attendance
    cursor.execute('''
        SELECT 
            subject,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent,
            SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) as late
        FROM attendance
        WHERE student_id = ?
        GROUP BY subject
        ORDER BY subject ASC
    ''', (student_id,))
    subject_attendance = []
    for row in cursor.fetchall():
        sub_row = dict(row)
        s_total = sub_row['total'] or 0
        s_pres = sub_row['present'] or 0
        sub_row['pct'] = round((s_pres / s_total * 100), 1) if s_total > 0 else 0.0
        subject_attendance.append(sub_row)

    # 3. Subject-wise performance
    cursor.execute('''
        SELECT * FROM performance
        WHERE student_id = ?
        ORDER BY subject ASC
    ''', (student_id,))
    performance_records = [dict(r) for r in cursor.fetchall()]

    perf_count = len(performance_records)
    avg_marks = round(sum(p['total_marks'] for p in performance_records) / perf_count, 1) if perf_count > 0 else 0.0
    avg_percentage = round(sum(p['percentage'] for p in performance_records) / perf_count, 1) if perf_count > 0 else 0.0
    overall_grade = calculate_grade(avg_percentage) if perf_count > 0 else 'N/A'

    # 4. Recent Attendance Log (last 15 records)
    cursor.execute('''
        SELECT * FROM attendance
        WHERE student_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 15
    ''', (student_id,))
    recent_attendance = [dict(r) for r in cursor.fetchall()]

    conn.close()

    # Risk level determination
    if att_pct >= 90:
        risk_level = "Safe"
        risk_color = "success"
    elif att_pct >= 75:
        risk_level = "Moderate"
        risk_color = "info"
    elif att_pct >= 60:
        risk_level = "Warning"
        risk_color = "warning"
    else:
        risk_level = "Critical"
        risk_color = "danger"

    return {
        'student': student,
        'attendance': {
            'total_classes': total_att,
            'present': present_att,
            'absent': absent_att,
            'late': late_att,
            'percentage': att_pct,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'subject_breakdown': subject_attendance,
            'recent_history': recent_attendance
        },
        'performance': {
            'total_subjects': perf_count,
            'avg_marks': avg_marks,
            'avg_percentage': avg_percentage,
            'overall_grade': overall_grade,
            'records': performance_records
        }
    }


def get_distinct_classes():
    """
    Canonical list of the school's classes: exactly Standards 1-6.
    Returns the fixed school structure (never DB-derived), so dropdowns
    always show Class 1..Class 6 with no duplicates.
    """
    return list(SCHOOL_CLASSES)


def get_distinct_divisions():
    """
    Canonical list of divisions: exactly A and B.
    Returns the fixed school structure (never DB-derived), so dropdowns
    always show Section A and Section B with no duplicates.
    """
    return list(SCHOOL_DIVISIONS)
