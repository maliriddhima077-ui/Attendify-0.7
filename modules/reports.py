# ==============================================================================
# MODULE 4: DASHBOARD, REPORTS, UI/UX & INTEGRATION (Member 4)
# Responsibilities: Institutional Report Compilers, Printable Letterhead Formatting,
#                   Dossier Generation & Class Summaries
# ==============================================================================

from datetime import datetime
from backend.database import get_db_connection
from modules.student import get_student_profile_data
from modules.attendance import get_attendance_analysis
from modules.performance import get_performance_analysis


def get_system_settings():
    """Fetch institution configuration settings."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'institution_name': 'St. Xavier Primary School',
        'attendance_threshold': 75.0,
        'academic_year': '2025-2026',
        'contact_email': 'principal@stxavierschool.edu',
        'department': 'Primary School Wing'
    }


def generate_attendance_report(class_name=None, division=None, subject=None, date_from=None, date_to=None):
    """
    Generate structured institutional attendance report.
    """
    settings = get_system_settings()
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT 
            s.id as student_id,
            s.name as student_name,
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

    if date_from and date_from.strip():
        where_clauses.append('(a.date >= ? OR a.date IS NULL)')
        params.append(date_from.strip())

    if date_to and date_to.strip():
        where_clauses.append('(a.date <= ? OR a.date IS NULL)')
        params.append(date_to.strip())

    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)

    query += ' GROUP BY s.id ORDER BY s.class_name ASC, s.roll ASC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    students_data = []
    tot_pct_sum = 0
    valid_count = 0
    excellent = 0
    good = 0
    warning = 0
    critical = 0

    for r in rows:
        st = dict(r)
        tot = st['total_classes'] or 0
        pres = st['present_count'] or 0
        pct = round((pres / tot * 100), 1) if tot > 0 else 0.0
        st['attendance_pct'] = pct

        if pct >= 90:
            st['category'] = 'Excellent'
            st['badge'] = 'success'
            excellent += 1
        elif pct >= 75:
            st['category'] = 'Good'
            st['badge'] = 'info'
            good += 1
        elif pct >= 60:
            st['category'] = 'Warning'
            st['badge'] = 'warning'
            warning += 1
        else:
            st['category'] = 'Critical'
            st['badge'] = 'danger'
            critical += 1

        if tot > 0:
            tot_pct_sum += pct
            valid_count += 1

        students_data.append(st)

    avg_att = round(tot_pct_sum / valid_count, 1) if valid_count > 0 else 0.0

    return {
        'report_type': 'attendance',
        'title': 'Institutional Attendance Summary Report',
        'generated_at': datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        'settings': settings,
        'filters': {
            'class_name': class_name or 'All Classes',
            'division': division or 'All Divisions',
            'subject': subject or 'All Subjects',
            'date_from': date_from or 'All Time',
            'date_to': date_to or 'Present'
        },
        'summary': {
            'total_students': len(students_data),
            'avg_attendance': avg_att,
            'excellent_count': excellent,
            'good_count': good,
            'warning_count': warning,
            'critical_count': critical,
            'at_risk_count': warning + critical
        },
        'data': students_data
    }


def generate_performance_report(class_name=None, division=None, semester=None, subject=None):
    """
    Generate structured academic performance and grade distribution report.
    """
    settings = get_system_settings()
    analysis = get_performance_analysis(class_name=class_name, division=division,
                                        semester=semester, subject=subject)

    return {
        'report_type': 'performance',
        'title': 'Academic Performance & Examination Dossier',
        'generated_at': datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        'settings': settings,
        'filters': {
            'class_name': class_name or 'All Classes',
            'division': division or 'All Divisions',
            'semester': semester or 'All Semesters',
            'subject': subject or 'All Subjects'
        },
        'summary': analysis['summary'],
        'subject_averages': analysis['subject_averages'],
        'data': analysis['records']
    }


def generate_student_dossier(student_id):
    """
    Generate a complete single-student analytical dossier.
    """
    settings = get_system_settings()
    profile = get_student_profile_data(student_id)
    if not profile:
        return None

    return {
        'report_type': 'student_dossier',
        'title': f"Student Academic & Attendance Dossier: {profile['student']['name']}",
        'generated_at': datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        'settings': settings,
        'profile': profile
    }


def generate_class_summary_report(class_name, division=None):
    """
    Generate an executive summary report for an entire academic batch/class.
    """
    settings = get_system_settings()
    att_analysis = get_attendance_analysis(class_name=class_name, division=division)
    perf_analysis = get_performance_analysis(class_name=class_name)

    return {
        'report_type': 'class_summary',
        'title': f"Class Performance & Attendance Summary ({class_name}{f' - Div {division}' if division else ''})",
        'generated_at': datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        'settings': settings,
        'class_name': class_name,
        'division': division or 'All Divisions',
        'attendance_summary': att_analysis['summary'],
        'performance_summary': perf_analysis['summary'],
        'students_attendance': att_analysis['students'],
        'subject_performance': perf_analysis['subject_averages']
    }
