# Backend package initialization
from .database import (
    get_db_connection,
    init_db,
    seed_sample_data,
    reset_data,
    log_activity,
    get_recent_activities
)
