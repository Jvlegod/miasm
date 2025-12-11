import sys
sys.path.insert(0, "/home/jvle/Desktop/works/sec/miasm/build/lib.linux-x86_64-cpython-311")


from miasm.core.locationdb import LocationDB
# example 1 
## x86
"""
from miasm.arch.x86.arch import mn_x86

loc_db = LocationDB()
l = mn_x86.fromstring('XOR ECX, ECX', loc_db, 32)
print(l)
print(mn_x86.asm(l))
"""
# aarch64

print("aarch64:")
from miasm.arch.aarch64.arch import mn_aarch64

loc_db = LocationDB()
l = mn_aarch64.fromstring('EOR X0, X0, X0', loc_db, 'l')
print(l)
a = mn_aarch64.asm(l)
print(a)
b = mn_aarch64.dis(a[0], "l")
print(b)
from miasm.analysis.machine import Machine
mn = Machine('aarch64l').mn
instr = mn.dis(b'\x00\x00\x00\xca', 'l')
print(instr)
machine = Machine('aarch64l')
lifter = machine.lifter_model_call(loc_db)
ircfg = lifter.new_ircfg()
lifter.add_instr_to_ircfg(instr, ircfg)
for lbl, irblock in ircfg.blocks.items():
    print(irblock)
print("working with IR ---")
for lbl, irblock in ircfg.blocks.items():
    for assignblk in irblock:
        rw = assignblk.get_rw()
        for dst, reads in rw.items():
            print('read:   ', [str(x) for x in reads])
            print('written:', dst)
            print()

# riscv

print("riscv:")
from miasm.arch.riscv.arch import mn_riscv

loc_db = LocationDB()
l = mn_riscv.fromstring("ADD X1, X3, X2", loc_db, 64)
print(l)
a = mn_riscv.asm(l)
print(a)
b = mn_riscv.dis(a[0], 64)
print(b)
from miasm.analysis.machine import Machine
mn = Machine('riscv').mn
instr = mn.dis(b'\x00\x21\x80\xb3', 64)
print(instr)
machine = Machine('riscv')
lifter = machine.lifter_model_call(loc_db)
ircfg = lifter.new_ircfg()
lifter.add_instr_to_ircfg(instr, ircfg)
for lbl, irblock in ircfg.blocks.items():
    print(irblock)
print("working with IR ---")
for lbl, irblock in ircfg.blocks.items():
    for assignblk in irblock:
        rw = assignblk.get_rw()
        for dst, reads in rw.items():
            print('read:   ', [str(x) for x in reads])
            print('written:', dst)
            print()

# arm
"""
from miasm.arch.arm.arch import mn_arm

loc_db = LocationDB()

l = mn_arm.fromstring("EOR R0, R0, R0", loc_db, 32)
print(l)
print(mn_arm.asm(l))
"""

# example 2
## x86
'''
loc_db = LocationDB()
"""
00000000 8d4904      lea    ecx, [ecx+0x4]
00000003 8d5b01      lea    ebx, [ebx+0x1]
00000006 80f901      cmp    cl, 0x1
00000009 7405        jz     0x10
0000000b 8d5bff      lea    ebx, [ebx-1]
0000000e eb03        jmp    0x13
00000010 8d5b01      lea    ebx, [ebx+0x1]
00000013 89d8        mov    eax, ebx
00000015 c3          ret
"""
s = b'\x8dI\x04\x8d[\x01\x80\xf9\x01t\x05\x8d[\xff\xeb\x03\x8d[\x01\x89\xd8\xc3'

from miasm.analysis.binary import Container
c = Container.from_string(s, loc_db)
from miasm.analysis.machine import Machine
machine = Machine('x86_32')
mdis = machine.dis_engine(c.bin_stream, loc_db=loc_db)
asmcfg = mdis.dis_multiblock(0)
for block in asmcfg.blocks:
    print(block)
jitter = machine.jitter(loc_db, jit_type='python')
jitter.init_stack()

run_addr = 0x40000000
from miasm.jitter.csts import PAGE_READ, PAGE_WRITE
jitter.vm.add_memory_page(run_addr, PAGE_READ | PAGE_WRITE, s)

def code_sentinelle(jitter):
    jitter.running = False
    jitter.pc = 0
    return True

jitter.add_breakpoint(0x1337beef, code_sentinelle)
jitter.push_uint32_t(0x1337beef)

jitter.set_trace_log()

jitter.init_run(run_addr)
jitter.continue_run()
'''

# example3
## x86
"""
loc_db = LocationDB()
from miasm.analysis.machine import Machine
s = b'\x8dI\x04\x8d[\x01\x80\xf9\x01t\x05\x8d[\xff\xeb\x03\x8d[\x01\x89\xd8\xc3'
from miasm.analysis.binary import Container
c = Container.from_string(s, loc_db)
machine = Machine('x86_32')
mdis = machine.dis_engine(c.bin_stream, loc_db=loc_db)
asmcfg = mdis.dis_multiblock(0)
lifter = machine.lifter_model_call(loc_db)
ircfg = lifter.new_ircfg_from_asmcfg(asmcfg)
from miasm.ir.symbexec import SymbolicExecutionEngine
sb = SymbolicExecutionEngine(lifter)
symbolic_pc = sb.run_at(ircfg, 0)
print(symbolic_pc)

sb = SymbolicExecutionEngine(lifter, machine.mn.regs.regs_init)
symbolic_pc = sb.run_at(ircfg, 0, step=True)
print("give a really val for ecx")

from miasm.expression.expression import ExprInt
sb.symbols[machine.mn.regs.ECX] = ExprInt(-3, 32)
symbolic_pc = sb.run_at(ircfg, 0, step=True)
"""
