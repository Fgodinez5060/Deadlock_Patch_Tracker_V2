/* Shared renderers and data layer for the Deadlock Patch Tracker.
 *
 * The site is static: there is no server. data/patches.json and data/roster.json are
 * fetched directly and every view is derived from them in the browser. Paths are
 * relative so the site works both at a domain root and under a GitHub Pages project
 * path (/<repo>/).
 */

/* ---------- data ---------- */

let _patches = null;
let _roster = null;

/* Fetched once per page load and shared by every caller. */
function loadPatches() {
    if (!_patches) {
        _patches = fetch('data/patches.json').then(res => {
            if (!res.ok) throw new Error('patches.json returned ' + res.status);
            return res.json();
        });
    }
    return _patches;
}

/* {heroes: [...], items: [...]} - the single source of truth for both the parser
 * and the site, replacing the old hardcoded HEROES array. */
function loadRoster() {
    if (!_roster) {
        _roster = fetch('data/roster.json').then(res => {
            if (!res.ok) throw new Error('roster.json returned ' + res.status);
            return res.json();
        });
    }
    return _roster;
}

/* Heroes/items touched by the newest patch — drives the NEW pills and rail dots. */
function latestChangedHeroes(patches) {
    return patches.length ? Object.keys(patches[0].heroes || {}) : [];
}
function latestChangedItems(patches) {
    return patches.length ? Object.keys(patches[0].items || {}) : [];
}

/* Every recorded change for one hero/item, newest first. Each patch stores a flat,
 * ordered list of bullet strings per hero/item — no ability sub-grouping, no tags. */
function heroHistory(patches, name) {
    return patches
        .filter(patch => patch.heroes && name in patch.heroes)
        .map(patch => ({
            patch_name: patch.headline,
            posttime: patch.posttime,
            bullets: patch.heroes[name],
        }));
}
function itemHistory(patches, name) {
    return patches
        .filter(patch => patch.items && name in patch.items)
        .map(patch => ({
            patch_name: patch.headline,
            posttime: patch.posttime,
            bullets: patch.items[name],
        }));
}

function showError(message) {
    const main = document.querySelector('main') || document.body;
    const box = el('section', 'panel');
    box.appendChild(el('div', 'empty-state', message));
    main.appendChild(box);
}

/* ---------- page chrome ---------- */

const CHROME_HTML = `
<nav>
    <a href="index.html"><img class="logo" src="static/Deadlock_logo.webp" alt="Deadlock"></a>
    <ul>
        <a href="patches.html" data-nav="patches"><li>Patches</li></a>
        <a href="heroes.html" data-nav="heroes"><li>Heroes</li></a>
        <a href="items.html" data-nav="items"><li>Items</li></a>
    </ul>
    <button class="info-btn" id="info-btn" aria-label="About this site">i</button>
</nav>

<div class="modal-overlay" id="about-modal" hidden>
    <div class="modal-card">
        <button class="modal-close" id="modal-close" aria-label="Close">&times;</button>
        <h2>About</h2>
        <p>My name is Fernando &mdash; I'm a Software Engineering graduate. I built this
        Deadlock Patch Tracker to turn an idea into something people could actually use:
        a fast, readable way to follow every change across the roster. Patch notes are
        scraped from Steam and split into heroes/items/general changes with plain
        pattern matching — no AI parsing involved.</p>
        <p>Got a suggestion, comment, or just want to connect? I'd love to hear it.</p>
        <div class="modal-links">
            <a href="https://www.linkedin.com/in/fernando-godinez-685233322/" target="_blank" rel="noopener noreferrer">LinkedIn</a>
        </div>
    </div>
</div>
`;

/* Injects the nav + about modal every page shares, then wires the modal.
 * Active nav item comes from <body data-page="..."> (Flask used request.path). */
