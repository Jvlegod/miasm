# -*- coding:utf-8 -*-

from builtins import range
from miasm.expression.expression import ExprId
from miasm.core.cpu import gen_reg, gen_regs, reg_info

xregs_str = ["X%d" % i for i in range(32)]
xregs_expr, xregs_init, xregs_info = gen_regs(
    xregs_str, globals(), 64)

PC, pc_info = gen_reg("PC", 64)


# TODO: add more special regs if needed
'''
    ZERO, RA, SP, GP, TP, T0, T1, T2, S0, S1, A0, A1,
    A2, A3, A4, A5, A6, A7, S2, S3, S4, S5, S6, S7,
    S8, S9, S10, S11, T3, T4, T5, T6,
    PC
'''
all_regs_ids = [
    X0, X1, X2, X3, X4, X5, X6, X7,
    X8, X9, X10, X11, X12, X13, X14, X15,
    X16, X17, X18, X19, X20, X21, X22, X23,
    X24, X25, X26, X27, X28, X29, X30, X31,
    PC
]

all_regs_ids_byname = dict([(x.name, x) for x in all_regs_ids])

riscv_abi_alias = {
    "ZERO": "X0",
    "RA":   "X1",
    "SP":   "X2",
    "GP":   "X3",
    "TP":   "X4",
    "T0":   "X5",
    "T1":   "X6",
    "T2":   "X7",
    "S0":   "X8",
    "FP":   "X8",
    "S1":   "X9",
    "A0":   "X10",
    "A1":   "X11",
    "A2":   "X12",
    "A3":   "X13",
    "A4":   "X14",
    "A5":   "X15",
    "A6":   "X16",
    "A7":   "X17",
    "S2":   "X18",
    "S3":   "X19",
    "S4":   "X20",
    "S5":   "X21",
    "S6":   "X22",
    "S7":   "X23",
    "S8":   "X24",
    "S9":   "X25",
    "S10":  "X26",
    "S11":  "X27",
    "T3":   "X28",
    "T4":   "X29",
    "T5":   "X30",
    "T6":   "X31",
}

all_regs_ids_byname.update(dict((x.name, x) for x in all_regs_ids))

for alias, base in riscv_abi_alias.items():
    all_regs_ids_byname[alias] = all_regs_ids_byname[base]

