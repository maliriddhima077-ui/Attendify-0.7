# Attendify modules package
from .student import (
    get_all_students,
    get_student_by_id,
    add_student,
    update_student,
    delete_student,
    get_student_profile_data,
    get_distinct_classes,
    get_distinct_divisions
)
from .attendance import (
    get_attendance_sheet,
    save_batch_attendance,
    get_attendance_history,
    get_attendance_analysis,
    get_distinct_subjects
)
from .performance import (
    get_all_performance,
    add_performance_record,
    update_performance_record,
    delete_performance_record,
    get_performance_analysis
)
from .dashboard import (
    get_dashboard_metrics,
    get_dashboard_charts_data,
    get_at_risk_students
)
from .reports import (
    generate_attendance_report,
    generate_performance_report,
    generate_student_dossier,
    generate_class_summary_report
)
