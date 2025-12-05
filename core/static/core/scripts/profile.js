(function(){
  const visits = { labels: window.profileData?.labels || [], data: window.profileData?.data || [] };
  const services = { labels: window.profileData?.top_services_labels || [], data: window.profileData?.top_services_data || [] };
  const centers = { labels: window.profileData?.top_centers_labels || [], data: window.profileData?.top_centers_data || [] };
  const weekday = { labels: window.profileData?.weekday_labels || [], data: window.profileData?.weekday_data || [] };
  const hours = { labels: Array.from({length:24}, (_,i)=> (i<10? '0':'')+i+':00'), data: window.profileData?.hour_data || [] };

        function makeLine(ctx, labels, data, color){
            return new Chart(ctx, { type:'line', data:{ labels, datasets:[{ data, label:'Записей', borderColor: color, backgroundColor: 'rgba(13,110,253,.1)', tension:.3, pointRadius: 2 }] }, options:{ responsive:true, maintainAspectRatio:false, scales:{ y:{ beginAtZero:true, ticks:{ stepSize:1 } } } } });
        }
        function makeBar(ctx, labels, data, color){
            return new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ data, label:'Кол-во', backgroundColor: color }] }, options:{ responsive:true, maintainAspectRatio:false, scales:{ y:{ beginAtZero:true, ticks:{ stepSize:1 } } } } });
        }
        function makeDoughnut(ctx, labels, data){
            return new Chart(ctx, { type:'doughnut', data:{ labels, datasets:[{ data, backgroundColor:['#0d6efd','#6610f2','#6f42c1','#d63384','#dc3545','#fd7e14','#ffc107','#198754','#20c997','#0dcaf0'] }] }, options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'bottom' } } } });
        }

    let chartsInitialized = false;
    let charts = [];
  function initCharts(){
    if (chartsInitialized) return;
    chartsInitialized = true;
                const dpr = window.devicePixelRatio || 1;
                function init(id, builder){
                        const canvas = document.getElementById(id);
                        if (!canvas) return null;
                        const parent = canvas.parentElement;
                        const width = parent.clientWidth;
                        const height = parent.clientHeight;
                        canvas.width = Math.floor(width * dpr);
                        canvas.height = Math.floor(height * dpr);
                        canvas.style.width = width + 'px';
                        canvas.style.height = height + 'px';
                        const ctx = canvas.getContext('2d');
                        return builder(ctx);
                }
                const visitsChart = init('visitsChart', (ctx)=> makeLine(ctx, visits.labels, visits.data, '#0d6efd'));
                const servicesChart = init('servicesChart', (ctx)=> makeDoughnut(ctx, services.labels, services.data));
                const centersChart = init('centersChart', (ctx)=> makeDoughnut(ctx, centers.labels, centers.data));
                const weekdayChart = init('weekdayChart', (ctx)=> makeBar(ctx, weekday.labels, weekday.data, '#198754'));
                const hoursChart = init('hoursChart', (ctx)=> makeBar(ctx, hours.labels, hours.data, '#6c757d'));
                if (visitsChart) charts.push(visitsChart);
                if (servicesChart) charts.push(servicesChart);
                if (centersChart) charts.push(centersChart);
                if (weekdayChart) charts.push(weekdayChart);
                if (hoursChart) charts.push(hoursChart);
  }

  const statsTab = document.getElementById('stats-tab');
  if (statsTab){
        statsTab.addEventListener('shown.bs.tab', function(){
            requestAnimationFrame(()=> setTimeout(initCharts, 0));
        });
  }
})();
