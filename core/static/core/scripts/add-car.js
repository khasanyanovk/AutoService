(function() {
    const data = window.addCarData || {};
    
    $(document).ready(function() {
        function showAlert(messagesHtml) {
            const $alerts = $('#formAlerts');
            $alerts.html(
                '<div class="alert alert-danger" role="alert">' +
                messagesHtml +
                '</div>'
            );
        }

        function loadModels(brandId, selectedModelId) {
            const $modelField = $("#id_model");
            
            if (brandId) {
                const url = data.loadModelsUrl;
                $modelField.html('<option value="">Загрузка...</option>');
                
                $.ajax({
                    url: url,
                    data: {
                        'brand_id': brandId
                    },
                    success: function (data) {
                        $modelField.html(data.options);
                        if (selectedModelId) {
                            $modelField.val(String(selectedModelId));
                        }
                    },
                    error: function() {
                        $modelField.html('<option value="">Ошибка загрузки моделей</option>');
                    }
                });
            } else {
                $modelField.html('<option value="">Сначала выберите марку</option>');
            }
        }

        $("#id_brand").change(function () {
            const brandId = $(this).val();
            loadModels(brandId, null);
            $("#id_model").val("");
        });
        
        // Get initial values from DOM after document is ready
        const initialBrandId = $("#id_brand").val();
        const initialModelId = $("#id_model").val();
        if (initialBrandId) {
            loadModels(initialBrandId, initialModelId);
        }

        $('select, input[type="text"], input[type="number"]').addClass('form-control');

        $('#carForm').on('submit', function(e) {
            const brandVal = $('#id_brand').val();
            const modelVal = $('#id_model').val();
            const errors = [];
            if (!brandVal) {
                errors.push('Пожалуйста, выберите марку автомобиля.');
            }
            if (!modelVal) {
                errors.push('Пожалуйста, выберите модель автомобиля.');
            }
            if (errors.length > 0) {
                e.preventDefault();
                showAlert(errors.map(e => '<div>' + e + '</div>').join(''));
                const top = $('#formAlerts').offset().top - 80;
                window.scrollTo({ top: top < 0 ? 0 : top, behavior: 'smooth' });
            }
        });
    });
})();
