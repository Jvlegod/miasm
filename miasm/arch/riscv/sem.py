from builtins import range
from future.utils import viewitems

from miasm.expression.expression import ExprId, ExprInt, ExprLoc, ExprMem, \
    ExprCond, ExprCompose, ExprOp, ExprAssign
from miasm.ir.ir import Lifter, IRBlock, AssignBlock
from miasm.arch.riscv.arch import mn_riscv
from miasm.arch.riscv.regs import *
from miasm.core.sembuilder import SemBuilder
from miasm.jitter.csts import EXCEPT_DIV_BY_ZERO, EXCEPT_INT_XX

# System register for ARM64-A 8.6
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
def add(arg1, arg2, arg3):
    arg1 = arg2 + arg3


@sbuild.parse
def sub(arg1, arg2, arg3):
    arg1 = arg2 - arg3


@sbuild.parse
def mov(arg1, arg2):
    arg1 = arg2

def get_mem_access(mem):
    updt = None
    if isinstance(mem, ExprOp):
        if mem.op == 'preinc':
            if len(mem.args) == 1:
                addr = mem.args[0]
            else:
                addr = mem.args[0] + mem.args[1]
        elif mem.op == 'segm':
            base = mem.args[0]
            op, (reg, shift) = mem.args[1].op, mem.args[1].args
            if op == 'SXTW':
                off = reg.signExtend(base.size) << shift.zeroExtend(base.size)
                addr = base + off
            elif op == 'UXTW':
                off = reg.zeroExtend(base.size) << shift.zeroExtend(base.size)
                addr = base + off
            elif op == 'LSL':
                if isinstance(shift, ExprInt) and int(shift) == 0:
                    addr = base + reg.zeroExtend(base.size)
                else:
                    addr = base + \
                        (reg.zeroExtend(base.size)
                         << shift.zeroExtend(base.size))
            else:
                raise NotImplementedError('bad op')
        elif mem.op == "postinc":
            addr, off = mem.args
            updt = ExprAssign(addr, addr + off)
        elif mem.op == "preinc_wb":
            base, off = mem.args
            addr = base + off
            updt = ExprAssign(base, base + off)
        else:
            raise NotImplementedError('bad op')
    else:
        raise NotImplementedError('bad op')
    return addr, updt

@sbuild.parse
def ret(arg1):
    PC = arg1
    ir.IRDst = arg1

mnemo_func = sbuild.functions
mnemo_func.update({
    'add': add,
})


def get_mnemo_expr(ir, instr, *args):
    if not instr.name.lower() in mnemo_func:
        raise NotImplementedError('unknown mnemo %s' % instr)
    instr, extra_ir = mnemo_func[instr.name.lower()](ir, instr, *args)
    return instr, extra_ir


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

