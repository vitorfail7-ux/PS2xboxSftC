#!/usr/bin/env python3
"""Rebuild the initial SCUS diagnostic from disc files and existing host tools.

Requires Celosia tools at df6b12b69e8c8c1d0012f5ac5b834ddb818bb2c2.
This generates the boot executable only; loaded XFF modules require additional
capture/recompilation steps. Keep the output outside the source repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from prepare_boot_config import EXPECTED_SHA256, prepare


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def rebuild(disc, analyzer, recompiler, celosia, output):
    disc, analyzer, recompiler, celosia, output = (
        p.resolve() for p in (disc, analyzer, recompiler, celosia, output))
    repo = Path(__file__).resolve().parent.parent
    if output.is_relative_to(repo):
        raise ValueError('diagnostic output must be outside the source repository')
    elf = disc / 'SCUS_974.72'
    if digest(elf) != EXPECTED_SHA256:
        raise ValueError('unsupported SCUS_974.72 SHA-256')
    inputs = [elf, disc / 'KERNEL.XFF', disc / 'MANAGER.XFF',
              disc / 'GAMECORE.XFF', disc / 'IOPRP300.IMG', disc / 'NICO.DAT']
    for path in [*inputs, analyzer, recompiler, celosia / 'funcmap_elf.py',
                 celosia / 'elfmini.py']:
        if not path.is_file():
            raise ValueError(f'missing input: {path}')
    # Refuse to mix outputs from different guest builds or previous attempts.
    output.mkdir(parents=True, exist_ok=False)
    script_dir = Path(__file__).resolve().parent

    def run(name, command, stdout=None):
        with (output / f'{name}.log').open('w', encoding='utf-8') as log:
            subprocess.run([str(p) for p in command], check=True,
                           stdout=stdout if stdout is not None else log,
                           stderr=log)

    with (output / 'symbols.txt').open('w', encoding='utf-8') as symbols:
        run('symbols', [sys.executable, script_dir / 'extract_boot_symbols.py',
                        disc / 'KERNEL.XFF'], stdout=symbols)
    run('map', [sys.executable, celosia / 'funcmap_elf.py', elf,
                output / 'symbols.txt', output / 'functions.csv'])
    run('analyzer', [analyzer, elf, output / 'analyzer.toml'])
    text = prepare((output / 'analyzer.toml').read_text(encoding='utf-8'),
                   elf, output / 'functions.csv', output / 'generated')
    (output / 'boot.toml').write_text(text, encoding='utf-8')
    run('recompiler', [recompiler, output / 'boot.toml'])
    # Record the exact inputs, tool binaries and function-map sources used.
    manifest_files = [*inputs, analyzer, recompiler, *celosia.glob('*.py'),
                      *script_dir.glob('*.py'), output / 'boot.toml',
                      output / 'functions.csv']
    manifest = {'stage': 'initial-boot-only', 'python': sys.version,
                'sha256': {str(p): digest(p) for p in sorted(manifest_files)}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return output / 'boot.toml'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('disc', 'analyzer', 'recompiler', 'celosia-tools', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        config = rebuild(args.disc, args.analyzer, args.recompiler,
                         args.celosia_tools, args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f'Initial boot generated: {config}')
    print('Loaded XFF modules and Xbox execution remain to be validated.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
