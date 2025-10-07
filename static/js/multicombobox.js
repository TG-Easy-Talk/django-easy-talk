(function () {
    const SELECTOR = 'select[multiple][data-combobox="multi"]';

    function init(select) {
        if (select.dataset.mcInited) return;
        select.dataset.mcInited = "true";

        const MAX_VISIBLE_CHIPS_COLLAPSED = 5;
        let chipsExpanded = false;

        const opts = Array.from(select.options).map(o => ({
            value: o.value, label: o.text, selected: o.selected, hidden: false
        }));
        let open = false, activeIndex = -1;
        const idBase = select.id || `mc_${Math.random().toString(36).slice(2)}`;
        const listboxId = `${idBase}_listbox`;

        const root = document.createElement('div');
        root.className = 'mc-root';
        const inputWrap = document.createElement('div');
        inputWrap.className = 'mc-inputwrap';
        root.appendChild(inputWrap);
        const chips = document.createElement('div');
        chips.className = 'mc-chips';
        inputWrap.appendChild(chips);

        const input = document.createElement('input');
        Object.assign(input, {type: 'text', className: 'mc-input'});
        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-controls', listboxId);
        input.setAttribute('aria-expanded', 'false');
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('spellcheck', 'false');
        input.setAttribute('placeholder', 'Buscar…');
        inputWrap.appendChild(input);

        const listbox = document.createElement('ul');
        Object.assign(listbox, {id: listboxId, className: 'mc-listbox'});
        listbox.setAttribute('role', 'listbox');
        listbox.setAttribute('aria-multiselectable', 'true');
        listbox.setAttribute('aria-hidden', 'true');
        root.appendChild(listbox);

        select.parentNode.insertBefore(root, select);
        select.hidden = true;

        const visibleOptions = () => opts.filter(o => !o.hidden);

        const rebuildListbox = () => {
            listbox.innerHTML = '';
            visibleOptions().forEach((o, i) => {
                const li = document.createElement('li');
                li.id = `${idBase}_opt_${i}`;
                li.className = 'mc-option';
                li.setAttribute('role', 'option');
                li.setAttribute('aria-selected', String(!!o.selected));
                li.textContent = o.label;
                li.dataset.indexVisible = String(i);
                li.addEventListener('mousedown', e => {
                    e.preventDefault();
                    toggleByVisibleIndex(i, true);
                });
                listbox.appendChild(li);
            });
            clampActive();
            markActive();
        };

        const makeChip = (label, onRemove) => {
            const chip = document.createElement('span');
            chip.className = 'mc-chip';
            chip.textContent = label;
            chip.title = label;
            const btn = document.createElement('button');
            btn.className = 'mc-chip-x';
            btn.type = 'button';
            btn.setAttribute('aria-label', `Remover ${label}`);
            btn.textContent = '×';
            btn.addEventListener('click', onRemove);
            chip.appendChild(btn);
            return chip;
        };

        const makeSummaryChip = (n) => {
            const chip = document.createElement('span');
            chip.className = 'mc-chip mc-chip-summary';
            chip.setAttribute('role', 'button');
            chip.setAttribute('tabindex', '0');
            chip.textContent = `+${n}`;
            chip.title = `Mostrar mais ${n}`;
            const toggle = () => {
                chipsExpanded = true;
                rebuildChips();
                input.focus();
            };
            chip.addEventListener('click', toggle);
            chip.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggle();
                }
            });
            return chip;
        };

        const rebuildChips = () => {
            chips.innerHTML = '';
            const selected = opts.filter(o => o.selected);
            const total = selected.length;

            chips.classList.toggle('is-expanded', chipsExpanded);

            if (!chipsExpanded && total > MAX_VISIBLE_CHIPS_COLLAPSED) {
                const show = MAX_VISIBLE_CHIPS_COLLAPSED - 1;
                selected.slice(0, show).forEach(o => chips.appendChild(makeChip(o.label, () => setSelected(o.value, false))));
                chips.appendChild(makeSummaryChip(total - show));
            } else {
                selected.forEach(o => chips.appendChild(makeChip(o.label, () => setSelected(o.value, false))));
                if (chipsExpanded && total > MAX_VISIBLE_CHIPS_COLLAPSED) {
                    const collapse = document.createElement('button');
                    collapse.type = 'button';
                    collapse.className = 'mc-chip mc-chip-summary';
                    collapse.textContent = 'colapsar';
                    collapse.addEventListener('click', () => {
                        chipsExpanded = false;
                        rebuildChips();
                        input.focus();
                    });
                    chips.appendChild(collapse);
                }
            }
        };

        const syncSelect = () => {
            const byVal = new Map(opts.map(o => [o.value, o.selected]));
            Array.from(select.options).forEach(o => (o.selected = !!byVal.get(o.value)));
            select.dispatchEvent(new Event('change', {bubbles: true}));
        };

        function openListbox() {
            if (open) return;
            open = true;
            listbox.setAttribute('aria-hidden', 'false');
            input.setAttribute('aria-expanded', 'true');
            if (visibleOptions().length) {
                activeIndex = 0;
                markActive();
            }
        }

        function closeListbox() {
            if (!open) return;
            open = false;
            listbox.setAttribute('aria-hidden', 'true');
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
            activeIndex = -1;
        }

        function clampActive() {
            const len = visibleOptions().length;
            if (!len) {
                activeIndex = -1;
                return;
            }
            if (activeIndex < 0) activeIndex = 0;
            if (activeIndex > len - 1) activeIndex = len - 1;
        }

        function markActive() {
            Array.from(listbox.children).forEach((li, i) => {
                li.classList.toggle('mc-active', i === activeIndex);
                if (i === activeIndex) input.setAttribute('aria-activedescendant', li.id);
            });
            if (activeIndex >= 0) listbox.children[activeIndex]?.scrollIntoView({block: 'nearest'});
        }

        function setSelected(value, on) {
            const o = opts.find(x => x.value === value);
            if (!o) return;
            o.selected = !!on;
            if (!o.selected && chipsExpanded && opts.filter(x => x.selected).length <= MAX_VISIBLE_CHIPS_COLLAPSED) chipsExpanded = false;
            rebuildChips();
            Array.from(listbox.children).forEach(li => {
                const idx = Number(li.dataset.indexVisible), vis = visibleOptions()[idx];
                if (vis) li.setAttribute('aria-selected', String(!!vis.selected));
            });
            syncSelect();
        }

        function toggleByVisibleIndex(i, keepOpen) {
            const o = visibleOptions()[i];
            if (!o) return;
            setSelected(o.value, !o.selected);
            if (!keepOpen) closeListbox();
            input.focus();
            markActive();
        }

        function filterOptions(q) {
            const t = q.trim().toLowerCase();
            opts.forEach(o => {
                o.hidden = t ? !o.label.toLowerCase().includes(t) : false;
            });
            rebuildListbox();
        }

        input.addEventListener('focus', openListbox);
        input.addEventListener('input', () => {
            openListbox();
            filterOptions(input.value);
        });
        input.addEventListener('keydown', (e) => {
            const k = e.key;
            if (k === 'ArrowDown') {
                e.preventDefault();
                openListbox();
                if (visibleOptions().length) {
                    activeIndex = Math.min(activeIndex + 1, visibleOptions().length - 1);
                    markActive();
                }
            } else if (k === 'ArrowUp') {
                e.preventDefault();
                openListbox();
                if (visibleOptions().length) {
                    activeIndex = Math.max(activeIndex - 1, 0);
                    markActive();
                }
            } else if (k === 'Home' && open) {
                e.preventDefault();
                activeIndex = 0;
                markActive();
            } else if (k === 'End' && open) {
                e.preventDefault();
                activeIndex = visibleOptions().length - 1;
                markActive();
            } else if ((k === 'Enter' || k === ' ') && open && activeIndex >= 0) {
                e.preventDefault();
                toggleByVisibleIndex(activeIndex, true);
            } else if (k === 'Escape' && open) {
                e.preventDefault();
                closeListbox();
            } else if (k === 'Backspace' && !input.value) {
                const last = opts.filter(o => o.selected).pop();
                if (last) {
                    e.preventDefault();
                    setSelected(last.value, false);
                }
            }
        });

        document.addEventListener('mousedown', e => {
            if (!root.contains(e.target)) closeListbox();
        });

        rebuildChips();
        rebuildListbox();
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll(SELECTOR).forEach(init);
    });
})();
