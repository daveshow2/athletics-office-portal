document.addEventListener("DOMContentLoaded", function() {
    
    // Fetch all athletes for the roster
    fetch('/api/athletes')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch roster');
            return response.json();
        })
        .then(data => {
            const tbody = document.getElementById('roster-table-body');
            if (!tbody) return;
            tbody.innerHTML = '';
            
            if (!data.athletes || data.athletes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">No athletes registered yet.</td></tr>';
                return;
            }

            data.athletes.forEach(athlete => {
                const row = `
                <tr>
                    <td class="fw-bold text-jru-blue">${athlete.name}</td>
                    <td>
                        <div class="fw-bold small text-muted uppercase" style="font-size:0.6rem;">${athlete.category}</div>
                        <div>${athlete.event}</div>
                    </td>
                    <td>
                        <div class="small fw-bold text-dark"><i class="bi bi-person-fill me-1"></i>${athlete.username}</div>
                        <button class="btn btn-sm btn-outline-warning py-0 px-2 mt-1" style="font-size:0.72rem;"
                            onclick="resetAthletePassword(${athlete.id}, '${athlete.name.replace("'", "\\'")}')">
                            <i class="bi bi-arrow-counterclockwise me-1"></i>Reset Password
                        </button>
                    </td>
                    <td>${athlete.age || '-'}</td>
                    <td>${athlete.height || '-'}</td>
                    <td>${athlete.weight || '-'}</td>
                    <td class="text-center">
                        <a href="/athlete/${athlete.id}" class="btn btn-sm btn-jru-outline me-1">View</a>
                        <button class="btn btn-sm btn-danger py-1 px-2" onclick="deleteAthlete(${athlete.id}, '${athlete.name.replace("'", "\\'")}')">
                            <i class="bi bi-trash"></i> Delete
                        </button>
                    </td>
                </tr>`;
                tbody.innerHTML += row;
            });
        })
        .catch(err => {
            console.error(err);
            const tbody = document.getElementById('roster-table-body');
            if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error loading roster.</td></tr>';
        });

    // Unified Form Handler
    function handleForm(formId, apiEndpoint, successMsg) {
        const form = document.getElementById(formId);
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                // Aggregate multiple events into a string
                if (formData.has('event')) {
                    data.event = formData.getAll('event').join(', ');
                }

                if (!data.event || data.event.length === 0) {
                    showToast('Please select at least one event.', 'danger');
                    return;
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

    // Delete Athlete Function (Globally accessible for the onclick)
    window.deleteAthlete = function(id, name) {
        if (confirm(`Are you sure you want to delete ${name}?\nThis will permanently remove all training and performance history.`)) {
            fetch(`/api/athlete/${id}`, {
                method: 'DELETE'
            })
            .then(res => res.json())
            .then(data => {
                if (data.message) {
                    showToast(data.message);
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showToast('Error: ' + data.error, 'danger');
                }
            })
            .catch(err => showToast('Network Error: ' + err, 'danger'));
        }
    };

    // Reset Athlete Password Function (Coach only)
    window.resetAthletePassword = function(id, name) {
        if (confirm(`Reset password for ${name}?\n\nTheir password will be reset to: athlete123`)) {
            fetch(`/api/athletes/${id}/reset-password`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.message) {
                    showToast(`✅ ${data.message}`, 'success');
                } else {
                    showToast('Error: ' + data.error, 'danger');
                }
            })
            .catch(err => showToast('Network Error: ' + err, 'danger'));
        }
    };
});
