# Juego de reflejos RV32E para Go Board, reloj 25 MHz.
# x2: MMIO; x3: ciclos/decima; x4: ciclos de preparacion.
# x8: ciclos de respuesta; x9: suma de ciclos; x10: aciertos.
# x11: LED objetivo; x12: estado pseudoaleatorio; x15: retorno.
# x1,x5,x6,x7,x13,x14: temporales.
# Solo x0..x15; sin multiplicacion, division ni shifts de la ALU.
# Constantes para modificar y regenerar durante la demostracion:
.equ RONDAS, 10
.equ PREP_HI, 18311
.equ PREP_LO, -1856
# PREP_HI*4096 + PREP_LO = 75000000 (3 s).
# Mantener RONDAS entre 1 y 10 para garantizar suma de 32 bits.
.section .text
.global _start
_start:
    lui x2, 0x80000
    lui x3, 610
    addi x3, x3, 1440     # 2500000 ciclos = 0.1 s
    lui x4, PREP_HI
    addi x4, x4, PREP_LO
new_game:
    addi x9, x0, 0
    addi x10, x0, 0
    sw x0, 4(x2)
    addi x1, x0, 17
    sw x1, 0(x2)          # Mostrar 11 antes de release
    jal x15, release
    addi x1, x0, 34
    sw x1, 0(x2)          # Mostrar 22 al regresar
start_press:
    lw x1, 8(x2)
    beq x1, x0, start_press
    lw x12, 12(x2)        # Semilla depende del instante humano de inicio
    jal x15, release
round:
    addi x1, x0, 15
    sw x1, 4(x2)          # Todos encendidos, captura hardware del inicio
    lw x5, 16(x2)
prepare:
    lw x6, 12(x2)
    sub x7, x6, x5
    bltu x7, x4, prepare
    jal x15, release     # Evitar aceptar un boton ya mantenido
    # Mezcla modulo 2^32: estado = 5*estado + contador + 1.
    lw x6, 12(x2)
    add x1, x12, x12
    add x1, x1, x1
    add x12, x12, x1
    add x12, x12, x6
    addi x12, x12, 1
    # Usar 11 bits variables del contador y mezclar con resto modulo 251.
    andi x12, x12, 2047
rng_small:
    addi x1, x0, 251
    bltu x12, x1, rng_done
    sub x12, x12, x1
    jal x0, rng_small
rng_done:
    andi x1, x12, 3
    addi x11, x0, 1
choose:
    beq x1, x0, target
    add x11, x11, x11
    addi x1, x1, -1
    jal x0, choose
target:
    sw x0, 0(x2)
    sw x11, 4(x2)         # LED e inicio se registran en el MISMO flanco
    lw x5, 16(x2)
    lui x14, 61035
    addi x14, x14, 640    # Limite de respuesta: 250000000 ciclos = 10 s
poll:
    lw x1, 8(x2)
    lw x6, 12(x2)
    sub x8, x6, x5
    bgeu x8, x14, error   # Timeout: no acumula ni aumenta aciertos
    beq x1, x0, poll
    bne x1, x11, error   # Pulsacion multiple tambien es incorrecta
    add x9, x9, x8
    addi x10, x10, 1
    sw x0, 4(x2)
    # Cociente entero ciclos/2500000 para mostrar decimas.
    addi x13, x0, 0
convert_time:
    bltu x8, x3, time_ready
    sub x8, x8, x3
    addi x13, x13, 1
    jal x0, convert_time
time_ready:
    jal x15, show_decimal
    # Mostrar la respuesta dos segundos.
    lui x13, 12207
    addi x13, x13, 128    # 50000000
    jal x15, delay
    addi x1, x0, RONDAS
    beq x10, x1, average
    jal x0, round
error:
    sw x0, 4(x2)
    addi x1, x0, 238
    sw x1, 0(x2)          # EE = error / timeout
    lui x13, 6104
    addi x13, x13, -1984  # 25000000 = 1 s
    jal x15, delay
    jal x0, round        # Se conservan x9 y x10
average:
    # Divisor = RONDAS*2500000. Sumar evita MUL.
    addi x14, x0, 0
    addi x1, x0, RONDAS
average_divisor:
    add x14, x14, x3
    addi x1, x1, -1
    bne x1, x0, average_divisor
    addi x13, x0, 0
average_loop:
    bltu x9, x14, average_ready
    sub x9, x9, x14
    addi x13, x13, 1
    jal x0, average_loop
average_ready:
    jal x15, show_decimal
    addi x1, x0, 15
    sw x1, 4(x2)          # Todos fijos: promedio final
    jal x15, release
restart:
    lw x1, 8(x2)
    beq x1, x0, restart
    jal x0, new_game     # Nueva partida solicita otra pulsacion de inicio

# Mostrar 0..99 en decimal empaquetado (decenas*16 + unidades).
# Entrada x13; destruye x1,x13,x14.
show_decimal:
    addi x14, x0, 0
    addi x1, x0, 10
decimal_loop:
    bltu x13, x1, decimal_ready
    addi x13, x13, -10
    addi x14, x14, 16
    jal x0, decimal_loop
decimal_ready:
    add x13, x13, x14
    sw x13, 0(x2)
    jalr x0, 0(x15)

# Espera x13 ciclos, resta unsigned para admitir wrap del contador.
# Destruye x1,x6,x14.
delay:
    lw x14, 12(x2)
delay_loop:
    lw x1, 12(x2)
    sub x6, x1, x14
    bltu x6, x13, delay_loop
    jalr x0, 0(x15)

# Exigir 20 ms continuos sin botones antes de aceptar otra pulsacion.
# Destruye x1,x6,x7,x13,x14; no llama otras subrutinas.
release:
    lui x13, 122
    addi x13, x13, 288    # 500000 ciclos = 20 ms
release_reset:
    lw x14, 12(x2)
release_loop:
    lw x1, 8(x2)
    bne x1, x0, release_reset
    lw x6, 12(x2)
    sub x7, x6, x14
    bltu x7, x13, release_loop
    jalr x0, 0(x15)
