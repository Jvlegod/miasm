import sys
sys.path.insert(0, "/home/jvle/Desktop/works/sec/miasm/build/lib.linux-x86_64-cpython-311")


from miasm.core.locationdb import LocationDB

def code_sentinelle(jitter):
    jitter.running = False
    jitter.pc = 0
    return True

def code_sentinelle_aarch64(jit):
    print("Hit sentinel!")
    print("X0 =", hex(jit.cpu.X0))
    jit.run = False

def code_sentinelle_riscv(jit):
    print("Hit sentinel!")
    print("X0 =", hex(jit.cpu.X1))
    jit.run = False


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

print("=== aarch64 ===")
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
print("Emulate:")
from miasm.analysis.binary import Container
'''
; x0 += 4
; x1 += 1
; if (w0 == 1) x1 += 1; else x1 -= 1;
; w0 = x1;  ret

    add     w0, w0, #4        // ecx += 4
    add     w1, w1, #1        // ebx += 1
    subs    wzr, w0, #1       // 设置标志，相当于 cmp w0, #1
    b.eq    1f                // ==1 跳转
    sub     w1, w1, #1        // !=1: ebx -= 1
    b       2f
1:  add     w1, w1, #1        // ==1: ebx += 1
2:  add     w0, w1, #0        // mov w0, w1
    ret
'''
s = b'\x00\x10\x00\x11\x21\x04\x00\x11\x1f\x04\x00\x71\x60\x00\x00\x54' \
    b'\x21\x04\x00\x51\x02\x00\x00\x14\x21\x04\x00\x11\x20\x00\x00\x11' \
    b'\xc0\x03\x5f\xd6'

loc_db = LocationDB()
c = Container.from_string(s, loc_db)
print(c)
mdis = machine.dis_engine(c.bin_stream, loc_db=loc_db)
asmcfg = mdis.dis_multiblock(0)
for block in asmcfg.blocks:
    print(block)
jitter = machine.jitter(loc_db, jit_type='python')
jitter.init_stack()
run_addr = 0x40000000
from miasm.jitter.csts import PAGE_READ, PAGE_WRITE

jitter.vm.add_memory_page(run_addr, PAGE_READ | PAGE_WRITE, s)
jitter.add_breakpoint(0x1337beef, code_sentinelle_aarch64)

SENTINEL = 0x1337beef
jitter.cpu.LR = SENTINEL

jitter.push_uint64_t(0x1337beef)
jitter.set_trace_log()
jitter.init_run(run_addr)
jitter.continue_run()

# riscv

print("=== riscv ===")
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
print("Emulate:")
from miasm.analysis.binary import Container
'''
; a0 += 4
; a1 += 1
; if ((a0 & 0xff) == 1) a1 += 1; else a1 -= 1;
; a0 = a1;  ret

    addi    a0, a0, 4         # ecx += 4
    addi    a1, a1, 1         # ebx += 1
    andi    t0, a0, 0xff      # t0 = (a0 & 0xff)
    addi    t0, t0, -1        # t0 = t0 - 1
    beq     t0, x0, 1f        # ==1 jmp
    addi    a1, a1, -1        # !=1: ebx -= 1
    beq     x0, x0, 2f        # nocond jmp
1:  addi    a1, a1, 1         # ==1: ebx += 1
2:  addi    a0, a1, 0         # mv a0, a1
    jalr    x0, ra, 0         # ret
'''
s = b'\x00\x45\x05\x13\x00\x15\x85\x93\x0f\xf5\x72\x93\xff\xf2\x82\x93' \
    b'\x00\x02\x83\x63\xff\xf5\x85\x93\x00\x00\x02\x63\x00\x15\x85\x93' \
    b'\x00\x05\x85\x13\x00\x00\x80\x67'

# s = b'\x00\x21\x80\xb3'

loc_db = LocationDB()
c = Container.from_string(s, loc_db)
print(c)
mdis = machine.dis_engine(c.bin_stream, loc_db=loc_db)
asmcfg = mdis.dis_multiblock(0)
for block in asmcfg.blocks:
    print(block)
jitter = machine.jitter(loc_db, jit_type='python')
jitter.init_stack()
run_addr = 0x40000000
from miasm.jitter.csts import PAGE_READ, PAGE_WRITE
jitter.vm.add_memory_page(run_addr, PAGE_READ | PAGE_WRITE, s)

SENTINEL = 0x1337beef
jitter.cpu.X1 = SENTINEL

jitter.add_breakpoint(0x1337beef, code_sentinelle_riscv)
jitter.push_uint64_t(0x1337beef)
jitter.set_trace_log()
jitter.init_run(run_addr)
jitter.continue_run()

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
