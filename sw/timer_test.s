# Prueba del contador: cuatro LEDs encendidos 3 s y apagados 3 s.
# Go Board: reloj de 25 MHz. 3 s = 75 000 000 ciclos.
# Requiere contador de 32 bits en 0x8000000C.
.section .text
.global _start
_start:
    lui  x2, 0x80000
    lui  x3, 18311
    addi x3, x3, -1856    # 18311*4096 - 1856 = 75000000
    addi x1, x0, 15
loop:
    sw   x1, 4(x2)       # Actualizar los cuatro LEDs
    lw   x4, 12(x2)      # Lectura inicial del contador
wait:
    lw   x5, 12(x2)
    sub  x6, x5, x4      # Diferencia modulo 2^32
    bltu x6, x3, wait    # Esperar al menos 75 millones de ciclos
    xori x1, x1, 15
    jal  x0, loop
