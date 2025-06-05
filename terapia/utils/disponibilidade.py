def get_matriz_disponibilidade_em_javascript(disponibilidade):
    """
    Cria uma matriz de booleanos que representa a disponibilidade.
    A ideia é que a matriz seja interpretável nos templates, então
    ela é retornada como uma string que pode ser decodificada pelo
    JavaScript no template.
    """
    matriz = [[False] * 24 for _ in range(7)]

    if disponibilidade.exists():
        for intervalo in disponibilidade.all():
            print(intervalo)
            dia_semana_inicio = intervalo.dia_semana_inicio_local % 7 # Ajusta para 0 = Domingo, 6 = Sábado
            dia_semana_fim = intervalo.dia_semana_fim_local % 7 # Ajusta para 0 = Domingo, 6 = Sábado
            hora_inicio = intervalo.hora_inicio_local.hour
            hora_fim = intervalo.hora_fim_local.hour

            ranges = []

            if dia_semana_inicio == dia_semana_fim:
                ranges = [range(hora_inicio, hora_fim)]
            else:
                ranges.append(range(hora_inicio, 24))
                i = dia_semana_inicio + 1

                while i <= dia_semana_fim:
                    if i != dia_semana_fim:
                        ranges.append(range(0, 24))
                    else:
                        ranges.append(range(0, hora_fim))
                    i += 1

            for i, _range in enumerate(ranges):
                for hora in _range:
                    matriz[dia_semana_inicio + i][hora] = True

    # Transformar em str.lower() para o JSON.parse() do JS poder entender
    matriz_em_javascript = str(matriz).lower()
    return matriz_em_javascript