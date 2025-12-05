function makeLine(ctx, labels, data, color){
    return new Chart(ctx, {
        type: 'line',
        data: {
        labels,
        datasets: [{
            label: 'Записей',
            data,
            borderColor: color,
            backgroundColor: 'rgba(13,110,253,0.1)',
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBackgroundColor: color,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
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
            backgroundColor: 'rgba(0,0,0,0.8)',
            padding: 12,
            borderRadius: 8,
            titleFont: { size: 14, weight: 'bold' },
            bodyFont: { size: 13 }
            }
        },
        scales: {
            y: {
            beginAtZero: true,
            ticks: { stepSize: 1 },
            grid: { color: 'rgba(0,0,0,0.05)' }
            },
            x: {
            grid: { display: false }
            }
        }
        }
    });
}

function makeBar(ctx, labels, data, color){
return new Chart(ctx, {
    type: 'bar',
    data: {
    labels,
    datasets: [{
        label: 'Количество',
        data,
        backgroundColor: color,
        borderRadius: 8,
        borderSkipped: false
    }]
    },
    options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
        backgroundColor: 'rgba(0,0,0,0.8)',
        padding: 12,
        borderRadius: 8
        }
    },
    scales: {
        y: {
        beginAtZero: true,
        ticks: { stepSize: 1 },
        grid: { color: 'rgba(0,0,0,0.05)' }
        },
        x: {
        grid: { display: false }
        }
    }
    }
});
}

function makeDoughnut(ctx, labels, data){
return new Chart(ctx, {
    type: 'doughnut',
    data: {
    labels,
    datasets: [{
        data,
        backgroundColor: [
        '#0d6efd', '#6610f2', '#6f42c1', '#d63384',
        '#dc3545', '#fd7e14', '#ffc107', '#198754',
        '#20c997', '#0dcaf0'
        ],
        borderWidth: 3,
        borderColor: '#fff',
        hoverOffset: 10
    }]
    },
    options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
        position: 'bottom',
        labels: {
            padding: 15,
            usePointStyle: true,
            font: { size: 12 }
        }
        },
        tooltip: {
        backgroundColor: 'rgba(0,0,0,0.8)',
        padding: 12,
        borderRadius: 8
        }
    }
    }
});
}