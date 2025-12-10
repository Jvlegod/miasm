#-*- coding:utf-8 -*-

from __future__ import print_function
from builtins import range
import re

from future.utils import viewitems

from miasm.core import utils
from miasm.expression.expression import *
from pyparsing import *
from miasm.core.cpu import *
from collections import defaultdict
import miasm.arch.riscv.regs as regs_module
from miasm.arch.riscv.regs import *
from miasm.core.asm_ast import AstNode, AstInt, AstId, AstMem, AstOp
from miasm.ir.ir import color_expr_html
from miasm.core.utils import BRACKET_O, BRACKET_C


log = logging.getLogger("riscv_arch")
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[%(levelname)-8s]: %(message)s"))
log.addHandler(console_handler)
log.setLevel(logging.WARN)

gpregs_64 = (xregs_info.parser)

gpregs_info = {64: xregs_info, }

class riscv_gpreg_noarg(reg_noarg):
    parser = gpregs_64
    gpregs_info = gpregs_info

    def decode(self, v):
        # TODO: support 32-bit mode
        size = 64
        self.expr = self.gpregs_info[size].expr[v & 0x1F]
        return True

    def encode(self):
        if not self.expr.size in self.gpregs_info:
            return False
        if not self.expr in self.gpregs_info[self.expr.size].expr:
            return False
        self.value = self.gpregs_info[self.expr.size].expr.index(self.expr)
        return True
    
class riscv_arg(m_arg):
    def asm_ast_to_expr(self, value, loc_db, size_hint=None, fixed_size=None):
        if size_hint is None:
            # TODO: support 32-bit mode
            size_hint = 64
        if fixed_size is None:
            fixed_size = set()

        if isinstance(value, AstId):
            if value.name in all_regs_ids_byname:
                reg = all_regs_ids_byname[value.name]
                fixed_size.add(reg.size)
                return reg

            if isinstance(value.name, ExprId):
                fixed_size.add(value.name.size)
                return value.name

            loc_key = loc_db.get_or_create_name_location(value.name)
            return m2_expr.ExprLoc(loc_key, size_hint)

        if isinstance(value, AstInt):
            assert size_hint is not None
            return m2_expr.ExprInt(value.value, size_hint)

        if isinstance(value, AstOp):
            args = [self.asm_ast_to_expr(arg, loc_db, None, fixed_size)
                    for arg in value.args]

            if len(fixed_size) == 0:
                pass
            elif len(fixed_size) == 1:
                size = list(fixed_size)[0]
                args = [self.asm_ast_to_expr(arg, loc_db, size, fixed_size)
                        for arg in value.args]
            else:
                raise ValueError("Size conflict")

            return m2_expr.ExprOp(value.op, *args)

        return None

class riscv_gpreg(riscv_gpreg_noarg, riscv_arg):
    pass

class additional_info(object):

    def __init__(self):
        self.except_on_instr = False

