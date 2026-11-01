#!/usr/bin/env python3
"""Rebuild captured XFF stages with Celosia tools at df6b12b69e8c8c1d0012f5ac5b834ddb818bb2c2.

Capture each stage when the original loader reaches its missing entry point.
Generated code and RAM dumps must stay outside the source repository.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

from prepare_boot_config import EXPECTED_SHA256
from rebuild_boot import digest


def configure(base, output):
    text = base.read_text(encoding='utf-8')
    general = tomllib.loads(text)['general']
    for key, value in (('input', output / 'SOTC.elf'),
                       ('ghidra_output', output / 'functions.csv'),
                       ('output', str(output / 'generated') + '/')):
        text, count = re.subn(r'(?m)^' + key + r' = .*$',
                             lambda _: key + ' = ' + json.dumps(str(value)), text)
        if count != 1:
            raise ValueError(f'expected one {key} setting in initial boot config')
    entries = set(general['entry_points'])
    for line in (output / 'merged_entries.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            entries.add(f'entry_{int(line, 16):08X}@0x{int(line, 16):08X}')
    text, count = re.subn(r'(?ms)^entry_points = \[.*?^\]',
                         lambda _: 'entry_points = [\n' + ''.join(
                             '  ' + json.dumps(entry) + ',\n' for entry in sorted(entries)) + ']', text)
    if count != 1 or 'live_immediate_addresses' in general:
        raise ValueError('use the initial boot config without previous XFF stages')
    live = [int(line, 16) for line in (output / 'dynamic_imm.txt').read_text().splitlines()
            if line and not line.startswith('#')]
    text = text.replace('[general]', '[general]\nlive_immediate_addresses = [' +
                        ','.join(hex(address) for address in live) + ']', 1)
    tomllib.loads(text)
    (output / 'config.toml').write_text(text, encoding='utf-8')


def rebuild(disc, boot, recompiler, celosia, output, captures):
    disc, boot, recompiler, celosia, output = (
        path.resolve() for path in (disc, boot, recompiler, celosia, output))
    repo = Path(__file__).resolve().parent.parent
    if output.is_relative_to(repo):
        raise ValueError('diagnostic output must be outside the source repository')
    if digest(disc / 'SCUS_974.72') != EXPECTED_SHA256:
        raise ValueError('unsupported SCUS_974.72 SHA-256')
    modules = [(disc / (name + '.XFF'), capture.resolve()) for name, capture in captures]
    inputs = [disc / 'SCUS_974.72', boot / 'symbols.txt', boot / 'boot.toml',
              recompiler, celosia / 'build_elf.py']
    inputs += [path for pair in modules for path in pair]
    for path in inputs:
        if not path.is_file() or '@' in str(path):
            raise ValueError(f'missing input or unsupported @ in path: {path}')
    for _, capture in modules:
        if capture.stat().st_size != 32 * 1024 * 1024:
            raise ValueError(f'expected a complete 32 MiB EE RAM capture: {capture}')
    output.mkdir(parents=True, exist_ok=False)

    def run(name, command):
        with (output / (name + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run([str(value) for value in command], check=True, stdout=log, stderr=log)

    run('combine', [sys.executable, celosia / 'build_elf.py', output,
                    disc / 'SCUS_974.72', boot / 'symbols.txt',
                    *(f'{module}@auto@{capture}' for module, capture in modules)])
    configure(boot / 'boot.toml', output)
    run('recompiler', [recompiler, output / 'config.toml'])
    inputs += [*celosia.glob('*.py'), Path(__file__).resolve(),
               output / 'config.toml', output / 'functions.csv']
    manifest = {'stage': [module.stem for module, _ in modules], 'python': sys.version,
                'sha256': {str(path): digest(path) for path in sorted(set(inputs))}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('disc', 'boot', 'recompiler', 'celosia-tools', 'output', 'kernel-ram'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--manager-ram', type=Path)
    parser.add_argument('--gamecore-ram', type=Path)
    args = parser.parse_args()
    if args.gamecore_ram and not args.manager_ram:
        parser.error('--gamecore-ram also requires --manager-ram')
    captures = [('KERNEL', args.kernel_ram)]
    captures += [(name, capture) for name, capture in
                 (('MANAGER', args.manager_ram), ('GAMECORE', args.gamecore_ram)) if capture]
    try:
        rebuild(args.disc, args.boot, args.recompiler, args.celosia_tools, args.output, captures)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f'Generated stages: {args.output / "config.toml"}')
    print('Compile generated/ into the runner, then run the original disc SCUS_974.72.')
    print('This does not validate gameplay or Xbox execution.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
