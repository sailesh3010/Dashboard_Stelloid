/**
 * Stelloid Command Center — Dashboard Application
 *
 * Consumes the FastAPI backend API at /api/v1 and renders
 * KPI cards, trend chart, distribution chart, and performance table.
 */

(() => {
  'use strict';

  // ========== Config ==========
  const API_BASE = '/api/v1';
  const CHANNEL_COLORS = {
    'Shopify':              '#6366f1',
    'Amazon US':            '#06b6d4',
    'Walmart Marketplace':  '#1e3a5f',
  };
  const CHANNEL_CSS_CLASS = {
    'Shopify':              'shopify',
    'Amazon US':            'amazon',
    'Walmart Marketplace':  'walmart',
  };

  // ========== State ==========
  let state = {
    channels: [],
    startDate: null,
    endDate: null,
    channel: '',
    businessScope: '',
    distributionMetric: 'net_revenue',
  };

  let trendChart = null;
  let distributionChart = null;

  // ========== Formatters ==========
  const currencyFmt = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });

  const currencyFmtDecimal = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const numberFmt = new Intl.NumberFormat('en-US');

  function compactCurrency(val) {
    if (val >= 1_000_000) return '$' + (val / 1_000_000).toFixed(1) + 'M';
    if (val >= 1_000)     return '$' + (val / 1_000).toFixed(0) + 'k';
    return '$' + val.toFixed(0);
  }

  function formatDateDisplay(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  function formatDateRange(start, end) {
    const s = new Date(start + 'T00:00:00');
    const e = new Date(end + 'T00:00:00');
    const opts = { month: 'short', day: 'numeric', year: 'numeric' };
    return s.toLocaleDateString('en-US', opts) + ' – ' + e.toLocaleDateString('en-US', opts);
  }

  // ========== API Layer ==========
  async function apiFetch(endpoint, params = {}) {
    const url = new URL(API_BASE + endpoint, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') {
        url.searchParams.set(k, v);
      }
    });
    const res = await fetch(url.toString());
    if (!res.ok) {
      console.warn(`API ${endpoint} returned ${res.status}`);
      return null;
    }
    return res.json();
  }

  function buildFilterParams() {
    return {
      start_date: state.startDate || '',
      end_date:   state.endDate || '',
      channel:    state.channel || '',
      business_scope: state.businessScope || '',
    };
  }

  // ========== DOM Helpers ==========
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ========== Init ==========
  async function init() {
    // Load channels for filter dropdowns
    const channels = await apiFetch('/channels');
    if (channels) {
      state.channels = channels;
      populateFilters(channels);
    }

    // Set default date range (last 30 days from today)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    // Format as YYYY-MM-DD
    state.endDate = formatISO(today);
    state.startDate = formatISO(thirtyDaysAgo);

    $('#filter-start-date').value = state.startDate;
    $('#filter-end-date').value = state.endDate;

    // Bind events
    bindEvents();

    // Fetch all data
    await fetchAllData();
  }

  function formatISO(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // ========== Populate Filters ==========
  function populateFilters(channels) {
    const scopeSelect = $('#filter-scope');
    const channelSelect = $('#filter-channel');

    // Unique business scopes
    const scopes = [...new Set(channels.map(c => c.business_scope))].sort();
    scopes.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      scopeSelect.appendChild(opt);
    });

    // Channel names
    channels.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.name;
      opt.textContent = c.name;
      channelSelect.appendChild(opt);
    });
  }

  // ========== Event Bindings ==========
  function bindEvents() {
    $('#filter-scope').addEventListener('change', (e) => {
      state.businessScope = e.target.value;
      fetchAllData();
    });

    $('#filter-channel').addEventListener('change', (e) => {
      state.channel = e.target.value;
      fetchAllData();
    });

    $('#filter-start-date').addEventListener('change', (e) => {
      state.startDate = e.target.value;
      fetchAllData();
    });

    $('#filter-end-date').addEventListener('change', (e) => {
      state.endDate = e.target.value;
      fetchAllData();
    });

    $('#distribution-metric').addEventListener('change', (e) => {
      state.distributionMetric = e.target.value;
      fetchDistribution();
    });

    // Value / Percentage toggle (visual only)
    $('#toggle-value').addEventListener('click', () => {
      $('#toggle-value').classList.add('active');
      $('#toggle-percentage').classList.remove('active');
    });
    $('#toggle-percentage').addEventListener('click', () => {
      $('#toggle-percentage').classList.add('active');
      $('#toggle-value').classList.remove('active');
    });
  }

  // ========== Fetch All Data ==========
  async function fetchAllData() {
    const params = buildFilterParams();

    // Parallel requests
    const [overview, trends, distribution, performance] = await Promise.all([
      apiFetch('/overview', params),
      apiFetch('/trends', params),
      apiFetch('/channel-distribution', { ...params, metric: state.distributionMetric }),
      apiFetch('/channel-performance', params),
    ]);

    if (overview) renderOverview(overview);
    if (trends) renderTrendChart(trends);
    if (distribution) renderDistributionChart(distribution);
    if (performance) renderPerformanceTable(performance);

    // Update date range display
    const dateRange = overview?.date_range || trends?.date_range;
    if (dateRange) {
      $('#date-range-text').textContent = formatDateRange(dateRange.start, dateRange.end);
    }
  }

  async function fetchDistribution() {
    const params = buildFilterParams();
    const distribution = await apiFetch('/channel-distribution', {
      ...params,
      metric: state.distributionMetric,
    });
    if (distribution) renderDistributionChart(distribution);
  }

  // ========== Render: KPI Overview ==========
  function renderOverview(data) {
    const o = data.overview;

    animateValue('kpi-gmv', currencyFmt.format(o.gmv));
    animateValue('kpi-net-revenue', currencyFmt.format(o.net_revenue));
    animateValue('kpi-contribution', currencyFmt.format(o.contribution));
    animateValue('kpi-returns', currencyFmt.format(o.returns_refunds));
    animateValue('kpi-net-orders', numberFmt.format(o.net_orders));
    animateValue('kpi-aov', currencyFmtDecimal.format(o.average_order_value));
  }

  function animateValue(id, value) {
    const el = document.getElementById(id);
    el.classList.remove('skeleton');
    el.textContent = value;
    // Trigger re-animation
    el.style.animation = 'none';
    // Force reflow
    void el.offsetHeight;
    el.style.animation = 'fadeIn 0.3s ease';
  }

  // ========== Render: Trend Chart ==========
  function renderTrendChart(data) {
    const ctx = document.getElementById('trend-chart').getContext('2d');

    const labels = data.trends.map(t => formatDateDisplay(t.date));
    const revenueData = data.trends.map(t => t.net_revenue);
    const contribData = data.trends.map(t => t.contribution);

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Net revenue',
            data: revenueData,
            borderColor: '#4a7dff',
            backgroundColor: 'rgba(74, 125, 255, 0.05)',
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: '#4a7dff',
            pointHoverBorderColor: '#ffffff',
            pointHoverBorderWidth: 2,
            tension: 0.3,
            fill: true,
          },
          {
            label: 'Contribution',
            data: contribData,
            borderColor: '#1a1d23',
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: '#1a1d23',
            pointHoverBorderColor: '#ffffff',
            pointHoverBorderWidth: 2,
            tension: 0.3,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1a1d23',
            titleColor: '#ffffff',
            bodyColor: '#d1d5db',
            borderColor: '#374151',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            displayColors: true,
            boxWidth: 8,
            boxHeight: 8,
            boxPadding: 4,
            usePointStyle: true,
            callbacks: {
              label: function(ctx) {
                return ctx.dataset.label + ': ' + currencyFmt.format(ctx.parsed.y);
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: '#9ca3af',
              font: { size: 11, family: 'Inter' },
              maxTicksLimit: 8,
            },
            border: { display: false },
          },
          y: {
            grid: {
              color: '#f0f1f3',
              drawBorder: false,
            },
            ticks: {
              color: '#9ca3af',
              font: { size: 11, family: 'Inter' },
              callback: (val) => compactCurrency(val),
              maxTicksLimit: 5,
            },
            border: { display: false },
            beginAtZero: true,
          },
        },
        animation: {
          duration: 600,
          easing: 'easeOutQuart',
        },
      },
    });
  }

  // ========== Render: Distribution Chart ==========
  function renderDistributionChart(data) {
    const ctx = document.getElementById('distribution-chart').getContext('2d');

    const labels = data.distribution.map(d => d.channel);
    const values = data.distribution.map(d => d.value);
    const colors = labels.map(l => CHANNEL_COLORS[l] || '#9ca3af');

    if (distributionChart) distributionChart.destroy();

    const isOrdersMetric = data.metric === 'net_orders';

    distributionChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: colors,
            borderRadius: 4,
            borderSkipped: false,
            barThickness: 32,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1a1d23',
            titleColor: '#ffffff',
            bodyColor: '#d1d5db',
            borderColor: '#374151',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            callbacks: {
              label: function(ctx) {
                const val = ctx.parsed.x;
                return isOrdersMetric
                  ? numberFmt.format(val)
                  : currencyFmt.format(val);
              },
            },
          },
        },
        scales: {
          x: {
            grid: {
              color: '#f0f1f3',
              drawBorder: false,
            },
            ticks: {
              color: '#9ca3af',
              font: { size: 11, family: 'Inter' },
              callback: (val) => isOrdersMetric
                ? numberFmt.format(val)
                : compactCurrency(val),
              maxTicksLimit: 5,
            },
            border: { display: false },
            beginAtZero: true,
          },
          y: {
            grid: { display: false },
            ticks: {
              color: '#6b7280',
              font: { size: 12, family: 'Inter', weight: 500 },
            },
            border: { display: false },
          },
        },
        animation: {
          duration: 600,
          easing: 'easeOutQuart',
        },
      },
    });
  }

  // ========== Render: Performance Table ==========
  function renderPerformanceTable(data) {
    const tbody = document.getElementById('performance-tbody');
    tbody.innerHTML = '';

    data.channels.forEach((ch, idx) => {
      const cssClass = CHANNEL_CSS_CLASS[ch.channel] || '';
      const tr = document.createElement('tr');
      tr.style.animation = `fadeInUp 0.3s ease both ${0.05 * idx}s`;

      tr.innerHTML = `
        <td>
          <div class="channel-name-cell">
            <span class="channel-dot ${cssClass}"></span>
            ${escapeHtml(ch.channel)}
          </div>
        </td>
        <td>${currencyFmt.format(ch.gmv)}</td>
        <td>${currencyFmt.format(ch.net_revenue)}</td>
        <td>${currencyFmt.format(ch.contribution)}</td>
        <td>${currencyFmt.format(ch.returns_refunds)}</td>
        <td>${numberFmt.format(ch.net_orders)}</td>
        <td>${currencyFmtDecimal.format(ch.average_order_value)}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ========== Start ==========
  document.addEventListener('DOMContentLoaded', init);
})();
