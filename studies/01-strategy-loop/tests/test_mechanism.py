"""Protect static evidence from silently following the wrong instruction path."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'analysis'))
from inspect_mechanism import decode, walk, memory_operand


FIXTURE = '''0000000000000100 <strategy::replay()>:
 100: fd400460 ldr d0, [x3, #0x8]
 104: 1e602008 fcmp d0, #0.0
 108: 54000040 b.eq 0x110 <strategy::replay()+0x10>
 10c: 17fffffd b 0x100 <strategy::replay()>
 110: fd000460 str d0, [x3, #0x8]
 114: 17fffffb b 0x100 <strategy::replay()>
0000000000000118 <strategy::trace_replay()>:
 118: d65f03c0 ret
'''


class StaticEvidenceChecks(unittest.TestCase):
    def test_branch_target_and_fallthrough_are_distinct(self):
        instructions = decode(FIXTURE)
        self.assertNotIn(0x118, instructions)
        self.assertEqual([i['pc'] for i in walk(instructions,0x100,{0x108:False})],
                         ['0x100','0x104','0x108','0x10c'])
        self.assertEqual([i['pc'] for i in walk(instructions,0x100,{0x108:True})],
                         ['0x100','0x104','0x108','0x110','0x114'])

    def test_unreviewed_or_unused_branch_choices_fail(self):
        instructions = decode(FIXTURE)
        with self.assertRaises(KeyError):
            walk(instructions,0x100,{})
        with self.assertRaises(ValueError):
            walk(instructions,0x100,{0x108:True,0x999:False})
        instructions[0x114] = dict(pc='0x114',opcode='ret',operands='',encoding='d65f03c0')
        with self.assertRaises(ValueError):
            walk(instructions,0x100,{0x108:True})

    def test_paired_and_vector_operand_widths_are_bytes(self):
        for opcode,operands,wanted,direction in (
            ('ldp','d0, d1, [x3, #0x10]',16,'read'),
            ('stur','q31, [x3, #-0x18]',16,'write'),
            ('str','xzr, [x3]',8,'write')):
            value=memory_operand(dict(pc='0x100',opcode=opcode,operands=operands),{'x3':'state'})
            self.assertEqual((value['bytes'],value['direction'],value['category']),
                             (wanted,direction,'state'))
        with self.assertRaises(KeyError):
            memory_operand(dict(pc='0x100',opcode='ldr',operands='d0, [x4]'),{'x3':'state'})
        with self.assertRaises(ValueError):
            memory_operand(dict(pc='0x100',opcode='unknown',operands='d0, [x3]'),{'x3':'state'})


if __name__ == '__main__':
    unittest.main()
