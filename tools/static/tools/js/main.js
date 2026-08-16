// Shared front-end behaviour for ResumeIQ.

// ---------------------------------------------------------------------
// FLASH MESSAGES: the confirmation/error banner renders at the very top
// of the page (right under the navbar). On long pages like Contact, the
// form that triggered it can be far below the fold, so after a normal
// full-page form submit the banner is easy to miss. Scroll it into view
// and give it a brief highlight pulse so it's impossible to miss.
// ---------------------------------------------------------------------
function initFlashMessageScroll() {
  const box = document.querySelector('.messages');
  if (!box) return;
  box.scrollIntoView({ behavior: 'smooth', block: 'center' });
  box.classList.add('flash-highlight');
  setTimeout(() => box.classList.remove('flash-highlight'), 1600);
}

// ---------------------------------------------------------------------
// AURA HOVER: track the cursor over every .btn and feed its position
// into --mx/--my so the glow in style.css follows the pointer exactly.
// ---------------------------------------------------------------------
function initAuraButtons() {
  document.querySelectorAll('.btn').forEach((btn) => {
    btn.addEventListener('mousemove', (e) => {
      const rect = btn.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      btn.style.setProperty('--mx', `${x}%`);
      btn.style.setProperty('--my', `${y}%`);
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.setProperty('--mx', '50%');
      btn.style.setProperty('--my', '50%');
    });
  });
}

// ---------------------------------------------------------------------
// PANEL FOCUS GROUP: within any .panel-focus-group container, hovering
// one .panel grows it and intensifies its edge glow, while sibling
// panels shrink and dim slightly — used on the Tools page only.
// ---------------------------------------------------------------------
function initPanelFocusGroups() {
  document.querySelectorAll('.panel-focus-group').forEach((container) => {
    const panels = Array.from(container.querySelectorAll('.panel'));
    if (panels.length < 2) return;

    panels.forEach((panel) => {
      panel.addEventListener('mouseenter', () => {
        panels.forEach((p) => {
          p.classList.toggle('is-focused', p === panel);
          p.classList.toggle('is-other', p !== panel);
        });
      });
    });

    container.addEventListener('mouseleave', () => {
      panels.forEach((p) => p.classList.remove('is-focused', 'is-other'));
    });
  });
}

// ---------------------------------------------------------------------
// TOOL CARD FOCUS: hovering one of the three home-page tool cards grows
// and glows it (same calm scale + dim treatment as the Tools page
// "Working" panels) while the other two shrink and dim.
// ---------------------------------------------------------------------
function initToolCardFocusGroup() {
  const container = document.querySelector('.tool-cards');
  if (!container) return;

  const cards = Array.from(container.querySelectorAll('.tool-card'));
  if (cards.length < 2) return;

  cards.forEach((card) => {
    card.addEventListener('mouseenter', () => {
      cards.forEach((c) => {
        c.classList.toggle('is-focused', c === card);
        c.classList.toggle('is-other', c !== card);
      });
    });
  });

  container.addEventListener('mouseleave', () => {
    cards.forEach((c) => c.classList.remove('is-focused', 'is-other'));
  });
}

// ---------------------------------------------------------------------
// CLICK RIPPLE: a quick expanding circle bursts from the exact click
// point on any .btn, then removes itself once the animation finishes.
// ---------------------------------------------------------------------
function initButtonRipples() {
  document.querySelectorAll('.btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
      btn.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });
}

// ---------------------------------------------------------------------
// ATS SCORE RING: animates the circular progress ring and counts the
// number up from 0 once the "ATS Score" panel scrolls into view.
// Runs once per page load (IntersectionObserver disconnects itself
// after the first reveal).
// ---------------------------------------------------------------------
function initAtsScoreRing() {
  const panel = document.querySelector('.ats-wheel-block');
  if (!panel) return;

  const ring = panel.querySelector('.score-ring-fill');
  const numEl = panel.querySelector('.score-num');
  if (!ring || !numEl) return;

  const score = parseFloat(ring.dataset.score || numEl.dataset.target || '0');
  const radius = ring.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;
  ring.style.strokeDasharray = `${circumference}`;
  ring.style.strokeDashoffset = `${circumference}`;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const reveal = () => {
    panel.classList.add('is-visible');

    if (reducedMotion) {
      ring.style.strokeDashoffset = `${circumference - (score / 100) * circumference}`;
      numEl.textContent = Math.round(score);
      return;
    }

    // Kick off the ring fill (CSS transition handles the easing).
    requestAnimationFrame(() => {
      ring.style.strokeDashoffset = `${circumference - (score / 100) * circumference}`;
    });

    // Count the number up over the same ~1.6s window.
    const duration = 1600;
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      numEl.textContent = Math.round(score * eased);
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  if (!('IntersectionObserver' in window)) {
    reveal();
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        reveal();
        observer.disconnect();
      }
    });
  }, { threshold: 0.4 });

  observer.observe(panel);
}

// ---------------------------------------------------------------------
// PRINT TITLE: browsers print the page <title> as a header/footer
// watermark ("Resume Creator — ResumeIQ ...url... 1/1"). Swap it down to
// a short, clean "ResumeIQ" for the duration of the print job only, then
// restore the real title once the print dialog closes.
// ---------------------------------------------------------------------
function initPrintTitleFix() {
  let originalTitle = document.title;
  window.addEventListener('beforeprint', () => {
    originalTitle = document.title;
    document.title = 'ResumeIQ';
  });
  window.addEventListener('afterprint', () => {
    document.title = originalTitle;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initAuraButtons();
  initPanelFocusGroups();
  initToolCardFocusGroup();
  initButtonRipples();
  initAtsScoreRing();
  initPrintTitleFix();
  initFlashMessageScroll();

  const box = document.getElementById('upload-box');
  const input = document.getElementById('resume_file');
  if (!box || !input) return;

  ['dragover', 'dragenter'].forEach(evt => {
    box.addEventListener(evt, (e) => {
      e.preventDefault();
      box.style.background = 'var(--teal-soft)';
    });
  });

  ['dragleave', 'drop'].forEach(evt => {
    box.addEventListener(evt, (e) => {
      e.preventDefault();
      box.style.background = '';
    });
  });

  box.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      input.dispatchEvent(new Event('change'));
    }
  });
});
