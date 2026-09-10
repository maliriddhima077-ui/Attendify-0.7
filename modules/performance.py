from backend.database import get_db_connection, log_activity, calculate_grade


def get_all_performance(student_id=None, class_name=None, division=None, semester=None, subject=None, search=None):
    """Retrieve performance exam records with optional filters."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT 
            p.*,
            s.name as student_name,
            s.roll,
            s.class_name,
            s.division,
            s.email
        FROM performance p
        JOIN students s ON p.student_id = s.id
        WHERE 1=1
    '''
    params = []

    if student_id:
        query += ' AND p.student_id = ?'
        params.append(student_id)

    if class_name and class_name.strip():
        query += ' AND s.class_name = ?'
        params.append(class_name.strip())

    if division and division.strip():
        query += ' AND s.division = ?'
        params.append(division.strip())

    if semester and semester.strip():
        query += ' AND p.semester = ?'
        params.append(semester.strip())

    if subject and subject.strip():
        query += ' AND p.subject = ?'
        params.append(subject.strip())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += ' AND (s.name LIKE ? OR s.roll LIKE ? OR p.subject LIKE ?)'
        params.extend([term, term, term])

    query += ' ORDER BY p.id DESC'

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def add_performance_record(student_id, subject, internal_marks, external_marks, semester):
    """Validate marks and insert a new student academic performance record."""
    if not student_id or not subject or not semester:
        return False, "Student, Subject, and Semester are required.", None

    try:
        internal = float(internal_marks)
        external = float(external_marks)
    except (ValueError, TypeError):
        return False, "Marks must be valid numerical values.", None

    if internal < 0 or internal > 40:
        return False, "Internal marks must be between 0 and 40.", None

    if external < 0 or external > 60:
        return False, "External marks must be between 0 and 60.", None

    total = round(internal + external, 1)
    percentage = round((total / 100.0) * 100, 1)
    grade = calculate_grade(percentage)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, roll FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return False, "Selected student does not exist.", None

    try:
        cursor.execute('''
            INSERT INTO performance (student_id, subject, internal_marks, external_marks, total_marks, percentage, grade, semester)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, subject.strip(), internal, external, total, percentage, grade, semester.strip()))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()

        log_activity("Performance Added", f"Recorded {subject} marks ({total}/100, Grade: {grade}) for {student['name']} ({student['roll']})")
        return True, "Academic performance record added successfully.", new_id
    except Exception as e:
        conn.close()
        return False, f"Failed to record performance: {str(e)}", None


def update_performance_record(record_id, subject, internal_marks, external_marks, semester):
    """Validate and update an existing performance record."""
    try:
        internal = float(internal_marks)
        external = float(external_marks)
    except (ValueError, TypeError):
        return False, "Marks must be valid numerical values."

    if internal < 0 or internal > 40:
        return False, "Internal marks must be between 0 and 40."

    if external < 0 or external > 60:
        return False, "External marks must be between 0 and 60."

    total = round(internal + external, 1)
    percentage = round((total / 100.0) * 100, 1)
    grade = calculate_grade(percentage)

    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE performance
            SET subject = ?, internal_marks = ?, external_marks = ?, total_marks = ?, percentage = ?, grade = ?, semester = ?
            WHERE id = ?
        ''', (subject.strip(), internal, external, total, percentage, grade, semester.strip(), record_id))
        conn.commit()
        conn.close()

        log_activity("Performance Updated", f"Updated performance record #{record_id} ({subject}: {total}%)")
        return True, "Performance record updated successfully."
    except Exception as e:
        conn.close()
        return False, f"Database error: {str(e)}"


def delete_performance_record(record_id):
    """Delete a performance record."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM performance WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        log_activity("Performance Deleted", f"Deleted performance record #{record_id}")
        return True, "Performance record deleted successfully."
    except Exception as e:
        conn.close()
        return False, f"Database error: {str(e)}"


