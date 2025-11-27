
let servicesData = {};

$(document).ready(function() {
    let selectedServiceCenter = null;
    let selectedService = null;
    let selectedDate = null;
    let selectedTime = null;

    const restore = {
        sc: $('#id_service_center').data('restore-sc') || '',
        st: $('#id_service_type').data('restore-st') || '',
        date: $('#datePicker').data('restore-date') || '',
        time: $('#id_scheduled_time').data('restore-time') || '',
        notes: $('#id_notes').data('restore-notes') || ''
    };

    $('#id_service_center').change(function() {
        selectedServiceCenter = $(this).val();
        if (selectedServiceCenter) {
            loadServices(selectedServiceCenter);
        } else {
            $('#serviceCardsContainer').html(
                '<div class="col-12">' +
                '<div class="alert alert-info alert-sticky" data-keep="true">' +
                '<i class="bi bi-info-circle me-2"></i>' +
                'Сначала выберите автосервис для отображения доступных услуг' +
                '</div>' +
                '</div>'
            );
            selectedService = null;
            $('#id_service_type').val('');
            servicesData = {};
        }
        updateTimeSlots();
        checkFormCompletion();
    });

    $('#datePicker').change(function() {
        selectedDate = $(this).val();
        $('#id_scheduled_date').val(selectedDate);
        updateTimeSlots();
        checkFormCompletion();
    });

    function loadServices(serviceCenterId) {
        $('#serviceCardsContainer').html(
            '<div class="col-12 text-center py-4">' +
            '<div class="loading-spinner mx-auto mb-2"></div>' +
            '<p class="text-muted">Загрузка услуг...</p>' +
            '</div>'
        );

        const getServicesUrl = $('#serviceCardsContainer').data('get-services-url');
        
        $.ajax({
            url: getServicesUrl,
            data: {
                'service_center_id': serviceCenterId
            },
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(data) {
                console.log('Received services data:', data);
                
                let services = [];
                
                if (data.services && Array.isArray(data.services)) {
                    services = data.services;
                } else if (Array.isArray(data)) {
                    services = data;
                } else if (data.options) {
                    services = extractServicesFromOptions(data.options);
                }
                
                if (services.length > 0) {
                    loadServiceDetails(services, serviceCenterId);
                } else {
                    $('#serviceCardsContainer').html(
                        '<div class="col-12">' +
                        '<div class="alert alert-warning">' +
                        '<i class="bi bi-exclamation-triangle me-2"></i>' +
                        'Для выбранного автосервиса нет доступных услуг.' +
                        '</div>' +
                        '</div>'
                    );
                }
            },
            error: function(xhr, status, error) {
                console.error('Error loading services:', error);
                $('#serviceCardsContainer').html(
                    '<div class="col-12">' +
                    '<div class="alert alert-danger">' +
                    '<i class="bi bi-exclamation-triangle me-2"></i>' +
                    'Ошибка загрузки услуг. Пожалуйста, попробуйте еще раз.' +
                    '</div>' +
                    '</div>'
                );
            }
        });
    }

    function loadServiceDetails(services, serviceCenterId) {
        servicesData = {};
        
        let html = '';
        let loadedCount = 0;
        const totalCount = services.length;
        const getDetailsUrl = $('#serviceCardsContainer').data('get-details-url');
        
        services.forEach(function(service) {
            const serviceId = service.id || service.value;
            const serviceName = (service.name || service.text || 'Услуга').split(' - ')[0].trim();

            servicesData[serviceId] = {
                id: serviceId,
                name: serviceName,
                description: service.description || '',
                duration: service.duration || '60',
                price: service.price || '0'
            };

            $.ajax({
                url: getDetailsUrl,
                data: {
                    'service_id': serviceId,
                    'service_center_id': serviceCenterId
                },
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                success: function(serviceData) {
                    if (serviceData.service) {
                        servicesData[serviceId].duration = serviceData.service.duration || servicesData[serviceId].duration;
                        servicesData[serviceId].price = serviceData.service.price || servicesData[serviceId].price;
                        servicesData[serviceId].description = serviceData.service.description || servicesData[serviceId].description;
                    }
                    
                    loadedCount++;              
                    if (loadedCount === totalCount) {
                        renderServiceCards();
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error loading service details:', error);
                    loadedCount++;
                    
                if (loadedCount === totalCount) {
                        renderServiceCards();
                    }
                }
            });

            html += `
            <div class="col-md-6 mb-3">
                <div class="card service-card h-100" data-service-id="${serviceId}">
                    <div class="card-body">
                        <h5 class="card-title text-primary">${serviceName}</h5>
                        <p class="card-text small text-muted mb-3">${service.description || 'Загрузка...'}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="badge bg-secondary">${service.duration || '60'} мин.</span>
                            <strong class="text-dark h5 mb-0">${service.price || '0'} ₽</strong>
                        </div>
                    </div>
                </div>
            </div>
        `;
        });

        $('#serviceCardsContainer').html(html);

        function renderServiceCards() {
            let updatedHtml = '';
            
            services.forEach(function(service) {
                const serviceId = service.id || service.value;
                const serviceInfo = servicesData[serviceId] || {};
                
                updatedHtml += `
                    <div class="col-md-6 mb-3">
                        <div class="card service-card h-100" data-service-id="${serviceId}">
                            <div class="card-body">
                                <h6 class="card-title text-primary">${serviceInfo.name}</h6>
                                ${serviceInfo.description ? `<p class="card-text small text-muted mb-3">${serviceInfo.description}</p>` : ''}
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="badge bg-secondary">${serviceInfo.duration} мин.</span>
                                    <strong class="text-dark h5 mb-0">${serviceInfo.price} ₽</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            $('#serviceCardsContainer').html(updatedHtml);

            $('.service-card').click(function() {
                $('.service-card').removeClass('selected');
                $(this).addClass('selected');
                selectedService = $(this).data('service-id');
                $('#id_service_type').val(selectedService);
                updateTimeSlots();
                checkFormCompletion();
            });

            if (restore.st) {
                const card = document.querySelector(`.service-card[data-service-id="${restore.st}"]`);
                if (card) {
                    $(card).trigger('click');
                }
            }
        }
    }

    function extractServicesFromOptions(html) {
        const services = [];
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        const options = tempDiv.querySelectorAll('option');
        options.forEach(option => {
            if (option.value) {
                services.push({
                    id: option.value,
                    text: option.text,
                    value: option.value
                });
            }
        });
        
        return services;
    }

    function updateTimeSlots() {
        if (!selectedServiceCenter || !selectedService || !selectedDate) {
            $('#timeSlotsContainer').html(
                '<div class="alert alert-info alert-sticky" data-keep="true">' +
                '<i class="bi bi-info-circle me-2"></i>' +
                'Сначала выберите автосервис, услугу и дату для отображения доступного времени' +
                '</div>'
            );
            return;
        }
        
        $('#timeSlotsContainer').html(
            '<div class="text-center py-4">' +
            '<div class="loading-spinner mx-auto mb-2"></div>' +
            '<p class="text-muted">Загрузка доступного времени...</p>' +
            '</div>'
        );
        
        const getTimeSlotsUrl = $('#timeSlotsContainer').data('get-time-slots-url');
        
        $.ajax({
            url: getTimeSlotsUrl,
            data: {
                'service_center': selectedServiceCenter,
                'service_type': selectedService,
                'date': selectedDate,
                'is_today': (new Date(selectedDate)).toDateString() === (new Date()).toDateString() ? '1' : '0',
                'client_now': new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', hour12: false })
            },
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(data) {
                if (data.error) {
                    $('#timeSlotsContainer').html(
                        '<div class="alert alert-danger">' +
                        '<i class="bi bi-exclamation-triangle me-2"></i>' +
                        'Ошибка: ' + data.error +
                        '</div>'
                    );
                    return;
                }
                
                if (data.available_slots && data.available_slots.length > 0) {
                    let html = '<div class="row">';
                    data.available_slots.forEach(function(slot) {
                        html += `
                            <div class="col-6 col-md-3 mb-3">
                                <div class="time-slot" data-time="${slot}">
                                    ${slot}
                                </div>
                            </div>
                        `;
                    });
                    html += '</div>';
                    $('#timeSlotsContainer').html(html);
                    
                    $('.time-slot').click(function() {
                        $('.time-slot').removeClass('selected');
                        $(this).addClass('selected');
                        selectedTime = $(this).data('time');
                        $('#id_scheduled_time').val(selectedTime);
                        checkFormCompletion();
                    });

                    if (restore.time) {
                        const slotEl = document.querySelector(`.time-slot[data-time="${restore.time}"]`);
                        if (slotEl) {
                            $(slotEl).trigger('click');
                        }
                    }
                } else {
                    $('#timeSlotsContainer').html(
                        '<div class="alert alert-warning">' +
                        '<i class="bi bi-clock me-2"></i>' +
                        'На выбранную дату нет свободного времени. Пожалуйста, выберите другую дату.' +
                        '</div>'
                    );
                }
            },
            error: function(xhr, status, error) {
                $('#timeSlotsContainer').html(
                    '<div class="alert alert-danger">' +
                    '<i class="bi bi-exclamation-triangle me-2"></i>' +
                    'Ошибка загрузки времени: ' + error +
                    '</div>'
                );
            }
        });
    }
    
    function checkFormCompletion() {
        if (selectedServiceCenter && selectedService && selectedDate && selectedTime && $('#id_car').val()) {
            $('#submitBtn').prop('disabled', false);
        } else {
            $('#submitBtn').prop('disabled', true);
        }
    }

    $('#id_car').change(function() {
        checkFormCompletion();
    });

    $('#id_notes').addClass('form-control notes-textarea');

    (function restoreState(){
        if (restore.sc) {
            $('#id_service_center').val(restore.sc).trigger('change');
        }
        if (restore.date) {
            $('#datePicker').val(restore.date).trigger('change');
        }
        if (restore.notes) {
            $('#id_notes').val(restore.notes);
        }
    })();
});
