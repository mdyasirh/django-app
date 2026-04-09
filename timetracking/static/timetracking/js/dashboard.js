(function () {
    'use strict';

    const table = document.getElementById('hr-table');
    const searchInput = document.getElementById('search-input');
    const deptFilter = document.getElementById('dept-filter');

    function applyFilters() {
        const query = (searchInput.value || '').toLowerCase().trim();
        const dept = deptFilter.value;
        table.querySelectorAll('tr.employee-row').forEach(row => {
            const name = row.dataset.name || '';
            const d = row.dataset.department || '';
            const matches = name.includes(query) && (!dept || d === dept);
            row.classList.toggle('d-none', !matches);
            if (!matches) {
                const detail = table.querySelector(`tr.detail-row[data-detail-for="${row.dataset.id}"]`);
                if (detail) detail.classList.add('d-none');
            }
        });
    }

    searchInput.addEventListener('input', applyFilters);
    deptFilter.addEventListener('change', applyFilters);

    // Sorting
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
                const detail = table.querySelector(`tr.detail-row[data-detail-for="${row.dataset.id}"]`);
                tbody.appendChild(row);
                if (detail) tbody.appendChild(detail);
            });
        });
    });

    // Row expansion
    table.querySelectorAll('tr.employee-row').forEach(row => {
        row.addEventListener('click', async () => {
            const id = row.dataset.id;
            const detail = table.querySelector(`tr.detail-row[data-detail-for="${id}"]`);
            if (!detail) return;

            // Collapse others
            table.querySelectorAll('tr.detail-row').forEach(d => {
                if (d !== detail) d.classList.add('d-none');
            });

            if (!detail.classList.contains('d-none')) {
                detail.classList.add('d-none');
                return;
            }

            const cell = detail.querySelector('.detail-cell');
            cell.innerHTML = '<div class="text-center text-muted py-3">Loading…</div>';
            detail.classList.remove('d-none');

            try {
                const resp = await fetch(
                    `/hr/detail/${id}/?month=${window.FITLIFE_MONTH}&year=${window.FITLIFE_YEAR}`
                );
                if (!resp.ok) throw new Error();
                cell.innerHTML = await resp.text();
                wireDetailButtons(cell, id);
            } catch (err) {
                cell.innerHTML = '<div class="text-danger py-2">Failed to load details.</div>';
            }
        });
    });

    function wireDetailButtons(cell, id) {
        const ackBtn = cell.querySelector('.js-acknowledge');
        const remBtn = cell.querySelector('.js-send-reminder');

        if (ackBtn) {
            ackBtn.addEventListener('click', async (ev) => {
                ev.stopPropagation();
                try {
                    const resp = await fetch(`/hr/acknowledge/${id}/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken'),
                        },
                        body: JSON.stringify({
                            month: window.FITLIFE_MONTH,
                            year: window.FITLIFE_YEAR,
                        }),
                    });
                    if (!resp.ok) throw new Error();
                    showToast('Month acknowledged as reviewed.', 'success');
                    const row = table.querySelector(`tr.employee-row[data-id="${id}"]`);
                    if (row && !row.querySelector('.badge.bg-success')) {
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-success ms-1';
                        badge.textContent = 'Reviewed';
                        row.querySelector('td').appendChild(badge);
                    }
                } catch (err) {
                    showToast('Could not acknowledge.', 'danger');
                }
            });
        }

        if (remBtn) {
            remBtn.addEventListener('click', async (ev) => {
                ev.stopPropagation();
                try {
                    const resp = await fetch(`/hr/reminder/${id}/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken'),
                        },
                        body: JSON.stringify({
                            month: window.FITLIFE_MONTH,
                            year: window.FITLIFE_YEAR,
                        }),
                    });
                    if (!resp.ok) throw new Error();
                    const data = await resp.json();
                    showToast(data.message || 'Reminder sent.', 'primary');
                } catch (err) {
                    showToast('Reminder could not be sent.', 'danger');
                }
            });
        }

        cell.querySelectorAll('button').forEach(b => {
            b.addEventListener('click', ev => ev.stopPropagation());
        });
    }
})();
