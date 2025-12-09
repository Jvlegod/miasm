# -*- coding:utf-8 -*-

from builtins import range
from miasm.expression.expression import ExprId
from miasm.core.cpu import gen_reg, gen_regs, reg_info

exception_flags = ExprId('exception_flags', 32)
interrupt_num = ExprId('interrupt_num', 32)

# ---------------------------------------------------------------------------
#  Integer registers: X0..X31 (64-bit, RV64I)
# ---------------------------------------------------------------------------

# 硬件名，用于 IR / 汇编
gpregs_str = ["X%d" % i for i in range(32)]
gpregs_expr, gpregs_init, gpregs_info = gen_regs(
    gpregs_str, globals(), 64
)

# ABI 别名
ZERO = X0    # x0 / zero
RA   = X1    # return address
SP   = X2    # stack pointer
GP   = X3
TP   = X4

T0   = X5
T1   = X6
T2   = X7

S0   = X8
FP   = X8    # frame pointer (alias of S0)
S1   = X9

A0   = X10
A1   = X11
A2   = X12
A3   = X13
A4   = X14
A5   = X15
A6   = X16
A7   = X17

S2   = X18
S3   = X19
S4   = X20
S5   = X21
S6   = X22
S7   = X23
S8   = X24
S9   = X25
S10  = X26
S11  = X27

T3   = X28
T4   = X29
T5   = X30
T6   = X31

# 如果你也想要“不含 SP 的 GPR 列表”，可以像 aarch64 一样再调一次 gen_regs：
# 注意 gen_regs 会复用已有寄存器定义，不会创建新寄存器
gpregs_nosp_str = [name for name in gpregs_str if name != "X2"]
gpregs_nosp, _, gpregs_nosp_info = gen_regs(
    gpregs_nosp_str, globals(), 64
)

# ---------------------------------------------------------------------------
#  Floating-point registers: F0..F31 (64-bit for RV64 with D extension)
# ---------------------------------------------------------------------------

fregs_str = ["F%d" % i for i in range(32)]
fregs_expr, fregs_init, fregs_info = gen_regs(
    fregs_str, globals(), 64
)

FT0  = F0
FT1  = F1
FT2  = F2
FT3  = F3
FT4  = F4
FT5  = F5
FT6  = F6
FT7  = F7

FS0  = F8
FS1  = F9

FA0  = F10
FA1  = F11
FA2  = F12
FA3  = F13
FA4  = F14
FA5  = F15
FA6  = F16
FA7  = F17

FS2  = F18
FS3  = F19
FS4  = F20
FS5  = F21
FS6  = F22
FS7  = F23
FS8  = F24
FS9  = F25
FS10 = F26
FS11 = F27

FT8  = F28
FT9  = F29
FT10 = F30
FT11 = F31

# ---------------------------------------------------------------------------
#  CSR / system registers（TODO: normal to use）
# ---------------------------------------------------------------------------

sysregs_str = [
    # float CSR
    'FFLAGS', 'FRM', 'FCSR',

    'CYCLE', 'TIME', 'INSTRET',
    'CYCLEH', 'TIMEH', 'INSTRETH',

    # Supervisor-level CSRs
    'SSTATUS', 'SIE', 'STVEC', 'SSCRATCH',
    'SEPC', 'SCAUSE', 'STVAL', 'SIP', 'SATP',

    # Machine-level CSRs
    'MSTATUS', 'MISA', 'MIE', 'MTVEC',
    'MSCRATCH', 'MEPC', 'MCAUSE', 'MTVAL', 'MIP',
    'MCOUNTEREN', 'MENVCFG',

    # User-level
    'USTATUS', 'UIE', 'UTVEC', 'USCRATCH',
    'UEPC', 'UCAUSE', 'UTVAL', 'UIP',
]

sysregs_expr, sysregs_init, sysregs_info = gen_regs(
    sysregs_str, globals(), 64
)

# ---------------------------------------------------------------------------
#  Program Counter
# ---------------------------------------------------------------------------

PC, _ = gen_reg("PC", 64)
PC_init = ExprId("PC_init", 64)

# ---------------------------------------------------------------------------
#  （可选）通用 flags，方便重用通用算术 helper
#  RISC-V 本身没有这些寄存器，但 IR 里用它们没问题
# ---------------------------------------------------------------------------

reg_zf = 'zf'
reg_nf = 'nf'
reg_of = 'of'
reg_cf = 'cf'

zf = ExprId(reg_zf, size=1)
nf = ExprId(reg_nf, size=1)
of = ExprId(reg_of, size=1)
cf = ExprId(reg_cf, size=1)

zf_init = ExprId("zf_init", size=1)
nf_init = ExprId("nf_init", size=1)
of_init = ExprId("of_init", size=1)
cf_init = ExprId("cf_init", size=1)

all_regs_ids = (
    gpregs_expr +          # X0..X31
    fregs_expr +           # F0..F31
    sysregs_expr +         # CSRs
    [
        exception_flags,
        interrupt_num,
        PC,
        zf, nf, of, cf,
    ]
)

all_regs_ids_no_alias = all_regs_ids

attrib_to_regs = {
    'l': all_regs_ids_no_alias,
    'b': all_regs_ids_no_alias,
}

all_regs_ids_byname = dict((x.name, x) for x in all_regs_ids)

all_regs_ids_init = [ExprId("%s_init" % x.name, x.size)
                     for x in all_regs_ids]

regs_init = {}
for i, r in enumerate(all_regs_ids):
    regs_init[r] = all_regs_ids_init[i]

regs_flt_expr = fregs_expr
