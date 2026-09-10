/**
 * ATTENDIFY — Attendance Register Sheet Helpers
 * Handles batch mark actions ('Mark All Present', 'Mark All Absent', 'Mark All Late')
 * and dynamic live tally calculations.
 */

document.addEventListener('DOMContentLoaded', () => {
    const markAllPresentBtn = document.getElementById('markAllPresentBtn');
    const markAllAbsentBtn = document.getElementById('markAllAbsentBtn');
    const markAllLateBtn = document.getElementById('markAllLateBtn');
    const attendanceForm = document.getElementById('attendanceRegisterForm');

    function setAllAttendance(status) {
        if (!attendanceForm) return;
        const radios = attendanceForm.querySelectorAll(`input[type="radio"][value="${status}"]`);
        radios.forEach(radio => {
            radio.checked = true;
        });
        updateAttendanceSummary();
    }

    if (markAllPresentBtn) {
        markAllPresentBtn.addEventListener('click', () => setAllAttendance('Present'));
    }

    if (markAllAbsentBtn) {
        markAllAbsentBtn.addEventListener('click', () => setAllAttendance('Absent'));
    }

    if (markAllLateBtn) {
        markAllLateBtn.addEventListener('click', () => setAllAttendance('Late'));
    }

    function updateAttendanceSummary() {
        if (!attendanceForm) return;
        const checkedRadios = attendanceForm.querySelectorAll('input[type="radio"]:checked');
        let present = 0, absent = 0, late = 0;

        checkedRadios.forEach(r => {
            if (r.value === 'Present') present++;
            else if (r.value === 'Absent') absent++;
            else if (r.value === 'Late') late++;
        });

        const elPresent = document.getElementById('tallyPresent');
        const elAbsent = document.getElementById('tallyAbsent');
        const elLate = document.getElementById('tallyLate');
        const elTotal = document.getElementById('tallyTotal');

        if (elPresent) elPresent.textContent = present;
        if (elAbsent) elAbsent.textContent = absent;
        if (elLate) elLate.textContent = late;
        if (elTotal) elTotal.textContent = present + absent + late;
    }

    if (attendanceForm) {
        attendanceForm.addEventListener('change', (e) => {
            if (e.target.type === 'radio') {
                updateAttendanceSummary();
            }
        });
        updateAttendanceSummary();
    }
});
