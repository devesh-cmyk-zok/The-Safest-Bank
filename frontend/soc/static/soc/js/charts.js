// SOC charts (Chart.js). Colors come from validated tokens in soc.css:
// status scale for good/bad meaning, --soc-series-1 for single-series bars,
// --soc-neutral-mark for the "everything else" bucket. Text uses ink tokens, never series colors.
(function () {
  const css = getComputedStyle(document.documentElement);
  const token = (name) => css.getPropertyValue(name).trim();
  const SURFACE = token('--soc-card');
  const INK = token('--soc-text');
  const MUTED = token('--soc-text-muted');
  const GRID = 'rgba(148,163,184,0.12)';

  Chart.defaults.color = MUTED;
  Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
  Chart.defaults.font.size = 11;
  Chart.defaults.plugins.tooltip.backgroundColor = token('--soc-bg');
  Chart.defaults.plugins.tooltip.borderColor = token('--soc-border-lt');
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.titleColor = INK;
  Chart.defaults.plugins.tooltip.bodyColor = INK;

  // 2px surface-colored border = the gap between stacked segments / adjacent bars.
  const bar = (label, data, color, extra) => ({
    label, data, backgroundColor: color, borderColor: SURFACE, borderWidth: 2,
    borderRadius: 4, borderSkipped: 'start', maxBarThickness: 28, ...extra,
  });
  const axes = (stacked, yTitle) => ({
    x: { stacked, grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 12 } },
    y: { stacked, beginAtZero: true, grid: { color: GRID }, ticks: { precision: 0 },
         title: yTitle ? { display: true, text: yTitle } : undefined },
  });

  window.socCharts = {
    stackedHours(id, d) {
      return new Chart(document.getElementById(id), {
        type: 'bar',
        data: { labels: d.labels, datasets: [
          bar('Cleared', d.cleared, token('--soc-neutral-mark')),
          bar('Flagged', d.flagged, token('--soc-high')),
        ] },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { display: true, position: 'top', align: 'end', labels: { color: INK, boxWidth: 10, boxHeight: 10 } } },
          scales: axes(true, 'transfers'),
        },
      });
    },
    riskBands(id, bands) {
      const order = [['low', 'Low', '--soc-low'], ['medium', 'Medium', '--soc-medium'],
        ['high', 'High', '--soc-high'], ['critical', 'Critical', '--soc-critical']];
      return new Chart(document.getElementById(id), {
        type: 'bar',
        data: { labels: order.map((o) => o[1]), datasets: [
          bar('Transfers', order.map((o) => bands[o[0]]), order.map((o) => token(o[2]))),
        ] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: axes(false) },
      });
    },
    horizontal(id, labels, values, label) {
      return new Chart(document.getElementById(id), {
        type: 'bar',
        data: { labels, datasets: [bar(label, values, token('--soc-series-1'))] },
        options: {
          indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
          scales: { x: { beginAtZero: true, grid: { color: GRID }, ticks: { precision: 0 } }, y: { grid: { display: false }, ticks: { color: INK } } },
        },
      });
    },
  };
})();
