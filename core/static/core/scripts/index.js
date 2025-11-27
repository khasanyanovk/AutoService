// Animated counters for statistics
document.addEventListener('DOMContentLoaded', function() {
    const badges = document.querySelectorAll('.trust-badge span');
    
    function animateValue(element, start, end, duration, suffix = '') {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= end) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current) + suffix;
        }, 16);
    }
    
    // Intersection Observer for counter animation
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.animated) {
                const text = entry.target.textContent;
                if (text.includes('10+')) {
                    entry.target.textContent = '0+ лет опыта';
                    animateValue(entry.target, 0, 10, 1000, '+ лет опыта');
                } else if (text.includes('98%')) {
                    entry.target.textContent = '0% довольных клиентов';
                    animateValue(entry.target, 0, 98, 1000, '% довольных клиентов');
                }
                entry.target.dataset.animated = 'true';
            }
        });
    }, { threshold: 0.5 });
    
    badges.forEach(badge => observer.observe(badge));
});
