# Juego de reflejos sobre Pochoco SoC

Proyecto 2 - Arquitectura de Computadores, Universidad de los Andes, 2026-2.
Integrantes: Sebastián Germain, Valentina Pizarro y Florencia Osandón.

## Equipo y herramientas
Go Board con FPGA Lattice iCE40 HX1K, reloj de 25 MHz, cuatro botones, cuatro LED y dos displays. En Windows 11 se usa la terminal abierta mediante `start.bat` de OSS CAD Suite. Deben estar disponibles Python 3, Yosys, nextpnr-ice40, icepack e iceprog. Para programar, la interfaz USB A/0 debe tener el controlador compatible que ya se configuró en el computador de prueba.

## Compilar y programar
Desde la terminal de OSS CAD Suite, entrar a la carpeta que contiene `build_game.py`:

```bat
cd /d C:\pochoco_soc-main\pochoco_soc-main
python3 build_game.py --program
```

El script regenera el HEX, sintetiza `game_top`, ubica y conecta el circuito para HX1K/vq100 con objetivo de 25 MHz, genera el BIN y programa la memoria flash. Se detiene si una herramienta informa error. Confirmar `VERIFY OK` al finalizar.

Solo generar el programa:

```bat
python3 assembler.py sw/game.s sw/game.hex
```

Solo compilar el circuito, sin programar:

```bat
python3 build_game.py
```

No usar el `sw/Makefile` heredado para esta entrega: utiliza herramientas RISC-V externas. El juego se ensambla con `assembler.py`, escrito en Python y sin invocar un ensamblador externo.

## Uso
1. Al encender se muestra 00. Presionar y soltar cualquier botón.
2. Antes de cada ronda se encienden los cuatro LED durante al menos tres segundos.
3. Cuando queda uno encendido, presionar su botón: D1/SW1, D2/SW2, D3/SW3 o D4/SW4.
4. Una respuesta correcta muestra su tiempo por unos dos segundos. El número está en décimas: 14 equivale a 1,4 s; no es el número de ronda.
5. Un botón incorrecto, varios botones simultáneos o diez segundos sin respuesta producen EE. Se repite la ronda sin incrementar el contador de aciertos ni sumar el tiempo.
6. Tras diez aciertos se muestra el promedio y quedan los cuatro LED encendidos. Para otra partida, presionar y soltar una vez para volver a 00 y otra vez para comenzar.

## Archivos principales
- `rtl/game_top.v`: conecta los pines e instancia el SoC con `sw/game.hex`.
- `rtl/pochoco_soc.v`: integra CPU, memoria y periféricos; reset inicial con contador de 16 bits.
- `rtl/pochoco_periph.v`: LED, displays, sincronización de botones, contador de ciclos y captura del inicio.
- `sw/game.s`: juego final; `sw/game.hex`: imagen de 32 bits por línea.
- `assembler.py`: assembler de dos pasadas para el subconjunto utilizado.
- `docs/informe_borrador.pdf` y `.md`: documentación técnica para revisar antes de entregar.
- `docs/pruebas_assembler.txt`: verificaciones del código recibido.

Los ejemplos, el Makefile heredado y `game_respaldo.s` se conservan como antecedentes; no son la entrada de `build_game.py`.

## Cambiar una constante para la demostración
En `sw/game.s`, cambiar temporalmente `.equ RONDAS, 10` a `.equ RONDAS, 3`. Guardar y ejecutar `python3 build_game.py --program`. El promedio se calculará sobre tres respuestas. Restaurar a 10 antes de la entrega. Usar valores de 1 a 10: esta versión no valida el rango automáticamente.

Para cambiar la espera a cuatro segundos: PREP_HI = 24414, PREP_LO = 256; se obtiene 100000000 ciclos. No reducir la espera por debajo de tres segundos para la entrega.

## Validación y pendientes
Se reportaron pruebas físicas de botones, temporización, una partida de diez aciertos con promedio 14 y un error EE con repetición. Al extender el reset a 16 bits se reportaron tres arranques correctos consecutivos con la versión de diagnóstico; después se confirmó el funcionamiento con pantalla inicial 00. La causa física exacta del fallo anterior de arranque no quedó demostrada.

Antes de entregar: repetir una partida completa con esta versión final, comprobar que un error después de varios aciertos conserva el conteo, probar el límite de diez segundos y observar varias partidas para confirmar variación perceptible de LED. Registrar evidencias propias. Confirmar el enlace del repositorio.

## Publicación en GitHub
Crear un repositorio y subir el contenido de esta carpeta, dejando este README en la raíz. Incluir RTL, assembler, game.s, game.hex e informe revisado. El paquete no ha sido publicado automáticamente. Los avisos de autoría y licencia del RTL base se conservan.

## Base del proyecto
Código base: Nicolás Villegas, Pochoco SoC, https://github.com/nic0villegasc/pochoco_soc. Requisitos tomados del enunciado de Proyecto 2 suministrado en el curso. Este trabajo recibió asistencia de ChatGPT para desarrollo, diagnóstico y documentación; revisar las reglas del curso y comprender el código para la defensa oral.
