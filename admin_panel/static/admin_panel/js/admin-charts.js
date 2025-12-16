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
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: color,
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            fill: true,
            borderWidth: 2
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
                backgroundColor: 'rgba(0,0,0,0.85)',
                padding: 10,
                borderRadius: 6,
                titleFont: { size: 13, weight: '600' },
                bodyFont: { size: 12 },
                displayColors: false
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: { 
                    stepSize: 1,
                    font: { size: 11 },
                    padding: 8
                },
                grid: { 
                    color: 'rgba(0,0,0,0.04)',
                    drawBorder: false
                }
            },
            x: {
                ticks: {
                    font: { size: 11 },
                    maxRotation: 45,
                    minRotation: 0
                },
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
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 50
    }]
    },
    options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            padding: 10,
            borderRadius: 6,
            titleFont: { size: 13, weight: '600' },
            bodyFont: { size: 12 },
            displayColors: false
        }
    },
    scales: {
        y: {
            beginAtZero: true,
            ticks: { 
                stepSize: 1,
                font: { size: 11 },
                padding: 8
            },
            grid: { 
                color: 'rgba(0,0,0,0.04)',
                drawBorder: false
            }
        },
        x: {
            ticks: {
                font: { size: 11 }
            },
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
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 8
    }]
    },
    options: {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
        legend: {
            position: 'bottom',
            labels: {
                padding: 12,
                usePointStyle: true,
                pointStyle: 'circle',
                font: { size: 11 },
                boxWidth: 8,
                boxHeight: 8
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            padding: 10,
            borderRadius: 6,
            titleFont: { size: 13, weight: '600' },
            bodyFont: { size: 12 },
            displayColors: true,
            boxWidth: 10,
            boxHeight: 10
        }
    }
    }
});
}