/**
 * Admin Panel Common Utilities
 * Reusable functions for admin panel pages
 */

/**
 * Get CSRF token from cookies or form
 * @returns {string} CSRF token
 */
export function getCsrf() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';').map(v => v.trim());
    for (const c of cookies) {
        if (c.startsWith(name + '=')) {
            return c.slice(name.length + 1);
        }
    }
    const inp = document.querySelector('input[name=csrfmiddlewaretoken]');
    return inp ? inp.value : '';
}

/**
 * Create a debounced version of a function
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * Fetch and replace HTML content from server
 * @param {string} url - URL to fetch
 * @param {string} selector - Selector of element to replace
 * @param {Function} callback - Optional callback after replace
 */
export function fetchAndReplace(url, selector, callback) {
    return fetch(url, { 
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => response.text())
    .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newElement = doc.querySelector(selector);
        const currentElement = document.querySelector(selector);
        
        if (newElement && currentElement) {
            currentElement.innerHTML = newElement.innerHTML;
        }
        
        if (callback) callback();
    })
    .catch(err => console.error('Fetch error:', err));
}

/**
 * Build query string from form data
 * @param {HTMLFormElement} form - Form element
 * @param {Object} extraParams - Additional parameters to include
 * @returns {string} Query string
 */
export function buildQueryString(form, extraParams = {}) {
    const params = new URLSearchParams(new FormData(form));
    
    for (const [key, value] of Object.entries(extraParams)) {
        if (value !== null && value !== undefined) {
            params.set(key, value);
        }
    }
    
    return params.toString();
}

/**
 * Setup avatar preview for file input
 * @param {string} inputSelector - Selector for file input
 * @param {string} previewSelector - Selector for preview image
 */
export function setupAvatarPreview(inputSelector, previewSelector) {
    const input = document.querySelector(inputSelector);
    const preview = document.querySelector(previewSelector);
    
    if (!input || !preview) return;
    
    input.addEventListener('change', function() {
        const file = this.files && this.files[0];
        if (file) {
            const url = URL.createObjectURL(file);
            preview.src = url;
            preview.classList.remove('d-none');
        }
    });
}

/**
 * Setup Enter key submit for input
 * @param {HTMLInputElement} input - Input element
 * @param {Function} callback - Function to call on Enter
 */
export function submitOnEnter(input, callback) {
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            callback();
        }
    });
}

/**
 * Clear input value and trigger callback
 * @param {string} buttonSelector - Selector for clear buttons
 * @param {Function} callback - Function to call after clearing
 */
export function setupClearButtons(buttonSelector, callback) {
    document.querySelectorAll(buttonSelector).forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (input) {
                input.value = '';
                if (callback) callback();
            }
        });
    });
}
