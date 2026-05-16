/**
 * athlete_portal.js - Athlete self-view portal logic
 * Loads personal analytics, training logs, and competition results.
 */

// ─── Tab Navigation ────────────────────────────────────────────────────────
let resultsLoaded = false;
document.querySelectorAll('#portalTabs .nav-link').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#portalTabs .nav-link').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        // Lazy-load results tab on first visit
        if (btn.dataset.tab === 'results' && !resultsLoaded) {
            resultsLoaded = true;
            loadResults();
        }
    });
});

// ─── Toast Utility ────────────────────────────────────────────────────────
// Redundant showToast removed; using ui_utils.js instead.

// ─── Chart Instances ──────────────────────────────────────────────────────
let perfChart = null;
let loadChart = null;
let allAthleteLogs = []; // Cache for training logs detail view

// ─── Load Analytics ───────────────────────────────────────────────────────
let analyticsEventSelectorInitialized = false;

async function loadAnalytics(selectedEvent = null) {
    try {
        let url = `/api/analytics/athlete/${athleteId}`;
        if (selectedEvent) url += `?event=${encodeURIComponent(selectedEvent)}`;
        const res = await fetch(url);
        const data = await res.json();

        // ── Populate event selector (once, on first load) ──────────────────
        if (!analyticsEventSelectorInitialized) {
            analyticsEventSelectorInitialized = true;
            const evtSelect = document.getElementById('portal-analytics-event');
            if (evtSelect && data.available_events && data.available_events.length > 0) {
                evtSelect.innerHTML = data.available_events.map((ev, i) =>
                    `<option value="${ev}" ${ev === data.athlete.selected_event ? 'selected' : ''}>${ev}${i === 0 ? ' ★' : ''}</option>`
                ).join('');
                evtSelect.addEventListener('change', function () {
                    const val = this.value;
                    loadAnalytics(val);
                    loadTrainingLogs(val);
                    // Also refresh results if tab is active or lazy-loaded
                    if (resultsLoaded) loadResults(val);
                });
            }
        } else {
            // Keep selector in sync with returned selected_event
            const evtSelect = document.getElementById('portal-analytics-event');
            if (evtSelect && data.athlete.selected_event) {
                evtSelect.value = data.athlete.selected_event;
            }
        }
        
        // Sync the Results tab filter as well
        const resFilter = document.getElementById('eventFilter');
        if (resFilter) resFilter.value = data.athlete.selected_event;
        selectedResultEvent = data.athlete.selected_event;

        // ── Peak Performance ───────────────────────────────────────────────
        document.getElementById('an-peak').textContent = data.peak_performance.value || '--';
        document.getElementById('an-peakdate').textContent = data.peak_performance.date || '--';
        document.getElementById('an-risk').textContent = data.risk_assessment.level || '--';
        document.getElementById('an-confidence').textContent = data.peak_performance.confidence
            ? `${Math.min(100, Math.round(data.peak_performance.confidence))}%` : '--';

        // ── Hero Stats ─────────────────────────────────────────────────────
        document.getElementById('ps-risk').textContent = data.risk_assessment.level;
        document.getElementById('ps-latestresult').textContent =
            data.performance_history.length > 0
                ? data.performance_history[data.performance_history.length - 1].formatted_value
                : '--';

        // ── Recommendation ─────────────────────────────────────────────────
        document.getElementById('an-recommendation').textContent = data.risk_assessment.recommendation || '--';

        // ── Performance Trend Chart ────────────────────────────────────────
        const perfLabels    = data.performance_history.map(p => p.date);
        const perfVals      = data.performance_history.map(p => p.value);
        const perfFormatted = data.performance_history.map(p => p.formatted_value);
        const isTime = data.athlete.selected_event &&
            ['Sprint', 'Run', 'Hurdles', 'Steeplechase', 'Walk'].some(x => data.athlete.selected_event.includes(x));

        if (perfChart) perfChart.destroy();
        const perfCtx = document.getElementById('portalPerfChart').getContext('2d');
        perfChart = new Chart(perfCtx, {
            type: 'line',
            data: {
                labels: perfLabels,
                datasets: [{
                    label: data.athlete.selected_event,
                    data: perfVals,
                    borderColor: '#003087',
                    backgroundColor: 'rgba(0,48,135,0.08)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#FFC107',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => perfFormatted[ctx.dataIndex] || ctx.raw
                        }
                    }
                },
                scales: {
                    y: {
                        reverse: isTime,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        title: { display: true, text: isTime ? 'Time (s)' : 'Distance (m)' }
                    }
                }
            }
        });

        // ── Training Load vs Fatigue Chart ────────────────────────────────
        const thData = data.training_history;
        if (loadChart) loadChart.destroy();
        const loadCtx = document.getElementById('portalLoadChart').getContext('2d');
        loadChart = new Chart(loadCtx, {
            type: 'bar',
            data: {
                labels: thData.dates,
                datasets: [
                    {
                        label: 'Training Load',
                        data: thData.load,
                        backgroundColor: 'rgba(0,48,135,0.75)',
                        borderRadius: 4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Morning Fatigue (1-7)',
                        data: thData.fatigue,
                        type: 'line',
                        borderColor: '#FFC107',
                        backgroundColor: 'rgba(255,193,7,0.15)',
                        tension: 0.4,
                        fill: false,
                        pointBackgroundColor: '#FFC107',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            afterBody: (items) => {
                                return '\n(Click for day details)';
                            }
                        }
                    }
                },
                onClick: (evt, elements) => {
                    if (elements.length > 0) {
                        const idx = elements[0].index;
                        const detail = thData.details[idx];
                        if (detail) showDayDetails(detail);
                    }
                },
                onHover: (evt, elements) => {
                    evt.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                scales: {
                    y:  { title: { display: true, text: 'Load' }, grid: { color: 'rgba(0,0,0,0.05)' } },
                    y1: { position: 'right', title: { display: true, text: 'Fatigue (1-7 Scale)' }, min: 0, max: 7, grid: { drawOnChartArea: false } }
                }
            }
        });

        // ── Race Strategy ──────────────────────────────────────────────────
        if (data.strategy && data.strategy.phases && data.strategy.phases.length > 0) {
            document.getElementById('strategy-section').style.display = 'block';
            const tbody = document.getElementById('portal-strategy-body');
            tbody.innerHTML = data.strategy.phases.map(p => `
                <tr>
                    <td class="fw-bold">${p.phase}</td>
                    <td><span class="badge bg-jru-blue">${p.target}</span></td>
                    <td>${p.strategy}</td>
                </tr>`).join('');
        } else if (data.strategy && data.strategy.splits) {
            // Fallback: splits format
            document.getElementById('strategy-section').style.display = 'block';
            const tbody = document.getElementById('portal-strategy-body');
            tbody.innerHTML = data.strategy.splits.map(p => `
                <tr>
                    <td class="fw-bold">${p.distance}</td>
                    <td><span class="badge bg-jru-blue">${p.target ? p.target + 's' : '--'}</span></td>
                    <td>${p.strategy}</td>
                </tr>`).join('');
        } else {
            document.getElementById('strategy-section').style.display = 'none';
        }

    } catch (e) {
        console.error('Analytics load error:', e);
    }
}

