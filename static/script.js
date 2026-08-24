// DineMatch - Client-side JavaScript

// Utility function to show toast notifications
function showToast(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.insertBefore(alertDiv, document.body.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Format currency
function formatCurrency(amount) {
    return '₹' + amount.toFixed(2);
}

// Format JSON string to readable list
function formatList(jsonStr) {
    try {
        const arr = JSON.parse(jsonStr);
        return Array.isArray(arr) ? arr.join(', ') : jsonStr;
    } catch {
        return jsonStr;
    }
}

// Initialize tooltips (if using Bootstrap tooltips)
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initTooltips();
});

// API Helper Functions
const API = {
    async createGroup(groupName, memberCount) {
        return fetch('/create_group', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({group_name: groupName, member_count: memberCount})
        }).then(r => r.json());
    },
    
    async joinGroup(groupCode, name) {
        return fetch('/join_group', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({group_code: groupCode, name: name})
        }).then(r => r.json());
    },
    
    async submitPreferences(data) {
        return fetch('/preferences', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        }).then(r => r.json());
    },
    
    async submitVote(groupId, memberId, restaurantId) {
        return fetch(`/group/${groupId}/vote`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({member_id: memberId, restaurant_id: restaurantId})
        }).then(r => r.json());
    },
    
    async splitBill(total, members, tip = 0) {
        return fetch('/split_bill', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({total, members, tip})
        }).then(r => r.json());
    },
    
    async getVotes(groupId) {
        return fetch(`/api/group/${groupId}/votes`)
            .then(r => r.json());
    },
    
    async getMembersCount(groupId) {
        return fetch(`/api/group/${groupId}/members-count`)
            .then(r => r.json());
    }
};

// Export for use in templates
window.API = API;
window.showToast = showToast;
window.formatCurrency = formatCurrency;
window.formatList = formatList;
