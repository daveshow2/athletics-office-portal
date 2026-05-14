document.addEventListener("DOMContentLoaded", function() {
    
    function fetchLogs(month = '') {
        const url = month ? `/api/training/all?month=${month}` : '/api/training/all';
        fetch(url)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                const tbody = document.getElementById('logs-table-body');
                if (!tbody) return;
                
                let allLogs = data.logs || []; 
                const pendingLogs = allLogs.filter(l => l.status === 'pending');
                
                // Update Approval Toolbar
                const toolbar = document.getElementById('approval-toolbar');
                const pendingText = document.getElementById('pendingCountText');
                if (toolbar && pendingText) {
                    if (pendingLogs.length > 0) {
                        toolbar.style.display = 'block';
                        pendingText.textContent = `You have ${pendingLogs.length} training log(s) awaiting approval.`;
                    } else {
                        toolbar.style.display = 'none';
                    }
                }

                if (allLogs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" class="text-center">No logs found.</td></tr>';
                    return;
                }

                let htmlContent = '';
                allLogs.forEach(log => {
                    const statusBadge = log.status === 'confirmed' 
                        ? '<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-check-circle me-1"></i>Confirmed</span>'
                        : '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle"><i class="bi bi-clock-history me-1"></i>Pending</span>';

                    const confirmBtn = log.status === 'pending'
                        ? `<button class="btn btn-sm btn-success me-1" onclick="event.stopPropagation(); confirmLog(${log.id})" title="Confirm Log">
                             <i class="bi bi-check-lg"></i>
                           </button>`
                        : '';

                    htmlContent += `
                    <tr style="cursor:pointer;" onclick="showLogDetails(${log.id})">
                        <td>${log.date}</td>
                        <td class="fw-bold text-jru-blue">
                            <a href="/athlete/${log.athlete_id}" class="text-decoration-none text-jru-blue" onclick="event.stopPropagation()">${log.athlete_name}</a>
                        </td>
                        <td><span class="badge bg-light text-dark border">${log.type}</span></td>
                        <td>${log.distance || 0}</td>
                        <td>${log.duration || 0}</td>
                        <td><span class="badge ${log.intensity > 7 ? 'bg-danger text-white' : 'bg-jru-blue'}">${log.intensity || 0}</span></td>
                        <td><span class="badge ${log.fatigue > 7 ? 'bg-danger' : 'bg-jru-gold text-dark'}">${log.fatigue || 0}</span></td>
                        <td>${statusBadge}</td>
                        <td class="text-center text-nowrap">
                             ${confirmBtn}
                             <button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteLog(${log.id})" title="Delete entry">
                                 <i class="bi bi-trash"></i>
                             </button>
                        </td>
                    </tr>`;
                });
                tbody.innerHTML = htmlContent;

                // Detail function
                window.showLogDetails = function(logId) {
                    const log = allLogs.find(l => l.id === logId);
                    if (!log) return;
                    renderSessionDetails(log);
                };
            })
            .catch(err => {
                console.error('Error fetching logs:', err);
                const tbody = document.getElementById('logs-table-body');
                if (tbody) {
                    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Error loading logs. Please try again.</td></tr>';
                }
            });
    }

    // Initial fetch
    fetchLogs();

    // Month filter logic
    const monthFilter = document.getElementById('monthFilter');
    const exportBtn = document.getElementById('exportBtn');
    if (monthFilter) {
        monthFilter.addEventListener('change', function() {
            const month = this.value;
            fetchLogs(month);
            if (exportBtn) {
                exportBtn.href = month ? `/api/export/training?month=${month}` : '/api/export/training';
            }
        });
    }

    // Populate athlete select for the log form
    let allAthletes = [];
    fetch('/api/athletes')
        .then(response => response.json())
        .then(data => {
            allAthletes = data.athletes;
            const select = document.getElementById('athleteSelect');
            if (select) {
                select.innerHTML = '<option value="">Choose Athlete...</option>';
                data.athletes.forEach(athlete => {
                    const opt = document.createElement('option');
                    opt.value = athlete.id;
                    opt.textContent = athlete.name;
                    select.appendChild(opt);
                });
            }
        });

    const athleteSel = document.getElementById('athleteSelect');
    if (athleteSel) {
        athleteSel.addEventListener('change', function() {
            const selectedIds = Array.from(this.selectedOptions).map(opt => opt.value);
            specializeTrainingForm(selectedIds, allAthletes);
        });
    }

    // Live Training Load Preview Logic
    const trForm = document.getElementById('logTrainingForm');
    if (trForm) {
        const intensityInput = trForm.querySelector('[name="intensity"]');
        const durationInput = trForm.querySelector('[name="duration"]');
        const previewEl = document.getElementById('live-load-preview');

        const updatePreview = () => {
            const load = parseInt(intensityInput.value || 0) * parseInt(durationInput.value || 0);
            previewEl.textContent = `${load} Load Units`;
            if (load > 600) previewEl.className = 'badge bg-danger fs-6';
            else if (load > 400) previewEl.className = 'badge bg-warning text-dark fs-6';
            else previewEl.className = 'badge bg-jru-blue fs-6';
        };

        intensityInput.addEventListener('input', updatePreview);
        durationInput.addEventListener('input', updatePreview);
    }

    // Handle Training Log Submission
    const logForm = document.getElementById('logTrainingForm');
    if (logForm) {
        logForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(logForm);
            let data = {};
            
            if (formData.has('athlete_ids')) {
                data = Object.fromEntries(formData.entries());
                data.athlete_ids = formData.getAll('athlete_ids');
            } else {
                data = Object.fromEntries(formData.entries());
            }

            // Package Main Set Details into a single JSON field
            if (data.main_dist || data.main_effort || data.main_time) {
                data.main_set_details = JSON.stringify({
                    dist: data.main_dist || 0,
                    effort: data.main_effort || 0,
                    time: data.main_time || 0,
                    extra: data.extra_work || ''
                });
            }
            
            fetch('/api/training', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(resData => {
                if (resData.message || resData.id) {
                    showToast('Training log submitted!');
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showToast('Error: ' + resData.error, 'danger');
                }
            })
            .catch(err => showToast('Network Error: ' + err, 'danger'));
        });
    }

    // Confirm All logic
    const confirmAllBtn = document.getElementById('confirmAllBtn');
    if (confirmAllBtn) {
        confirmAllBtn.addEventListener('click', function() {
            if (!confirm('Confirm all pending logs? These will immediately be included in analytics.')) return;
            fetch('/api/training/confirm-all', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    showToast(data.message);
                    fetchLogs();
                })
                .catch(err => showToast('Error confirming logs', 'danger'));
        });
    }
});

