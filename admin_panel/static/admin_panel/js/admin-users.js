document.addEventListener('DOMContentLoaded', function(){
    const form = document.getElementById('userFiltersForm');
    const resetBtn = document.getElementById('resetFilters');
    const tableContainer = document.querySelector('.dashboard-card:last-child');

    function buildQueryString(){
        const formData = new FormData(form);
        const params = new URLSearchParams();
        for (const [key, value] of formData.entries()) {
        if (value) params.append(key, value);
        }
        return params.toString();
    }

    function fetchUsers(){
        const queryString = buildQueryString();
        const url = window.location.pathname + (queryString ? '?' + queryString : '');
        
        fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.text())
        .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newTable = doc.querySelector('.dashboard-card:last-child');
        if (newTable && tableContainer) {
            tableContainer.innerHTML = newTable.innerHTML;
        }
        })
        .catch(err => console.error('Fetch error:', err));
        
        history.replaceState({}, '', url);
    }

    function submitOnEnter(e){ 
        if (e.key === 'Enter') { 
        e.preventDefault(); 
        fetchUsers(); 
        } 
    }

    function debounce(fn, delay){ 
        let t; 
        return function(...args){ 
        clearTimeout(t); 
        t = setTimeout(()=>fn.apply(this,args), delay); 
        }; 
    }

    const debouncedFetch = debounce(fetchUsers, 500);

    if (form) {
        form.querySelectorAll('input[type="date"]').forEach(el => 
        el.addEventListener('change', fetchUsers)
        );
        form.querySelectorAll('input[type="checkbox"]').forEach(el => 
        el.addEventListener('change', fetchUsers)
        );
        form.querySelectorAll('input[type="text"]').forEach(el => {
        el.addEventListener('keydown', submitOnEnter);
        el.addEventListener('input', debouncedFetch);
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', function(){
        form.querySelectorAll('input[type="text"]').forEach(el => el.value = '');
        form.querySelectorAll('input[type="date"]').forEach(el => el.value = '');
        form.querySelectorAll('input[type="checkbox"]').forEach(el => el.checked = false);
        fetchUsers();
        });
    }

    document.querySelectorAll('.btn-clear-input').forEach(function(btn){
        btn.addEventListener('click', function(){
        const targetId = this.getAttribute('data-target');
        const input = document.getElementById(targetId);
        if (input){ 
            input.value = ''; 
            fetchUsers(); 
        }
        });
    });
});