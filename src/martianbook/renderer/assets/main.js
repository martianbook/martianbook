// ── Theme ────────────────────────────────────────────────────────────────

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('martian-theme', theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

(function () {
  const saved = localStorage.getItem('martian-theme');
  applyTheme(saved || getSystemTheme());
})();

window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', e => {
  if (!localStorage.getItem('martian-theme')) {
    applyTheme(e.matches ? 'light' : 'dark');
  }
});

// ── Cell-level collapse ───────────────────────────────────────────────────

function toggleCell(header) {
  header.closest('.cell').classList.toggle('collapsed');
}

function expandAll() {
  document.querySelectorAll('.cell').forEach(c => c.classList.remove('collapsed'));
}

function collapseAll() {
  document.querySelectorAll('.cell').forEach(c => c.classList.add('collapsed'));
}

// ── Per-block collapse ────────────────────────────────────────────────────
// Called when user clicks a block label row (SOURCE, OUTPUT, ARTIFACT).
// Toggles only the content area of that specific block.

function toggleBlock(labelRow) {
  const block   = labelRow.closest('.block');
  const content = block.querySelector('.block-content');
  const chevron = labelRow.querySelector('.block-chevron');
  if (!content) return;

  const isCollapsed = content.dataset.collapsed === 'true';
  content.dataset.collapsed  = String(!isCollapsed);
  content.style.display      = isCollapsed ? '' : 'none';
  chevron.style.transform    = isCollapsed ? '' : 'rotate(-90deg)';
}

// ── Init ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Auto-collapse entire cells with no output, artifacts, or exceptions
  document.querySelectorAll('.cell').forEach(cell => {
    const hasContent = cell.querySelector(
      '.block-output, .block-artifact, .block-exception'
    );
    if (!hasContent) cell.classList.add('collapsed');
  });
});