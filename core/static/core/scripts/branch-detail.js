(function() {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  const form = document.getElementById('reviewForm');
  if (form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      const url = window.location.href;
      const formData = new FormData(form);
      fetch(url, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        },
        body: formData
      }).then(async (resp) => {
        const data = await resp.json().catch(() => ({}));
        if (resp.ok && data.success) {
          document.getElementById('reviewFormArea').innerHTML = data.html;
        } else {
          // Re-render form with errors
          if (data.form_html) {
            document.getElementById('reviewFormArea').innerHTML = '<h6 class="mb-2">Оставить отзыв</h6>' + '<form id="reviewForm" method="post">' + data.form_html + '</form>';
            // re-bind submit handler after replacing HTML
            setTimeout(() => {
              const newForm = document.getElementById('reviewForm');
              if (newForm) {
                newForm.addEventListener('submit', arguments.callee.bind(this));
              }
            }, 0);
          }
        }
      }).catch(() => {});
    });
  }
})();
