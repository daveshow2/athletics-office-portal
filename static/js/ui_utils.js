/**
 * Global UI Utilities for JRU Track & Field Platform
 */

function showToast(message, type = 'success') {
    const toastEl = document.getElementById('liveToast');
    const toastBody = document.getElementById('toast-message');
    const toastHeader = toastEl.querySelector('.toast-header');
    
    if (!toastEl || !toastBody) {
        console.error("Toast elements not found in DOM");
        alert(message); // Fallback
        return;
    }

    toastBody.textContent = message;
    
    // Style based on type
    toastHeader.className = 'toast-header text-white';
    if (type === 'success') {
        toastHeader.classList.add('bg-success');
    } else if (type === 'danger' || type === 'error') {
        toastHeader.classList.add('bg-danger');
    } else if (type === 'warning') {
        toastHeader.classList.add('bg-warning', 'text-dark');
    } else {
        toastHeader.classList.add('jru-navbar'); // JRU Deep Blue
    }
    
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

// Set default date for all date inputs found in the page
document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll('input[type="date"]').forEach(input => {
        if (!input.value) {
            input.value = new Date().toISOString().split('T')[0];
        }
    });
});

// Specialized Workout Mappings
const WORKOUT_MAP = {
    'Sprint': ['Block Starts', 'Max Velocity', 'Acceleration', 'Speed Endurance', 'Relay Drills'],
    'Run': ['Tempo Run', 'Intervals', 'Long Slow Distance (LSD)', 'Threshold Run', 'Fartlek'],
    'Hurdles': ['Hurdle Technique', 'Lead Leg Drills', 'Trail Leg Drills', 'Full Flights', 'Hurdle Mobility'],
    'Steeplechase': ['Water Jump Drills', 'Barrier Technique', 'Steeple Intervals', 'LSD', 'Fartlek'],
    'Jump': ['Approach Work', 'Technical Jumps', 'Box Jumps', 'Plyometrics', 'Landing Drills'],
    'Throw': ['Technique Drills', 'Full Throws', 'Medicine Ball Work', 'Specific Strength', 'Release Drills'],
    'Shot Put': ['Technique Drills', 'Full Throws', 'Medicine Ball Work', 'Specific Strength', 'Release Drills'],
    'Generic': ['Track Session', 'Weight Room', 'Active Recovery', 'Mobility', 'General Drills']
};

/**
 * Dynamically updates the training log form based on selected athletes' events
 * @param {Array} athleteIds - Selected athlete IDs
 * @param {Array} athletesList - Reference list of all athletes with events
 */
function specializeTrainingForm(athleteIds, athletesList) {
    const workoutSelect = document.getElementById('workoutTypeSelect');
    if (!workoutSelect) return;

    if (!athleteIds || athleteIds.length === 0) {
        updateWorkoutOptions(workoutSelect, 'Generic');
        return;
    }

    // Find events for selected athletes
    const selectedAthletes = athletesList.filter(a => athleteIds.includes(String(a.id)));
    
    if (selectedAthletes.length === 0) {
        updateWorkoutOptions(workoutSelect, 'Generic');
        return;
    }

    const uniqueEvents = [...new Set(selectedAthletes.map(a => a.event))];

    let category = 'Generic';
    
    // Check for categories across all selected athletes
    const isAllSprint = selectedAthletes.every(a => /Sprint/i.test(a.event));
    const isAllRun = selectedAthletes.every(a => /Run/i.test(a.event) && !/Sprint/i.test(a.event));
    const isAllHurdles = selectedAthletes.every(a => /Hurdle/i.test(a.event));
    const isAllJump = selectedAthletes.every(a => /Jump/i.test(a.event));
    const isAllThrow = selectedAthletes.every(a => /Throw|Put/i.test(a.event));
    const isAllSteeple = selectedAthletes.every(a => /Steeplechase/i.test(a.event));

    if (isAllSprint) category = 'Sprint';
    else if (isAllRun) category = 'Run';
    else if (isAllHurdles) category = 'Hurdles';
    else if (isAllJump) category = 'Jump';
    else if (isAllThrow) category = 'Throw';
    else if (isAllSteeple) category = 'Steeplechase';

    updateWorkoutOptions(workoutSelect, category);
}

function updateWorkoutOptions(select, category) {
    const currentVal = select.value;
    const workouts = WORKOUT_MAP[category] || WORKOUT_MAP['Generic'];
    
    select.innerHTML = '';
    
    // Always include a general option if it's specialized
    if (category !== 'Generic') {
        const opt = document.createElement('option');
        opt.value = 'General Drills';
        opt.textContent = 'General Drills';
        select.appendChild(opt);
    }

    workouts.forEach(w => {
        const opt = document.createElement('option');
        opt.value = w;
        opt.textContent = w;
        select.appendChild(opt);
    });

    // Add standard ones
    ['Weight Room', 'Active Recovery'].forEach(w => {
        const opt = document.createElement('option');
        opt.value = w;
        opt.textContent = w;
        select.appendChild(opt);
    });

    // Try to restore value if it still exists
    if ([...select.options].some(o => o.value === currentVal)) {
        select.value = currentVal;
    }
}

// Global Intensity Range Value Display Logic
document.addEventListener("input", function(e) {
    if (e.target && e.target.classList.contains('intensity-range')) {
        const valueSpan = e.target.closest('.mb-3').querySelector('.intensity-value');
        if (valueSpan) {
            valueSpan.textContent = e.target.value;
        }
    }
});

/**
 * Handle Training Form Field Visibility (Realistic Situations)
 * Hides Distance field for Weight Room, Active Recovery, and Mobility
 * as they typically don't have a track distance in meters.
 */
document.addEventListener("change", function(e) {
    if (e.target && e.target.id === 'workoutTypeSelect') {
        toggleDistanceField(e.target);
    }
});

function toggleDistanceField(selectEl) {
    const distanceContainer = document.getElementById('training-distance-container');
    if (!distanceContainer) return;

    const distanceInput = distanceContainer.querySelector('input[name="distance"]');
    const type = selectEl.value;

    // List of types that don't require distance
    const noDistanceTypes = ['Weight Room', 'Active Recovery', 'Mobility', 'Recovery'];

    if (noDistanceTypes.includes(type)) {
        distanceContainer.style.display = 'none';
        if (distanceInput) {
            distanceInput.required = false;
            distanceInput.value = 0; // Set to 0 for backend consistency
        }
    } else {
        distanceContainer.style.display = 'block';
        if (distanceInput) {
            distanceInput.required = true;
            // Only clear it if it was 0 from a previous hide
            if (distanceInput.value === "0") distanceInput.value = "";
        }
    }
}

// Ensure initial state is correct on page load/modal open
document.addEventListener("DOMContentLoaded", function() {
    const workoutSelect = document.getElementById('workoutTypeSelect');
    if (workoutSelect) {
        toggleDistanceField(workoutSelect);
    }
});

// Since modals might reset content, we also listen for modal shown events
document.addEventListener('shown.bs.modal', function (event) {
    const workoutSelect = event.target.querySelector('#workoutTypeSelect');
    if (workoutSelect) {
        toggleDistanceField(workoutSelect);
    }
});

// Global Pending Approval Notification
function updatePendingBadge() {
    fetch('/api/approvals/count')
        .then(res => res.json())
        .then(data => {
            const badge = document.getElementById('global-pending-badge');
            if (badge) {
                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(err => console.error('Error fetching pending count:', err));
}

document.addEventListener('DOMContentLoaded', updatePendingBadge);
