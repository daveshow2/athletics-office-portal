document.addEventListener("DOMContentLoaded", function() {
    
    // Fetch dashboard stats and athlete data
    const refreshDashboard = (eventFilter = '') => {
        const url = eventFilter ? `/api/analytics/dashboard?event=${encodeURIComponent(eventFilter)}` : '/api/analytics/dashboard';
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Update Stats Cards
                document.getElementById('stat-total-athletes').textContent = data.stats.total_athletes;
                document.getElementById('stat-active-logs').textContent = data.stats.active_logs;
                document.getElementById('stat-high-risk').textContent = data.stats.high_risk_count;
                document.getElementById('stat-peak-approaching').textContent = data.stats.peak_approaching;

                // Populate Athlete Table
                const tbody = document.getElementById('athlete-table-body');
                tbody.innerHTML = ''; // Clear default rows
                if (data.athletes.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No athletes found for this event.</td></tr>';
                }
                data.athletes.forEach(athlete => {
                    const initials = athlete.name.split(' ').map(n=>n[0]).join('').substring(0,2);
                    const row = `
                    <tr>
                        <td>
                            <div class="d-flex align-items-center">
                                <div class="bg-light rounded-circle p-2 me-2 text-jru-blue fw-bold" style="width: 38px; height: 38px; display:flex; align-items:center; justify-content:center;">${initials}</div>
                                <strong>${athlete.name}</strong>
                            </div>
                        </td>
                        <td>${athlete.event}</td>
                        <td class="fw-bold">${athlete.latest_result}</td>
                        <td><span class="badge badge-jru-gold"><i class="bi bi-graph-up-arrow"></i> ${athlete.predicted_peak}</span></td>
                        <td><span class="badge bg-${athlete.risk_class} bg-opacity-10 text-${athlete.risk_class} border border-${athlete.risk_class}">${athlete.injury_risk}</span></td>
                        <td>
                            <button class="btn btn-sm btn-jru-outline py-1 px-2 mb-1" onclick="showToast('${athlete.recommendation}', '${athlete.risk_class}')">Analyze Risk</button>
                            <a href="/athlete/${athlete.id}" class="btn btn-sm btn-jru-primary py-1 px-2">View Profile</a>
                        </td>
                    </tr>`;
                    tbody.innerHTML += row;
                });

                // Populate athlete selects for all modals (only if we have all athletes or it's the first load)
                // Note: The modals usually global so we might only want to fill them once or with the full list.
                // For simplicity, we'll keep the current logic but maybe skip if eventFilter is set
                if (!eventFilter) {
                    const athleteSelects = document.querySelectorAll('#athleteSelect, .select-athlete-list');
                    athleteSelects.forEach(select => {
                        const currentVal = select.value;
                        select.innerHTML = '<option value="">Choose Athlete...</option>';
                        data.athletes.forEach(athlete => {
                            const opt = document.createElement('option');
                            opt.value = athlete.id;
                            opt.textContent = athlete.name;
                            select.appendChild(opt);
                        });
                        select.value = currentVal;
                    });
                }
            });
    };

    // Storing athletes globally for specialization logic
    let allAthletes = [];
    fetch('/api/athletes')
        .then(res => res.json())
        .then(data => {
            allAthletes = data.athletes;
        });

    const athleteSel = document.getElementById('athleteSelect');
    if (athleteSel) {
        athleteSel.addEventListener('change', function() {
            const selectedIds = Array.from(this.selectedOptions).map(opt => opt.value);
            specializeTrainingForm(selectedIds, allAthletes);
        });
    }

    // Initial load for dashboard and ranking table
    refreshDashboard();

    // Event listener for ranking table selector
    const rankingSelector = document.getElementById('rankingEventSelector');
    if (rankingSelector) {
        rankingSelector.addEventListener('change', (e) => refreshDashboard(e.target.value));
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
            // Visual feedback based on load
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
                let data = {};
                
                // Special handling for multi-select athlete_ids
                if (formData.has('athlete_ids')) {
                    data = Object.fromEntries(formData.entries());
                    data.athlete_ids = formData.getAll('athlete_ids');
                } else {
                    data = Object.fromEntries(formData.entries());
                }
                
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

    handleForm('addAthleteForm', '/api/athlete', 'Athlete registered successfully!');
    handleForm('logTrainingForm', '/api/training', 'Training log submitted!');
    handleForm('addPerformanceForm', '/api/perf_result', 'Performance result logged!');
    handleForm('addWellnessForm', '/api/wellness', 'Wellness log submitted!');

    // Performance Trend Chart Logic
    let perfChart;
    const updatePerformanceChart = (eventType) => {
        fetch(`/api/analytics/trend/${eventType}`)
            .then(response => response.json())
            .then(data => {
                const ctxPerf = document.getElementById('performanceChart').getContext('2d');
                
                if (perfChart) perfChart.destroy();
                
                const unit = data.is_time ? '(s)' : '(m)';
                
                perfChart = new Chart(ctxPerf, {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: `Team Average ${data.event}`,
                            data: data.data,
                            borderColor: '#003366', // JRU Dark Blue
                            backgroundColor: 'rgba(0, 51, 102, 0.15)',
                            borderWidth: 3,
                            pointBackgroundColor: '#FFCC00', // JRU Gold
                            pointBorderColor: '#003366',
                            pointBorderWidth: 2,
                            pointRadius: 6,
                            pointHoverRadius: 8,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return 'Avg Result: ' + data.formatted_data[context.dataIndex];
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                reverse: data.is_time, // Lower time is better for sprints, higher is better for jumps
                                title: { display: true, text: data.is_time ? 'Performance (Time)' : 'Performance (Distance)' }
                            }
                        }
                    }
                });
            });
    };

    // Initial load and selector listener
    const eventSelector = document.getElementById('eventTrendSelector');
    if (eventSelector) {
        updatePerformanceChart(eventSelector.value);
        eventSelector.addEventListener('change', (e) => updatePerformanceChart(e.target.value));
    }

    // Fetch Load vs Fatigue Chart Data
    fetch('/api/analytics/load_fatigue')
        .then(response => response.json())
        .then(data => {
            const ctxLoad = document.getElementById('loadChart').getContext('2d');
            new Chart(ctxLoad, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Training Load',
                        data: data.load,
                        backgroundColor: '#003366', // JRU Dark Blue
                        borderRadius: 6,
                        barPercentage: 0.6
                    },
                    {
                        type: 'line',
                        label: 'Avg Fatigue (1-7)',
                        data: data.fatigue,
                        borderColor: '#FFCC00', // JRU Gold
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
                                afterBody: () => '\n(Click for team summary)'
                            }
                        }
                    },
                    onClick: (evt, elements) => {
                        if (elements.length > 0) {
                            const idx = elements[0].index;
                            const summary = data.summaries[idx];
                            if (summary) showTeamSummary(summary);
                        }
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Team Avg Load' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: { display: true, text: 'Avg Fatigue (1-7)' },
                            min: 0,
                            max: 7,
                            grid: { drawOnChartArea: false }
                        }
                    }
                }
            });
        });
});

