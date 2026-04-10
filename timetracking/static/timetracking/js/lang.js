/* EN/DE language toggle — uses data-en and data-de attributes */
(function () {
    'use strict';
    function apply(lang) {
        if (lang !== 'en' && lang !== 'de') lang = 'en';
        document.querySelectorAll('[data-en][data-de]').forEach(function (el) {
            el.innerText = el.dataset[lang];
        });
        document.documentElement.lang = lang;
        document.querySelectorAll('.lang-btn').forEach(function (b) {
            b.classList.toggle('active', b.dataset.lang === lang);
        });
        try { localStorage.setItem('fitlife_lang', lang); } catch (e) {}
    }
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.lang-btn');
        if (btn) apply(btn.dataset.lang);
    });
    var stored = 'en';
    try { stored = localStorage.getItem('fitlife_lang') || 'en'; } catch (e) {}
    apply(stored);
})();
