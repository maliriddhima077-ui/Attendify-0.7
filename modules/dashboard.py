# ==============================================================================
# MODULE 4: DASHBOARD, REPORTS, UI/UX & INTEGRATION (Member 4)
# Responsibilities: Dashboard KPI Calculations, Chart.js Aggregations,
#                   At-Risk Students Detection, Activity Timeline
# ==============================================================================

from datetime import datetime
from backend.database import get_db_connection


def _scope_filter(standard=None, division=None):
    """
    Build a SQL WHERE fragment + params scoped to one class (standard/division).
    Returns ('', []) when no scope is provided (Principal sees everything).
    """
    if standard and division:
        return ' AND s.class_name = ? AND s.division = ?', [standard, division]
    return '', []


def get_dashboard_metrics(standard=None, division=None):
    """
    Compute real-time summary KPIs for the administrative dashboard:
    1. Total Students
    2. Present Today (or latest instructional day)
    3. Absent Today
    4. Average Attendance %
    5. Average Performance %
    6. Students Below Attendance Threshold (< 75%)

    When standard+division are supplied (Class Teacher view), every metric
    is restricted to that single class section.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    scope_sql, scope_params = _scope_filter(standard, division)

    # 1. Total active students
    cursor.execute(f'''
        SELECT COUNT(*) as count FROM students s WHERE 1=1 {scope_sql}
    ''', scope_params)
    total_students = cursor.fetchone()['count'] or 0

    # 2 & 3. Today's or Latest Day's Attendance
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(f'''
        SELECT COUNT(*) as count
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = ? {scope_sql}
    ''', [today_str] + scope_params)
    today_count = cursor.fetchone()['count']

    effective_date = today_str
    if today_count == 0:
        # Fallback to the most recent recorded date within scope
        cursor.execute(f'''
            SELECT a.date as latest_date
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE 1=1 {scope_sql}
            ORDER BY a.date DESC LIMIT 1
        ''', scope_params)
        latest_row = cursor.fetchone()
        if latest_row:
            effective_date = latest_row['latest_date']

    cursor.execute(f'''
        SELECT
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
            SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) as late_count
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = ? {scope_sql}
    ''', [effective_date] + scope_params)
    daily_stats = dict(cursor.fetchone())
    present_today = daily_stats['present_count'] or 0
    absent_today = daily_stats['absent_count'] or 0
    late_today = daily_stats['late_count'] or 0

    # 4. Overall Average Attendance
    cursor.execute(f'''
        SELECT
            COUNT(a.id) as total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_total
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1 {scope_sql}
    ''', scope_params)
    att_row = dict(cursor.fetchone())
    total_att_records = att_row['total_classes'] or 0
    present_total = att_row['present_total'] or 0
    avg_attendance = round((present_total / total_att_records * 100), 1) if total_att_records > 0 else 0.0

    # 5. Overall Average Performance
    cursor.execute(f'''
        SELECT AVG(p.percentage) as avg_perf
        FROM performance p
        JOIN students s ON p.student_id = s.id
        WHERE 1=1 {scope_sql}
    ''', scope_params)
    perf_row = cursor.fetchone()
    avg_performance = round(perf_row['avg_perf'], 1) if perf_row['avg_perf'] is not None else 0.0

    # 6. Students Below Threshold (< 75%)
    cursor.execute(f'''
        SELECT
            s.id,
            COUNT(a.id) as total,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        WHERE 1=1 {scope_sql}
        GROUP BY s.id
    ''', scope_params)
    student_att_rows = cursor.fetchall()
    at_risk_count = 0
    for r in student_att_rows:
        tot = r['total'] or 0
        pres = r['present'] or 0
        pct = (pres / tot * 100) if tot > 0 else 0.0
        if tot > 0 and pct < 75.0:
            at_risk_count += 1

    conn.close()

    return {
        'total_students': total_students,
        'present_today': present_today,
        'absent_today': absent_today,
        'late_today': late_today,
        'effective_date': effective_date,
        'avg_attendance': avg_attendance,
        'avg_performance': avg_performance,
        'at_risk_count': at_risk_count
    }


def get_dashboard_charts_data(standard=None, division=None):
    """
    Aggregate dataset series for Chart.js interactive visualizations:
    - Chart 1: Attendance Distribution (Present, Absent, Late)
    - Chart 2: Monthly Attendance Trend
    - Chart 3: Performance Tiers
    - Chart 4: Subject Performance Comparison
    - Chart 5: Attendance vs Academic Performance Correlation

    When standard+division are supplied, every series is scoped to that class.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    scope_sql, scope_params = _scope_filter(standard, division)

    # Chart 1: Attendance Distribution Breakdown
    cursor.execute(f'''
        SELECT
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent,
            SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) as late
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1 {scope_sql}
    ''', scope_params)
    att_dist = dict(cursor.fetchone())
    chart_attendance_pie = {
        'labels': ['Present', 'Absent', 'Late'],
        'data': [
            att_dist['present'] or 0,
            att_dist['absent'] or 0,
            att_dist['late'] or 0
        ]
    }

    # Chart 2: Monthly Attendance Trend (group by YYYY-MM)
    cursor.execute(f'''
        SELECT
            strftime('%Y-%m', a.date) as month,
            COUNT(*) as total,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1 {scope_sql}
        GROUP BY month
        ORDER BY month ASC
        LIMIT 12
    ''', scope_params)
    monthly_rows = cursor.fetchall()
    month_labels = []
    month_percentages = []
    month_names = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
        '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
        '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
    }
    for mr in monthly_rows:
        m_str = mr['month']
        if m_str and '-' in m_str:
            parts = m_str.split('-')
            label = f"{month_names.get(parts[1], parts[1])} {parts[0]}"
        else:
            label = m_str
        tot = mr['total'] or 0
        pres = mr['present'] or 0
        pct = round((pres / tot * 100), 1) if tot > 0 else 0.0
        month_labels.append(label)
        month_percentages.append(pct)

    chart_monthly_trend = {
        'labels': month_labels if month_labels else ['Current Term'],
        'data': month_percentages if month_percentages else [0]
    }

    # Chart 3: Performance Distribution
    cursor.execute(f'''
        SELECT p.percentage
        FROM performance p
        JOIN students s ON p.student_id = s.id
        WHERE 1=1 {scope_sql}
    ''', scope_params)
    perf_rows = [r['percentage'] for r in cursor.fetchall()]
    excellent = sum(1 for p in perf_rows if p >= 80)
    good = sum(1 for p in perf_rows if 70 <= p < 80)
    average = sum(1 for p in perf_rows if 50 <= p < 70)
    poor = sum(1 for p in perf_rows if p < 50)

    chart_performance_dist = {
        'labels': ['Excellent (≥80%)', 'Good (70-79%)', 'Average (50-69%)', 'Needs Improvement (<50%)'],
        'data': [excellent, good, average, poor]
    }

    # Chart 4: Subject Performance Comparison
    cursor.execute(f'''
        SELECT p.subject, AVG(p.percentage) as avg_pct
        FROM performance p
        JOIN students s ON p.student_id = s.id
        WHERE 1=1 {scope_sql}
        GROUP BY p.subject
        ORDER BY avg_pct DESC
    ''', scope_params)
    subject_rows = cursor.fetchall()
    chart_subjects = {
        'labels': [r['subject'] for r in subject_rows],
        'data': [round(r['avg_pct'], 1) for r in subject_rows]
    }

    # Chart 5: Attendance vs Academic Performance Correlation
    # NOTE: scope filter is applied once on the outer student rows only,
    # because the LEFT JOINs already restrict to each scoped student.
    cursor.execute('''
        SELECT
            s.id,
            s.name,
            s.roll,
            COUNT(DISTINCT a.id) as total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_classes,
            AVG(p.percentage) as avg_marks
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        LEFT JOIN performance p ON s.id = p.student_id
        {scope}
        GROUP BY s.id
        HAVING total_classes > 0 AND avg_marks IS NOT NULL
        ORDER BY s.roll ASC
    '''.format(scope=('WHERE 1=1 ' + scope_sql) if scope_sql else ''),
        scope_params)
    correlation_rows = cursor.fetchall()
    corr_labels = []
    corr_attendance = []
    corr_performance = []

    for cr in correlation_rows:
        tot = cr['total_classes'] or 0
        pres = cr['present_classes'] or 0
        att_pct = round((pres / tot * 100), 1) if tot > 0 else 0.0
        perf_pct = round(cr['avg_marks'], 1) if cr['avg_marks'] is not None else 0.0

        corr_labels.append(f"{cr['roll']} - {cr['name'].split()[0]}")
        corr_attendance.append(att_pct)
        corr_performance.append(perf_pct)

    chart_correlation = {
        'labels': corr_labels,
        'attendance': corr_attendance,
        'performance': corr_performance
    }

    conn.close()

    return {
        'attendance_pie': chart_attendance_pie,
        'monthly_trend': chart_monthly_trend,
        'performance_dist': chart_performance_dist,
        'subject_performance': chart_subjects,
        'correlation': chart_correlation
    }


