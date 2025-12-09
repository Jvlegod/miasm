import sys
sys.path.insert(0, "/home/jvle/Desktop/works/sec/miasm/build/lib.linux-x86_64-cpython-311")


from miasm.core.locationdb import LocationDB

def code_sentinelle_riscv(jit):
    print("Hit sentinel!")
    print("X0 =", hex(jit.cpu.X1))
    jit.run = False

from miasm.arch.riscv.arch import mn_riscv

loc_db = LocationDB()
l = mn_riscv.fromstring("ADD X1, X3, X2", loc_db, 64)
# l = mn_riscv.fromstring("SLTIU X1, X5, 5", loc_db, 64)

print(l)
a = mn_riscv.asm(l)
print(a)
b = mn_riscv.dis(a[0], 64)
print(b)
from miasm.analysis.machine import Machine
mn = Machine('riscv').mn
instr = mn.dis(b'\x00\x21\x80\xb3', 64)
# instr = mn.dis(b'\x00\x52\xb0\x93', 64)
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

print("Symbolic execution:")
lifter = machine.lifter_model_call(loc_db)
ircfg = lifter.new_ircfg_from_asmcfg(asmcfg)
from miasm.ir.symbexec import SymbolicExecutionEngine
sb = SymbolicExecutionEngine(lifter)
symbolic_pc = sb.run_at(ircfg, 0)
print(symbolic_pc)
sb = SymbolicExecutionEngine(lifter, machine.mn.regs.regs_init)
symbolic_pc = sb.run_at(ircfg, 0, step=True)
from miasm.expression.expression import ExprInt
sb.symbols[machine.mn.regs.X1] = ExprInt(-3, 64)
symbolic_pc = sb.run_at(ircfg, 0, step=True)