function showTeamSummary(s) {
    const modalBody = document.getElementById('team-summary-body');
    const modalTitle = document.getElementById('team-summary-title');
    if (!modalBody || !modalTitle) return;

    modalTitle.innerHTML = `<i class="bi bi-people me-2"></i>Team Summary: ${s.date}`;

    const html = `
        <div class="list-group list-group-flush">
            <div class="list-group-item bg-light fw-bold py-2"><i class="bi bi-activity me-2"></i>ACTIVITY OVERVIEW</div>
            <div class="list-group-item">
                <div class="row text-center py-2">
                    <div class="col-6 border-end">
                        <div class="text-muted small">Athletes Logged</div>
                        <div class="fw-bold fs-4 text-jru-blue">${s.athletes_trained}</div>
                    </div>
                    <div class="col-6">
                        <div class="text-muted small">Top Workout</div>
                        <div class="fw-bold">${s.top_workout}</div>
                    </div>
                </div>
            </div>
            
            <div class="list-group-item bg-light fw-bold py-2 mt-2"><i class="bi bi-bar-chart me-2"></i>TEAM AVERAGES</div>
            <div class="list-group-item">
                <div class="row text-center py-2">
                    <div class="col-6 border-end">
                        <div class="text-muted small">Avg Load / Athlete</div>
                        <div class="fw-bold text-jru-blue">${s.avg_load}</div>
                    </div>
                    <div class="col-6">
                        <div class="text-muted small">Avg Fatigue Score</div>
                        <div class="fw-bold text-warning">${s.avg_fatigue} / 10</div>
                    </div>
                </div>
            </div>
            <div class="list-group-item">
                <div class="row text-center py-2">
                    <div class="col-12">
                        <div class="text-muted small">Total Team Volume</div>
                        <div class="fw-bold text-success">${s.total_volume.toLocaleString()} m</div>
                    </div>
                </div>
            </div>
            
            <div class="list-group-item p-3 text-center">
                <a href="/training-logs" class="btn btn-sm btn-jru-outline w-100">View All Detailed Logs</a>
            </div>
        </div>`;

    modalBody.innerHTML = html;
    new bootstrap.Modal(document.getElementById('teamSummaryModal')).show();
}