window.confirmLog = function(logId) {
    fetch(`/api/training/confirm/${logId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast('Log confirmed!');
            // Instead of reload, just refetch to keep filter state
            const monthVal = document.getElementById('monthFilter')?.value || '';
            // We need a way to call the internal fetchLogs, or just reload for simplicity
            location.reload();
        })
        .catch(err => showToast('Error confirming log', 'danger'));
}

window.deleteLog = async function(logId) {
    if (!confirm('Are you sure you want to delete this training log? This will permanently remove the data for this athlete.')) return;
    try {
        const res = await fetch(`/api/training/${logId}`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok) {
            showToast('Training log deleted.');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.error || 'Error deleting log', 'danger');
        }
    } catch (e) {
        showToast('Network error', 'danger');
    }
}

function renderSessionDetails(log) {
    const modalBody = document.getElementById('day-details-body');
    const modalTitle = document.getElementById('day-details-title');
    if (!modalBody || !modalTitle) return;

    modalTitle.innerHTML = `<i class="bi bi-journal-text me-2"></i>Session Details &mdash; ${log.athlete_name}`;

    let volumeLoadHtml = '';
    if (log.main_set_details) {
        try {
            const ms = JSON.parse(log.main_set_details);
            const sprintLoad = (ms.dist || 0) * ((ms.effort || 0) / 100);
            if (sprintLoad > 0) volumeLoadHtml = `<div class="text-success small fw-bold mt-1">Sprint Volume Load: ${sprintLoad.toFixed(1)}m</div>`;
        } catch(e) {}
    }

    modalBody.innerHTML = `
        <div class="list-group list-group-flush">
            <div class="list-group-item bg-light fw-bold py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-lightning-charge me-2"></i>TRAINING DATA</span>
                    <span class="badge bg-jru-blue">${log.date}</span>
                </div>
            </div>
            <div class="list-group-item">
                <div class="row text-center py-2">
                    <div class="col-4 border-end">
                        <div class="text-muted small">Type</div>
                        <div class="fw-bold">${log.type}</div>
                    </div>
                    <div class="col-4 border-end">
                        <div class="text-muted small">Load Units</div>
                        <div class="fw-bold text-jru-blue">${log.intensity * log.duration}</div>
                    </div>
                    <div class="col-4">
                        <div class="text-muted small">Intensity</div>
                        <div class="fw-bold">${log.intensity}/10</div>
                    </div>
                </div>
            </div>
            <div class="list-group-item">
                <div class="row text-center py-2">
                    <div class="col-6 border-end">
                        <div class="text-muted small">Duration</div>
                        <div class="fw-bold">${log.duration} min</div>
                    </div>
                    <div class="col-6">
                        <div class="text-muted small">Distance</div>
                        <div class="fw-bold">${log.distance || 0} m</div>
                        ${volumeLoadHtml}
                    </div>
                </div>
            </div>
            
            ${log.warmup_notes || log.main_set_details ? `
            <div class="list-group-item bg-light border-top border-bottom py-3">
                <div class="fw-bold mb-2 text-jru-blue"><i class="bi bi-info-circle me-1"></i>SESSION BREAKDOWN</div>
                ${log.warmup_notes ? `
                    <div class="mb-2">
                        <label class="small text-muted fw-bold d-block uppercase" style="font-size:0.65rem;">WARM-UP / DRILLS</label>
                        <div style="font-size:0.9rem;">${log.warmup_notes}</div>
                    </div>
                ` : ''}
                ${log.main_set_details ? (() => {
                    const ms = JSON.parse(log.main_set_details);
                    return `
                    <div class="p-2 rounded mt-2 shadow-sm" style="background: #fff9e6; border: 1px solid #ffeeba;">
                        <label class="small text-muted fw-bold d-block mb-1" style="font-size:0.65rem; color:#856404 !important;">MAIN SET PEAK</label>
                        <div class="fw-bold">
                            ${ms.dist}m @ ${ms.effort}% ${ms.time ? `in ${ms.time}s` : ''}
                        </div>
                        ${ms.extra ? `
                            <div class="mt-2 border-top pt-1 small text-muted">
                                <strong>Extra work:</strong> ${ms.extra}
                            </div>` : ''}
                    </div>`;
                })() : ''}
            </div>` : ''}
            
            <div class="list-group-item text-center py-3 bg-light">
                <span class="text-muted small">Log submitted on ${log.submitted_at || 'N/A'}</span>
            </div>
        </div>
    `;

    const modalEl = document.getElementById('dayDetailsModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}
