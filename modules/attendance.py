# ==============================================================================
# MODULE 2: ATTENDANCE MANAGEMENT MODULE (Member 2)
# Responsibilities: Class Attendance Register, Batch Upsert, History Log,
#                   Attendance Formula Calculation & Threshold Categorization
# ==============================================================================

from datetime import datetime
from backend.database import get_db_connection, log_activity


def get_attendance_sheet(class_name, division, subject, date_str):
    """
    Retrieve students in a given class and division, along with any existing
    attendance status recorded for the specified date and subject.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT 
            s.id, s.name, s.roll, s.class_name, s.division,
            a.status as recorded_status,
            a.id as attendance_id
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ? AND a.subject = ?
        WHERE s.class_name = ? AND s.division = ?
        ORDER BY s.roll ASC
    '''
    cursor.execute(query, (date_str, subject, class_name, division))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        # Default to 'Present' if no record has been created yet
        item['status'] = item['recorded_status'] if item['recorded_status'] else 'Present'
        result.append(item)

    return result


def save_batch_attendance(date_str, subject, class_name, division, attendance_dict):
    """
    Save or update attendance for multiple students atomically.
    attendance_dict: { 'student_id': 'Present' | 'Absent' | 'Late', ... }
    """
    if not date_str or not subject:
        return False, "Date and Subject are mandatory.", 0

    if not attendance_dict:
        return False, "No student attendance data submitted.", 0

    conn = get_db_connection()
    cursor = conn.cursor()

    records = []
    for student_id_str, status in attendance_dict.items():
        try:
            s_id = int(student_id_str)
            if status in ['Present', 'Absent', 'Late']:
                records.append((s_id, date_str, status, subject))
        except ValueError:
            continue

    if not records:
        conn.close()
        return False, "No valid attendance entries found.", 0

    try:
        cursor.executemany('''
            INSERT INTO attendance (student_id, date, status, subject)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id, date, subject) DO UPDATE SET
                status = excluded.status,
                created_at = CURRENT_TIMESTAMP
        ''', records)
        conn.commit()
        count = len(records)
        conn.close()

        log_activity("Attendance Marked", f"Saved attendance for {count} students in {class_name}-{division} ({subject}, Date: {date_str})")
        return True, f"Attendance saved successfully for {count} students.", count
    except Exception as e:
        conn.close()
        return False, f"Failed to save attendance: {str(e)}", 0


def get_attendance_history(date_from=None, date_to=None, student_id=None, class_name=None, division=None, subject=None, status=None, search=None, limit=500):
    """
    Retrieve historical attendance logs matching optional filter criteria.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT 
            a.id, a.date, a.status, a.subject, a.created_at,
            s.id as student_id, s.name as student_name, s.roll, s.class_name, s.division, s.email
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    '''
    params = []

    if date_from and date_from.strip():
        query += ' AND a.date >= ?'
        params.append(date_from.strip())

    if date_to and date_to.strip():
        query += ' AND a.date <= ?'
        params.append(date_to.strip())

    if student_id:
        query += ' AND s.id = ?'
        params.append(student_id)

    if class_name and class_name.strip():
        query += ' AND s.class_name = ?'
        params.append(class_name.strip())

    if division and division.strip():
        query += ' AND s.division = ?'
        params.append(division.strip())

    if subject and subject.strip():
        query += ' AND a.subject = ?'
        params.append(subject.strip())

    if status and status.strip():
        query += ' AND a.status = ?'
        params.append(status.strip())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += ' AND (s.name LIKE ? OR s.roll LIKE ? OR a.subject LIKE ?)'
        params.extend([term, term, term])

    query += ' ORDER BY a.date DESC, a.id DESC LIMIT ?'
    params.append(limit)

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_attendance_analysis(class_name=None, division=None, subject=None):
    """
    Calculate high-level attendance metrics and student-by-student attendance breakdown.
    Categories:
    - Excellent: 90%+
    - Good: 75–89%
    - Warning: 60–74%
    - Critical: Below 60%
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT 
            s.id as student_id,
            s.name,
            s.roll,
            s.class_name,
            s.division,
            s.email,
            COUNT(a.id) as total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
            SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) as late_count
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
    '''
    where_clauses = []
    params = []

    if class_name and class_name.strip():
        where_clauses.append('s.class_name = ?')
        params.append(class_name.strip())

    if division and division.strip():
        where_clauses.append('s.division = ?')
        params.append(division.strip())

    if subject and subject.strip():
        where_clauses.append('(a.subject = ? OR a.subject IS NULL)')
        params.append(subject.strip())

    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)

    query += ' GROUP BY s.id ORDER BY s.class_name ASC, s.roll ASC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    students_analysis = []
    cat_counts = {'Excellent': 0, 'Good': 0, 'Warning': 0, 'Critical': 0}
    total_pct_sum = 0
    valid_student_count = 0

    for r in rows:
        st = dict(r)
        total = st['total_classes'] or 0
        present = st['present_count'] or 0
        absent = st['absent_count'] or 0
        late = st['late_count'] or 0

        pct = round((present / total * 100), 1) if total > 0 else 0.0
        st['attendance_pct'] = pct

        if pct >= 90:
            category = 'Excellent'
            badge = 'success'
        elif pct >= 75:
            category = 'Good'
            badge = 'info'
        elif pct >= 60:
            category = 'Warning'
            badge = 'warning'
        else:
            category = 'Critical'
            badge = 'danger'

        st['category'] = category
        st['badge'] = badge
        cat_counts[category] += 1

        if total > 0:
            total_pct_sum += pct
            valid_student_count += 1

        students_analysis.append(st)

    avg_class_attendance = round(total_pct_sum / valid_student_count, 1) if valid_student_count > 0 else 0.0

    return {
        'students': students_analysis,
        'summary': {
            'total_students': len(students_analysis),
            'avg_attendance': avg_class_attendance,
            'excellent_count': cat_counts['Excellent'],
            'good_count': cat_counts['Good'],
            'warning_count': cat_counts['Warning'],
            'critical_count': cat_counts['Critical'],
            'at_risk_count': cat_counts['Warning'] + cat_counts['Critical']
        }
    }


def get_distinct_subjects():
    """Retrieve distinct list of subjects recorded in attendance and performance."""
    conn = get_db_connection()
    rows1 = conn.execute("SELECT DISTINCT subject FROM attendance WHERE subject IS NOT NULL AND subject != ''").fetchall()
    rows2 = conn.execute("SELECT DISTINCT subject FROM performance WHERE subject IS NOT NULL AND subject != ''").fetchall()
    conn.close()

    subjects = set([r['subject'] for r in rows1] + [r['subject'] for r in rows2])
    if not subjects:
        subjects = {"Mathematics", "Science", "English", "Social Science", "Computer Science", "Hindi"}
    return sorted(list(subjects))