def get_at_risk_students(threshold=75.0, limit=8, standard=None, division=None):
    """
    Identify students falling below attendance threshold for proactive intervention.
    Scoped to one class section when standard+division are supplied.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    scope_sql, scope_params = _scope_filter(standard, division)

    cursor.execute(f'''
        SELECT
            s.id,
            s.name,
            s.roll,
            s.class_name,
            s.division,
            s.email,
            COUNT(a.id) as total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_classes,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_classes
        FROM students s
        JOIN attendance a ON s.id = a.student_id
        WHERE 1=1 {scope_sql}
        GROUP BY s.id
        HAVING total_classes > 0
    ''', scope_params)
    rows = cursor.fetchall()
    conn.close()

    at_risk = []
    for r in rows:
        st = dict(r)
        tot = st['total_classes']
        pres = st['present_classes']
        pct = round((pres / tot * 100), 1) if tot > 0 else 0.0
        st['attendance_pct'] = pct

        if pct < threshold:
            if pct < 60:
                st['risk_level'] = 'Critical'
                st['risk_badge'] = 'danger'
            else:
                st['risk_level'] = 'Warning'
                st['risk_badge'] = 'warning'
            at_risk.append(st)

    # Sort lowest attendance first
    at_risk.sort(key=lambda x: x['attendance_pct'])
    return at_risk[:limit]
