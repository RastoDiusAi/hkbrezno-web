(function () {
  'use strict';
  var PAGES = ["domov", "novinky", "zapasy", "rozpisladu", "timy", "klub", "rodicia", "partneri", "prihlaska", "sukromie"];
  var CLUB_SECTIONS = ['o-klube', 'vedenie', 'trenerska-struktura'];

  function setClubSection(section, updateHistory) {
    if (CLUB_SECTIONS.indexOf(section) === -1) section = 'o-klube';
    document.documentElement.dataset.clubSection = section;
    document.querySelectorAll('[data-club-tab]').forEach(function (button) {
      var active = button.dataset.clubTab === section;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
    });
    document.querySelectorAll('[data-club-panel]').forEach(function (panel) {
      panel.hidden = panel.dataset.clubPanel !== section;
    });
    if (updateHistory) {
      var url = new URL(location.href);
      url.searchParams.set('page', 'klub');
      url.searchParams.set('sekcia', section);
      history.pushState({ page: 'klub', section: section }, '', url.pathname + url.search);
    }
  }

  function go(page, updateHistory) {
    if (PAGES.indexOf(page) === -1) return;
    document.documentElement.dataset.page = page;
    document.documentElement.classList.remove('nav-open');
    if (updateHistory !== false) {
      var url = page === 'domov' ? location.pathname : location.pathname + '?page=' + encodeURIComponent(page);
      history.pushState({ page: page }, '', url);
    }
    if (page === 'klub') setClubSection('o-klube', false);
    window.scrollTo(0, 0);
    onScroll();
  }

  function scrollToTarget(targetId, smooth) {
    if (!targetId) return;
    window.requestAnimationFrame(function () {
      var target = document.getElementById(targetId);
      if (target) target.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
    });
  }

  var requestedPage = new URLSearchParams(location.search).get('page');
  if (requestedPage && PAGES.indexOf(requestedPage) !== -1) go(requestedPage, false);
  setClubSection(new URLSearchParams(location.search).get('sekcia') || 'o-klube', false);
  scrollToTarget(location.hash.slice(1), false);
  window.addEventListener('popstate', function () {
    var params = new URLSearchParams(location.search);
    var page = params.get('page') || 'domov';
    go(page, false);
    setClubSection(params.get('sekcia') || 'o-klube', false);
    scrollToTarget(location.hash.slice(1), false);
  });

  document.addEventListener('click', function (event) {
    var clubTab = event.target.closest('[data-club-tab]');
    if (clubTab) {
      event.preventDefault();
      setClubSection(clubTab.dataset.clubTab, true);
      return;
    }
    var trigger = event.target.closest('[data-go]');
    if (!trigger) return;
    event.preventDefault();
    go(trigger.dataset.go);
    if (trigger.dataset.scrollTarget) {
      var url = new URL(location.href);
      url.hash = trigger.dataset.scrollTarget;
      history.replaceState({ page: trigger.dataset.go }, '', url.pathname + url.search + url.hash);
      scrollToTarget(trigger.dataset.scrollTarget, true);
    }
  });

  var bar = document.querySelector('[data-navbar]');
  if (bar) {
    var burger = document.createElement('button');
    burger.className = 'hk-burger';
    burger.type = 'button';
    burger.setAttribute('aria-label', 'Menu');
    burger.setAttribute('aria-expanded', 'false');
    for (var i = 0; i < 3; i += 1) burger.appendChild(document.createElement('span'));
    burger.addEventListener('click', function () {
      var isOpen = document.documentElement.classList.toggle('nav-open');
      burger.setAttribute('aria-expanded', String(isOpen));
    });
    bar.appendChild(burger);
    document.addEventListener('click', function (event) {
      if (!document.documentElement.classList.contains('nav-open')) return;
      if (bar.contains(event.target)) return;
      document.documentElement.classList.remove('nav-open');
      burger.setAttribute('aria-expanded', 'false');
    });
  }

  function onScroll() {
    var y = window.scrollY || document.documentElement.scrollTop || 0;
    if (bar) bar.classList.toggle('is-stuck', y > 120);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  var scheduleNode = document.querySelector('[data-home-schedule]');
  var schedule = [];
  if (scheduleNode) {
    try { schedule = JSON.parse(scheduleNode.textContent); } catch (error) { schedule = []; }
  }

  function bratislavaDate() {
    try {
      var parts = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Europe/Bratislava', year: 'numeric', month: '2-digit', day: '2-digit'
      }).formatToParts(new Date());
      var values = {};
      parts.forEach(function (part) { values[part.type] = part.value; });
      return values.year + '-' + values.month + '-' + values.day;
    } catch (error) {
      var now = new Date();
      return now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    }
  }

  function matchDateLabel(match) {
    var values = match.date.split('-').map(Number);
    var dayNames = ['Nedeľa', 'Pondelok', 'Utorok', 'Streda', 'Štvrtok', 'Piatok', 'Sobota'];
    var weekday = new Date(Date.UTC(values[0], values[1] - 1, values[2])).getUTCDay();
    return dayNames[weekday] + ' ' + values[2] + '. ' + values[1] + '. ' + values[0] + ' · ' + match.time;
  }

  function setText(selector, value) {
    var element = document.querySelector(selector);
    if (element) element.textContent = value;
  }

  function setTeam(side, name, logo) {
    setText('[data-home-' + side + '-name]', name);
    var image = document.querySelector('[data-home-' + side + '-logo]');
    if (image) {
      image.src = logo;
      image.alt = 'Logo ' + name;
    }
  }

  function renderTicker(matches) {
    var ticker = document.querySelector('[data-home-ticker]');
    var container = document.querySelector('[data-home-ticker-items]');
    if (!ticker || !container) return;
    container.replaceChildren();
    ticker.hidden = matches.length === 0;
    matches.forEach(function (match, index) {
      if (index > 0) {
        var divider = document.createElement('span');
        divider.style.color = '#2B4C7E';
        divider.textContent = '/';
        container.appendChild(divider);
      }
      var item = document.createElement('span');
      var strong = document.createElement('strong');
      var values = match.date.split('-').map(Number);
      strong.style.cssText = "color:#fff;font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:14px";
      strong.textContent = values[2] + '. ' + values[1] + '. · ' + match.time;
      item.appendChild(strong);
      item.appendChild(document.createTextNode(' ' + match.opponent + ' · ' + (match.location === 'home' ? 'doma' : 'vonku')));
      container.appendChild(item);
    });
  }

  function updateHomeSchedule() {
    if (!schedule.length) return;
    var today = bratislavaDate();
    var upcoming = schedule.filter(function (match) { return match.date >= today; });
    var featured = upcoming[0];
    var root = document.querySelector('[data-home-next-match]');
    if (!featured) {
      if (root) root.hidden = true;
      renderTicker([]);
      return;
    }
    if (root) root.hidden = false;
    setTeam('home', featured.home, featured.homeLogo);
    setTeam('away', featured.away, featured.awayLogo);
    setText('[data-home-match-date]', matchDateLabel(featured));
    setText('[data-home-match-venue]', featured.venue);
    setText('[data-home-match-location]', featured.location === 'home' ? 'Doma' : 'Vonku');
    var source = document.querySelector('[data-home-match-source]');
    if (source) source.href = featured.sourceUrl;
    renderTicker(upcoming.slice(1, 5));
  }

  updateHomeSchedule();
  window.setInterval(updateHomeSchedule, 60000);
})();
