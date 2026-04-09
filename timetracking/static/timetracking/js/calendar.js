(function () {
    'use strict';

    const modalEl = document.getElementById('entryModal');
    const modal = new bootstrap.Modal(modalEl);
    const dateInput = document.getElementById('entry-date');
    const dateLabel = document.getElementById('entry-date-label');
    const startInput = document.getElementById('entry-start');
    const endInput = document.getElementById('entry-end');
    const breakInput = document.getElementById('entry-break');
    const netSpan = document.getElementById('entry-net');
    const errorBox = document.getElementById('entry-error');
    const saveBtn = document.getElementById('entry-save');
    const deleteBtn = document.getElementById('entry-delete');

    function parseTime(v) {
        if (!v) return null;
        const [h, m] = v.split(':').map(Number);
        return h * 60 + m;
    }

    function computeNet() {
        const start = parseTime(startInput.value);
        const end = parseTime(endInput.value);
        const brk = parseInt(breakInput.value || '0', 10);
        if (start === null || end === null) {
            netSpan.textContent = '— h';
            return null;
        }
        const diff = end - start;
        const net = diff - brk;
        if (diff <= 0) {
            netSpan.textContent = '— h';
            return null;
        }
        netSpan.textContent = (Math.max(net, 0) / 60).toFixed(2) + ' h';
        return { start, end, brk, diff, net };
    }

    function validate() {
        errorBox.classList.add('d-none');
        errorBox.textContent = '';
        [startInput, endInput, breakInput].forEach(i => i.classList.remove('is-invalid-custom'));

        if (!startInput.value || !endInput.value) {
            showError('Please enter both a start and an end time.', [startInput, endInput]);
            return null;
        }
        const info = computeNet();
        if (info === null) {
            showError('Please enter valid times in HH:MM format.', [startInput, endInput]);
            return null;
        }
        if (info.diff <= 0) {
            showError('End time cannot be before start time.', [endInput]);
            return null;
        }
        if (info.brk < 0 || info.brk >= info.diff) {
            showError('Break duration exceeds total shift length.', [breakInput]);
            return null;
        }
        return info;
    }

    function showError(msg, fields) {
        errorBox.textContent = msg;
        errorBox.classList.remove('d-none');
        (fields || []).forEach(f => f.classList.add('is-invalid-custom'));
    }

    function openCell(cell) {
        const date = cell.dataset.date;
        dateInput.value = date;
        const d = new Date(date + 'T00:00:00');
        dateLabel.textContent = d.toLocaleDateString(undefined, {
            weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
        });
        startInput.value = cell.dataset.start || '';
        endInput.value = cell.dataset.end || '';
        breakInput.value = cell.dataset.break || 0;
        errorBox.classList.add('d-none');
        computeNet();
        deleteBtn.style.display = cell.dataset.start ? '' : 'none';
        modal.show();
    }

    document.querySelectorAll('.day-cell').forEach(cell => {
        cell.addEventListener('click', () => openCell(cell));
    });

    [startInput, endInput, breakInput].forEach(i => {
        i.addEventListener('input', computeNet);
    });

    saveBtn.addEventListener('click', async () => {
        const info = validate();
        if (!info) return;

        const payload = {
            date: dateInput.value,
            start_time: startInput.value,
            end_time: endInput.value,
            break_minutes: info.brk,
        };

        if (!navigator.onLine) {
            const key = 'fitlife_pending_' + payload.date;
            localStorage.setItem(key, JSON.stringify(payload));
            showToast('Offline — saved locally. Will sync.', 'warning');
            modal.hide();
            return;
        }

        try {
            const resp = await fetch('/api/save-entry/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok) {
                showError(data.error || 'Could not save.', []);
                return;
            }
            showToast('Hours saved successfully.', 'success');
            modal.hide();
            setTimeout(() => window.location.reload(), 400);
        } catch (err) {
            showError('Network error. Please retry.', []);
        }
    });

    deleteBtn.addEventListener('click', async () => {
        if (!confirm('Delete this entry?')) return;
        try {
            const resp = await fetch('/api/delete-entry/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ date: dateInput.value }),
            });
            if (!resp.ok) {
                const data = await resp.json();
                showError(data.error || 'Could not delete.', []);
                return;
            }
            showToast('Entry deleted.', 'success');
            modal.hide();
            setTimeout(() => window.location.reload(), 400);
        } catch (err) {
            showError('Network error. Please retry.', []);
        }
    });

    // Offline detection
    const banner = document.getElementById('offline-banner');
    function updateOnline() {
        if (navigator.onLine) {
            banner.classList.add('d-none');
            syncPending();
        } else {
            banner.classList.remove('d-none');
        }
    }
    async function syncPending() {
        for (const key of Object.keys(localStorage)) {
            if (!key.startsWith('fitlife_pending_')) continue;
            const payload = JSON.parse(localStorage.getItem(key));
            try {
                const resp = await fetch('/api/save-entry/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify(payload),
                });
                if (resp.ok) {
                    localStorage.removeItem(key);
                }
            } catch (_) { /* keep for next try */ }
        }
    }
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
    updateOnline();
})();
