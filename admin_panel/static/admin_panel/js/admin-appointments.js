/**
 * Admin Appointments Page - Filtering and AJAX Updates
 * Handles appointment table filtering, status updates, and comment additions
 */

document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    const elements = {
        form: document.getElementById('filtersForm'),
        branchSelect: document.getElementById('filterBranch'),
        dateFrom: document.getElementById('filterDateFrom'),
        dateTo: document.getElementById('filterDateTo'),
        userInput: document.getElementById('filterUser'),
        plateInput: document.getElementById('filterPlate'),
        statusChecks: document.querySelectorAll('.status-check'),
        statusLabel: document.getElementById('statusDropdownLabel'),
        clearStatusesBtn: document.getElementById('clearStatuses'),
        resetBtn: document.getElementById('resetFilters'),
        tableBody: document.querySelector('#appointmentsTableBody'),
        pagination: document.querySelector('#appointmentsPagination')
    };

    /**
     * Build URL with current filter parameters
     * @param {string} baseUrl - Base URL to append parameters to
     * @returns {URL} URL object with filters
     */
    function buildFiltersUrl(baseUrl) {
        const url = new URL(baseUrl, window.location.origin);
        
        if (elements.branchSelect && elements.branchSelect.value) {
            url.searchParams.set('branch', elements.branchSelect.value);
        }
        if (elements.dateFrom && elements.dateFrom.value) {
            url.searchParams.set('date_from', elements.dateFrom.value);
        }
        if (elements.dateTo && elements.dateTo.value) {
            url.searchParams.set('date_to', elements.dateTo.value);
        }
        if (elements.userInput && elements.userInput.value.trim()) {
            url.searchParams.set('user', elements.userInput.value.trim());
        }
        if (elements.plateInput && elements.plateInput.value.trim()) {
            url.searchParams.set('plate', elements.plateInput.value.trim());
        }

        const currentParams = new URLSearchParams(window.location.search);
        if (currentParams.has('page')) {
            url.searchParams.set('page', currentParams.get('page'));
        }

        elements.statusChecks.forEach(checkbox => {
            if (checkbox.checked) {
                url.searchParams.append('status', checkbox.value);
            }
        });

        return url;
    }

    /**
     * Replace appointments table and pagination from HTML response
     * @param {string} html - HTML response from server
     */
    function replaceAppointmentsFromHtml(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        const newBody = doc.querySelector('#appointmentsTableBody');
        if (newBody && elements.tableBody) {
            elements.tableBody.innerHTML = newBody.innerHTML;
        }
        
        const newPagination = doc.querySelector('#appointmentsPagination');
        if (newPagination && elements.pagination) {
            elements.pagination.innerHTML = newPagination.innerHTML;
        }
        
        const totalElNew = doc.querySelector('.card-header .text-muted.small');
        const totalElCur = document.querySelector('.card-header .text-muted.small');
        if (totalElNew && totalElCur) {
            totalElCur.textContent = totalElNew.textContent;
        }
        
        bindInlineRowHandlers();
        bindPaginationLinks();
    }

    /**
     * Fetch appointments with filters and replace table
     * @param {URL} url - URL with filters
     */
    function fetchAndReplace(url) {
        fetch(url, { 
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.text())
        .then(html => replaceAppointmentsFromHtml(html))
        .catch(err => console.error('Error fetching appointments:', err));
    }

    /**
     * Handle status filter changes
     */
    function onStatusesChanged() {
        updateStatusLabel();
        const url = buildFiltersUrl(window.location.pathname);
        history.replaceState({}, '', url);
        fetchAndReplace(url);
    }

    /**
     * Build URL for updating appointment
     * @param {string} id - Appointment ID
     * @returns {string} Update URL
     */
    function buildUpdateUrl(id) {
        // Template URL will be provided by Django template
        if (window.appointmentUpdateUrlTemplate) {
            return window.appointmentUpdateUrlTemplate.replace('00000000-0000-0000-0000-000000000000', id);
        }
        return '';
    }

    /**
     * Get CSRF token from cookies or form
     * @returns {string} CSRF token
     */
    function getCsrf() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';').map(v => v.trim());
        for (const c of cookies) {
            if (c.startsWith(name + '=')) {
                return c.slice(name.length + 1);
            }
        }
        const inp = document.querySelector('input[name=csrfmiddlewaretoken]');
        return inp ? inp.value : '';
    }

    /**
     * Bind event handlers to appointment row elements (status selects and comment buttons)
     */
    function bindInlineRowHandlers() {
        // Status update handlers
        document.querySelectorAll('select.appt-status').forEach(function(select) {
            select.addEventListener('change', function() {
                const tr = this.closest('tr');
                const id = tr.getAttribute('data-id');
                const formData = new FormData();
                formData.append('status', this.value);
                
                fetch(buildUpdateUrl(id), { 
                    method: 'POST', 
                    headers: { 
                        'X-Requested-With': 'XMLHttpRequest', 
                        'X-CSRFToken': getCsrf() 
                    }, 
                    body: formData 
                })
                .then(response => response.json())
                .then(data => {
                    // Handle response if needed
                })
                .catch(err => console.error('Error updating status:', err));
            });
        });

        // Comment append handlers
        document.querySelectorAll('.btn-append-comment').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const tr = this.closest('tr');
                const id = tr.getAttribute('data-id');
                const input = tr.querySelector('.appt-comment');
                const text = (input.value || '').trim();
                
                if (!text) return;
                
                const formData = new FormData();
                formData.append('comment', text);
                
                fetch(buildUpdateUrl(id), { 
                    method: 'POST', 
                    headers: { 
                        'X-Requested-With': 'XMLHttpRequest', 
                        'X-CSRFToken': getCsrf() 
                    }, 
                    body: formData 
                })
                .then(response => response.json())
                .then(payload => {
                    input.value = '';
                    const notesWrap = tr.querySelector('.notes-cell');
                    if (notesWrap) {
                        const prev = notesWrap.querySelector('.small.text-muted');
                        const html = `<div class="small text-muted mt-1">${(payload.notes || '').replace(/\n/g, '<br/>')}</div>`;
                        if (prev) {
                            prev.outerHTML = html;
                        } else {
                            notesWrap.insertAdjacentHTML('beforeend', html);
                        }
                    }
                })
                .catch(err => console.error('Error adding comment:', err));
            });
        });
    }

    /**
     * Update status dropdown label with count of selected statuses
     */
    function updateStatusLabel() {
        const count = Array.from(elements.statusChecks).filter(c => c.checked).length;
        if (elements.statusLabel) {
            elements.statusLabel.textContent = count ? `Выбрано: ${count}` : 'Все статусы';
        }
    }

    /**
     * Handle Enter key press in filter inputs
     * @param {KeyboardEvent} e - Keyboard event
     */
    function submitOnEnter(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            onStatusesChanged();
        }
    }

    /**
     * Bind click handlers to pagination links
     */
    function bindPaginationLinks() {
        document.querySelectorAll('#appointmentsPagination a.page-link').forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const href = link.getAttribute('href');
                const url = new URL(href, window.location.origin);
                const built = buildFiltersUrl(window.location.pathname);
                
                if (url.searchParams.get('page')) {
                    built.searchParams.set('page', url.searchParams.get('page'));
                }
                
                history.replaceState({}, '', built);
                fetchAndReplace(built);
            });
        });
    }

    // Initialize event listeners
    if (elements.branchSelect) {
        elements.branchSelect.addEventListener('change', onStatusesChanged);
    }
    if (elements.dateFrom) {
        elements.dateFrom.addEventListener('change', onStatusesChanged);
    }
    if (elements.dateTo) {
        elements.dateTo.addEventListener('change', onStatusesChanged);
    }
    
    elements.statusChecks.forEach(checkbox => {
        checkbox.addEventListener('change', onStatusesChanged);
    });

    if (elements.userInput) {
        elements.userInput.addEventListener('keydown', submitOnEnter);
    }
    if (elements.plateInput) {
        elements.plateInput.addEventListener('keydown', submitOnEnter);
    }

    if (elements.clearStatusesBtn) {
        elements.clearStatusesBtn.addEventListener('click', function(e) {
            e.preventDefault();
            elements.statusChecks.forEach(ch => ch.checked = false);
            updateStatusLabel();
            onStatusesChanged();
        });
    }

    if (elements.resetBtn) {
        elements.resetBtn.addEventListener('click', function() {
            if (elements.branchSelect) elements.branchSelect.value = '';
            if (elements.dateFrom) elements.dateFrom.value = '';
            if (elements.dateTo) elements.dateTo.value = '';
            if (elements.userInput) elements.userInput.value = '';
            if (elements.plateInput) elements.plateInput.value = '';
            elements.statusChecks.forEach(ch => ch.checked = false);
            updateStatusLabel();
            onStatusesChanged();
        });
    }

    // Clear input buttons
    document.querySelectorAll('.btn-clear-input').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (input) {
                input.value = '';
                onStatusesChanged();
            }
        });
    });

    // Initialize
    updateStatusLabel();
    bindInlineRowHandlers();
    bindPaginationLinks();
});
