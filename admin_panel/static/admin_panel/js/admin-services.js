document.addEventListener('DOMContentLoaded', function() {
  const searchInput = document.getElementById('searchService');
  const statusFilter = document.getElementById('filterStatus');
  const branchFilter = document.getElementById('filterBranch');
  const servicesContainer = document.getElementById('servicesContainer');
  const viewCardsBtn = document.getElementById('viewCards');
  const viewTableBtn = document.getElementById('viewTable');
  
  let originalCardsHTML = servicesContainer.innerHTML;
  let serviceCards = document.querySelectorAll('.service-card');

  if (viewCardsBtn && viewTableBtn) {
    viewCardsBtn.addEventListener('click', function() {
      viewCardsBtn.classList.add('active');
      viewTableBtn.classList.remove('active');
      servicesContainer.classList.remove('table-view');
      servicesContainer.classList.add('cards-view');
      
      servicesContainer.innerHTML = originalCardsHTML;
      serviceCards = document.querySelectorAll('.service-card');

      filterServices();
    });

    viewTableBtn.addEventListener('click', function() {
      viewTableBtn.classList.add('active');
      viewCardsBtn.classList.remove('active');
      servicesContainer.classList.remove('cards-view');
      servicesContainer.classList.add('table-view');
      convertToTableView();
    });
  }

  function convertToTableView() {
    if (!servicesContainer.classList.contains('table-view')) return;
   
    let tableHTML = `
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead class="table-light">
            <tr>
              <th>Название</th>
              <th>Описание</th>
              <th>Длительность</th>
              <th>Цена</th>
              <th>Филиал</th>
              <th>Статус</th>
              <th class="text-end">Действия</th>
            </tr>
          </thead>
          <tbody>
    `;
    
    serviceCards.forEach(card => {
      if (card.style.display === 'none') return;
      
      const name = card.querySelector('.service-name')?.textContent.trim() || '';
      const description = card.querySelector('.service-description')?.textContent.trim() || '—';
      const duration = card.querySelector('.detail-value')?.textContent.trim() || '';
      const price = card.querySelectorAll('.detail-value')[1]?.textContent.trim() || '';
      const branch = card.querySelectorAll('.detail-value')[2]?.textContent.trim() || '';
      const status = card.dataset.status === 'active' ? 
        '<span class="badge bg-success">Активна</span>' : 
        '<span class="badge bg-secondary">Неактивна</span>';
      
      const editLink = card.querySelector('.service-actions a')?.href || '#';
      
      tableHTML += `
        <tr>
          <td class="fw-semibold">${name}</td>
          <td class="text-muted small">${description}</td>
          <td>${duration}</td>
          <td>${price}</td>
          <td class="text-muted small">${branch}</td>
          <td>${status}</td>
          <td class="text-end">
            <a href="${editLink}" class="btn btn-sm btn-outline-primary">
              <i class="bi bi-pencil me-1"></i>Изменить
            </a>
          </td>
        </tr>
      `;
    });
    
    tableHTML += `
          </tbody>
        </table>
      </div>
    `;
    
    servicesContainer.innerHTML = tableHTML;
  }

  function filterServices() {
    const searchTerm = searchInput.value.toLowerCase();
    const status = statusFilter.value;
    const branch = branchFilter.value;

    serviceCards.forEach(card => {
      const name = card.dataset.name;
      const cardStatus = card.dataset.status;
      const cardBranch = card.dataset.branch;

      const matchSearch = name.includes(searchTerm);
      const matchStatus = !status || cardStatus === status;
      const matchBranch = !branch || cardBranch === branch;

      if (matchSearch && matchStatus && matchBranch) {
        card.style.display = 'block';
      } else {
        card.style.display = 'none';
      }
    });
    if (servicesContainer.classList.contains('table-view')) {
      convertToTableView();
    }
  }

  searchInput.addEventListener('input', filterServices);
  statusFilter.addEventListener('change', filterServices);
  branchFilter.addEventListener('change', filterServices);
});

function duplicateService(serviceId) {
  alert('Функция дублирования услуги будет доступна в следующем обновлении');
}

function deleteService(serviceId) {
  alert('Функция удаления услуги будет доступна в следующем обновлении');
}