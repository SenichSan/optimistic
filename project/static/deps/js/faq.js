// static/deps/js/accordion.js (smooth open/close, no jump)
document.addEventListener('DOMContentLoaded', function () {
  const root = document.querySelector('#faq-section') || document;
  const accordion = root.querySelector('.accordion');
  if (!accordion) return;

  const items = Array.from(accordion.querySelectorAll('.accordion-item'));

  // helper: create animation for a panel (open = true/false)
  function animatePanel(panel, open, duration = 260) {
    // cancel previous animation if exists
    if (panel._anim) {
      try { panel._anim.cancel(); } catch (e) { /* ignore */ }
      panel._anim = null;
    }

    // ensure panel has correct computed box-sizing before measure
    panel.style.overflow = 'hidden';

    const startHeight = panel.getBoundingClientRect().height;
    // when closed, startHeight is usually 0; measure content for target
    const contentHeight = measureContentHeight(panel);

    // compute target heights
    const fromHeight = open ? startHeight : contentHeight;
    const toHeight = open ? contentHeight : 0;

    // set explicit start height to allow animation
    panel.style.height = fromHeight + 'px';
    // ensure opacity baseline
    panel.style.opacity = (fromHeight === 0) ? '0' : '1';

    // Use Web Animations if available
    const keyframes = [
      { height: fromHeight + 'px', opacity: (fromHeight === 0) ? 0 : 1 },
      { height: toHeight + 'px',   opacity: (toHeight === 0) ? 0 : 1 }
    ];

    const timing = {
      duration: duration,
      easing: 'cubic-bezier(.2,.8,.2,1)',
      fill: 'forwards'
    };

    if (panel.animate) {
      panel._anim = panel.animate(keyframes, timing);
      panel._anim.addEventListener('finish', () => {
        panel._anim = null;
        // keep the panel at the final pixel height to avoid layout jumps
        panel.style.height = toHeight + 'px';
        panel.style.opacity = (toHeight === 0) ? '0' : '1';
        // if closed — keep overflow hidden; if opened — allow visible overflow
        panel.style.overflow = (toHeight === 0) ? 'hidden' : 'visible';
      });
      panel._anim.addEventListener('cancel', () => {
        panel._anim = null;
      });
    } else {
      // fallback for older browsers: instant switch (still better than switching to 'auto')
      panel.style.height = toHeight + 'px';
      panel.style.opacity = (toHeight === 0) ? '0' : '1';
      panel.style.overflow = (toHeight === 0) ? 'hidden' : 'visible';
    }
  }

  // measure content height even if panel currently has height 0
  function measureContentHeight(panel) {
    // temporarily set height to 'auto' but without transitions to measure
    const prevHeight = panel.style.height;
    const prevOverflow = panel.style.overflow;
    panel.style.height = 'auto';
    panel.style.overflow = 'visible';
    const h = panel.scrollHeight;
    // restore
    panel.style.height = prevHeight;
    panel.style.overflow = prevOverflow;
    return h;
  }

  // close others for single-open behaviour
  function closeOthers(exceptBtn) {
    items.forEach(item => {
      const b = item.querySelector('button');
      const p = item.querySelector('.accordion-content');
      if (b !== exceptBtn && b.getAttribute('aria-expanded') === 'true') {
        b.setAttribute('aria-expanded', 'false');
        p.setAttribute('aria-hidden', 'true');
        animatePanel(p, false);
      }
    });
  }

  items.forEach(item => {
    const btn = item.querySelector('button');
    const panel = item.querySelector('.accordion-content');

    // ensure panel baseline styles
    panel.style.overflow = 'hidden';
    panel.style.height = '0px';
    panel.style.opacity = '0';

    // sync initial states from markup
    if (btn.getAttribute('aria-expanded') === 'true') {
      const h = measureContentHeight(panel);
      panel.style.height = h + 'px';
      panel.style.opacity = '1';
      panel.style.overflow = 'visible';
      panel.setAttribute('aria-hidden', 'false');
    } else {
      panel.style.height = '0px';
      panel.style.opacity = '0';
      panel.style.overflow = 'hidden';
      panel.setAttribute('aria-hidden', 'true');
    }

    // click toggling
    btn.addEventListener('click', () => {
      const open = btn.getAttribute('aria-expanded') !== 'true';
      if (open) {
        closeOthers(btn); // comment out to allow multiple open
        btn.setAttribute('aria-expanded', 'true');
        panel.setAttribute('aria-hidden', 'false');
        animatePanel(panel, true);
      } else {
        btn.setAttribute('aria-expanded', 'false');
        panel.setAttribute('aria-hidden', 'true');
        animatePanel(panel, false);
      }
    });

    // keyboard support
    btn.addEventListener('keydown', (e) => {
      const allButtons = Array.from(accordion.querySelectorAll('button'));
      const idx = allButtons.indexOf(btn);
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          allButtons[(idx + 1) % allButtons.length].focus();
          break;
        case 'ArrowUp':
          e.preventDefault();
          allButtons[(idx - 1 + allButtons.length) % allButtons.length].focus();
          break;
        case 'Home':
          e.preventDefault();
          allButtons[0].focus();
          break;
        case 'End':
          e.preventDefault();
          allButtons[allButtons.length - 1].focus();
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          btn.click();
          break;
      }
    });

    // optional: update height if window resizes and panel is open
    window.addEventListener('resize', () => {
      if (btn.getAttribute('aria-expanded') === 'true') {
        // recompute natural content height and set it
        const newH = measureContentHeight(panel);
        // if there's a running animation, cancel and set to newH
        if (panel._anim) {
          try { panel._anim.cancel(); } catch (e) {}
          panel._anim = null;
        }
        panel.style.height = newH + 'px';
      }
    });
  });
});
