(function () {
    const input = document.querySelector('input[name="cpf"]')
    if (!input) return

    input.setAttribute('inputmode', 'numeric')
    input.setAttribute('maxlength', '14')
    input.setAttribute('placeholder', '000.000.000-00')

    function formatCPF(raw) {
        const v = (raw || '').replace(/\D/g, '').slice(0, 11)
        const p1 = v.slice(0, 3)
        const p2 = v.slice(3, 6)
        const p3 = v.slice(6, 9)
        const p4 = v.slice(9, 11)
        let out = p1
        if (p2) out += (out ? '.' : '') + p2
        if (p3) out += '.' + p3
        if (p4) out += '-' + p4
        return out
    }

    function onInput(e) {
        e.target.value = formatCPF(e.target.value)
    }

    input.addEventListener('input', onInput)
    input.addEventListener('blur', onInput)
    input.value = formatCPF(input.value)

    const form = input.form
    if (form) {
        form.addEventListener('submit', function () {
            input.value = input.value.replace(/\D/g, '').slice(0, 11)
        });
    }
})();

(function () {
    const input = document.querySelector('input[name="crp"]')
    if (!input) return

    input.setAttribute('inputmode', 'text')
    input.setAttribute('maxlength', '12')
    input.setAttribute('placeholder', '06/124424 ou 14/05473-7')
    input.setAttribute('autocomplete', 'off')

    const sanitize = raw =>
        String(raw || '')
            .toUpperCase()
            .replace(/\s+/g, '')
            .replace(/^CRP:?/, '')
            .replace(/[^0-9A-Z/-]/g, '')

    function formatCRP(raw) {
        let s = sanitize(raw)

        if (/^\d{2}(?!\/)/.test(s)) {
            s = s.replace(/^(\d{2})(?!\/)/, '$1/')
        }

        const slashIdx = s.indexOf('/')
        if (slashIdx === -1) {
            return s.replace(/\D/g, '').slice(0, 2)
        }

        const rr = s.slice(0, slashIdx).replace(/\D/g, '').slice(0, 2)
        let tail = s.slice(slashIdx + 1).replace(/\//g, '')

        const lettersMatch = tail.match(/^[A-Z]{1,2}/)
        if (lettersMatch) {
            const letters = lettersMatch[0]
            let digits = tail.slice(letters.length).replace(/\D/g, '')
            digits = digits.slice(0, 6)
            return `${rr}${rr ? '/' : ''}${letters}${digits}`
        }


        tail = tail.replace(/[^0-9-]/g, '').replace(/-+/g, '-')

        if (tail.includes('-')) {
            const onlyDigits = tail.replace(/-/g, '').replace(/\D/g, '')
            const pre = onlyDigits.slice(0, 5)
            const dv = onlyDigits.slice(5, 6)
            const seq = pre + (tail.indexOf('-') !== -1 ? (dv ? '-' + dv : '-') : '')
            return `${rr}${rr ? '/' : ''}${seq}`
        } else {
            const seq = tail.replace(/\D/g, '').slice(0, 7)
            return `${rr}${rr ? '/' : ''}${seq}`
        }
    }

    input.value = formatCRP(input.value || '')

    input.addEventListener('input', e => {
        e.target.value = formatCRP(e.target.value)
    })

    input.addEventListener('blur', e => {
        e.target.value = formatCRP(e.target.value)
    })
})()
