/**
 * ATTENDIFY — Dashboard Chart.js Visualizations
 * Renders 5 Interactive Real-Time Analytical Charts
 */

document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart === 'undefined') return;

    // Check if chart payload is embedded in page
    if (!window.DASHBOARD_CHARTS_DATA) return;

    const data = window.DASHBOARD_CHARTS_DATA;
    let chartInstances = {};

    function getChartThemeColors() {
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        return {
            textColor: isDark ? '#94a3b8' : '#64748b',
            gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)',
            tooltipBg: isDark ? '#1e293b' : '#0f172a'
        };
    }

    function initDashboardCharts() {
        const colors = getChartThemeColors();

        // ----------------------------------------------------
        // 1. Chart 1: Attendance Distribution (Doughnut)
        // ----------------------------------------------------
        const ctxPie = document.getElementById('chartAttendancePie');
        if (ctxPie) {
            if (chartInstances.pie) chartInstances.pie.destroy();
            chartInstances.pie = new Chart(ctxPie, {
                type: 'doughnut',
                data: {
                    labels: data.attendance_pie.labels,
                    datasets: [{
                        data: data.attendance_pie.data,
                        backgroundColor: ['#2bb673', '#ff4d6c', '#f59e0b'],
                        borderWidth: 0,
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: colors.textColor, font: { family: 'Plus Jakarta Sans', size: 12 }, padding: 16 }
                        },
                        tooltip: {
                            backgroundColor: colors.tooltipBg,
                            padding: 10,
                            cornerRadius: 8
                        }
                    }
                }
            });
        }

        // ----------------------------------------------------
        // 2. Chart 2: Monthly Attendance Trend (Line)
        // ----------------------------------------------------
        const ctxLine = document.getElementById('chartMonthlyTrend');
        if (ctxLine) {
            if (chartInstances.line) chartInstances.line.destroy();
            chartInstances.line = new Chart(ctxLine, {
                type: 'line',
                data: {
                    labels: data.monthly_trend.labels,
                    datasets: [{
                        label: 'Average Attendance %',
                        data: data.monthly_trend.data,
                        borderColor: '#3a60a0',
                        backgroundColor: 'rgba(58, 96, 160, 0.12)',
                        borderWidth: 3,
                        pointBackgroundColor: '#3a60a0',
                        pointBorderColor: '#fff',
                        pointHoverRadius: 6,
                        pointRadius: 4,
                        tension: 0.35,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            min: 0,
                            max: 100,
                            grid: { color: colors.gridColor },
                            ticks: { color: colors.textColor, callback: val => val + '%' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: colors.textColor }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: colors.tooltipBg,
                            callbacks: { label: ctx => ` Attendance: ${ctx.raw}%` }
                        }
                    }
                }
            });
        }

        // ----------------------------------------------------
        // 3. Chart 3: Academic Performance Distribution (Bar)
        // ----------------------------------------------------
        const ctxPerfDist = document.getElementById('chartPerformanceDist');
        if (ctxPerfDist) {
            if (chartInstances.perfDist) chartInstances.perfDist.destroy();
            chartInstances.perfDist = new Chart(ctxPerfDist, {
                type: 'bar',
                data: {
                    labels: data.performance_dist.labels,
                    datasets: [{
                        label: 'Student Count',
                        data: data.performance_dist.data,
                        backgroundColor: ['#2bb673', '#4a8dff', '#f59e0b', '#ff4d6c'],
                        borderRadius: 8,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: colors.gridColor },
                            ticks: { color: colors.textColor, precision: 0 }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: colors.textColor, font: { size: 11 } }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: { backgroundColor: colors.tooltipBg }
                    }
                }
            });
        }

        // ----------------------------------------------------
        // 4. Chart 4: Subject Performance Averages (Bar)
        // ----------------------------------------------------
        const ctxSubject = document.getElementById('chartSubjectPerf');
        if (ctxSubject) {
            if (chartInstances.subject) chartInstances.subject.destroy();
            chartInstances.subject = new Chart(ctxSubject, {
                type: 'bar',
                data: {
                    labels: data.subject_performance.labels,
                    datasets: [{
                        label: 'Subject Average %',
                        data: data.subject_performance.data,
                        backgroundColor: '#4d4177',
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            min: 0,
                            max: 100,
                            grid: { color: colors.gridColor },
                            ticks: { color: colors.textColor, callback: val => val + '%' }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: colors.textColor }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: colors.tooltipBg,
                            callbacks: { label: ctx => ` Score: ${ctx.raw}%` }
                        }
                    }
                }
            });
        }

        // ----------------------------------------------------
        // 5. Chart 5: Attendance vs Performance Comparison
        // ----------------------------------------------------
        const ctxCorrelation = document.getElementById('chartCorrelation');
        if (ctxCorrelation) {
            if (chartInstances.correlation) chartInstances.correlation.destroy();
            chartInstances.correlation = new Chart(ctxCorrelation, {
                type: 'bar',
                data: {
                    labels: data.correlation.labels,
                    datasets: [
                        {
                            label: 'Attendance %',
                            data: data.correlation.attendance,
                            backgroundColor: '#38bdf8',
                            borderRadius: 4
                        },
                        {
                            label: 'Performance %',
                            data: data.correlation.performance,
                            backgroundColor: '#4d4177',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            min: 0,
                            max: 100,
                            grid: { color: colors.gridColor },
                            ticks: { color: colors.textColor, callback: val => val + '%' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: colors.textColor, font: { size: 10 } }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { color: colors.textColor, font: { size: 12 } }
                        },
                        tooltip: { backgroundColor: colors.tooltipBg }
                    }
                }
            });
        }
    }

    // Initialize charts on load
    initDashboardCharts();

    // Re-render when dark/light mode changes
    window.addEventListener('themeChanged', () => {
        initDashboardCharts();
    });
});
