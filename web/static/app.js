(function () {
    'use strict';

    /* ── Toast ── */
    function toast(msg, type) {
        type = type || 'info';
        var el = document.createElement('div');
        el.className = 'toast ' + type;
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(function () {
            el.remove();
        }, 4000);
    }

    /* ── Format helpers ── */
    function formatIDR(n) {
        if (n == null) return '—';
        return 'Rp ' + Number(n).toLocaleString('id-ID');
    }
    function formatNum(n, decimals) {
        decimals = typeof decimals === 'number' ? decimals : 2;
        if (n == null) return '—';
        return Number(n).toLocaleString('id-ID', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    }

    /* ── Market Ticker (Dashboard) ── */
    function loadMarketTicker() {
        var cards = document.querySelectorAll('.ticker-card');
        if (!cards.length) return;

        fetch('/api/prices/idx')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) return;
                data.items.forEach(function (item) {
                    var el = document.querySelector('[data-ticker="' + item.symbol + '"]');
                    if (el) {
                        var priceEl = el.querySelector('.card-value');
                        if (priceEl) priceEl.textContent = formatNum(item.price);
                    }
                });
            })
            .catch(function () {});

        fetch('/api/prices/crypto/id')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) return;
                var btc = data.items.find(function (i) { return i.pair === 'BTC_IDR'; });
                var el = document.querySelector('[data-ticker="BTC_IDR"]');
                if (btc && el) {
                    var priceEl = el.querySelector('.card-value');
                    if (priceEl) priceEl.textContent = formatIDR(btc.last);
                }
            })
            .catch(function () {});

        fetch('/api/prices/antam')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var gold = data.items.find(function (i) { return i.symbol === 'GC=F' || i.name.indexOf('Emas') === 0; });
                var el = document.querySelector('[data-ticker="GOLD"]');
                if (gold && el && gold.price_idr) {
                    var priceEl = el.querySelector('.card-value');
                    if (priceEl) priceEl.textContent = formatIDR(gold.price_idr);
                }
            })
            .catch(function () {});
    }

    /* ── Section Collapsible ── */
    function initCollapsibles() {
        document.querySelectorAll('.section-header').forEach(function (header) {
            header.addEventListener('click', function () {
                var body = this.nextElementSibling;
                var isOpen = body.classList.contains('open');
                body.classList.toggle('open', !isOpen);
                this.classList.toggle('open', !isOpen);
            });
        });
    }

    /* ── Analysis Form ── */
    var analysisForm = document.getElementById('analysis-form');
    if (analysisForm) {
        analysisForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var formData = new FormData(analysisForm);
            var ticker = formData.get('ticker');
            var date = formData.get('date');
            var assetType = formData.get('asset_type');

            if (!ticker || !date) {
                toast('Harap isi ticker dan tanggal terlebih dahulu.', 'error');
                return;
            }

            window.location.href = '/analyze/' + encodeURIComponent(ticker.toUpperCase()) + '/' + encodeURIComponent(date) + '?asset_type=' + encodeURIComponent(assetType) + '&run=1';
        });
    }

    /* ── Analysis Stream (analysis.html page with run=1 param) ── */
    function startAnalysisStream() {
        var container = document.getElementById('analysis-stream');
        if (!container) return;

        var params = new URLSearchParams(window.location.search);
        var ticker = container.dataset.ticker;
        var date = container.dataset.date;
        var assetType = container.dataset.assetType || params.get('asset_type') || 'stock';

        if (params.get('run') !== '1') return;

        var progressBar = document.getElementById('progress-bar-fill');
        var statusText = document.getElementById('analysis-status');
        var resultContainer = document.getElementById('analysis-result');
        var loadingOverlay = document.getElementById('loading-overlay');

        if (loadingOverlay) loadingOverlay.classList.add('active');

        var streamUrl = '/api/analyze/stream?ticker=' + encodeURIComponent(ticker) +
            '&date=' + encodeURIComponent(date) +
            '&asset_type=' + encodeURIComponent(assetType);

        var evtSource = new EventSource(streamUrl);
        var completedSections = {};
        var totalSections = 7;
        var receivedSections = 0;

        evtSource.onmessage = function (event) {
            var data;
            try {
                data = JSON.parse(event.data);
            } catch (err) {
                return;
            }

            if (data.type === 'progress' && data.reports) {
                var reports = data.reports;
                Object.keys(reports).forEach(function (key) {
                    if (!completedSections[key]) {
                        completedSections[key] = true;
                        receivedSections++;

                        var sectionEl = document.getElementById('section-' + key);
                        if (sectionEl) {
                            var body = sectionEl.querySelector('.section-body');
                            var content = sectionEl.querySelector('.section-content');
                            if (content) content.textContent = reports[key];
                            if (body) {
                                body.classList.add('open');
                            }
                            var header = sectionEl.querySelector('.section-header');
                            if (header) header.classList.add('open');
                        }
                    }
                });

                if (progressBar) {
                    var pct = Math.min(95, Math.round((receivedSections / totalSections) * 100));
                    progressBar.style.width = pct + '%';
                }
                if (statusText) {
                    statusText.textContent = 'Menganalisis... (' + receivedSections + '/' + totalSections + ' bagian selesai)';
                }
            } else if (data.type === 'done') {
                evtSource.close();
                if (progressBar) progressBar.style.width = '100%';
                if (statusText) statusText.textContent = 'Analisis selesai!';
                if (loadingOverlay) loadingOverlay.classList.remove('active');

                var result = data.result;
                if (result && resultContainer) {
                    resultContainer.style.display = 'block';

                    Object.keys(result).forEach(function (key) {
                        if (key === 'rating') return;
                        var sectionEl = document.getElementById('section-' + key);
                        if (sectionEl && result[key]) {
                            var content = sectionEl.querySelector('.section-content');
                            if (content) content.textContent = result[key];
                            var body = sectionEl.querySelector('.section-body');
                            if (body && !body.classList.contains('open')) {
                                body.classList.add('open');
                            }
                            var header = sectionEl.querySelector('.section-header');
                            if (header && !header.classList.contains('open')) {
                                header.classList.add('open');
                            }
                        }
                    });

                    if (result.rating) {
                        var badge = document.getElementById('rating-badge');
                        if (badge) {
                            badge.textContent = result.rating.label;
                            badge.className = 'rating-badge ' + result.rating.class;
                        }
                    }
                }
            } else if (data.type === 'error') {
                evtSource.close();
                if (loadingOverlay) loadingOverlay.classList.remove('active');
                if (statusText) statusText.textContent = 'Error: ' + data.message;
                toast('Gagal menjalankan analisis: ' + data.message, 'error');
            }
        };

        evtSource.onerror = function () {
            evtSource.close();
            if (loadingOverlay) loadingOverlay.classList.remove('active');
        };
    }

    /* ── Price Dashboard ── */
    function loadPricesPage() {
        var cryptoGrid = document.getElementById('crypto-grid');
        var antamGrid = document.getElementById('antam-grid');
        var idxTable = document.getElementById('idx-table-body');

        if (cryptoGrid) {
            fetch('/api/prices/crypto/id')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    cryptoGrid.innerHTML = '';
                    if (data.error) {
                        cryptoGrid.innerHTML = '<p style="color:var(--text-muted);grid-column:span 3">' + data.error + '</p>';
                        return;
                    }
                    data.items.forEach(function (item) {
                        var changeClass = item.last > item.high ? 'down' : 'up';
                        var changeSign = item.last > item.high ? '-' : '+';
                        var div = document.createElement('div');
                        div.className = 'price-card';
                        div.innerHTML =
                            '<div class="name">' + item.pair + '</div>' +
                            '<div class="value">' + formatIDR(item.last) + '</div>' +
                            '<div class="change ' + changeClass + '">' + changeSign + formatIDR(Math.abs(item.change)) + '</div>';
                        cryptoGrid.appendChild(div);
                    });
                })
                .catch(function () {});
        }

        if (antamGrid) {
            fetch('/api/prices/antam')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    antamGrid.innerHTML = '';
                    data.items.forEach(function (item) {
                        var div = document.createElement('div');
                        div.className = 'price-card';
                        div.innerHTML =
                            '<div class="name">' + item.name + '</div>' +
                            '<div class="value">' + (item.price_idr ? formatIDR(item.price_idr) : item.note || '—') + '</div>' +
                            '<div class="pair">' + (item.unit || '') + '</div>';
                        antamGrid.appendChild(div);
                    });
                })
                .catch(function () {});
        }

        if (idxTable) {
            fetch('/api/prices/idx')
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    idxTable.innerHTML = '';
                    if (data.error) {
                        idxTable.innerHTML = '<tr><td colspan="3">' + data.error + '</td></tr>';
                        return;
                    }
                    data.items.forEach(function (item) {
                        var tr = document.createElement('tr');
                        tr.innerHTML =
                            '<td><strong>' + item.name + '</strong></td>' +
                            '<td style="font-family:var(--font-mono);font-size:0.8rem;color:var(--text-muted)">' + item.symbol + '</td>' +
                            '<td style="font-family:var(--font-mono)">' + formatNum(item.price) + '</td>';
                        idxTable.appendChild(tr);
                    });
                })
                .catch(function () {});
        }
    }

    /* ── Auto-refresh ── */
    function initAutoRefresh() {
        var refreshBar = document.getElementById('auto-refresh');
        if (!refreshBar) return;

        var countdownEl = document.getElementById('refresh-countdown');
        var interval = 30;
        var remaining = interval;

        function tick() {
            remaining--;
            if (countdownEl) countdownEl.textContent = remaining + 'd';
            if (remaining <= 0) {
                loadPricesPage();
                remaining = interval;
            }
        }

        setInterval(tick, 1000);

        var refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function () {
                loadPricesPage();
                remaining = interval;
            });
        }
    }

    /* ── Init ── */
    document.addEventListener('DOMContentLoaded', function () {
        loadMarketTicker();
        initCollapsibles();
        startAnalysisStream();
        loadPricesPage();
        initAutoRefresh();
    });
})();
