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

  const MIN_REGION = 1, MAX_REGION = 24, PAD_MAX = String(MAX_REGION).padStart(2, '0')
  const PARSE_RE = /^(\d{2})\/(\d{1,7})(?:-(\d))?$/

  const sanitize = raw =>
    String(raw || '')
      .toUpperCase()
      .replace(/\s+/g, '')
      .replace(/^CRP:?/, '')
      .replace(/[^0-9-]/g, '')

  function formatCRP(raw) {
    const s = sanitize(raw)
    const m = s.match(/-(\d)$/)
    const dv = m ? m[1] : ''
    const core = dv ? s.slice(0, -2) : s
    const digits = core.replace(/\D/g, '').slice(0, 9)
    const rr = digits.slice(0, 2), seq = digits.slice(2)
    return (rr ? rr + '/' : '') + seq + (dv && seq ? '-' + dv : '')
  }

  const isCompleteAndValid = v => {
    const m = PARSE_RE.exec(v || '')
    if (!m) return false
    const rr = +m[1], seq = m[2]
    return rr >= MIN_REGION && rr <= MAX_REGION && /[1-9]/.test(seq)
  }

  const regionMessage = v => {
    const m = /^(\d{2})\//.exec(v || '')
    if (!m) return ''
    const n = +m[1]
    return n >= MIN_REGION && n <= MAX_REGION ? '' : `Código regional inválido (use 01 a ${PAD_MAX}).`
  }

  input.value = formatCRP(input.value || '')

  input.addEventListener('input', e => {
    e.target.value = formatCRP(e.target.value)
    e.target.setCustomValidity('')
  })

  input.addEventListener('blur', e => {
    e.target.value = formatCRP(e.target.value)
    const v = e.target.value
    e.target.setCustomValidity(
      regionMessage(v) || (isCompleteAndValid(v) ? '' : (v ? 'Formato aceito: RR/NNNN..NN ou RR/NNNN..NN-D.' : ''))
    )
  })

  const form = input.form
  if (form) {
    form.addEventListener('submit', () => {
      const v = input.value
      if (isCompleteAndValid(v)) {
        const m = PARSE_RE.exec(v)
        input.value = `${m[1].padStart(2, '0')}/${m[2]}${m[3] ? '-' + m[3] : ''}`
      }
    })
  }
})()
