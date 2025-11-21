(() => {
    "use strict";

    const cfgEl = document.getElementById("perfil-config");
    let SERVER = {};
    try {
        SERVER = JSON.parse(cfgEl?.textContent || "{}");
    } catch (e) {
        SERVER = {};
    }

    const OCUPADOS = new Set(Array.isArray(SERVER.ocupados) ? SERVER.ocupados : []);

    const CFG = {
        MATRIZ: Array.isArray(SERVER.matriz) ? SERVER.matriz : [],
        DURACAO: Number(SERVER.duracao) || 50,
        MIN_ANT: Number(SERVER.minAntecedencia) || 0,
        MAX_ANT: Number(SERVER.maxAntecedencia) || 0,
        VALOR: Number(String(SERVER.valor ?? "0").replace(",", ".")) || 0,
    };

    const $ = (sel) => document.querySelector(sel);
    const pad = (n) => String(n).padStart(2, "0");
    const brl = (v) => v.toLocaleString("pt-BR", {style: "currency", currency: "BRL"});

    function dateKeyLocal(d) {
        const y = d.getFullYear(), m = d.getMonth() + 1, day = d.getDate();
        return `${y}-${pad(m)}-${pad(day)}`;
    }

    function idxToHora(i) {
        const mins = i * CFG.DURACAO;
        const h = Math.floor(mins / 60);
        const m = mins % 60;
        return `${pad(h)}:${pad(m)}`;
    }

    function horariosParaData(date) {
        const dow = date.getDay();
        const linha = CFG.MATRIZ[dow] || [];
        const agora = new Date();
        const minOK = new Date(agora.getTime() + CFG.MIN_ANT * 60 * 1000);
        const maxOK = CFG.MAX_ANT ? new Date(agora.getTime() + CFG.MAX_ANT * 60 * 1000) : null;

        const y = date.getFullYear(), m = date.getMonth(), d = date.getDate();
        const opcoes = [];

        for (let i = 0; i < linha.length; i++) {
            if (!linha[i]) continue;
            const [hh, mm] = idxToHora(i).split(":").map(Number);
            const dt = new Date(y, m, d, hh, mm, 0, 0);
            const value = `${y}-${pad(m + 1)}-${pad(d)}T${pad(hh)}:${pad(mm)}`;
            if (OCUPADOS.has(value)) continue;

            const ehPassadoNoDia = dt < agora;

            if (ehPassadoNoDia) {
                opcoes.push({label: `${pad(hh)}:${pad(mm)}`, value, disabled: true});
                continue;
            }

            if (CFG.MIN_ANT && dt < minOK) continue;
            if (maxOK && dt > maxOK) continue;

            opcoes.push({label: `${pad(hh)}:${pad(mm)}`, value, disabled: false});
        }
        return opcoes;
    }

    const BookingUI = (() => {
        const state = {escolhas: Object.create(null)};
        const els = {
            lista: $("#lista-slots"),
            totalValor: $("#total-valor"),
            totalDesc: $("#total-descricao"),
            btnConfirmar: $("#btn-confirmar"),
            hidden: $("#id_agendamentos"),
            sidebar: $("#agendamentoConsulta"),
        };

        function renderLista(selectedDates) {
            if (!selectedDates || selectedDates.length === 0) {
                els.lista.textContent = "";
                state.escolhas = Object.create(null);
                syncHiddenAndTotal();
                return;
            }

            els.lista.textContent = "";
            const datas = [...selectedDates].sort((a, b) => a - b);
            const chavesAtuais = new Set(datas.map(dateKeyLocal));

            for (const key of Object.keys(state.escolhas)) {
                if (!chavesAtuais.has(key)) {
                    delete state.escolhas[key];
                }
            }

            for (const date of datas) {
                const dataKey = dateKeyLocal(date);
                const opcoes = horariosParaData(date);

                const linha = document.createElement("div");
                linha.className = "linha-slot";

                const spanData = document.createElement("div");
                spanData.className = "data";
                spanData.textContent = new Intl.DateTimeFormat("pt-BR", {
                    day: "2-digit",
                    month: "2-digit"
                }).format(date);

                const select = document.createElement("select");
                select.className = "form-select form-select-sm";
                select.setAttribute("aria-label", `Selecione um horário para ${spanData.textContent}`);
                select.dataset.key = dataKey;

                if (opcoes.length === 0) {
                    const o = document.createElement("option");
                    o.value = "";
                    o.textContent = "Sem horários";
                    select.appendChild(o);
                    select.disabled = true;
                } else {
                    const ph = document.createElement("option");
                    ph.value = "";
                    ph.textContent = "Hora";
                    select.appendChild(ph);

                    let primeiraValida = null;

                    for (const o of opcoes) {
                        const opt = document.createElement("option");
                        opt.value = o.value;
                        opt.textContent = o.label;
                        if (o.disabled) {
                            opt.disabled = true;
                            opt.classList.add("slot-passado");
                        } else if (!primeiraValida) {
                            primeiraValida = o.value;
                        }
                        select.appendChild(opt);
                    }

                    if (
                        state.escolhas[dataKey] &&
                        !opcoes.some((o) => !o.disabled && o.value === state.escolhas[dataKey])
                    ) {
                        delete state.escolhas[dataKey];
                    }

                    if (!state.escolhas[dataKey] && primeiraValida) state.escolhas[dataKey] = primeiraValida;

                    if (state.escolhas[dataKey]) select.value = state.escolhas[dataKey];

                    if (!primeiraValida) select.disabled = true;
                }

                linha.appendChild(spanData);
                linha.appendChild(select);
                els.lista.appendChild(linha);
            }
            syncHiddenAndTotal();
        }

        function syncHiddenAndTotal() {
            const valores = Object.values(state.escolhas).filter(Boolean);
            els.hidden.value = JSON.stringify(valores);

            const qtd = valores.length;
            const total = CFG.VALOR * qtd;

            if (CFG.VALOR > 0 && qtd > 0) {
                const breakdown = `${brl(CFG.VALOR)} × ${qtd}`;
                const sum = `= ${brl(total)}`;
                els.totalValor.innerHTML = `<span class="breakdown">${breakdown}</span> <span class="sum">${sum}</span>`;
            } else {
                els.totalValor.textContent = brl(total);
            }
            els.btnConfirmar.disabled = (qtd === 0);
        }

        function onSelectChange(ev) {
            const t = ev.target;
            if (!(t instanceof HTMLSelectElement)) return;
            if (!t.matches("#lista-slots select.form-select")) return;

            const key = t.dataset.key;
            if (!key) return;

            if (t.value) state.escolhas[key] = t.value;
            else delete state.escolhas[key];

            syncHiddenAndTotal();
        }

        function setStickyTop() {
            const top = ((window.cabecalhoEspaco && window.cabecalhoEspaco.offsetHeight) ? window.cabecalhoEspaco.offsetHeight : 0) + 30;
            document.getElementById("agendamentoConsulta").style.top = `${top}px`;
        }

        return {renderLista, onSelectChange, setStickyTop};
    })();

    function initCalendar() {
        const now = new Date();
        const minY = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        const ptOneLetter = Object.assign({}, flatpickr.l10ns.pt, {
            weekdays: {
                shorthand: ["D", "S", "T", "Q", "Q", "S", "S"],
                longhand: ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
            }
        });

        flatpickr("#calendario", {
            locale: ptOneLetter,
            inline: true,
            mode: "multiple",
            dateFormat: "Y-m-d",
            monthSelectorType: "static",
            minDate: minY,
            onChange: (selectedDates) => BookingUI.renderLista(selectedDates),
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        initCalendar();
        document.getElementById("lista-slots").addEventListener("change", BookingUI.onSelectChange);
        BookingUI.setStickyTop();
        window.addEventListener("resize", BookingUI.setStickyTop);
    });
})();