def get_performance_analysis(class_name=None, division=None, semester=None, subject=None):
    """Compute comprehensive academic performance analytics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT 
            p.*,
            s.name as student_name,
            s.roll,
            s.class_name,
            s.division
        FROM performance p
        JOIN students s ON p.student_id = s.id
        WHERE 1=1
    '''
    params = []

    if class_name and class_name.strip():
        query += ' AND s.class_name = ?'
        params.append(class_name.strip())

    if division and division.strip():
        query += ' AND s.division = ?'
        params.append(division.strip())

    if semester and semester.strip():
        query += ' AND p.semester = ?'
        params.append(semester.strip())

    if subject and subject.strip():
        query += ' AND p.subject = ?'
        params.append(subject.strip())

    cursor.execute(query, params)
    records = [dict(r) for r in cursor.fetchall()]

    if not records:
        conn.close()
        return {
            'records': [],
            'summary': {
                'total_records': 0,
                'avg_percentage': 0.0,
                'highest_percentage': 0.0,
                'lowest_percentage': 0.0,
                'passed_count': 0,
                'failed_count': 0,
                'pass_rate': 0.0,
                'grade_counts': {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0},
                'categories': {'Excellent': 0, 'Good': 0, 'Average': 0, 'Needs Improvement': 0}
            },
            'subject_averages': []
        }

    percentages = [r['percentage'] for r in records]
    avg_pct = round(sum(percentages) / len(percentages), 1)
    highest_pct = max(percentages)
    lowest_pct = min(percentages)

    passed_count = sum(1 for p in percentages if p >= 40)
    failed_count = sum(1 for p in percentages if p < 40)
    pass_rate = round((passed_count / len(percentages)) * 100, 1)

    grade_counts = {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    for r in records:
        g = r['grade']
        if g in grade_counts:
            grade_counts[g] += 1
        else:
            grade_counts['F'] += 1

    categories = {
        'Excellent': sum(1 for p in percentages if p >= 80),
        'Good': sum(1 for p in percentages if 70 <= p < 80),
        'Average': sum(1 for p in percentages if 50 <= p < 70),
        'Needs Improvement': sum(1 for p in percentages if p < 50)
    }

    sub_query = '''
        SELECT 
            p.subject,
            COUNT(*) as count,
            AVG(p.internal_marks) as avg_internal,
            AVG(p.external_marks) as avg_external,
            AVG(p.total_marks) as avg_total,
            AVG(p.percentage) as avg_percentage,
            MAX(p.percentage) as highest_pct,
            MIN(p.percentage) as lowest_pct
        FROM performance p
        JOIN students s ON p.student_id = s.id
        WHERE 1=1
    '''
    sub_params = []
    if class_name and class_name.strip():
        sub_query += ' AND s.class_name = ?'
        sub_params.append(class_name.strip())
    if division and division.strip():
        sub_query += ' AND s.division = ?'
        sub_params.append(division.strip())
    if semester and semester.strip():
        sub_query += ' AND p.semester = ?'
        sub_params.append(semester.strip())

    sub_query += ' GROUP BY p.subject ORDER BY avg_percentage DESC'
    cursor.execute(sub_query, sub_params)
    subject_averages = []
    for r in cursor.fetchall():
        row = dict(r)
        row['avg_internal'] = round(row['avg_internal'], 1) if row['avg_internal'] else 0.0
        row['avg_external'] = round(row['avg_external'], 1) if row['avg_external'] else 0.0
        row['avg_total'] = round(row['avg_total'], 1) if row['avg_total'] else 0.0
        row['avg_percentage'] = round(row['avg_percentage'], 1) if row['avg_percentage'] else 0.0
        subject_averages.append(row)

    conn.close()

    return {
        'records': records,
        'summary': {
            'total_records': len(records),
            'avg_percentage': avg_pct,
            'highest_percentage': highest_pct,
            'lowest_percentage': lowest_pct,
            'passed_count': passed_count,
            'failed_count': failed_count,
            'pass_rate': pass_rate,
            'grade_counts': grade_counts,
            'categories': categories
        },
        'subject_averages': subject_averages
    }
