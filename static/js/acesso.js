(function () {
    const input = document.querySelector('input[name="cpf"]');
    if (!input) return;

    input.setAttribute('inputmode', 'numeric');
    input.setAttribute('maxlength', '14');
    input.setAttribute('placeholder', '000.000.000-00');

    function formatCPF(raw) {
        const v = (raw || '').replace(/\D/g, '').slice(0, 11);
        const p1 = v.slice(0, 3), p2 = v.slice(3, 6), p3 = v.slice(6, 9), p4 = v.slice(9, 11);
        let out = p1;
        if (p2) out += (out ? '.' : '') + p2;
        if (p3) out += '.' + p3;
        if (p4) out += '-' + p4;
        return out;
    }

    function onInput(e) {
        e.target.value = formatCPF(e.target.value);
    }

    input.addEventListener('input', onInput);
    input.addEventListener('blur', onInput);
    input.value = formatCPF(input.value);

    const form = input.form;
    if (form) {
        form.addEventListener('submit', function () {
            input.value = input.value.replace(/\D/g, '').slice(0, 11);
        });
    }
})();
