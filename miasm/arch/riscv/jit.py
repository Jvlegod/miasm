from builtins import range
import logging

from miasm.jitter.jitload import Jitter, named_arguments
from miasm.arch.riscv.sem import Lifter_X86_32, Lifter_X86_64
from miasm.jitter.codegen import CGen
from miasm.ir.translators.C import TranslatorC

log = logging.getLogger('jit_riscv')
hnd = logging.StreamHandler()
hnd.setFormatter(logging.Formatter("[%(levelname)-8s]: %(message)s"))
log.addHandler(hnd)
log.setLevel(logging.CRITICAL)


class riscv_CGen(CGen):
    def __init__(self, lifter):
        self.lifter = lifter
        self.PC = self.lifter.arch.regs.RIP
        self.translator = TranslatorC(self.lifter.loc_db)
        self.init_arch_C()

    def gen_post_code(self, attrib, pc_value):
        out = []
        if attrib.log_regs:
            # Update PC for dump_gpregs
            out.append("%s = %s;" % (self.C_PC, pc_value))
            out.append('dump_gpregs_32(jitcpu->cpu);')
        return out

class riscv_64_CGen(riscv_CGen):
    def gen_post_code(self, attrib, pc_value):
        out = []
        if attrib.log_regs:
            # Update PC for dump_gpregs
            out.append("%s = %s;" % (self.C_PC, pc_value))
            out.append('dump_gpregs_64(jitcpu->cpu);')
        return out