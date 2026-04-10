(function () {
    'use strict';

    const table = document.getElementById('hr-table');
    if (!table) return;

    const searchInput = document.getElementById('search-input');
    const deptFilter = document.getElementById('dept-filter');

    // ---------- CSRF helper ----------
    function csrfHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.getCookie('csrftoken'),
        };
    }

    // ---------- Search + department filter ----------
    function applyFilters() {
        const query = (searchInput.value || '').toLowerCase().trim();
        const dept = deptFilter.value;
        table.querySelectorAll('tr.employee-row').forEach(row => {
            const name = row.dataset.name || '';
            const d = row.dataset.department || '';
            const matches = name.includes(query) && (!dept || d === dept);
            row.classList.toggle('d-none', !matches);
            const detail = table.querySelector('#detailRow-' + row.dataset.id);
            if (detail) {
                detail.classList.toggle('d-none', !matches);
                if (!matches) detail.classList.remove('show');
            }
        });
    }
    if (searchInput) searchInput.addEventListener('input', applyFilters);
    if (deptFilter) deptFilter.addEventListener('change', applyFilters);

    // ---------- Sorting ----------
    let sortState = { key: null, asc: true };
    const numericKeys = new Set(['target', 'actual', 'delta']);

    table.querySelectorAll('thead th').forEach(th => {
        th.addEventListener('click', () => {
            const key = th.dataset.sort;
            if (!key) return;
            if (sortState.key === key) sortState.asc = !sortState.asc;
            else { sortState.key = key; sortState.asc = true; }

            const rows = Array.from(table.querySelectorAll('tr.employee-row'));
            rows.sort((a, b) => {
                let va = a.dataset[key] || '';
                let vb = b.dataset[key] || '';
                if (numericKeys.has(key)) {
                    va = parseFloat(va); vb = parseFloat(vb);
                }
                if (va < vb) return sortState.asc ? -1 : 1;
                if (va > vb) return sortState.asc ? 1 : -1;
                return 0;
            });
            const tbody = table.querySelector('tbody');
            rows.forEach(row => {
                const detail = table.querySelector('#detailRow-' + row.dataset.id);
                tbody.appendChild(row);
                if (detail) tbody.appendChild(detail);
            });
        });
    });

    // ---------- Prevent collapse toggle when clicking buttons inside detail ----------
    document.addEventListener('click', (ev) => {
        if (ev.target.closest('.detail-collapse button, .detail-collapse a, .detail-collapse input, .detail-collapse textarea')) {
            ev.stopPropagation();
        }
    }, true);

    // ---------- Acknowledge ----------
    document.addEventListener('click', async (ev) => {
        const btn = ev.target.closest('.btn-acknowledge');
        if (!btn) return;
        ev.stopPropagation();
        const id = btn.dataset.employeeId;
        const row = table.querySelector(`tr.employee-row[data-id="${id}"]`);

        btn.disabled = true;
        btn.textContent = 'Acknowledging…';
        try {
            const resp = await fetch('/hr/acknowledge/' + id + '/', {
                method: 'POST',
                headers: csrfHeaders(),
                body: JSON.stringify({
                    month: window.FITLIFE_MONTH,
                    year: window.FITLIFE_YEAR,
                }),
            });
            if (!resp.ok) throw new Error();

            // Update badge in main row
            if (row) {
                const wrapper = row.querySelector('.status-badge-wrapper');
                if (wrapper) {
                    wrapper.innerHTML = '<span class="badge bg-success ms-1">Reviewed</span>';
                }
            }
            window.showToast('Employee hours acknowledged.', 'success');
            btn.textContent = 'Acknowledged ✓';
            btn.classList.remove('btn-success');
            btn.classList.add('btn-outline-success');
            setTimeout(() => {
                btn.disabled = false;
                btn.textContent = 'Re-acknowledge';
                btn.classList.add('btn-success');
                btn.classList.remove('btn-outline-success');
            }, 1500);
        } catch (err) {
            window.showToast('Could not acknowledge.', 'danger');
            btn.disabled = false;
            btn.textContent = 'Acknowledge';
        }
    });

    // ---------- Reminder modal wiring ----------
    const reminderModalEl = document.getElementById('reminderModal');
    const reminderTo = document.getElementById('reminderTo');
    const reminderSubject = document.getElementById('reminderSubject');
    const reminderEmployeeId = document.getElementById('reminderEmployeeId');
    const confirmSendReminder = document.getElementById('confirmSendReminder');

    // Populate modal when a "Send Reminder" button is clicked
    document.addEventListener('click', (ev) => {
        const btn = ev.target.closest('.btn-send-reminder');
        if (!btn) return;
        ev.stopPropagation();
        reminderEmployeeId.value = btn.dataset.employeeId;
        reminderTo.value = btn.dataset.employeeEmail || '';
        // personalize subject if empty
        if (!reminderSubject.value.includes(btn.dataset.employeeName)) {
            reminderSubject.value = reminderSubject.value.replace(
                /^Working Hours/, 'Working Hours — ' + btn.dataset.employeeName + ' —'
            );
        }
    });

    if (confirmSendReminder) {
        confirmSendReminder.addEventListener('click', async () => {
            const id = reminderEmployeeId.value;
            if (!id) return;
            confirmSendReminder.disabled = true;
            confirmSendReminder.textContent = 'Sending…';
            try {
                const resp = await fetch('/hr/reminder/' + id + '/', {
                    method: 'POST',
                    headers: csrfHeaders(),
                    body: JSON.stringify({
                        month: window.FITLIFE_MONTH,
                        year: window.FITLIFE_YEAR,
                    }),
                });
                if (!resp.ok) throw new Error();

                // Close the modal
                const modalInstance = bootstrap.Modal.getInstance(reminderModalEl) ||
                                      new bootstrap.Modal(reminderModalEl);
                modalInstance.hide();

                // Update DOM status of the employee row
                const row = table.querySelector(`tr.employee-row[data-id="${id}"]`);
                if (row) {
                    const wrapper = row.querySelector('.status-badge-wrapper');
                    if (wrapper && !wrapper.querySelector('.bg-success')) {
                        wrapper.innerHTML = '<span class="badge bg-primary ms-1">Reminder sent</span>';
                    }
                }
                window.showToast('Reminder sent successfully', 'info');
            } catch (err) {
                window.showToast('Reminder could not be sent.', 'danger');
            } finally {
                confirmSendReminder.disabled = false;
                confirmSendReminder.textContent = 'Send';
            }
        });
    }
})();
