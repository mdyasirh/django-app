/**
 * FitLife Studio – Custom I18N (EN/DE) Toggle
 * Uses data-en / data-de attributes on elements.
 */

function applyLang() {
  const lang = localStorage.getItem('lang') || 'en';
  document.querySelectorAll('[data-en][data-de]').forEach(el => {
    el.textContent = el.getAttribute('data-' + lang);
  });
  const btn = document.getElementById('langToggle');
  if (btn) {
    btn.textContent = lang === 'en' ? 'EN | DE' : 'DE | EN';
  }
}

function toggleLang() {
  const current = localStorage.getItem('lang') || 'en';
  const next = current === 'en' ? 'de' : 'en';
  localStorage.setItem('lang', next);
  applyLang();
}

// Apply language on page load
document.addEventListener('DOMContentLoaded', applyLang);
