#!/usr/bin/env python3
"""Assembler educativo para el subconjunto RV32E usado por Pochoco.
Uso: python3 assembler.py entrada.s salida.hex
Dos pasadas: primero etiquetas, despues codificacion de palabras de 32 bits.
Solo x0..x15. No usa ni invoca assemblers externos.
Los desplazamientos de bits se rechazan porque la ALU base no los implementa.
"""
import argparse
import re
from pathlib import Path

R = {'add': (0, 0), 'sub': (0, 32), 'slt': (2, 0),
     'sltu': (3, 0), 'xor': (4, 0), 'or': (6, 0), 'and': (7, 0)}
I = {'addi': 0, 'slti': 2, 'sltiu': 3, 'xori': 4, 'ori': 6, 'andi': 7}
B = {'beq': 0, 'bne': 1, 'blt': 4, 'bge': 5, 'bltu': 6, 'bgeu': 7}
LOAD = {'lb': 0, 'lh': 1, 'lw': 2, 'lbu': 4, 'lhu': 5}
STORE = {'sb': 0, 'sh': 1, 'sw': 2}
NAME = r'[A-Za-z_.$][\w.$]*'


def number(text, symbols):
    if text in symbols:
        return symbols[text]
    try:
        return int(text, 0)
    except ValueError:
        raise ValueError('Numero o simbolo desconocido: ' + text) from None


def reg(text):
    if not re.fullmatch(r'x(?:[0-9]|1[0-5])', text):
        raise ValueError('Registro invalido: ' + text + ' (usar x0..x15)')
    return int(text[1:])


def signed(value, bits):
    if not -(1 << (bits - 1)) <= value < (1 << (bits - 1)):
        raise ValueError(f'Inmediato {value} fuera del rango de {bits} bits con signo')
    return value & ((1 << bits) - 1)


def memory(text, symbols):
    match = re.fullmatch(r'([^()]+)\(\s*(x\d+)\s*\)', text)
    if not match:
        raise ValueError('Usar offset(xN): ' + text)
    return signed(number(match[1].strip(), symbols), 12), reg(match[2])


def encode(op, args, pc, symbols, labels):
    def count(n):
        if len(args) != n or any(not a for a in args):
            raise ValueError(f'{op} requiere {n} operandos')

    def offset(text, bits):
        # Una etiqueta es una direccion; un numero/constante es un offset en bytes.
        value = number(text, symbols) - (pc if text in labels else 0)
        if value % 4:
            raise ValueError('El destino debe estar alineado a 4 bytes')
        return signed(value, bits)

    if op == 'nop':
        count(0)
        return 0x13
    if op == 'j':
        count(1)
        return encode('jal', ['x0', args[0]], pc, symbols, labels)
    if op == 'mv':
        count(2)
        return encode('addi', [args[0], args[1], '0'], pc, symbols, labels)
    if op in R:
        count(3)
        rd, rs1, rs2 = map(reg, args)
        f3, f7 = R[op]
        return f7 << 25 | rs2 << 20 | rs1 << 15 | f3 << 12 | rd << 7 | 0x33
    if op in I:
        count(3)
        imm = signed(number(args[2], symbols), 12)
        return imm << 20 | reg(args[1]) << 15 | I[op] << 12 | reg(args[0]) << 7 | 0x13
    if op in ('lui', 'auipc'):
        count(2)
        imm = number(args[1], symbols)
        if not 0 <= imm <= 0xfffff:
            raise ValueError('LUI/AUIPC requiere campo de 20 bits: 0..0xfffff')
        return imm << 12 | reg(args[0]) << 7 | (0x37 if op == 'lui' else 0x17)
    if op in LOAD or op == 'jalr':
        count(2)
        imm, rs1 = memory(args[1], symbols)
        f3, opcode = (0, 0x67) if op == 'jalr' else (LOAD[op], 0x03)
        return imm << 20 | rs1 << 15 | f3 << 12 | reg(args[0]) << 7 | opcode
    if op in STORE:
        count(2)
        imm, rs1 = memory(args[1], symbols)
        return (imm >> 5) << 25 | reg(args[0]) << 20 | rs1 << 15 | STORE[op] << 12 | (imm & 31) << 7 | 0x23
    if op in B:
        count(3)
        imm = offset(args[2], 13)
        return ((imm >> 12) & 1) << 31 | ((imm >> 5) & 63) << 25 | reg(args[1]) << 20 | reg(args[0]) << 15 | B[op] << 12 | ((imm >> 1) & 15) << 8 | ((imm >> 11) & 1) << 7 | 0x63
    if op == 'jal':
        count(2)
        imm = offset(args[1], 21)
        return ((imm >> 20) & 1) << 31 | ((imm >> 1) & 1023) << 21 | ((imm >> 11) & 1) << 20 | ((imm >> 12) & 255) << 12 | reg(args[0]) << 7 | 0x6f
    raise ValueError('Instruccion no soportada: ' + op)


def assemble(source):
    symbols, labels, lines = {}, set(), []
    pc = 0
    # Primera pasada: cada instruccion admitida ocupa exactamente 4 bytes.
    for line_no, raw in enumerate(source.splitlines(), 1):
        try:
            text = re.split(r'#|//|;', raw, maxsplit=1)[0].strip()
            while text:
                match = re.match('(' + NAME + r')\s*:', text)
                if not match:
                    break
                name = match[1]
                if name in symbols:
                    raise ValueError('Simbolo duplicado: ' + name)
                symbols[name] = pc
                labels.add(name)
                text = text[match.end():].strip()
            if not text:
                continue
            parts = text.split(None, 1)
            op = parts[0].lower()
            tail = parts[1].strip() if len(parts) == 2 else ''
            if op == '.text' and not tail:
                continue
            if op == '.section' and tail == '.text':
                continue
            if op in ('.global', '.globl') and re.fullmatch(NAME, tail):
                continue
            args = [a.strip() for a in tail.split(',')] if tail else []
            if op == '.equ':
                if len(args) != 2 or not re.fullmatch(NAME, args[0]):
                    raise ValueError('Usar .equ NOMBRE, numero')
                if args[0] in symbols:
                    raise ValueError('Simbolo duplicado: ' + args[0])
                # Constantes numericas o referencias a constantes anteriores.
                if args[1] in labels:
                    raise ValueError('.equ no acepta etiquetas de codigo')
                symbols[args[0]] = number(args[1], symbols)
                continue
            lines.append((line_no, pc, op, args))
            pc += 4
        except ValueError as exc:
            raise ValueError(f'Linea {line_no}: {exc}') from None
    words = []
    # Segunda pasada: etiquetas ya conocidas, incluidos saltos hacia adelante.
    for line_no, pc, op, args in lines:
        try:
            words.append(encode(op, args, pc, symbols, labels))
        except ValueError as exc:
            raise ValueError(f'Linea {line_no}: {exc}') from None
    if not words:
        raise ValueError('El archivo no contiene instrucciones')
    return words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entrada', type=Path)
    parser.add_argument('salida', type=Path)
    args = parser.parse_args()
    try:
        if args.entrada.resolve() == args.salida.resolve():
            raise ValueError('Entrada y salida deben ser archivos distintos')
        words = assemble(args.entrada.read_text(encoding='utf-8-sig'))
        args.salida.write_text(''.join(f'{w:08x}\n' for w in words), encoding='ascii')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')
    print(f'OK: {len(words)} instrucciones ({4 * len(words)} bytes) -> {args.salida}')


if __name__ == '__main__':
    main()
