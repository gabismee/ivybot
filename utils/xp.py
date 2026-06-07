def nivel_por_xp(xp: int) -> tuple[int, int, int]:
    xp = int(xp or 0)
    nivel = 1
    requerido = 100
    restante = xp
    while restante >= requerido:
        restante -= requerido
        nivel += 1
        requerido = int(100 + (nivel - 1) * 75)
    return nivel, restante, requerido
