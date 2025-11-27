(function() {
    const data = window.editCarData || {};
    
    $(document).ready(function() {
        $("#id_brand").change(function () {
            const url = data.loadModelsUrl;
            const brandId = $(this).val();
            
            if (brandId) {
                $.ajax({
                    url: url,
                    data: {
                        'brand_id': brandId
                    },
                    success: function (data) {
                        $("#id_model").html(data.options);
                    }
                });
            } else {
                $("#id_model").html('<option value="">Сначала выберите марку</option>');
            }
        });

        $('select, input[type="text"], input[type="number"]').addClass('form-control');
    });
})();
