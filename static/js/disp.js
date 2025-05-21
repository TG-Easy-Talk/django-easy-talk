document.querySelectorAll('[draggable="false"]').forEach((item) => {
    item.classList.add('prevent-select')

    // Prevenir que elementos sejam arrastados quando o usuário estiver arrastando o mouse na grade
    item.addEventListener('dragstart', (e) => {
        e.preventDefault()
    })
})

const classesNaoSelecionado = ["bg-body-secondary"]
const classesSelecionado = ["bg-secondary"]
const celulasGrade = document.querySelectorAll('[data-grade]')

function transformarJsonEmMatriz(json) {
    const matriz = []

    for (let i = 0; i < 7; i++) {
        matriz[i] = []
        for (let j = 0; j < 24; j++) {
            if (!matriz[i][j])
                matriz[i][j] = false
        }
    }

    disponibilidade = json

    disponibilidade.forEach((disp) => {
        const i = Number(disp.dia_semana - 1)
        const intervalos = disp.intervalos

        intervalos.forEach((intervalo) => {
            inicio = Number(intervalo.horario_inicio.split(':')[0])
            fim = Number(intervalo.horario_fim.split(':')[0])

            for (let j = inicio; j < fim; j++) {
                matriz[i][j] = true
            }
        })
    })

    return matriz
}

function transformarMatrizEmJson() {
    const disponibilidade = []

    for (let i = 0; i < 7; i++) {
        const intervalos = []
        let intervaloAtual = null

        for (let j = 0; j < 24; j++) {

            if (matriz[i][j]) {
                if (!intervaloAtual)
                    intervaloAtual = {
                        horario_inicio: `${j.toString().padStart(2, '0')}:00`,
                        horario_fim: `${(j + 1).toString().padStart(2, '0')}:00`
                    }
                else
                    intervaloAtual.horario_fim = `${(j + 1).toString().padStart(2, '0')}:00`
            }
            else {
                if (intervaloAtual) {
                    intervalos.push(intervaloAtual)
                    intervaloAtual = null
                }
            }
        }

        if (intervaloAtual)
            intervalos.push(intervaloAtual)
            intervaloAtual = null

        console.log(intervalos)

        if (intervalos.length > 0)
            disponibilidade.push({ dia_semana: i + 1, intervalos: intervalos })
    }

    return JSON.stringify(disponibilidade)
}

function atualizarItemPelaMatriz(item) {
    const linha = Number(item.dataset.linha)
    const coluna = Number(item.dataset.coluna)

    if (matriz[linha][coluna])
        selecionar(item)
    else
        tirar(item)
}

function atualizarMatrizPeloItem(item) {
    const linha = Number(item.dataset.linha)
    const coluna = Number(item.dataset.coluna)
    matriz[linha][coluna] = item.dataset.selecionado === "true" ? true : false
}

function selecionar(item) {
    item.dataset.selecionado = "true"
    classesNaoSelecionado.forEach(classe => item.classList.remove(classe))
    classesSelecionado.forEach(classe => item.classList.add(classe))
}

function tirar(item) {
    item.dataset.selecionado = "false"
    classesSelecionado.forEach(classe => item.classList.remove(classe))
    classesNaoSelecionado.forEach(classe => item.classList.add(classe))
}

function selecionarOuTirar(item) {
    if (item.dataset.selecionado === "false")
        selecionar(item)
    else
        tirar(item)

    atualizarMatrizPeloItem(item)
    disponibilidadeInput.value = transformarMatrizEmJson()
}

function limparGrade() {
    celulasGrade.forEach((item) => tirar(item))
}