(function () {
    'use strict';

    // ---------- helpers ----------
    function parseHHMM(v) {
        if (!v) return null;
        const m = /^(\d{1,2}):(\d{2})$/.exec(v);
        if (!m) return null;
        const h = parseInt(m[1], 10);
        const mm = parseInt(m[2], 10);
        if (h < 0 || h > 23 || mm < 0 || mm > 59) return null;
        return h * 60 + mm;
    }

    function minutesToLabel(mins) {
        if (mins == null || isNaN(mins)) return '—';
        const h = Math.floor(mins / 60);
        const m = Math.round(mins - h * 60);
        return `${h}h ${m.toString().padStart(2, '0')}m`;
    }

    function csrfHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.getCookie('csrftoken'),
        };
    }

    function breakMinutesFromHHMM(str) {
        // "HH:MM" → minutes; empty → 0
        if (!str) return 0;
        const m = parseHHMM(str);
        return m == null ? 0 : m;
    }

    function minutesToHHMM(mins) {
        const h = Math.floor(mins / 60);
        const m = mins - h * 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
    }

    // ---------- state: enter edit mode ----------
    function enterEditMode(cell) {
        const dataDate = cell.dataset.date;
        const start = cell.dataset.start || '';
        const end = cell.dataset.end || '';
        const brkMins = parseInt(cell.dataset.break || '0', 10) || 0;
        const brk = brkMins ? minutesToHHMM(brkMins) : '';

        const view = cell.querySelector('.cell-view');
        if (!view) return;
        view.style.display = 'none';

        const editor = document.createElement('div');
        editor.className = 'cell-editor';
        editor.innerHTML = `
            <div class="mb-1">
                <label class="form-label form-label-sm mb-0 small text-muted">Start</label>
                <input type="time" class="form-control form-control-sm start-time" value="${start}">
            </div>
            <div class="mb-1">
                <label class="form-label form-label-sm mb-0 small text-muted">End</label>
                <input type="time" class="form-control form-control-sm end-time" value="${end}">
            </div>
            <div class="mb-1">
                <label class="form-label form-label-sm mb-0 small text-muted">Break</label>
                <input type="time" class="form-control form-control-sm break-time" value="${brk}">
            </div>
            <div class="net-preview small fw-bold text-primary mt-1">Net: —</div>
            <div class="invalid-feedback d-none editor-error"></div>
            <div class="d-flex gap-1 mt-2">
                <button type="button" class="btn btn-sm btn-success save-time-btn flex-fill">Save</button>
                <button type="button" class="btn btn-sm btn-outline-secondary cancel-time-btn">Cancel</button>
            </div>
        `;
        cell.appendChild(editor);

        const startInput = editor.querySelector('.start-time');
        const endInput = editor.querySelector('.end-time');
        const breakInput = editor.querySelector('.break-time');
        const netPreview = editor.querySelector('.net-preview');
        const errorBox = editor.querySelector('.editor-error');
        const saveBtn = editor.querySelector('.save-time-btn');
        const cancelBtn = editor.querySelector('.cancel-time-btn');

        function clearInvalid() {
            [startInput, endInput, breakInput].forEach(i => i.classList.remove('is-invalid'));
            errorBox.classList.add('d-none');
            errorBox.textContent = '';
        }

        function showInvalid(message, fields) {
            errorBox.textContent = message;
            errorBox.classList.remove('d-none');
            (fields || []).forEach(f => f.classList.add('is-invalid'));
            saveBtn.disabled = true;
        }

        function validateAndCompute() {
            clearInvalid();
            saveBtn.disabled = false;

            const sMin = parseHHMM(startInput.value);
            const eMin = parseHHMM(endInput.value);
            const bMin = breakMinutesFromHHMM(breakInput.value);

            if (sMin == null || eMin == null) {
                netPreview.textContent = 'Net: —';
                saveBtn.disabled = true;
                return null;
            }
            if (eMin <= sMin) {
                netPreview.textContent = 'Net: —';
                showInvalid('End must be after Start', [endInput]);
                return null;
            }
            const shift = eMin - sMin;
            if (bMin < 0 || bMin >= shift) {
                netPreview.textContent = 'Net: —';
                showInvalid('Break exceeds total shift length', [breakInput]);
                return null;
            }
            const net = shift - bMin;
            netPreview.textContent = 'Net: ' + minutesToLabel(net);
            return { startMin: sMin, endMin: eMin, breakMin: bMin, netMin: net };
        }

        [startInput, endInput, breakInput].forEach(i => {
            i.addEventListener('input', validateAndCompute);
            i.addEventListener('change', validateAndCompute);
        });

        cancelBtn.addEventListener('click', () => {
            editor.remove();
            view.style.display = '';
        });

        saveBtn.addEventListener('click', async () => {
            const info = validateAndCompute();
            if (!info) return;

            const payload = {
                date: dataDate,
                start_time: startInput.value,
                end_time: endInput.value,
                break_minutes: info.breakMin,
            };

            // Offline queue
            if (!navigator.onLine) {
                localStorage.setItem('fitlife_pending_' + dataDate, JSON.stringify(payload));
                window.showToast('Offline — saved locally. Will sync.', 'warning');
                replaceWithSavedView(cell, view, editor, payload, info.netMin);
                return;
            }

            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving…';
            try {
                const resp = await fetch('/api/save-entry/', {
                    method: 'POST',
                    headers: csrfHeaders(),
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (!resp.ok) {
                    showInvalid(data.error || 'Could not save.', []);
                    saveBtn.disabled = false;
                    saveBtn.textContent = 'Save';
                    return;
                }
                window.showToast('Hours saved successfully', 'success');
                replaceWithSavedView(cell, view, editor, payload, info.netMin, data.net_hours);
                refreshWeekTotal();
            } catch (err) {
                showInvalid('Network error. Please retry.', []);
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save';
            }
        });

        startInput.focus();
    }

    function replaceWithSavedView(cell, oldView, editor, payload, netMin, serverNetHours) {
        cell.dataset.start = payload.start_time;
        cell.dataset.end = payload.end_time;
        cell.dataset.break = String(payload.break_minutes);
        const netHours = serverNetHours || (netMin / 60).toFixed(2);
        cell.dataset.net = netHours;

        const newView = document.createElement('div');
        newView.className = 'cell-view';
        newView.innerHTML = `
            <div class="entry-view">
                <div class="entry-net">${netHours} h</div>
                <div class="entry-range">${payload.start_time} – ${payload.end_time}</div>
                <div class="entry-break text-muted small">Break ${payload.break_minutes}m</div>
                <button type="button" class="btn btn-sm btn-outline-secondary mt-2 add-time-btn">Edit</button>
                <button type="button" class="btn btn-sm btn-outline-danger mt-2 delete-time-btn">Delete</button>
            </div>
        `;
        editor.remove();
        oldView.remove();
        cell.appendChild(newView);
    }

    async function deleteEntry(cell) {
        if (!confirm('Delete this entry?')) return;
        try {
            const resp = await fetch('/api/delete-entry/', {
                method: 'POST',
                headers: csrfHeaders(),
                body: JSON.stringify({ date: cell.dataset.date }),
            });
            if (!resp.ok) {
                const data = await resp.json();
                window.showToast(data.error || 'Delete failed', 'danger');
                return;
            }
            window.showToast('Entry deleted', 'success');
            // replace view with empty-cell view
            cell.dataset.start = '';
            cell.dataset.end = '';
            cell.dataset.break = '0';
            cell.dataset.net = '';
            const view = cell.querySelector('.cell-view');
            if (view) {
                view.innerHTML = `
                    <div class="entry-empty text-muted">
                        <div class="plus">+</div>
                        <button type="button" class="btn btn-sm btn-outline-primary add-time-btn">Add</button>
                    </div>
                `;
            }
            refreshWeekTotal();
        } catch (err) {
            window.showToast('Network error', 'danger');
        }
    }

    function refreshWeekTotal() {
        let total = 0;
        document.querySelectorAll('.day-cell').forEach(c => {
            const n = parseFloat(c.dataset.net || '0');
            if (!isNaN(n)) total += n;
        });
        const el = document.getElementById('week-total');
        if (el) el.textContent = total.toFixed(2) + ' h';
    }

    // ---------- event delegation ----------
    document.addEventListener('click', (ev) => {
        const addBtn = ev.target.closest('.add-time-btn');
        if (addBtn) {
            const cell = addBtn.closest('.day-cell');
            if (cell && !cell.querySelector('.cell-editor')) {
                enterEditMode(cell);
            }
            return;
        }
        const delBtn = ev.target.closest('.delete-time-btn');
        if (delBtn) {
            const cell = delBtn.closest('.day-cell');
            if (cell) deleteEntry(cell);
        }
    });

    // ---------- offline sync ----------
    const banner = document.getElementById('offline-banner');
    async function syncPending() {
        for (const key of Object.keys(localStorage)) {
            if (!key.startsWith('fitlife_pending_')) continue;
            const payload = JSON.parse(localStorage.getItem(key));
            try {
                const resp = await fetch('/api/save-entry/', {
                    method: 'POST',
                    headers: csrfHeaders(),
                    body: JSON.stringify(payload),
                });
                if (resp.ok) {
                    localStorage.removeItem(key);
                }
            } catch (_) { /* retry later */ }
        }
    }
    function updateOnline() {
        if (navigator.onLine) {
            if (banner) banner.classList.add('d-none');
            syncPending();
        } else {
            if (banner) banner.classList.remove('d-none');
        }
    }
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
    updateOnline();
})();