// ─── Load Training Logs ───────────────────────────────────────────────────
async function loadTrainingLogs(eventFilter = null) {
    try {
        const res = await fetch('/api/training/all');
        const data = await res.json();
        let myLogs = data.logs.filter(l => l.athlete_id === athleteId);

        if (eventFilter && eventFilter !== '__all__') {
            myLogs = myLogs.filter(l => l.event_trained === eventFilter);
        }
        
        // Populate personal stat cards
        document.getElementById('ps-sessions').textContent = myLogs.length;

        const avgLoad = myLogs.length > 0
            ? Math.round(myLogs.reduce((s, l) => s + l.intensity * l.duration, 0) / myLogs.length)
            : 0;
        document.getElementById('ps-avgload').textContent = avgLoad;

        const tbody = document.getElementById('portal-logs-body');
        if (myLogs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No training logs yet. Click "Log Training" to get started!</td></tr>';
            return;
        }
        allAthleteLogs = myLogs;
        tbody.innerHTML = myLogs.slice(0, 50).map(l => {
            const load = l.intensity * l.duration;
            const loadClass = load > 600 ? 'danger' : load > 350 ? 'warning' : 'success';
            const statusBadge = l.status === 'confirmed'
                ? '<span class="badge bg-success-subtle text-success border border-success-subtle fw-normal"><i class="bi bi-check-circle me-1"></i>Confirmed</span>'
                : '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle fw-normal"><i class="bi bi-clock-history me-1"></i>Pending Review</span>';

            return `<tr style="cursor:pointer;" onclick="showSingleLogDetails(${l.id})">
                <td>${l.date}</td>
                <td><span class="badge bg-jru-blue">${l.type}</span></td>
                <td><span class="badge bg-light text-dark border">${l.event_trained || '--'}</span></td>
                <td>${l.distance || '--'}</td>
                <td>${l.duration}</td>
                <td class="text-center"><span class="badge bg-light text-dark border">${l.intensity}</span></td>
                <td class="text-center"><span class="badge bg-light text-dark border">${l.fatigue || '--'}</span></td>
                <td><span class="badge text-bg-${loadClass}">${load}</span></td>
                <td class="text-nowrap">
                    ${statusBadge}
                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="event.stopPropagation(); deleteTrainingLog(${l.id})" title="Delete entry">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('Training logs error:', e);
    }
}

window.deleteTrainingLog = async function(logId) {
    console.log('[DELETE] deleteTrainingLog called with logId:', logId);
    if (!confirm('Are you sure you want to delete this training log? This will affect your ACWR and recovery analytics.')) return;
    try {
        console.log('[DELETE] Sending DELETE request to /api/training/' + logId);
        const res = await fetch(`/api/training/${logId}`, { method: 'DELETE' });
        const data = await res.json();
        console.log('[DELETE] Response status:', res.status, 'data:', data);
        if (res.ok) {
            showToast('Training log deleted successfully!', 'success');
            await loadTrainingLogs();
            loadAnalytics(); // Refresh charts
        } else {
            console.error('[DELETE] Server error:', data);
            showToast(data.error || 'Error deleting log', 'danger');
        }
    } catch (e) {
        console.error('[DELETE] Network/fetch error:', e);
        showToast('Network error: ' + e.message, 'danger');
    }
}
// Track the currently selected event for filtering
let selectedResultEvent = null;

window.deleteResult = async function(resultId) {
    if (!confirm('Are you sure you want to delete this performance record? This will affect your trend analytics and predictions.')) return;
    try {
        const res = await fetch(`/api/perf_result/${resultId}`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok) {
            showToast('Performance record removed.', 'success');
            loadResults(selectedResultEvent);
            loadAnalytics(selectedResultEvent);
        } else {
            showToast(data.error || 'Error deleting result', 'danger');
        }
    } catch (e) {
        showToast('Network error', 'danger');
    }
}

// ─── Load Performance Results ─────────────────────────────────────────────
async function loadResults(forceEvent = null) {
    const filterEl = document.getElementById('eventFilter');
    const eventParam = forceEvent || (filterEl && filterEl.value) || '';
    const url = eventParam
        ? `/api/analytics/athlete/${athleteId}?event=${encodeURIComponent(eventParam)}`
        : `/api/analytics/athlete/${athleteId}`;
    try {
        const res = await fetch(url);
        const data = await res.json();
        const history = data.performance_history;
        const tbody = document.getElementById('portal-results-body');

        // ── Populate event filter dropdown (only on first load) ────────────
        if (filterEl && filterEl.options.length === 0 && data.available_events) {
            data.available_events.forEach(ev => {
                const opt = document.createElement('option');
                opt.value = ev;
                opt.textContent = ev;
                if (ev === data.athlete.selected_event) opt.selected = true;
                filterEl.appendChild(opt);
            });

            // Wire change listener once
            filterEl.addEventListener('change', () => {
                selectedResultEvent = filterEl.value;
                loadResults(selectedResultEvent);
                loadAnalytics(selectedResultEvent);
                loadTrainingLogs(selectedResultEvent);
            });
        }

        // Keep module-level state in sync
        selectedResultEvent = data.athlete.selected_event;

        if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No competition results for <strong>${data.athlete.selected_event}</strong>. Log a result or choose a different event.</td></tr>`;
            return;
        }

        tbody.innerHTML = [...history].reverse().map(r => {
            const statusBadge = r.status === 'confirmed'
                ? '<span class="badge bg-success-subtle text-success border border-success-subtle fw-normal"><i class="bi bi-check-circle me-1"></i>Confirmed</span>'
                : '<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle fw-normal"><i class="bi bi-clock-history me-1"></i>Pending Review</span>';

            const rankVal = r.rank ? `#${r.rank}` : '--';

            return `
            <tr>
                <td>${r.date}</td>
                <td>${r.competition || 'Training Session'}</td>
                <td><span class="badge bg-jru-blue">${data.athlete.selected_event}</span></td>
                <td class="fw-bold text-jru-gold">${r.formatted_value}</td>
                <td><span class="badge bg-light text-dark">${rankVal}</span></td>
                <td class="text-nowrap">
                    ${statusBadge}
                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteResult(${r.result_id})" title="Delete entry">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('Results load error:', e);
    }
}

// ─── Form Submissions ─────────────────────────────────────────────────────

// Borg CR10 descriptors
const BORG_CR10 = {
    0: 'Nothing at all (Rest)',
    1: 'Very Light',
    2: 'Light',
    3: 'Moderate',
    4: 'Somewhat Hard',
    5: 'Hard',
    6: 'Hard+',
    7: 'Very Hard',
    8: 'Very Hard+',
    9: 'Very Very Hard',
    10: 'Maximal (Cannot continue)'
};

function setupIntensitySliders() {
    // ── Borg CR10 RPE slider ──────────────────────────────────────────
    const rpeSlider     = document.getElementById('rpeSlider');
    const rpeBadge      = document.getElementById('rpe-value-badge');
    const rpeDescriptor = document.getElementById('rpe-descriptor');
    if (rpeSlider) {
        const updateRPE = () => {
            const v = parseInt(rpeSlider.value);
            if (rpeBadge) rpeBadge.textContent = v;
            if (rpeDescriptor) {
                rpeDescriptor.textContent = BORG_CR10[v] || '';
                // Colour-code the descriptor background
                const colour = v <= 2 ? '#c8e6c9' : v <= 4 ? '#fff9c4' : v <= 6 ? '#ffe0b2' : '#ffcdd2';
                rpeDescriptor.style.background = colour;
            }
            // Live load preview in portal modal
            const form = rpeSlider.closest('form');
            const dur  = form?.querySelector('[name="duration"]');
            const preview = document.getElementById('portal-load-preview') || document.getElementById('live-load-preview');
            if (dur && preview) preview.textContent = `${v * (parseInt(dur.value) || 0)} Load Units`;
        };
        rpeSlider.addEventListener('input', updateRPE);
        updateRPE(); // initialise descriptor on load
    }

    // ── Generic intensity-range (other modals) ────────────────────────
    document.querySelectorAll('.intensity-range').forEach(range => {
        if (range.id === 'rpeSlider') return; // handled above
        const badge = range.closest('[class*="mb"]')?.querySelector('.intensity-value');
        range.addEventListener('input', () => {
            if (badge) badge.textContent = range.value;
            const form = range.closest('form');
            const dur  = form?.querySelector('[name="duration"]');
            const preview = document.getElementById('live-load-preview');
            if (dur && preview) preview.textContent = `${range.value * (parseInt(dur.value) || 0)} Load Units`;
        });
    });

    // ── Duration input → live load refresh ───────────────────────────
    const dur = document.querySelector('#logTrainingForm [name="duration"]');
    if (dur) dur.addEventListener('input', () => {
        const rpe = rpeSlider ? parseInt(rpeSlider.value) : (parseInt(document.querySelector('.intensity-range')?.value) || 5);
        const preview = document.getElementById('portal-load-preview') || document.getElementById('live-load-preview');
        if (preview) preview.textContent = `${rpe * (parseInt(dur.value) || 0)} Load Units`;
    });

    // ── Post-session Fatigue badge ────────────────────────────────────
    const fatSlider = document.getElementById('fatigueSlider');
    const fatBadge  = document.getElementById('fatigue-value-badge');
    if (fatSlider && fatBadge) {
        fatSlider.addEventListener('input', () => { fatBadge.textContent = fatSlider.value; });
    }

    // ── Hooper Index live score ───────────────────────────────────────
    const hooperSliders = {
        fatigueHiSlider:  'fatigue-hi-badge',
        sleepQSlider:     'sleep-q-badge',
        sorenessHiSlider: 'soreness-hi-badge',
        stressHiSlider:   'stress-hi-badge',
        moodHiSlider:     'mood-hi-badge',
    };
    Object.entries(hooperSliders).forEach(([id, badgeId]) => {
        const sl = document.getElementById(id);
        const bg = document.getElementById(badgeId);
        if (sl && bg) {
            sl.addEventListener('input', () => { bg.textContent = sl.value; updateHooperScore(); });
        }
    });

    // Rec. 5: Hydration & Nutrition slider badges
    const hydSlider  = document.getElementById('hydrationSlider');
    const hydBadge   = document.getElementById('hydration-badge');
    const nutSlider  = document.getElementById('nutritionSlider');
    const nutBadge   = document.getElementById('nutrition-badge');
    if (hydSlider && hydBadge) hydSlider.addEventListener('input', () => { hydBadge.textContent = hydSlider.value; });
    if (nutSlider && nutBadge) nutSlider.addEventListener('input', () => { nutBadge.textContent = nutSlider.value; });

    function updateHooperScore() {
        const f  = parseInt(document.getElementById('fatigueHiSlider')?.value  || 4);
        const so = parseInt(document.getElementById('sorenessHiSlider')?.value || 4);
        const st = parseInt(document.getElementById('stressHiSlider')?.value   || 4);
        const m  = parseInt(document.getElementById('moodHiSlider')?.value     || 4);
        const sl = parseInt(document.getElementById('sleepQSlider')?.value    || 4);
        
        // Technically perfect formula: Fatigue + Soreness + Stress + (8 - Motivation) + (8 - SleepQuality)
        const score = f + so + st + (8 - m) + (8 - sl);
        
        const scoreEl = document.getElementById('hooper-score');
        const labelEl = document.getElementById('hooper-label');
        if (scoreEl) scoreEl.textContent = score;
        if (labelEl) {
            if (score <= 15) {
                labelEl.textContent = '✅ Good Readiness';
                labelEl.className = 'badge bg-success mt-1';
            } else if (score <= 25) {
                labelEl.textContent = '⚠️ Acceptable';
                labelEl.className = 'badge bg-warning text-dark mt-1';
            } else {
                labelEl.textContent = '🔴 At Risk — Reduce Load';
                labelEl.className = 'badge bg-danger mt-1';
            }
        }
    }
    updateHooperScore(); // initialise
}


document.getElementById('logTrainingForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const fd = new FormData(this);
    const body = Object.fromEntries(fd.entries());
    body.athlete_ids = [parseInt(body.athlete_id)];

    // Package Main Set Details into a single JSON field for Sprinter Specialization
    if (body.main_dist || body.main_effort || body.main_time) {
        body.main_set_details = JSON.stringify({
            dist: body.main_dist || 0,
            effort: body.main_effort || 0,
            time: body.main_time || 0,
            extra: body.extra_work || ''
        });
    }
    try {
        const res = await fetch('/api/training', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const d = await res.json();
        if (res.ok) {
            showToast('Training log submitted!');
            bootstrap.Modal.getInstance(document.getElementById('logTrainingModal'))?.hide();
            this.reset();
            loadTrainingLogs();
        } else { showToast(d.error || 'Error submitting log.', false); }
    } catch (err) { showToast('Network error.', false); }
});

document.getElementById('logWellnessForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const fd = new FormData(this);
    const body = Object.fromEntries(fd.entries());
    try {
        const res = await fetch('/api/wellness', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const d = await res.json();
        if (res.ok) {
            showToast('Wellness log submitted! Morning data recorded.');
            bootstrap.Modal.getInstance(document.getElementById('logWellnessModal'))?.hide();
            this.reset();
            loadAnalytics();
        } else {
            // Rec. 1: Show validation error from API
            const errMsg = d.error || 'Error submitting wellness log.';
            showToast(errMsg, false);
        }
    } catch (err) { showToast('Network error.', false); }
});

document.getElementById('logResultForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const fd = new FormData(this);
    const body = Object.fromEntries(fd.entries());
    try {
        const res = await fetch('/api/perf_result', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const d = await res.json();
        if (res.ok) {
            showToast('Result logged!');
            bootstrap.Modal.getInstance(document.getElementById('logResultModal'))?.hide();
            this.reset();
            loadAnalytics();
            loadResults();
        } else { showToast(d.error || 'Error.', false); }
    } catch (err) { showToast('Network error.', false); }
});

// ─── Multi-Event Training Form Specialization ───────────────────────────────
function getEventCategory(eventName) {
    if (/Sprint/i.test(eventName)) return 'Sprint';
    if (/Hurdle/i.test(eventName)) return 'Hurdles';
    if (/Steeplechase/i.test(eventName)) return 'Steeplechase';
    if (/Run|Walk/i.test(eventName)) return 'Run';
    if (/Jump|Vault/i.test(eventName)) return 'Jump';
    if (/Throw|Put|Discus|Hammer|Javelin/i.test(eventName)) return 'Throw';
    return 'Generic';
}

function populateMultiEventForm(allEvents) {
    const eventSelect = document.getElementById('portal-event-select');
    const workoutSelect = document.getElementById('workoutTypeSelect');
    const eventBadge   = document.getElementById('portal-event-badge');

    if (!eventSelect || !workoutSelect) return;

    // Handle multi-event primary strings (e.g. "100m Sprint, 200m Sprint")
    const primaryEvent = (typeof athleteEvent !== 'undefined' && athleteEvent.includes(',')) 
        ? athleteEvent.split(',')[0].trim() 
        : (typeof athleteEvent !== 'undefined' ? athleteEvent : (allEvents[0] || ''));
    const orderedEvents = [primaryEvent, ...allEvents.filter(e => e !== primaryEvent)];
    eventSelect.innerHTML = '';
    orderedEvents.forEach((ev, i) => {
        const opt = document.createElement('option');
        opt.value = ev;
        opt.textContent = i === 0 ? `${ev} (Primary)` : ev;
        eventSelect.appendChild(opt);
    });
    const resEventSelect = document.getElementById('portal-result-event-select');
    if (resEventSelect) {
        resEventSelect.innerHTML = orderedEvents.map(ev => `<option value="${ev}">${ev}</option>`).join('');
    }

    // Build merged workout drills from ALL athlete events
    function buildMergedDrills(eventsList) {
        const drills = new Set();
        const WMAP = typeof WORKOUT_MAP !== 'undefined' ? WORKOUT_MAP : {};
        eventsList.forEach(ev => {
            const cat = getEventCategory(ev);
            (WMAP[cat] || WMAP['Generic'] || []).forEach(d => drills.add(d));
        });
        // Always include these
        drills.add('Weight Room');
        drills.add('Active Recovery');
        return [...drills];
    }

    function setWorkoutOptions(eventsList, badgeLabel) {
        const merged = buildMergedDrills(eventsList);
        workoutSelect.innerHTML = merged.map(d => `<option value="${d}">${d}</option>`).join('');
        if (eventBadge) eventBadge.textContent = badgeLabel;
    }

    // Initial: show merged drills for all events
    setWorkoutOptions(orderedEvents, orderedEvents.length > 1 ? `${orderedEvents.length} Events` : primaryEvent);

    // When a specific event is selected → show only that event's drills
    eventSelect.addEventListener('change', function () {
        const selected = this.value;
        if (selected === '__all__') {
            setWorkoutOptions(orderedEvents, `${orderedEvents.length} Events`);
        } else {
            setWorkoutOptions([selected], selected);
        }
    });

    // Distance label based on primary event
    const distLabel = document.getElementById('portal-dist-label');
    const distHint  = document.getElementById('portal-dist-hint');
    const distInput = document.getElementById('portal-dist-input');
    if (/Throw|Put|Jump|Vault/i.test(primaryEvent)) {
        if (distLabel) distLabel.textContent = 'Best Mark (m)';
        if (distHint)  distHint.textContent  = 'Enter best throw/jump distance in metres.';
        if (distInput) distInput.placeholder  = '0.00';
    }
}

// ─── Bootstrap ───────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    setupIntensitySliders();

    // Load analytics first (which returns available_events), then specialize form
    fetch(`/api/analytics/athlete/${athleteId}`)
        .then(r => r.json())
        .then(data => {
            const allEvents = data.available_events || (typeof athleteEvent !== 'undefined' ? [athleteEvent] : []);
            populateMultiEventForm(allEvents);
        })
        .catch(() => {
            // Fallback: use primary event only
            if (typeof athleteEvent !== 'undefined') populateMultiEventForm([athleteEvent]);
        });

    loadAnalytics();
    loadTrainingLogs();
    loadResults();

    handleForm('logTrainingForm', '/api/training', 'Training log submitted!');
    handleForm('logWellnessForm', '/api/wellness', 'Wellness log submitted!');
    handleForm('logResultForm', '/api/perf_result', 'Competition result logged!');

    window.deleteWellnessLog = function(wellnessId) {
        if (!confirm('Are you sure you want to delete this wellness log?')) return;
        fetch(`/api/wellness/${wellnessId}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.message) {
                showToast('Wellness log deleted.');
                setTimeout(() => location.reload(), 1000);
            } else {
                showToast('Error: ' + data.error, 'danger');
            }
        })
        .catch(err => showToast('Network Error', 'danger'));
    };

    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(i => i.value = today);
});

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
                        <label class="text-muted small fw-bold d-block mb-1 text-jru-blue">WARM-UP / DRILLS</label>
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
    const modalEl = document.getElementById('dayDetailsModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

window.showSingleLogDetails = function(logId) {
    const log = allAthleteLogs.find(l => l.id === logId);
    if (!log) return;

    // Adapt to showDayDetails format to reuse template logic
    const detail = {
        date: log.date,
        has_data: true,
        training: {
            id: log.id,
            type: log.type,
            load: log.intensity * log.duration,
            volume_load: 0, // Not pre-calculated for history log response yet
            duration: log.duration,
            distance: log.distance,
            intensity: log.intensity,
            warmup_notes: log.warmup_notes,
            main_set_details: log.main_set_details
        },
        wellness: null // Not linked to individual log entries in this view
    };
    
    // Volume load check
    if (log.main_set_details) {
        try {
            const ms = JSON.parse(log.main_set_details);
            detail.training.volume_load = (ms.dist || 0) * ((ms.effort || 0) / 100);
        } catch(e) {}
    }

    showDayDetails(detail);
    // Override title for specific session
    setTimeout(() => {
        const titleEl = document.getElementById('day-details-title');
        if (titleEl) titleEl.innerHTML = `<i class="bi bi-journal-text me-2"></i>Session Breakdown &mdash; ${log.date}`;
    }, 5);
}

// ─── Change Password Form ─────────────────────────────────────────────────
document.getElementById('changePasswordForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const alertEl = document.getElementById('change-pwd-alert');
    const current  = document.getElementById('cpwd-current').value.trim();
    const newPwd   = document.getElementById('cpwd-new').value.trim();
    const confirm  = document.getElementById('cpwd-confirm').value.trim();

    alertEl.className = 'alert d-none py-2';

    try {
        const res = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_password: current, new_password: newPwd, confirm_password: confirm })
        });
        const data = await res.json();
        if (res.ok) {
            alertEl.className = 'alert alert-success py-2';
            alertEl.innerHTML = '<i class="bi bi-check-circle me-1"></i> ' + data.message;
            this.reset();
        } else {
            alertEl.className = 'alert alert-danger py-2';
            alertEl.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i> ' + (data.error || 'An error occurred.');
        }
    } catch (err) {
        alertEl.className = 'alert alert-danger py-2';
        alertEl.innerHTML = '<i class="bi bi-wifi-off me-1"></i> Network error. Please try again.';
    }
});