document.addEventListener('DOMContentLoaded', () => {
    document.body.insertAdjacentHTML('afterbegin', CHROME_HTML);

    const active = document.body.dataset.page;
    if (active) {
        const link = document.querySelector(`nav a[data-nav="${active}"]`);
        if (link) link.classList.add('active');
    }

    const modal = document.getElementById('about-modal');
    const openBtn = document.getElementById('info-btn');
    const closeBtn = document.getElementById('modal-close');
    if (!modal || !openBtn) return;

    const close = () => { modal.hidden = true; };
    openBtn.addEventListener('click', () => { modal.hidden = false; });
    closeBtn.addEventListener('click', close);
    modal.addEventListener('click', e => { if (e.target === modal) close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
});

/* ---------- rendering ---------- */

function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
}

function fmtDate(ts) {
    return new Date(ts * 1000).toLocaleDateString(undefined, {
        month: 'short', day: 'numeric', year: 'numeric',
    });
}

function typeBadge(type) {
    const labels = { update: 'Update', balance: 'Balance', hero_release: 'Hero Release' };
    return el('span', `badge type-${type}`, labels[type] || type);
}

/* A plain, un-tagged bullet list — every change is rendered exactly as scraped, with
 * no buff/nerf/fix classification (that was the most fragile, most "AI-flavored" part
 * of the previous schema and is not reproduced here). */
function changeList(bullets) {
    const ul = el('ul', 'change-list');
    (bullets || []).forEach(text => {
        const li = el('li', 'change');
        li.appendChild(el('span', 'text', text));
        ul.appendChild(li);
    });
    return ul;
}

function heroHref(name) {
    return 'hero.html?name=' + encodeURIComponent(name);
}
function itemHref(name) {
    return 'item.html?name=' + encodeURIComponent(name);
}

function heroLink(name) {
    const a = el('a', 'hero-line');
    a.href = heroHref(name);
    const img = el('img');
    img.src = `static/heroes/${name}.webp`;
    img.alt = name;
    img.loading = 'lazy';
    a.appendChild(img);
    a.appendChild(el('span', 'name', name));
    return a;
}

/* No item icon art exists yet (see README) — a plain text link stands in for now. */
function itemLink(name) {
    const a = el('a', 'item-line');
    a.href = itemHref(name);
    a.appendChild(el('span', 'name', name));
    return a;
}

/* One hero's or item's bullet list on its own detail page. */
function heroChangesFrag(entry) {
    return changeList(entry.bullets);
}
function itemChangesFrag(entry) {
    return changeList(entry.bullets);
}

/* Full patch body: heroes, items, general */
function patchBody(patch) {
    const frag = document.createDocumentFragment();

    const heroes = patch.heroes || {};
    if (Object.keys(heroes).length > 0) {
        const sect = el('div', 'sect');
        sect.appendChild(el('h3', 'sect-title', 'Heroes'));
        const cols = el('div', 'hero-cols');
        Object.keys(heroes).forEach(name => {
            const block = el('div', 'hero-block');
            block.appendChild(heroLink(name));
            block.appendChild(changeList(heroes[name]));
            cols.appendChild(block);
        });
        sect.appendChild(cols);
        frag.appendChild(sect);
    }

    const items = patch.items || {};
    if (Object.keys(items).length > 0) {
        const sect = el('div', 'sect');
        sect.appendChild(el('h3', 'sect-title', 'Items'));
        Object.keys(items).forEach(name => {
            sect.appendChild(itemLink(name));
            sect.appendChild(changeList(items[name]));
        });
        frag.appendChild(sect);
    }

    const general = patch.general || [];
    if (general.length > 0) {
        const sect = el('div', 'sect');
        sect.appendChild(el('h3', 'sect-title', 'General'));
        sect.appendChild(changeList(general));
        frag.appendChild(sect);
    }

    return frag;
}

function patchSummary(patch) {
    const parts = [];
    const nHeroes = Object.keys(patch.heroes || {}).length;
    const nItems = Object.keys(patch.items || {}).length;
    const nGeneral = (patch.general || []).length;
    if (nHeroes) parts.push(`${nHeroes} hero${nHeroes > 1 ? 'es' : ''}`);
    if (nItems) parts.push(`${nItems} item${nItems > 1 ? 's' : ''}`);
    if (nGeneral) parts.push(`${nGeneral} general`);
    return parts.join(' · ') || 'No changes listed';
}

/* Fills a .hero-rail element with all hero icons; activeName highlights + centers one */
function populateHeroRail(rail, activeName) {
    return Promise.all([loadRoster(), loadPatches()]).then(([roster, patches]) => {
        const HEROES = roster.heroes;
        const changed = new Set(latestChangedHeroes(patches));

        // recently-changed heroes first for quick access, alphabetical within each group
        const sorted = [
            ...HEROES.filter(name => changed.has(name)),
            ...HEROES.filter(name => !changed.has(name)),
        ];

        sorted.forEach(name => {
            const a = el('a', name === activeName ? 'active' : '');
            a.href = heroHref(name);
            a.title = name;

            const img = el('img');
            img.src = `static/heroes/${name}.webp`;
            img.alt = name;
            img.loading = 'lazy';
            a.appendChild(img);

            if (changed.has(name)) a.appendChild(el('span', 'rail-dot'));

            rail.appendChild(a);
        });

        const active = rail.querySelector('a.active');
        if (active) rail.scrollTop = active.offsetTop - rail.clientHeight / 2;
    });
}

/* Dropdown: options = [{label, sub, value}], onSelect(value) */
function createDropdown(options, initialValue, onSelect) {
    const dd = el('div', 'dd');
    const btn = el('button', 'dd-btn');
    const label = el('span', 'dd-label');
    const caret = el('span', 'dd-caret', '▼');
    btn.appendChild(label);
    btn.appendChild(caret);
    dd.appendChild(btn);

    const list = el('div', 'dd-list');
    dd.appendChild(list);

    let current = initialValue;

    function renderList() {
        list.innerHTML = '';
        options.forEach(opt => {
            const item = el('div', 'dd-item' + (opt.value === current ? ' active' : ''));
            item.appendChild(el('span', '', opt.label));
            if (opt.sub) item.appendChild(el('span', 'sub', opt.sub));
            item.addEventListener('click', () => {
                current = opt.value;
                label.textContent = opt.label;
                dd.classList.remove('open');
                renderList();
                onSelect(opt.value);
            });
            list.appendChild(item);
        });
    }

    const initial = options.find(o => o.value === initialValue) || options[0];
    label.textContent = initial ? initial.label : '';
    renderList();

    btn.addEventListener('click', e => {
        e.stopPropagation();
        dd.classList.toggle('open');
    });
    document.addEventListener('click', () => dd.classList.remove('open'));

    return dd;
}
