(function() {
    const data = window.profileEditData || {};
    const avatarFieldId = data.avatarFieldId;
    
    if (avatarFieldId) {
        const avatarInput = document.getElementById(avatarFieldId);
        if (avatarInput) {
            avatarInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const preview = document.getElementById('avatarPreview');
                        if (preview) {
                            preview.src = e.target.result;
                        }
                    }
                    reader.readAsDataURL(file);
                }
            });
        }
    }
    
    document.addEventListener('DOMContentLoaded', function() {
        const inputs = document.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (!input.classList.contains('btn')) {
                input.classList.add('form-control');
            }
        });
    });
})();
