/**
 * Admin Dashboard Charts and Interactive Elements
 * Handles Chart.js visualizations and AJAX interactions for the admin dashboard
 */

(function() {
    'use strict';

    // Chart.js global configuration
    Chart.defaults.color = '#6c757d';

    /**
     * Initialize overall visits line chart
     * @param {Object} chartData - Data object with labels and data arrays
     * @param {string} updateUrl - URL for AJAX updates
     */
    function initVisitsChart(chartData, updateUrl) {
        const visitsCtx = document.getElementById('overallVisitsChart');
        if (!visitsCtx) return null;

        const ctx = visitsCtx.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 320);
        gradient.addColorStop(0, 'rgba(13, 110, 253, 0.3)');
        gradient.addColorStop(1, 'rgba(13, 110, 253, 0.01)');

        const visitsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Записей',
                    data: chartData.data,
                    borderColor: '#0d6efd',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#0d6efd',
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: '#0d6efd',
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        displayColors: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, padding: 10 },
                        grid: { color: 'rgba(0,0,0,0.05)', drawBorder: false }
                    },
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { padding: 10 }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });

        // Setup period filter buttons
        setupPeriodFilters('.btn-overall-period', updateUrl, visitsChart);

        return visitsChart;
    }

    /**
     * Initialize overall services doughnut chart
     * @param {Object} chartData - Data object with labels and data arrays
     */
    function initServicesChart(chartData) {
        const serviceCtx = document.getElementById('overallServicesChart');
        if (!serviceCtx) return null;

        return new Chart(serviceCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: chartData.labels,
                datasets: [{
                    data: chartData.data,
                    backgroundColor: [
                        '#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545',
                        '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0'
                    ],
                    borderWidth: 3,
                    borderColor: '#fff',
                    hoverOffset: 15
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed + ' записей';
                                return label;
                            }
                        }
                    }
                },
                cutout: '65%'
            }
        });
    }

    /**
     * Setup period filter buttons for charts
     * @param {string} selector - Button selector
     * @param {string} updateUrl - AJAX endpoint URL
     * @param {Chart} chart - Chart.js instance to update
     */
    function setupPeriodFilters(selector, updateUrl, chart) {
        document.querySelectorAll(selector).forEach(btn => {
            btn.addEventListener('click', function() {
                // Update active state
                document.querySelectorAll(selector).forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const period = this.getAttribute('data-period');
                fetch(`${updateUrl}?period=${period}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                    .then(r => r.json())
                    .then(payload => {
                        if (!chart) return;
                        chart.data.labels = payload.labels;
                        chart.data.datasets[0].data = payload.data;
                        chart.update();
                    })
                    .catch(err => console.error('Error updating chart:', err));
            });
        });
    }

    /**
     * Setup status table period filters
     * @param {string} updateUrl - AJAX endpoint URL
     */
    function setupStatusFilters(updateUrl) {
        document.querySelectorAll('.btn-status-period').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.btn-status-period').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const period = this.getAttribute('data-period');
                fetch(`${updateUrl}?period=${period}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                    .then(r => r.json())
                    .then(payload => {
                        updateStatusTable(payload.items || []);
                    })
                    .catch(err => console.error('Error updating status table:', err));
            });
        });
    }

    /**
     * Update status table with new data
     * @param {Array} items - Array of status items
     */
    function updateStatusTable(items) {
        const tbody = document.getElementById('overallStatusTableBody');
        if (!tbody) return;

        const rows = items.map(item => {
            const badgeClass = getStatusBadgeClass(item.status);
            return `<tr>
                <td><span class="badge ${badgeClass}">${item.label}</span></td>
                <td class="text-end"><strong>${item.count}</strong></td>
            </tr>`;
        });

        tbody.innerHTML = rows.length ? rows.join('') : 
            '<tr><td colspan="2" class="text-center text-muted py-3">Нет данных</td></tr>';
    }

    /**
     * Get Bootstrap badge class for appointment status
     * @param {string} status - Appointment status
     * @returns {string} Badge class
     */
    function getStatusBadgeClass(status) {
        const statusMap = {
            'SCHEDULED': 'bg-primary',
            'IN_PROGRESS': 'bg-warning',
            'COMPLETED': 'bg-success',
            'CANCELLED': 'bg-danger'
        };
        return statusMap[status] || 'bg-secondary';
    }

    /**
     * Initialize dashboard - called from template with data
     * @param {Object} config - Configuration object with chart data and URLs
     */
    window.initAdminDashboard = function(config) {
        // Initialize visits chart
        if (config.visitsChart) {
            initVisitsChart(config.visitsChart, config.visitsUpdateUrl);
        }

        // Initialize services chart
        if (config.servicesChart) {
            initServicesChart(config.servicesChart);
        }

        // Initialize status table filters
        if (config.statusUpdateUrl) {
            setupStatusFilters(config.statusUpdateUrl);
        }
    };

})();
