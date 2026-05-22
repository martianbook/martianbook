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

// ── Mode ─────────────────────────────────────────────────────────────────

const SERVE_MODE = document.documentElement.dataset.mode === 'serve';

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

// ── Text node editing (serve mode only) ──────────────────────────────────

async function saveTextNode(textId) {
  if (!SERVE_MODE) return;
  const textarea = document.getElementById(`textarea-${textId}`);
  if (!textarea) return;

  const btn = textarea.closest('.text-node').querySelector('.text-node-btn');
  const originalText = btn.textContent;
  btn.textContent = 'saving…';
  btn.disabled = true;

  try {
    const res = await fetch('/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: textId, content: textarea.value }),
    });
    if (res.ok) {
      btn.textContent = 'saved ✓';
      // Mark as edited if not already
      const node = textarea.closest('.text-node');
      if (!node.querySelector('.text-node-edited')) {
        const toolbar = node.querySelector('.text-node-toolbar');
        const badge = document.createElement('span');
        badge.className = 'text-node-edited';
        badge.textContent = 'edited';
        toolbar.insertBefore(badge, toolbar.querySelector('.text-node-btn'));
      }
      setTimeout(() => { btn.textContent = 'save'; btn.disabled = false; }, 1500);
    } else {
      btn.textContent = 'error';
      setTimeout(() => { btn.textContent = originalText; btn.disabled = false; }, 2000);
    }
  } catch {
    btn.textContent = 'error';
    setTimeout(() => { btn.textContent = originalText; btn.disabled = false; }, 2000);
  }
}

async function deleteTextNode(textId) {
  if (!SERVE_MODE) return;
  if (!confirm('Delete this text block?')) return;

  try {
    const res = await fetch(`/text/${textId}`, { method: 'DELETE' });
    if (res.ok) {
      const node = document.querySelector(`[data-text-id="${textId}"]`);
      if (node) node.remove();
    }
  } catch {
    alert('Could not delete text block.');
  }
}

async function addTextNode(anchorId) {
  if (!SERVE_MODE) return;

  try {
    const res = await fetch('/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anchor_id: anchorId, content: '' }),
    });

    if (!res.ok) return;
    const { id } = await res.json();

    // Inject a new editable text node DOM element above the add button
    const addRow = document.querySelector(
      `.add-text-node-row[data-anchor="${anchorId}"]`
    ) || document.querySelector(
      // fallback: find add button near this cell
      `.cell[data-id="${anchorId}"]`
    )?.previousElementSibling;

    // Simplest approach: reload the page to get server-rendered HTML with the new node
    window.location.reload();
  } catch {
    alert('Could not add text block.');
  }
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

  // In serve mode: auto-resize textareas to content
  if (SERVE_MODE) {
    document.querySelectorAll('.text-node-area').forEach(ta => {
      ta.style.height = 'auto';
      ta.style.height = ta.scrollHeight + 'px';
      ta.addEventListener('input', () => {
        ta.style.height = 'auto';
        ta.style.height = ta.scrollHeight + 'px';
      });
    });
  }
});