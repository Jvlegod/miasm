from builtins import range
from future.utils import viewitems

from miasm.expression.expression import ExprId, ExprInt, ExprLoc, ExprMem, \
    ExprCond, ExprCompose, ExprOp, ExprAssign
from miasm.ir.ir import Lifter, IRBlock, AssignBlock
from miasm.arch.riscv.arch import mn_riscv
from miasm.arch.riscv.regs import *
from miasm.core.sembuilder import SemBuilder
from miasm.jitter.csts import EXCEPT_DIV_BY_ZERO, EXCEPT_INT_XX

# System register for riscv64
system_regs = {
    # op0 op1 crn crm op2
}

# SemBuilder context
ctx = {
    "PC": PC,
    "ExprId": ExprId,
    "exception_flags": exception_flags,
    "interrupt_num": interrupt_num,
    "EXCEPT_DIV_BY_ZERO": EXCEPT_DIV_BY_ZERO,
    "EXCEPT_INT_XX": EXCEPT_INT_XX,
}

sbuild = SemBuilder(ctx)


# instruction definition ##############

@sbuild.parse
def add(rd, rs1, rs2):
    rd = rs1 + rs2


@sbuild.parse
def addi(rd, rs1, imm):
    rd = rs1 + imm.signExtend(rs1.size)


@sbuild.parse
def andi(rd, rs1, imm):
    rd = rs1 & imm.zeroExtend(rs1.size)


@sbuild.parse
def beq(rs1, rs2, target):
    cond = ExprOp("==", rs1, rs2)

    fallthrough = ExprLoc(ir.get_next_loc_key(instr), PC.size)

    dst = ExprCond(cond, target, fallthrough)

    PC = dst
    ir.IRDst = dst


@sbuild.parse
def jalr(rd, rs1, imm):
    ret_addr = ExprInt(instr.offset + instr.l, PC.size)
    rd = ret_addr

    dst = rs1 + imm.signExtend(rs1.size)
    PC = dst
    ir.IRDst = dst


@sbuild.parse
def ret(arg1):
    PC = arg1
    ir.IRDst = arg1

mnemo_func = sbuild.functions
mnemo_func.update({
    # TODO: add more mnemonics here
})


def get_mnemo_expr(ir, instr, *args):
    if not instr.name.lower() in mnemo_func:
        raise NotImplementedError('unknown mnemo %s' % instr)
    instr_ir, extra_ir = mnemo_func[instr.name.lower()](ir, instr, *args)
    return instr_ir, extra_ir

class riscvinfo(object):
    mode = "riscv"
    # offset


class Lifter_Riscv64(Lifter):

    def __init__(self, loc_db):
        # TODO: support 32 bits mode
        Lifter.__init__(self, mn_riscv, 64, loc_db)
        self.pc = PC
        self.sp = X2
        self.IRDst = ExprId('IRDst', 64)
        self.addrsize = 64

    def get_ir(self, instr):
        instr_ir, extra_ir = get_mnemo_expr(self, instr, *instr.args)
        self.mod_pc(instr, instr_ir, extra_ir)
        instr_ir, extra_ir = self.del_dst_zr(instr, instr_ir, extra_ir)
        return instr_ir, extra_ir

    def expraff_fix_regs_for_mode(self, e):
        dst = e.dst
        src = e.src
        return ExprAssign(dst, src)

    def irbloc_fix_regs_for_mode(self, irblock, mode=64):
        irs = []
        for assignblk in irblock:
            new_assignblk = dict(assignblk)
            for dst, src in viewitems(assignblk):
                del(new_assignblk[dst])
                new_assignblk[dst] = src
            irs.append(AssignBlock(new_assignblk, assignblk.instr))
        return IRBlock(self.loc_db, irblock.loc_key, irs)

    def mod_pc(self, instr, instr_ir, extra_ir):
        "Replace PC by the instruction's offset"
        cur_offset = ExprInt(instr.offset, 64)
        pc_fixed = {self.pc: cur_offset}
        for i, expr in enumerate(instr_ir):
            dst, src = expr.dst, expr.src
            if dst != self.pc:
                dst = dst.replace_expr(pc_fixed)
            src = src.replace_expr(pc_fixed)
            instr_ir[i] = ExprAssign(dst, src)

        for idx, irblock in enumerate(extra_ir):
            extra_ir[idx] = irblock.modify_exprs(lambda expr: expr.replace_expr(pc_fixed) \
                                                 if expr != self.pc else expr,
                                                 lambda expr: expr.replace_expr(pc_fixed))


    def del_dst_zr(self, instr, instr_ir, extra_ir):
        "Writes to x0 (zero register) are discarded"
        # riscv: ZERO=>X0
        regs_to_fix = [X0]

        instr_ir = [expr for expr in instr_ir if expr.dst not in regs_to_fix]

        new_irblocks = []
        for irblock in extra_ir:
            irs = []
            for assignblk in irblock:
                new_dsts = {
                    dst: src for dst, src in viewitems(assignblk)
                    if dst not in regs_to_fix
                }
                irs.append(AssignBlock(new_dsts, assignblk.instr))
            new_irblocks.append(IRBlock(self.loc_db, irblock.loc_key, irs))

        return instr_ir, new_irblocks
