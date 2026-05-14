document.addEventListener("DOMContentLoaded", function() {
    
    // Fetch individual athlete analytics
    if (typeof athleteId === 'undefined') return;

    let currentChart = null;
    let currentLoadChart = null;
    let allTrainingLogs = []; // Cache for session details view

    function fetchAndPopulate(event = null) {
        let url = `/api/analytics/athlete/${athleteId}`;
        if (event) url += `?event=${encodeURIComponent(event)}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Populate Event Selector if not already populated
                const selector = document.getElementById('event-view-selector');
                if (selector && selector.options.length <= 1 && data.available_events) {
                    selector.innerHTML = '';
                    data.available_events.forEach(ev => {
                        const opt = document.createElement('option');
                        opt.value = ev;
                        opt.textContent = ev;
                        opt.selected = ev === data.athlete.selected_event;
                        selector.appendChild(opt);
                    });
                }

                // Populate Metrics
                const peakVal = document.getElementById('athlete-peak-time');
                const peakDate = document.getElementById('athlete-peak-date');
                
                if (data.peak_performance && data.peak_performance.value && data.peak_performance.value !== 'N/As') {
                    peakVal.textContent = data.peak_performance.value + data.peak_performance.unit;
                    peakDate.textContent = 'Expected: ' + data.peak_performance.date;
                } else {
                    peakVal.textContent = 'N/A';
                    peakDate.textContent = 'Needs more data';
                }

                // Update Event Tag
                const eventTag = document.getElementById('event-tag-badge');
                if (eventTag) eventTag.textContent = data.athlete.selected_event;

                // Risk & Recommendation
                const riskBadge = document.getElementById('athlete-risk-badge');
                riskBadge.className = `badge bg-${data.risk_assessment.class} fs-4 border border-${data.risk_assessment.class}`;
                riskBadge.textContent = data.risk_assessment.level;
                
                document.getElementById('athlete-recommendation').textContent = data.risk_assessment.recommendation;

                // Strategy Table
                const strategyRow = document.getElementById('race-strategy-row');
                const tbody = document.getElementById('strategy-body');
                tbody.innerHTML = ''; // Clear previous

                if (data.strategy && data.strategy.splits) {
                    strategyRow.style.display = 'block';
                    data.strategy.splits.forEach(split => {
                        const row = `
                        <tr>
                            <td class="fw-bold">${split.distance}</td>
                            <td class="text-jru-blue fw-bold">${split.target ? split.target + 's' : '-'}</td>
                            <td class="text-muted"><i class="bi bi-info-circle me-1"></i> ${split.strategy}</td>
                        </tr>
                        `;
                        tbody.innerHTML += row;
                    });
                } else {
                    strategyRow.style.display = 'none';
                }

                // Performance History Table
                const perfBody = document.getElementById('performance-history-body');
                perfBody.innerHTML = '';
                if (data.performance_history && data.performance_history.length > 0) {
                    [...data.performance_history].reverse().forEach(p => {
                        const rank = p.rank ? `#${p.rank}` : '--';
                        const pts = p.value ? (1000 - (parseFloat(p.value)*10)).toFixed(0) : '--';
                        const statusBadge = p.status === 'confirmed' 
                            ? '<span class="badge bg-success-subtle text-success border border-success-subtle fw-normal"><i class="bi bi-check-circle me-1"></i>Verified</span>'
                            : '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle fw-normal"><i class="bi bi-clock-history me-1"></i>Pending</span>';

                        const confirmBtn = p.status === 'pending'
                            ? `<button class="btn btn-sm btn-success me-1" onclick="event.stopPropagation(); confirmResult(${p.result_id})" title="Confirm Result">
                                 <i class="bi bi-check-lg"></i>
                               </button>`
                            : '';

                        const row = `
                        <tr>
                            <td>${p.date}</td>
                            <td class="fw-bold">${p.competition || 'Sanctioned Meet'}</td>
                            <td class="text-jru-blue fw-bold fs-5">${p.formatted_value}</td>
                            <td>${statusBadge}</td>
                            <td><span class="badge bg-light text-dark">${rank}</span></td>
                            <td>
                                <div class="btn-group">
                                    ${confirmBtn}
                                    <button class="btn btn-sm btn-outline-secondary" onclick="openEditResultModal(${p.result_id})" title="Edit Result">
                                        <i class="bi bi-pencil-fill"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteResult(${p.result_id})" title="Delete Result">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                        `;
                        perfBody.innerHTML += row;
                    });
                } else {
                    perfBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No records found for this event.</td></tr>';
                }

                currentChart = setupPerformanceChart(data.performance_history, data.athlete.selected_event);
                currentLoadChart = setupLoadChart(data.training_history);

                // Populate Training History Table
                const trainingBody = document.getElementById('training-history-body');
                if (trainingBody) {
                    trainingBody.innerHTML = '';
                    if (data.training_history && data.training_history.history && data.training_history.history.length > 0) {
                        allTrainingLogs = data.training_history.history; // Store for detail view
                        data.training_history.history.forEach(log => {
                            const statusBadge = log.status === 'confirmed' 
                                ? '<span class="badge bg-success-subtle text-success border border-success-subtle fw-normal">Confirmed</span>'
                                : '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle fw-normal">Pending</span>';
                            
                            const confirmBtn = log.status === 'pending'
                                ? `<button class="btn btn-sm btn-success me-1" onclick="event.stopPropagation(); confirmLog(${log.id})" title="Confirm Log">
                                     <i class="bi bi-check-lg"></i>
                                   </button>`
                                : '';

                            const row = `
                            <tr style="cursor:pointer;" onclick="showSingleLogDetails(${log.id})">
                                <td>${log.date}</td>
                                <td><span class="badge bg-light text-dark border">${log.type}</span></td>
                                <td>${log.distance || 0}m</td>
                                <td>${log.duration}m</td>
                                <td class="text-center"><span class="badge bg-light text-dark border">${log.intensity}</span></td>
                                <td class="text-center"><span class="badge bg-light text-dark border">${log.fatigue || '--'}</span></td>
                                <td class="fw-bold text-jru-blue">${log.load}</td>
                                <td class="text-nowrap">
                                    ${statusBadge}
                                    ${confirmBtn}
                                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="event.stopPropagation(); deleteTrainingLog(${log.id})" title="Delete Log">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </td>
                            </tr>
                            `;
                            trainingBody.innerHTML += row;
                        });
                    } else {
                        trainingBody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No training history found.</td></tr>';
                    }
                }

                // Handle Specialize Form for this single athlete
                const workoutSelect = document.getElementById('workoutTypeSelect');
                if (workoutSelect) {
                    const athleteEvent = data.athlete.event;
                    specializeTrainingForm([String(athleteId)], [{id: athleteId, event: athleteEvent}]);
                }
            });
    }

    // Initial load
    fetchAndPopulate();

    // Event selector handler
    const eventSelector = document.getElementById('event-view-selector');
    if (eventSelector) {
        eventSelector.addEventListener('change', function(e) {
            fetchAndPopulate(e.target.value);
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

    // Unified Form Handler
    function handleForm(formId, apiEndpoint, successMsg) {
        const form = document.getElementById(formId);
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                fetch(apiEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                })
                .then(res => res.json())
                .then(resData => {
                    if (resData.message || resData.id) {
                        showToast(successMsg || 'Action successful!');
                        setTimeout(() => location.reload(), 2000);
                    } else {
                        showToast('Error: ' + resData.error, 'danger');
                    }
                })
                .catch(err => showToast('Network Error: ' + err, 'danger'));
            });
        }
    }



    handleForm('logTrainingForm', '/api/training', 'Training log submitted!');
    handleForm('addPerformanceForm', '/api/perf_result', 'Performance result logged!');
    handleForm('addWellnessForm', '/api/wellness', 'Wellness log submitted!');

    window.deleteResult = function(resultId) {
        if (!confirm('Are you sure you want to delete this performance record? All associated analytics will be recalculated.')) return;
        fetch(`/api/perf_result/${resultId}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.message) {
                showToast('Performance record deleted.');
                setTimeout(() => fetchAndPopulate(document.getElementById('event-view-selector')?.value), 1000);
            } else {
                showToast('Error: ' + data.error, 'danger');
            }
        })
        .catch(err => showToast('Network Error', 'danger'));
    };

    window.deleteTrainingLog = function(logId) {
        if (!confirm('Are you sure you want to delete this training log?')) return;
        fetch(`/api/training/${logId}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.message) {
                showToast('Training log deleted.');
                setTimeout(() => fetchAndPopulate(document.getElementById('event-view-selector')?.value), 1000);
            } else {
                showToast('Error: ' + data.error, 'danger');
            }
        })
        .catch(err => showToast('Network Error', 'danger'));
    };

    window.deleteWellnessLog = function(wellnessId) {
        if (!confirm('Are you sure you want to delete this wellness log?')) return;
        fetch(`/api/wellness/${wellnessId}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.message) {
                showToast('Wellness log deleted.');
                setTimeout(() => fetchAndPopulate(document.getElementById('event-view-selector')?.value), 1000);
            } else {
                showToast('Error: ' + data.error, 'danger');
            }
        })
        .catch(err => showToast('Network Error', 'danger'));
    };

    // Edit Result Form (PUT)
    const editResultForm = document.getElementById('editResultForm');
    if (editResultForm) {
        editResultForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const fd = new FormData(editResultForm);
            const d = Object.fromEntries(fd.entries());
            const resultId = d.result_id;
            fetch(`/api/perf_result/${resultId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(d)
            })
            .then(res => res.json())
            .then(res => {
                if (res.message) {
                    showToast('Result updated successfully!');
                    bootstrap.Modal.getInstance(document.getElementById('editResultModal'))?.hide();
                    setTimeout(() => fetchAndPopulate(document.getElementById('event-view-selector')?.value), 800);
                } else {
                    showToast('Error: ' + res.error, 'danger');
                }
            })
            .catch(err => showToast('Network Error: ' + err, 'danger'));
        });
    }

    // Special handler for Edit Profile (PUT method)
    const editForm = document.getElementById('editProfileForm');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(editForm);
            const data = Object.fromEntries(formData.entries());
            
            fetch(`/api/athlete/${athleteId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(resData => {
                if (resData.message) {
                    showToast('Profile updated successfully!');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showToast('Error: ' + resData.error, 'danger');
                }
            })
            .catch(err => showToast('Network Error: ' + err, 'danger'));
        });
    }

    function setupPerformanceChart(history, eventName) {
        if (!history || history.length === 0) {
           const ctx = document.getElementById('athletePerformanceChart').getContext('2d');
           return new Chart(ctx, { type: 'line', data: { labels: [], datasets: [] }, options: { plugins: { title: { display: true, text: `No Data for ${eventName}` } } } });
        }
        
        const ctx = document.getElementById('athletePerformanceChart').getContext('2d');
        const labels = history.map(h => h.date);
        const values = history.map(h => h.value);
        const formattedValues = history.map(h => h.formatted_value);
        
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: eventName + ' Performance',
                    data: values,
                    borderColor: '#003366', // JRU Dark Blue
                    backgroundColor: 'rgba(0, 51, 102, 0.1)',
                    borderWidth: 3,
                    pointBackgroundColor: '#FFCC00', // JRU Gold
                    pointBorderColor: '#003366',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                plugins: { 
                    legend: { display: true },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Result: ' + formattedValues[context.dataIndex];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        reverse: eventName.includes('Sprint') || eventName.includes('Run') || eventName.includes('Hurdles'),
                        title: { display: true, text: 'Performance' }
                    }
                }
            }
        });
    }

    function setupLoadChart(history) {
        if (!history || !history.dates || history.dates.length === 0) return null;

        const ctx = document.getElementById('athleteLoadChart').getContext('2d');
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: history.dates,
                datasets: [{
                    label: 'Training Load (Int x Dur)',
                    data: history.load,
                    backgroundColor: '#003366', // JRU Dark Blue
                    borderRadius: 4
                },
                {
                    type: 'line',
                    label: 'Morning Fatigue (1-7)',
                    data: history.fatigue,
                    borderColor: '#FFCC00',
                    backgroundColor: '#FFCC00',
                    borderWidth: 3,
                    pointRadius: 5,
                    yAxisID: 'y1',
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            afterBody: () => '\n(Click for day details)'
                        }
                    }
                },
                onClick: (evt, elements) => {
                    if (elements.length > 0) {
                        const idx = elements[0].index;
                        const detail = history.details[idx];
                        if (detail) showDayDetails(detail);
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Training Load' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Fatigue (1-7 Scale)' },
                        min: 0,
                        max: 7,
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }
});

// Approval logic for profile page
window.confirmLog = function(logId) {
    fetch(`/api/training/confirm/${logId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast('Log confirmed!');
            setTimeout(() => location.reload(), 800);
        })
        .catch(err => showToast('Error confirming log', 'danger'));
}