class instruction_riscv(instruction):
    __slots__ = []

    def __init__(self, *args, **kargs):
        super(instruction_riscv, self).__init__(*args, **kargs)

    @staticmethod
    def arg2str(expr, index=None, loc_db=None):
        wb = False
        if expr.is_id() or expr.is_int():
            return str(expr)
        elif expr.is_loc():
            if loc_db is not None:
                return loc_db.pretty_str(expr.loc_key)
            else:
                return str(expr)
        elif isinstance(expr, m2_expr.ExprOp) and expr.op in shift_expr:
            op_str = shift_str[shift_expr.index(expr.op)]
            return "%s %s %s" % (expr.args[0], op_str, expr.args[1])
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "slice_at":
            return "%s LSL %s" % (expr.args[0], expr.args[1])
        elif isinstance(expr, m2_expr.ExprOp) and expr.op in extend_lst:
            op_str = expr.op
            return "%s %s %s" % (expr.args[0], op_str, expr.args[1])
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "postinc":
            if int(expr.args[1]) != 0:
                return "[%s], %s" % (expr.args[0], expr.args[1])
            else:
                return "[%s]" % (expr.args[0])
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "preinc_wb":
            if int(expr.args[1]) != 0:
                return "[%s, %s]!" % (expr.args[0], expr.args[1])
            else:
                return "[%s]" % (expr.args[0])
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "preinc":
            if len(expr.args) == 1:
                return "[%s]" % (expr.args[0])
            elif not isinstance(expr.args[1], m2_expr.ExprInt) or int(expr.args[1]) != 0:
                return "[%s, %s]" % (expr.args[0], expr.args[1])
            else:
                return "[%s]" % (expr.args[0])
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == 'segm':
            arg = expr.args[1]
            if isinstance(arg, m2_expr.ExprId):
                arg = str(arg)
            elif arg.op == 'LSL' and int(arg.args[1]) == 0:
                arg = str(arg.args[0])
            else:
                arg = "%s %s %s" % (arg.args[0], arg.op, arg.args[1])
            return '[%s, %s]' % (expr.args[0], arg)

        else:
            raise NotImplementedError("bad op")

    @staticmethod
    def arg2html(expr, index=None, loc_db=None):
        wb = False
        if expr.is_id() or expr.is_int() or expr.is_loc():
            return color_expr_html(expr, loc_db)
        elif isinstance(expr, m2_expr.ExprOp) and expr.op in shift_expr:
            op_str = shift_str[shift_expr.index(expr.op)]
            return "%s %s %s" % (
                color_expr_html(expr.args[0], loc_db),
                utils.set_html_text_color(op_str, utils.COLOR_OP),
                color_expr_html(expr.args[1], loc_db)
            )
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "slice_at":
            return "%s LSL %s" % (
                color_expr_html(expr.args[0], loc_db),
                color_expr_html(expr.args[1], loc_db)
            )
        elif isinstance(expr, m2_expr.ExprOp) and expr.op in extend_lst:
            op_str = expr.op
            return "%s %s %s" % (
                color_expr_html(expr.args[0], loc_db),
                op_str,
                color_expr_html(expr.args[1], loc_db)
            )
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "postinc":
            if int(expr.args[1]) != 0:
                return BRACKET_O + color_expr_html(expr.args[0], loc_db) + BRACKET_C + ", " + color_expr_html(expr.args[1], loc_db)
            else:
                return BRACKET_O + color_expr_html(expr.args[0], loc_db) + BRACKET_C
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "preinc_wb":
            if int(expr.args[1]) != 0:
                return BRACKET_O + color_expr_html(expr.args[0], loc_db) + ", " + color_expr_html(expr.args[1], loc_db) + BRACKET_C + '!'
            else:
                return BRACKET_O + color_expr_html(expr.args[0], loc_db) + BRACKET_C
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == "preinc":
            if len(expr.args) == 1:
                return BRACKET_O + color_expr_html(expr.args[0], loc_db) + BRACKET_C
            elif not isinstance(expr.args[1], m2_expr.ExprInt) or int(expr.args[1]) != 0:
                return BRACKET_O + color_expr_html(expr.args[0], loc_db) + ", " + color_expr_html(expr.args[1], loc_db) + BRACKET_C
            else:
                return BRACKET_O + color_expr_html(expr.args[0], loc_db) + BRACKET_C
        elif isinstance(expr, m2_expr.ExprOp) and expr.op == 'segm':
            arg = expr.args[1]
            if isinstance(arg, m2_expr.ExprId):
                arg = str(arg)
            elif arg.op == 'LSL' and int(arg.args[1]) == 0:
                arg = str(arg.args[0])
            else:
                arg = "%s %s %s" % (
                    color_expr_html(arg.args[0], loc_db),
                    utils.set_html_text_color(arg.op, utils.COLOR_OP),
                    color_expr_html(arg.args[1], loc_db)
                )
            return BRACKET_O + color_expr_html(expr.args[0], loc_db) + ', ' +  arg + BRACKET_C

        else:
            raise NotImplementedError("bad op")

class mn_riscv(cls_mn):
    name = "riscv"
    regs = regs_module
    num = 0
    all_mn = []
    all_mn_mode = defaultdict(list)
    all_mn_name = defaultdict(list)
    all_mn_inst = defaultdict(list)
    bintree = {}
    delayslot = 0
    # TODO: support 32-bit mode, however RISC-V is mostly 64-bit now.
    pc = {64: PC}
    sp = {64: X2}
    instruction = instruction_riscv
    max_instruction_len = 4

    @classmethod
    def getpc(cls, attrib=None):
        return PC

    @classmethod
    def getsp(cls, attrib=None):
        return X2

    def additional_info(self):
        info = additional_info()
        return info

    @classmethod
    def check_mnemo(cls, fields):
        pass

    @classmethod
    def getmn(cls, name):
        return name.upper()

    @classmethod
    def mod_fields(cls, fields):
        l = sum(x.l for x in fields)
        # RISC-V only has 16-bit and 32-bit instructions
        if l not in (16, 32):
            raise ValueError(f"Invalid RISC-V instruction length: {l}")
        return fields
    @classmethod
    def gen_modes(cls, subcls, name, bases, dct, fields):
        dct['mode'] = None
        return [(subcls, name, bases, dct, fields)]

def riscvop(name, fields, args=None, alias=False):
    dct = {"fields": fields}
    dct["alias"] = alias
    if args is not None:
        dct['args'] = args
    type(name, (mn_riscv,), dct)

class riscv_gpreg(riscv_gpreg_noarg, riscv_arg):
    pass

rd  = bs(l=5, cls=(riscv_gpreg,), fname="rd")
rs1 = bs(l=5, cls=(riscv_gpreg,), fname="rs1")
rs2 = bs(l=5, cls=(riscv_gpreg,), fname="rs2")

# nop
riscvop("nop", [bs("00000000000000000000000000010011")])

# ADD
riscvop("add",[bs("0000000"), rs2, rs1, bs("000"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("sub",[bs("0100000"), rs2, rs1, bs("000"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("and",[bs("0000000"), rs2, rs1, bs("111"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("or",[bs("0000000"), rs2, rs1, bs("110"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("xor",[bs("0000000"), rs2, rs1, bs("100"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("sll",[bs("0000000"), rs2, rs1, bs("001"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("srl",[bs("0000000"), rs2, rs1, bs("101"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("sra",[bs("0100000"), rs2, rs1, bs("101"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("slt",[bs("0000000"), rs2, rs1, bs("010"), rd, bs("0110011")], [rd, rs1, rs2])

riscvop("sltu",[bs("0000000"), rs2, rs1, bs("011"), rd, bs("0110011")], [rd, rs1, rs2]) 
