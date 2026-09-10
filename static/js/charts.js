/**
 * ATTENDIFY — Specialized Profile & Performance Analytics Charts
 */

document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart === 'undefined') return;

    function getThemeColors() {
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        return {
            textColor: isDark ? '#94a3b8' : '#64748b',
            gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)',
            tooltipBg: isDark ? '#1e293b' : '#0f172a'
        };
    }

    // --------------------------------------------------------
    // 1. Student Profile Charts
    // --------------------------------------------------------
    const profileAttCtx = document.getElementById('studentProfileAttChart');
    if (profileAttCtx && window.STUDENT_PROFILE_DATA) {
        const pData = window.STUDENT_PROFILE_DATA;
        const colors = getThemeColors();

        new Chart(profileAttCtx, {
            type: 'doughnut',
            data: {
                labels: ['Present', 'Absent', 'Late'],
                datasets: [{
                    data: [pData.attendance.present, pData.attendance.absent, pData.attendance.late],
                    backgroundColor: ['#2bb673', '#ff4d6c', '#f59e0b'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: { position: 'bottom', labels: { color: colors.textColor } }
                }
            }
        });
    }

    const profilePerfCtx = document.getElementById('studentProfilePerfChart');
    if (profilePerfCtx && window.STUDENT_PROFILE_DATA) {
        const pData = window.STUDENT_PROFILE_DATA;
        const colors = getThemeColors();
        const subLabels = pData.performance.records.map(r => r.subject);
        const subMarks = pData.performance.records.map(r => r.percentage);

        new Chart(profilePerfCtx, {
            type: 'bar',
            data: {
                labels: subLabels,
                datasets: [{
                    label: 'Score %',
                    data: subMarks,
                    backgroundColor: '#4d4177',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { min: 0, max: 100, grid: { color: colors.gridColor }, ticks: { color: colors.textColor, callback: v => v + '%' } },
                    x: { grid: { display: false }, ticks: { color: colors.textColor, font: { size: 10 } } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // --------------------------------------------------------
    // 2. Performance Analytics Page Charts
    // --------------------------------------------------------
    const perfPassCtx = document.getElementById('perfPassPieChart');
    if (perfPassCtx && window.PERF_ANALYTICS_DATA) {
        const aData = window.PERF_ANALYTICS_DATA;
        const colors = getThemeColors();

        new Chart(perfPassCtx, {
            type: 'doughnut',
            data: {
                labels: ['Passed (≥40%)', 'Failed (<40%)'],
                datasets: [{
                    data: [aData.summary.passed_count, aData.summary.failed_count],
                    backgroundColor: ['#2bb673', '#ff4d6c'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '68%',
                plugins: {
                    legend: { position: 'bottom', labels: { color: colors.textColor } }
                }
            }
        });
    }

    const perfGradeCtx = document.getElementById('perfGradeBarChart');
    if (perfGradeCtx && window.PERF_ANALYTICS_DATA) {
        const aData = window.PERF_ANALYTICS_DATA;
        const colors = getThemeColors();
        const grades = ['A+', 'A', 'B+', 'B', 'C', 'D', 'F'];
        const gradeCounts = grades.map(g => aData.summary.grade_counts[g] || 0);

        new Chart(perfGradeCtx, {
            type: 'bar',
            data: {
                labels: grades,
                datasets: [{
                    label: 'Students',
                    data: gradeCounts,
                    backgroundColor: ['#2bb673', '#88a5e0', '#3a60a0', '#4d4177', '#f59e0b', '#f97316', '#ff4d6c'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, grid: { color: colors.gridColor }, ticks: { color: colors.textColor, precision: 0 } },
                    x: { grid: { display: false }, ticks: { color: colors.textColor } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
});