window.confirmResult = function(resultId) {
    fetch(`/api/perf_result/confirm/${resultId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast('Result verified!');
            setTimeout(() => location.reload(), 800);
        })
        .catch(err => showToast('Error verifying result', 'danger'));
}

function showDayDetails(d) {
    const modalBody = document.getElementById('day-details-body');
    const modalTitle = document.getElementById('day-details-title');
    if (!modalBody || !modalTitle) return;

    modalTitle.innerHTML = `<i class="bi bi-calendar-event me-2"></i>Details for ${d.date}`;

    let html = '';
    if (!d.has_data) {
        html = `<div class="p-4 text-center text-muted">
                    <i class="bi bi-slash-circle display-4 d-block mb-3"></i>
                    No training or wellness data logged for this day.
                </div>`;
    } else {
        html = `<div class="list-group list-group-flush">`;
        
        // --- TRAINING SECTION ---
        if (d.training && d.training.id) {
            html += `
                <div class="list-group-item bg-light fw-bold py-2 d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-lightning-charge me-2"></i>TRAINING SESSION</span>
                </div>
                <div class="list-group-item">
                    <div class="row text-center py-2">
                        <div class="col-6 border-end">
                            <div class="text-muted small">Type</div>
                            <div class="fw-bold">${d.training.type}</div>
                        </div>
                        <div class="col-6">
                            <div class="text-muted small">Load Units</div>
                            <div class="fw-bold text-jru-blue">${d.training.load}</div>
                        </div>
                    </div>
                </div>
                <div class="list-group-item">
                    <div class="row text-center py-2">
                        <div class="col-6 border-end">
                            <div class="text-muted small">Duration</div>
                            <div class="fw-bold">${d.training.duration} min</div>
                        </div>
                        <div class="col-6">
                            <div class="text-muted small">Distance</div>
                            <div class="fw-bold">${d.training.distance ? d.training.distance + ' m' : '--'}</div>
                        </div>
                    </div>
                </div>`;

            // NEW: Add breakdown notes if they exist
            if (d.training.warmup_notes || d.training.main_set_details) {
                html += `
                <div class="list-group-item bg-light p-3">
                    ${d.training.warmup_notes ? `
                    <div class="mb-3">
                        <label class="text-muted small fw-bold d-block mb-1">WARM-UP / DRILLS</label>
                        <div class="bg-white p-2 rounded border small">${d.training.warmup_notes}</div>
                    </div>` : ''}
                    ${d.training.main_set_details ? `
                    <div>
                        <label class="text-muted small fw-bold d-block mb-1 text-primary">MAIN TRAINING SET</label>
                        <div class="bg-white p-2 rounded border small fw-bold">${d.training.main_set_details}</div>
                    </div>` : ''}
                </div>`;
            }
        }

        // --- WELLNESS SECTION ---
        if (d.wellness && d.wellness.id) {
            html += `
                <div class="list-group-item bg-light fw-bold py-2 mt-2 d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-heart-pulse me-2"></i>WELLNESS & RECOVERY</span>
                </div>
                <div class="list-group-item">
                    <div class="row text-center py-2 border-bottom mb-2">
                        <div class="col-4 border-end">
                            <div class="text-muted small">Fatigue</div>
                            <div class="fw-bold fs-5">${d.wellness.fatigue}/7</div>
                        </div>
                        <div class="col-4 border-end">
                            <div class="text-muted small">Stress</div>
                            <div class="fw-bold fs-5">${d.wellness.stress_level}/7</div>
                        </div>
                        <div class="col-4">
                            <div class="text-muted small">Soreness</div>
                            <div class="fw-bold fs-5">${d.wellness.soreness}/7</div>
                        </div>
                    </div>
                    <div class="row text-center py-2">
                        <div class="col-4 border-end">
                            <div class="text-muted small">Sleep Qual.</div>
                            <div class="fw-bold">${d.wellness.sleep_quality}/7</div>
                        </div>
                        <div class="col-4 border-end">
                            <div class="text-muted small">Mood/Motiv.</div>
                            <div class="fw-bold">${d.wellness.motivation}/7</div>
                        </div>
                        <div class="col-4">
                            <div class="text-muted small">Sleep Duration</div>
                            <div class="fw-bold">${d.wellness.sleep_hours} hrs</div>
                        </div>
                    </div>
                </div>`;
        }
        html += `</div>`;
    }

    modalBody.innerHTML = html;
    new bootstrap.Modal(document.getElementById('dayDetailsModal')).show();
}

// Handler for viewing individual session details
window.showSingleLogDetails = function(logId) {
    const log = allTrainingLogs.find(l => l.id === logId);
    if (!log) return;

    // Adapt to showDayDetails format to reuse template logic
    const detail = {
        date: log.date,
        has_data: true,
        training: {
            id: log.id,
            type: log.type,
            load: log.load,
            duration: log.duration,
            distance: log.distance,
            warmup_notes: log.warmup_notes,
            main_set_details: log.main_set_details
        },
        wellness: null // Not applicable for single training log view
    };

    showDayDetails(detail);
    
    // Override title for specific session context
    setTimeout(() => {
        const titleEl = document.getElementById('day-details-title');
        if (titleEl) titleEl.innerHTML = `<i class="bi bi-journal-text me-2"></i>Session Details &mdash; ${log.date}`;
    }, 5);
};
