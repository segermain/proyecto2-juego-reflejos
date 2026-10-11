"""Desde OSS CAD Suite: python3 build_game.py [--program]"""
import argparse
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--program', action='store_true')
args = parser.parse_args()

def run(command):
    print('\n>>> ' + ' '.join(command), flush=True)
    subprocess.run(command, cwd=root, check=True)

try:
    run([sys.executable, 'assembler.py', 'sw/game.s', 'sw/game.hex'])
    words = (root / 'sw/game.hex').read_text().splitlines()
    if len(words) > 512:
        raise ValueError('El programa excede la RAM de 512 palabras')
    sources = sorted(p.relative_to(root).as_posix() for p in (root / 'rtl').rglob('*.v'))
    run(['yosys', '-p', 'read_verilog ' + ' '.join(sources) + '; synth_ice40 -top game_top -json game_top.json; stat'])
    run(['nextpnr-ice40', '--hx1k', '--package', 'vq100', '--freq', '25', '--json', 'game_top.json', '--pcf', 'goboard.pcf', '--asc', 'game_top.asc'])
    run(['icepack', 'game_top.asc', 'game_top.bin'])
    if args.program:
        run(['iceprog', 'game_top.bin'])
    print('\nOK: construccion terminada' + (' y placa programada.' if args.program else '.'))
except (OSError, subprocess.CalledProcessError, ValueError) as exc:
    print('\nERROR: ' + str(exc), file=sys.stderr)
    sys.exit(1)
