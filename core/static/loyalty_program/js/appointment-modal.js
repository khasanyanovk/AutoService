/**
 * Loyalty Program - Appointment Details Modal
 * Handles appointment details display with loyalty program integration
 */

/**
 * Load appointment details via AJAX
 * @param {string|number} appointmentId - The appointment ID
 */
function loadAppointmentDetails(appointmentId) {
    const modal = new bootstrap.Modal(document.getElementById('appointmentModal'));
    const modalBody = document.getElementById('appointmentModalBody');
    
    modalBody.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Загрузка...</span>
        </div>
      </div>
    `;
    
    modal.show();
    
    fetch(`/appointments/${appointmentId}/`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        modalBody.innerHTML = renderAppointmentDetails(data);
        attachModalHandlers(appointmentId);
    })
    .catch(error => {
        modalBody.innerHTML = `
        <div class="alert alert-danger">
          <i class="bi bi-exclamation-triangle me-2"></i>Ошибка загрузки данных
        </div>
      `;
    });
}

/**
 * Render appointment details HTML
 * @param {Object} data - Appointment data from server
 * @returns {string} HTML string
 */
function renderAppointmentDetails(data) {
    const statusClass = data.status === 'SCHEDULED' ? 'primary' :
                       data.status === 'IN_PROGRESS' ? 'warning' :
                       data.status === 'COMPLETED' ? 'success' : 'secondary';
    
    const loyalty = data.loyalty || {};
    const paymentSection = renderPaymentSection(data, loyalty);
    
    return `
      <div class="info-row" style="display: flex; justify-content: space-between; padding: 1.25rem; margin-bottom: 1rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px;">
        <div class="info-label" style="font-weight: 600; color: #6c757d; display: flex; align-items: center; gap: 0.5rem;">
          <i class="bi bi-wrench-adjustable-circle" style="font-size: 1.25rem; color: #0d6efd;"></i>
          Услуга
        </div>
        <div class="info-value" style="font-weight: 700; color: #212529; font-size: 1.1rem;">${data.service_type}</div>
      </div>

      <div class="info-row" style="display: flex; justify-content: space-between; padding: 1.25rem; margin-bottom: 1rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px;">
        <div class="info-label" style="font-weight: 600; color: #6c757d; display: flex; align-items: center; gap: 0.5rem;">
          <i class="bi bi-geo-alt" style="font-size: 1.25rem; color: #0d6efd;"></i>
          Филиал
        </div>
        <div class="info-value" style="font-weight: 700; color: #212529; font-size: 1.1rem;">${data.service_center}</div>
      </div>

      <div class="info-row" style="display: flex; justify-content: space-between; padding: 1.25rem; margin-bottom: 1rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px;">
        <div class="info-label" style="font-weight: 600; color: #6c757d; display: flex; align-items: center; gap: 0.5rem;">
          <i class="bi bi-calendar3" style="font-size: 1.25rem; color: #0d6efd;"></i>
          Дата
        </div>
        <div class="info-value" style="font-weight: 700; color: #212529; font-size: 1.1rem;">${data.scheduled_date}</div>
      </div>

      <div class="info-row" style="display: flex; justify-content: space-between; padding: 1.25rem; margin-bottom: 1rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px;">
        <div class="info-label" style="font-weight: 600; color: #6c757d; display: flex; align-items: center; gap: 0.5rem;">
          <i class="bi bi-clock" style="font-size: 1.25rem; color: #0d6efd;"></i>
          Время
        </div>
        <div class="info-value" style="font-weight: 700; color: #212529; font-size: 1.1rem;">${data.scheduled_time}</div>
      </div>

      <div class="info-row" style="display: flex; justify-content: space-between; padding: 1.25rem; margin-bottom: 1rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px;">
        <div class="info-label" style="font-weight: 600; color: #6c757d; display: flex; align-items: center; gap: 0.5rem;">
          <i class="bi bi-car-front" style="font-size: 1.25rem; color: #0d6efd;"></i>
          Автомобиль
        </div>
        <div class="info-value" style="font-weight: 700; color: #212529; font-size: 1.1rem;">${data.car}</div>
      </div>

      <div class="info-row" style="display: flex; justify-content: space-between; padding: 1.25rem; margin-bottom: 1rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px;">
        <div class="info-label" style="font-weight: 600; color: #6c757d; display: flex; align-items: center; gap: 0.5rem;">
          <i class="bi bi-info-circle" style="font-size: 1.25rem; color: #0d6efd;"></i>
          Статус
        </div>
        <div class="info-value">
          <span class="badge bg-${statusClass}" style="padding: 0.5rem 1.25rem; border-radius: 50px; font-size: 0.95rem; text-transform: uppercase;">
            ${data.status_display}
          </span>
        </div>
      </div>

      ${paymentSection}

      <div class="mt-4 d-flex gap-2 justify-content-end">
        ${data.status === 'SCHEDULED' && (!data.payment || data.payment.status !== 'succeeded') ? `
          <button type="button" class="btn btn-danger btn-cancel-appointment" data-appointment-id="${data.id}">
            <i class="bi bi-x-circle me-2"></i>Отменить запись
          </button>
        ` : ''}
      </div>
    `;
}

/**
 * Render payment section based on appointment and payment status
 * @param {Object} data - Appointment data
 * @param {Object} loyalty - Loyalty account data
 * @returns {string} HTML string for payment section
 */
function renderPaymentSection(data, loyalty) {
    if (data.status === 'CANCELLED') {
        return '';
    }

    // Paid online
    if (data.payment && data.payment.status === 'succeeded') {
        return `
          <div class="payment-section paid">
            <div class="payment-status text-success">
              <i class="bi bi-check-circle-fill fs-1"></i>
              <p class="mt-2 mb-0 fw-bold fs-5">Оплачено онлайн</p>
            </div>
            <div class="payment-amount">
              ${data.price} ₽
            </div>
            <p class="text-muted">Платеж выполнен ${data.payment.paid_at}</p>
          </div>
        `;
    }

    // Paid offline (completed)
    if (data.status === 'COMPLETED') {
        return `
          <div class="payment-section paid">
            <div class="payment-status text-success">
              <i class="bi bi-check-circle-fill fs-1"></i>
              <p class="mt-2 mb-0 fw-bold fs-5">Оплачено в центре</p>
            </div>
            <div class="payment-amount">
              ${data.price} ₽
            </div>
            <p class="text-muted">Услуга завершена</p>
          </div>
        `;
    }

    // Pending payment
    if (data.payment && data.payment.status === 'pending') {
        return `
          <div class="payment-section" style="background: linear-gradient(135deg, #fff8e1 0%, #ffe4b5 100%); border: 3px dashed #ffc107;">
            <div class="payment-status text-warning">
              <i class="bi bi-hourglass-split fs-1"></i>
              <p class="mt-2 mb-0 fw-bold fs-5">Ожидает оплаты</p>
            </div>
            <div class="payment-amount" style="background: linear-gradient(135deg, #0d6efd, #6610f2); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
              ${loyalty.price_after_discount || data.price} ₽
            </div>
            <p class="mb-3">Платеж создан, но еще не завершен</p>
            <a href="/payments/appointments/${data.id}/check-payment/" class="btn btn-primary">
              <i class="bi bi-arrow-clockwise me-2"></i>Проверить статус
            </a>
            ${data.payment.confirmation_url ? `
              <a href="${data.payment.confirmation_url}" class="btn btn-success ms-2">
                <i class="bi bi-credit-card me-2"></i>Продолжить оплату
              </a>
            ` : ''}
          </div>
        `;
    }

    // Ready to pay
    return renderPaymentForm(data, loyalty);
}

/**
 * Render payment form with loyalty program discounts and bonuses
 * @param {Object} data - Appointment data
 * @param {Object} loyalty - Loyalty account data
 * @returns {string} HTML string for payment form
 */
function renderPaymentForm(data, loyalty) {
    let discountText = '';
    if (loyalty.discount_amount > 0) {
        if (loyalty.status_discount_percent > 0 && loyalty.personal_discount_percent > 0) {
            discountText = `(${loyalty.status_display}: ${loyalty.status_discount_percent}% + Персональная: ${loyalty.personal_discount_percent}%)`;
        } else if (loyalty.status_discount_percent > 0) {
            discountText = `(${loyalty.status_display}: ${loyalty.status_discount_percent}%)`;
        } else {
            discountText = `(Персональная: ${loyalty.personal_discount_percent}%)`;
        }
    }

    return `
      <div class="payment-section" style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border: 2px solid #2196f3;">
        <div class="text-center mb-3">
          <i class="bi bi-credit-card fs-1 text-primary"></i>
          <p class="mt-2 mb-0 fw-bold fs-5">Оплата онлайн</p>
        </div>
        
        <!-- Price breakdown -->
        <div class="price-breakdown">
          <div class="d-flex justify-content-between mb-2">
            <span class="text-muted">Базовая цена:</span>
            <span class="fw-bold">${loyalty.base_price || data.price} ₽</span>
          </div>
          ${loyalty.discount_amount > 0 ? `
            <div class="d-flex justify-content-between mb-2 text-success">
              <span><i class="bi bi-tag-fill me-1"></i>Скидка ${discountText}:</span>
              <span class="fw-bold">-${loyalty.discount_amount} ₽</span>
            </div>
          ` : ''}
          <div class="d-flex justify-content-between mb-2">
            <span class="text-muted">Доступно бонусов:</span>
            <span class="fw-bold text-primary">${loyalty.bonus_balance || 0} ₽</span>
          </div>
          <div class="d-flex justify-content-between mb-2 text-info">
            <span><i class="bi bi-info-circle me-1"></i>Можно использовать (макс 70%):</span>
            <span class="fw-bold">до ${loyalty.max_bonus_usage || 0} ₽</span>
          </div>
          <hr style="margin: 1rem 0; opacity: 0.3;">
          <div class="d-flex justify-content-between">
            <span class="fs-5 fw-bold">Итого к оплате:</span>
            <span class="fs-4 fw-bold text-primary" id="modal-final-price">${loyalty.price_after_discount || data.price} ₽</span>
          </div>
        </div>
        
        <!-- Bonus selector -->
        <div class="bonus-selector mb-3">
          <label for="modal-bonus-amount" class="form-label fw-bold">
            <i class="bi bi-gift me-1"></i>Использовать бонусы:
          </label>
          <div class="input-group mb-3">
            <input type="number" 
                   class="form-control form-control-lg" 
                   id="modal-bonus-amount" 
                   min="0" 
                   max="${loyalty.max_bonus_usage || 0}" 
                   value="0"
                   step="1">
            <span class="input-group-text">₽</span>
          </div>
          <button type="button" class="btn btn-info w-100 mb-2" id="modal-use-max-bonus">
            <i class="bi bi-arrow-up-circle me-1"></i>Использовать максимум (${loyalty.max_bonus_usage || 0} ₽)
          </button>
          <small class="text-muted d-block text-center">
            <i class="bi bi-info-circle me-1"></i>Можно оплатить до 70% стоимости бонусами
          </small>
        </div>
        
        <div class="text-center">
          <button type="button" class="btn btn-success btn-lg" id="modal-pay-button" data-appointment-id="${data.id}">
            <i class="bi bi-credit-card me-2"></i>Оплатить <span id="modal-pay-amount">${loyalty.price_after_discount || data.price}</span> ₽
          </button>
        </div>
      </div>
    `;
}

/**
 * Attach event handlers for modal interactions
 * @param {string|number} appointmentId - The appointment ID
 */
function attachModalHandlers(appointmentId) {
    const bonusInput = document.getElementById('modal-bonus-amount');
    const useMaxBtn = document.getElementById('modal-use-max-bonus');
    const payButton = document.getElementById('modal-pay-button');
    const finalPriceEl = document.getElementById('modal-final-price');
    const payAmountEl = document.getElementById('modal-pay-amount');
    
    const maxBonusUsage = bonusInput ? parseFloat(bonusInput.getAttribute('max')) : 0;
    const priceAfterDiscount = parseFloat(finalPriceEl ? finalPriceEl.textContent : 0);
    
    // Update price when bonus amount changes
    function updatePrice() {
        if (!bonusInput || !finalPriceEl || !payAmountEl) return;
        
        let bonusAmount = parseFloat(bonusInput.value) || 0;
        bonusAmount = Math.min(bonusAmount, maxBonusUsage);
        bonusAmount = Math.max(0, bonusAmount);
        bonusInput.value = Math.floor(bonusAmount);
        
        const finalPrice = Math.max(0, priceAfterDiscount - bonusAmount);
        finalPriceEl.textContent = finalPrice.toFixed(2) + ' ₽';
        payAmountEl.textContent = finalPrice.toFixed(2);
    }
    
    if (bonusInput) {
        bonusInput.addEventListener('input', updatePrice);
    }
    
    if (useMaxBtn) {
        useMaxBtn.addEventListener('click', function() {
            if (bonusInput) {
                bonusInput.value = maxBonusUsage;
                updatePrice();
            }
        });
    }
    
    if (payButton) {
        payButton.addEventListener('click', function() {
            const bonusAmount = bonusInput ? (bonusInput.value || 0) : 0;
            const url = `/payments/appointments/${appointmentId}/pay/?bonus_amount=${bonusAmount}`;
            window.location.href = url;
        });
    }

    const cancelBtn = document.querySelector('.btn-cancel-appointment');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            if (confirm('Вы уверены, что хотите отменить запись?')) {
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/appointments/${appointmentId}/cancel/`;
                
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = csrfToken;
                form.appendChild(csrfInput);
                
                document.body.appendChild(form);
                form.submit();
            }
        });
    }
}

/**
 * Initialize appointment modal handlers
 */
function initAppointmentModal() {
    document.querySelectorAll('.btn-appointment-details').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const appointmentId = this.getAttribute('data-appointment-id');
            loadAppointmentDetails(appointmentId);
        });
    });

    document.querySelectorAll('.appointment-item').forEach(item => {
        item.addEventListener('click', function() {
            const appointmentId = this.getAttribute('data-appointment-id');
            loadAppointmentDetails(appointmentId);
        });
        
        item.addEventListener('mouseenter', function() {
            this.style.background = 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)';
            this.style.transform = 'translateX(5px)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.background = '';
            this.style.transform = '';
        });
    });
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAppointmentModal);
} else {
    initAppointmentModal();
}
