document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(el) { return new bootstrap.Tooltip(el); });

    var toggle = document.getElementById('darkModeToggle');
    if (toggle) {
        var theme = localStorage.getItem('crm_theme') || 'light';
        if (theme === 'dark') { document.documentElement.setAttribute('data-theme', 'dark'); toggle.checked = true; }
        toggle.addEventListener('change', function() {
            var t = this.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', t);
            localStorage.setItem('crm_theme', t);
        });
    }

    var ctx1 = document.getElementById('revenueChart');
    if (ctx1) {
        fetch('/api/chart/revenue').then(r => r.json()).then(d => {
            new Chart(ctx1, { type: 'bar', data: { labels: d.labels, datasets: [{ label: 'Revenue', data: d.values, backgroundColor: '#0d6efd' }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } } });
        });
    }
    var ctx2 = document.getElementById('statusChart');
    if (ctx2) {
        fetch('/api/chart/wo-status').then(r => r.json()).then(d => {
            new Chart(ctx2, { type: 'doughnut', data: { labels: d.labels, datasets: [{ data: d.values, backgroundColor: d.colors }] },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } } });
        });
    }
    var ctx3 = document.getElementById('scrapChart');
    if (ctx3) {
        fetch('/api/chart/scrap').then(r => r.json()).then(d => {
            new Chart(ctx3, { type: 'line', data: { labels: d.labels, datasets: [{ label: 'Scrap Payout', data: d.values, borderColor: '#198754', tension: 0.3, fill: true }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } } });
        });
    }
});
