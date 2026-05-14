document.addEventListener("DOMContentLoaded", function() {
    loadPendingTraining();
    loadPendingResults();
});

function loadPendingTraining() {
    fetch('/api/approvals/training')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('pending-training-body');
            const countBadge = document.getElementById('training-count');
            
            if (data.logs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-5 text-muted">No pending training logs.</td></tr>';
                countBadge.style.display = 'none';
                document.getElementById('confirmAllTraining').disabled = true;
                return;
            }

            countBadge.textContent = data.logs.length;
            countBadge.style.display = 'inline-block';
            document.getElementById('confirmAllTraining').disabled = false;

            tbody.innerHTML = data.logs.map(log => `
                <tr>
                    <td><strong>${log.athlete_name}</strong></td>
                    <td>${log.date}</td>
                    <td><span class="badge bg-light text-dark border">${log.type}</span></td>
                    <td>${log.distance}m / ${log.duration}m</td>
                    <td class="fw-bold text-jru-blue">${log.load}</td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-success" onclick="approveLog(${log.id})">
                            <i class="bi bi-check-lg"></i> Confirm
                        </button>
                        <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteLog(${log.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        });
}

function loadPendingResults() {
    fetch('/api/approvals/results')
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('pending-results-body');
            const countBadge = document.getElementById('results-count');
            
            if (data.results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-5 text-muted">No pending competition results.</td></tr>';
                countBadge.style.display = 'none';
                document.getElementById('confirmAllResult').disabled = true;
                return;
            }

            countBadge.textContent = data.results.length;
            countBadge.style.display = 'inline-block';
            document.getElementById('confirmAllResult').disabled = false;

            tbody.innerHTML = data.results.map(res => `
                <tr>
                    <td><strong>${res.athlete_name}</strong></td>
                    <td>${res.date}</td>
                    <td><span class="badge bg-jru-blue">${res.event}</span></td>
                    <td class="fw-bold text-jru-gold fs-5">${res.value}</td>
                    <td class="text-muted small">${res.competition || '--'}</td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-success" onclick="approveResult(${res.id})">
                            <i class="bi bi-check-lg"></i> Verify
                        </button>
                        <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteResult(${res.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        });
}

window.approveLog = function(id) {
    fetch(`/api/training/confirm/${id}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast('Training log confirmed!');
            loadPendingTraining();
            updatePendingBadge(); // Shared navbar badge
        });
}

window.approveResult = function(id) {
    fetch(`/api/perf_result/confirm/${id}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast('Performance result verified!');
            loadPendingResults();
            updatePendingBadge();
        });
}

window.confirmAllTraining = function() {
    if (!confirm('Confirm all pending training logs?')) return;
    fetch('/api/training/confirm-all', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast('All logs confirmed!');
            loadPendingTraining();
            updatePendingBadge();
        });
}

window.confirmAllResults = function() {
    if (!confirm('Verify all pending competition results?')) return;
    fetch('/api/perf_result/confirm-all', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast('All results verified!');
            loadPendingResults();
            updatePendingBadge();
        });
}

window.deleteLog = function(id) {
    if (!confirm('Are you sure you want to delete this log?')) return;
    fetch(`/api/training/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            showToast('Log deleted.', 'warning');
            loadPendingTraining();
            updatePendingBadge();
        });
}

window.deleteResult = function(id) {
    if (!confirm('Are you sure you want to delete this result?')) return;
    fetch(`/api/perf_result/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            showToast('Result deleted.', 'warning');
            loadPendingResults();
            updatePendingBadge();
        });
}
