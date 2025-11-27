(function(){
    const adminDashboardData = window.adminDashboardData || {};
    
    const visitsCtx = document.getElementById('overallVisitsChart');
    let visitsChart = null;
    if (visitsCtx) {
        visitsChart = new Chart(visitsCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: adminDashboardData.overall_visits_labels || [],
                datasets: [{
                    label: 'Записей',
                    data: adminDashboardData.overall_visits_data || [],
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13,110,253,.15)',
                    tension: .3,
                    pointRadius: 2
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        });
    }

    document.querySelectorAll('.btn-overall-period').forEach(btn => {
        btn.addEventListener('click', function(){
            const period = this.getAttribute('data-period');
            const url = adminDashboardData.overall_visits_url;
            if (!url) return;
            fetch(url + '?period=' + period, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json())
                .then(payload => {
                    if (!visitsChart) return;
                    visitsChart.data.labels = payload.labels;
                    visitsChart.data.datasets[0].data = payload.data;
                    visitsChart.update();
                });
        })
    });

    document.querySelectorAll('.btn-status-period').forEach(btn => {
        btn.addEventListener('click', function(){
            const period = this.getAttribute('data-period');
            const url = adminDashboardData.overall_statuses_url;
            if (!url) return;
            fetch(url + '?period=' + period, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(r => r.json())
                .then(payload => {
                    const tbody = document.getElementById('overallStatusTableBody');
                    if (!tbody) return;
                    const rows = (payload.items || []).map(item => {
                        const badgeClass = item.status === 'SCHEDULED' ? 'bg-primary' :
                                           item.status === 'IN_PROGRESS' ? 'bg-warning' :
                                           item.status === 'COMPLETED' ? 'bg-success' :
                                           item.status === 'CANCELLED' ? 'bg-danger' : 'bg-secondary';
                        return `<tr>
                            <td><span class="badge ${badgeClass}">${item.label}</span></td>
                            <td class="text-end"><strong>${item.count}</strong></td>
                        </tr>`;
                    });
                    tbody.innerHTML = rows.length ? rows.join('') : '<tr><td colspan="2" class="text-center text-muted py-3">Нет данных</td></tr>';
                });
        })
    });

    const serviceCtx = document.getElementById('overallServicesChart');
    if (serviceCtx) {
        new Chart(serviceCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: adminDashboardData.overall_service_labels || [],
                datasets: [{
                    data: adminDashboardData.overall_service_data || [],
                    backgroundColor: ['#0d6efd','#6610f2','#6f42c1','#d63384','#dc3545','#fd7e14','#ffc107','#198754','#20c997','#0dcaf0'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } } }
        });
    }
})();
