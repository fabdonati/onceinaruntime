"""Follow selected replay paths in the retained GCC 16.2 AArch64 object.

The recorded branch choices assume an unchanged cash or long position and a
bar before the last one. Event-first paths also assume another strategy follows.
The object hash ties those choices to the instruction addresses reviewed here.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

OBJECT_SHA256 = '7b875f7c0a55018d323e4f9f75dc63fbd380fd5ffcfab92bbc54ee041ab4b9eb'
STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]

# Each iteration returns to its starting PC, including a taken loop back edge.
# For history/cash GCC has a distinct steady-state loop after the initial update.
PATHS = [
    dict(order='strategy', layout='history', position='cash', start=0xc6c,
         branches={0xc80: False, 0xc68: False},
         bases={'x8':'features', 'x6':'features', 'x5':'bars', 'x0':'state', 'x12':'rules', 'x2':'configs'}),
    dict(order='strategy', layout='history', position='long', start=0xc00,
         branches={0xc14: True, 0xff4: False, 0xffc: False},
         bases={'x8':'features', 'x6':'features', 'x5':'bars', 'x0':'state', 'x12':'rules', 'x2':'configs'}),
    dict(order='strategy', layout='snapshot', position='cash', start=0x14a0,
         branches={0x14b4: False, 0x14bc: True, 0x150c: True},
         bases={'x3':'features', 'x5':'bars', 'x0':'state', 'x12':'rules', 'x2':'configs'}),
    dict(order='strategy', layout='snapshot', position='long', start=0x14a0,
         branches={0x14b4: True, 0x1538: True, 0x159c: False, 0x150c: True},
         bases={'x3':'features', 'x5':'bars', 'x0':'state', 'x12':'rules', 'x2':'configs'}),
    dict(order='event', layout='history', position='cash', start=0xf10,
         branches={0xf34: False, 0xf3c: False, 0xf0c: False},
         bases={'x4':'features', 'x10':'bars', 'x3':'state', 'x12':'rules', 'x8':'configs'}),
    dict(order='event', layout='history', position='long', start=0xf10,
         branches={0xf34: True, 0x1088: True, 0xf0c: False},
         bases={'x4':'features', 'x10':'bars', 'x3':'state', 'x12':'rules', 'x8':'configs'}),
    dict(order='event', layout='snapshot', position='cash', start=0xe24,
         branches={0xe48: False, 0xe50: False, 0xe20: False},
         bases={'x4':'features', 'x14':'bars', 'x3':'state', 'x12':'rules', 'x9':'configs'}),
    dict(order='event', layout='snapshot', position='long', start=0xe24,
         branches={0xe48: True, 0x10d4: True, 0xe20: False},
         bases={'x4':'features', 'x14':'bars', 'x3':'state', 'x12':'rules', 'x9':'configs'}),
]


def decode(text):
    active = False
    result = {}
    for line in text.splitlines():
        header = re.match(r'^[0-9a-f]+ <(.+)>:$', line)
        if header:
            active = header[1].startswith('strategy::replay(')
        match = re.match(r'^\s+([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)$', line)
        if active and match:
            pc = int(match[1], 16)
            if pc in result:
                raise ValueError('duplicate instruction address')
            result[pc] = dict(pc=hex(pc), encoding=match[2], opcode=match[3],
                              operands=match[4].split(' <')[0])
    if not result:
        raise ValueError('non-diagnostic replay not decoded')
    return result


def walk(instructions, start, branches):
    pc = start
    path, used = [], set()
    for _ in range(512):
        insn = instructions[pc]
        path.append(insn)
        op, operands = insn['opcode'], insn['operands']
        if op == 'b' or op.startswith('b.'):
            target = int(operands.split(',')[-1].strip(), 16)
            if op == 'b': pc = target
            else:
                used.add(pc)
                pc = target if branches[pc] else pc+4
        elif op in ('ret', 'bl', 'blr', 'br', 'cbz', 'cbnz', 'tbz', 'tbnz'):
            raise ValueError('unsupported control flow in selected steady path')
        else: pc += 4
        if pc == start:
            if used != set(branches):
                raise ValueError('unused or missing branch decisions')
            return path
    raise ValueError('path did not close within 512 instructions')


def memory_operand(insn, bases):
    op, operands = insn['opcode'], insn['operands']
    if '[' not in operands:
        return None
    if op not in ('ldr','ldp','ldur','str','stp','stur'):
        raise ValueError('unhandled memory instruction')
    base = re.search(r'\[(x\d+|sp)', operands)[1]
    registers = operands.split('[')[0].rstrip(', ').split(', ')
    widths = {'x':8, 'w':4, 'd':8, 's':4, 'q':16}
    width = sum(widths[r[0]] for r in registers)
    return dict(pc=insn['pc'], category=bases[base],
                direction='read' if op.startswith('ld') else 'write',
                bytes=width, instruction=op+' '+operands)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    default_object = (ROOT / 'build/release' / STUDY.relative_to(ROOT)
                      / 'CMakeFiles/strategy_core.dir/src/replay.cpp.o')
    p.add_argument('--object', type=Path, default=default_object)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    fingerprint = hashlib.sha256(args.object.read_bytes()).hexdigest()
    if fingerprint != OBJECT_SHA256:
        raise ValueError('object changed; review paths before updating the pinned hash')
    args.output.mkdir(parents=True, exist_ok=False)
    command = ['xcrun','llvm-objdump','--disassemble','--reloc','--demangle',str(args.object.resolve())]
    r = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
    (args.output/'disassembly.txt').write_text(r.stdout)
    instructions = decode(r.stdout)
    report = dict(kind='static path analysis; not timing or hardware counters',
                  command=sys.argv, object_sha256=fingerprint,
                  analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  disassembly_command=command, replay_static_instruction_count=len(instructions), paths=[])
    for spec in PATHS:
        path = walk(instructions, spec['start'], spec['branches'])
        memory = [m for i in path if (m := memory_operand(i,spec['bases'])) is not None]
        counts = Counter(i['opcode'] for i in path)
        totals = {k: {d:sum(m['bytes'] for m in memory if m['category']==k and m['direction']==d)
                       for d in ('read','write')} for k in ('state','features','bars','configs','rules')}
        report['paths'].append(dict(order=spec['order'], layout=spec['layout'], position=spec['position'],
            start=hex(spec['start']), branch_choices={hex(k):v for k,v in spec['branches'].items()},
            instructions=len(path), mnemonic_counts=dict(counts), memory_operand_bytes=totals,
            memory=memory, path=path))
    (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Reviewed steady paths', '',
           'Nonfinal bar; unchanged position; event-first excludes the last strategy.',
           'Static path counts and load/store operand bytes, not cycles or DRAM traffic.', '']
    for row in report['paths']:
        lines += [f'## {row["order"]} / {row["layout"]} / {row["position"]}', '', '```asm']
        lines += [f'{i["pc"]:>8}  {i["opcode"]:8} {i["operands"]}' for i in row['path']]
        lines += ['```', '']
        print(row['order'],row['layout'],row['position'],row['instructions'],row['memory_operand_bytes'])
    (args.output/'paths.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
