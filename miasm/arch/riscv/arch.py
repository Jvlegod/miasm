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
import miasm.arch.x86.regs as regs_module
from miasm.arch.x86.regs import *
from miasm.core.asm_ast import AstNode, AstInt, AstId, AstMem, AstOp
from miasm.ir.ir import color_expr_html
from miasm.core.utils import BRACKET_O, BRACKET_C


log = logging.getLogger("riscv_arch")
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("[%(levelname)-8s]: %(message)s"))
log.addHandler(console_handler)
log.setLevel(logging.WARN)

class instruction_riscv(instruction):
    __slots__ = []

    def __init__(self, *args, **kargs):
        super(instruction_riscv, self).__init__(*args, **kargs)

    @staticmethod
    def arg2str(expr, index=None, loc_db=None):
        if expr.is_id() or expr.is_int():
            o = str(expr)
        elif expr.is_loc():
            if loc_db is not None:
                o = loc_db.pretty_str(expr.loc_key)
            else:
                o = str(expr)
        elif ((isinstance(expr, ExprOp) and expr.op == 'far' and
               isinstance(expr.args[0], ExprMem)) or
              isinstance(expr, ExprMem)):
            if isinstance(expr, ExprOp):
                prefix, expr = "FAR ", expr.args[0]
            else:
                prefix = ""
            sz = SIZE2MEMPREFIX[expr.size]
            segm = ""
            if is_mem_segm(expr):
                segm = "%s:" % expr.ptr.args[0]
                expr = expr.ptr.args[1]
            else:
                expr = expr.ptr
            if isinstance(expr, ExprOp):
                s = str(expr).replace('(', '').replace(')', '')
            else:
                s = str(expr)
            o = prefix + sz + ' PTR ' + str(segm) + '[%s]' % s
        elif isinstance(expr, ExprOp) and expr.op == 'segm':
            o = "%s:%s" % (expr.args[0], expr.args[1])
        else:
            raise ValueError('check this %r' % expr)
        return "%s" % o


    @staticmethod
    def arg2html(expr, index=None, loc_db=None):
        if expr.is_id() or expr.is_int() or expr.is_loc():
            o = color_expr_html(expr, loc_db)
        elif ((isinstance(expr, ExprOp) and expr.op == 'far' and
               isinstance(expr.args[0], ExprMem)) or
              isinstance(expr, ExprMem)):
            if isinstance(expr, ExprOp):
                prefix, expr = "FAR ", expr.args[0]
            else:
                prefix = ""
            sz = SIZE2MEMPREFIX[expr.size]
            sz =  '<font color="%s">%s</font>' % (utils.COLOR_MEM, sz)
            segm = ""
            if is_mem_segm(expr):
                segm = "%s:" % expr.ptr.args[0]
                expr = expr.ptr.args[1]
            else:
                expr = expr.ptr
            if isinstance(expr, ExprOp):
                s = color_expr_html(expr, loc_db)#.replace('(', '').replace(')', '')
            else:
                s = color_expr_html(expr, loc_db)
            o = prefix + sz + ' PTR ' + str(segm) + BRACKET_O + str(s) + BRACKET_C
        elif isinstance(expr, ExprOp) and expr.op == 'segm':
            o = "%s:%s" % (
                color_expr_html(expr.args[0], loc_db),
                color_expr_html(expr.args[1], loc_db)
            )
        else:
            raise ValueError('check this %r' % expr)
        return "%s" % o

    def v_opmode(self):
        return self.additional_info.v_opmode

    def v_admode(self):
        return self.additional_info.v_admode

    def dstflow(self):
        if self.name in conditional_branch + unconditional_branch:
            return True
        if self.name.startswith('LOOP'):
            return True
        return self.name in ['CALL']
    
    def dstflow2label(self, loc_db):
        if self.additional_info.g1.value & 14 and self.name in repeat_mn:
            return
        expr = self.args[0]
        if not expr.is_int():
            return
        addr = (int(expr) + int(self.offset)) & int(expr.mask)
        loc_key = loc_db.get_or_create_offset_location(addr)
        self.args[0] = ExprLoc(loc_key, expr.size)

    def breakflow(self):
        if self.name in conditional_branch + unconditional_branch:
            return True
        if self.name.startswith('LOOP'):
            return True
        if self.name.startswith('RET'):
            return True
        if self.name.startswith('INT'):
            return True
        if self.name.startswith('SYS'):
            return True
        return self.name in ['CALL', 'HLT', 'IRET', 'IRETD', 'IRETQ', 'ICEBP', 'UD2']

    def splitflow(self):
        if self.name in conditional_branch:
            return True
        if self.name in unconditional_branch:
            return False
        if self.name.startswith('LOOP'):
            return True
        if self.name.startswith('INT'):
            return True
        if self.name.startswith('SYS'):
            return True
        return self.name in ['CALL']

    def setdstflow(self, a):
        return

    def is_subcall(self):
        return self.name in ['CALL']

    def getdstflow(self, loc_db):
        if self.additional_info.g1.value & 14 and self.name in repeat_mn:
            addr = int(self.offset)
            loc_key = loc_db.get_or_create_offset_location(addr)
            return [ExprLoc(loc_key, self.v_opmode())]
        return [self.args[0]]

    def get_symbol_size(self, symbol, loc_db):
        return self.mode

    def fixDstOffset(self):
        expr = self.args[0]
        if self.offset is None:
            raise ValueError('symbol not resolved %s' % l)
        if not isinstance(expr, ExprInt):
            log.warning('dynamic dst %r', expr)
            return
        self.args[0] = ExprInt(int(expr) - self.offset, self.mode)

    def get_info(self, c):
        self.additional_info.g1.value = c.g1.value
        self.additional_info.g2.value = c.g2.value
        self.additional_info.stk = hasattr(c, 'stk')
        self.additional_info.v_opmode = c.v_opmode()
        self.additional_info.v_admode = c.v_admode()
        self.additional_info.prefix = c.prefix
        self.additional_info.prefixed = getattr(c, "prefixed", b"")

    def __str__(self):
        return self.to_string()

    def to_string(self, loc_db=None):
        o = super(instruction_x86, self).to_string(loc_db)
        if self.additional_info.g1.value & 1:
            o = "LOCK %s" % o
        if self.additional_info.g1.value & 2:
            if getattr(self.additional_info.prefixed, 'default', b"") != b"\xF2":
                o = "REPNE %s" % o
        if self.additional_info.g1.value & 8:
            if getattr(self.additional_info.prefixed, 'default', b"") != b"\xF3":
                o = "REP %s" % o
        elif self.additional_info.g1.value & 4:
            if getattr(self.additional_info.prefixed, 'default', b"") != b"\xF3":
                o = "REPE %s" % o
        return o

    def to_html(self, loc_db=None):
        o = super(instruction_x86, self).to_html(loc_db)
        if self.additional_info.g1.value & 1:
            text =  utils.set_html_text_color("LOCK", utils.COLOR_MNEMO)
            o = "%s %s" % (text, o)
        if self.additional_info.g1.value & 2:
            if getattr(self.additional_info.prefixed, 'default', b"") != b"\xF2":
                text =  utils.set_html_text_color("REPNE", utils.COLOR_MNEMO)
                o = "%s %s" % (text, o)
        if self.additional_info.g1.value & 8:
            if getattr(self.additional_info.prefixed, 'default', b"") != b"\xF3":
                text =  utils.set_html_text_color("REP", utils.COLOR_MNEMO)
                o = "%s %s" % (text, o)
        elif self.additional_info.g1.value & 4:
            if getattr(self.additional_info.prefixed, 'default', b"") != b"\xF3":
                text =  utils.set_html_text_color("REPE", utils.COLOR_MNEMO)
                o = "%s %s" % (text, o)
        return o


    def get_args_expr(self):
        args = []
        for a in self.args:
            a = a.replace_expr(replace_regs[self.mode])
            args.append(a)
        return args

class mn_riscv(cls_mn):
    name = "riscv"
    prefix_op_size = False
    prefix_ad_size = False
    regs = regs_module
    all_mn = []
    all_mn_mode = defaultdict(list)
    all_mn_name = defaultdict(list)
    all_mn_inst = defaultdict(list)
    bintree = {}
    num = 0
    delayslot = 0
    pc = {16: IP, 32: EIP, 64: RIP}
    sp = {16: SP, 32: ESP, 64: RSP}
    instruction = instruction_x86
    max_instruction_len = 15

    @classmethod
    def getpc(cls, attrib):
        return cls.pc[attrib]

    @classmethod
    def getsp(cls, attrib):
        return cls.sp[attrib]

    def v_opmode(self):
        if hasattr(self, 'stk'):
            stk = 1
        else:
            stk = 0
        return v_opmode_info(self.mode, self.opmode, self.rex_w.value, stk)

    def v_admode(self):
        size, opmode, admode = self.mode, self.opmode, self.admode
        if size in [16, 32]:
            if admode:
                return invmode[size]
            else:
                return size
        elif size == 64:
            if admode == 1:
                return 32
            return 64

    def additional_info(self):
        info = additional_info()
        info.g1.value = self.g1.value
        info.g2.value = self.g2.value
        info.stk = hasattr(self, 'stk')
        info.v_opmode = self.v_opmode()
        info.prefixed = b""
        if hasattr(self, 'prefixed'):
            info.prefixed = self.prefixed.default
        return info

    @classmethod
    def check_mnemo(cls, fields):
        pass

    @classmethod
    def getmn(cls, name):
        return name.upper()

    @classmethod
    def mod_fields(cls, fields):
        prefix = [d_g1, d_g2, d_rex_p, d_rex_w, d_rex_r, d_rex_x, d_rex_b]
        return prefix + fields

    @classmethod
    def gen_modes(cls, subcls, name, bases, dct, fields):
        dct['mode'] = None
        return [(subcls, name, bases, dct, fields)]

    @classmethod
    def fromstring(cls, text, loc_db, mode):
        pref = 0
        prefix, new_s = get_prefix(text)
        if prefix == "LOCK":
            pref |= 1
            text = new_s
        elif prefix == "REPNE" or prefix == "REPNZ":
            pref |= 2
            text = new_s
        elif prefix == "REPE" or prefix == "REPZ":
            pref |= 4
            text = new_s
        elif prefix == "REP":
            pref |= 8
            text = new_s
        c = super(mn_x86, cls).fromstring(text, loc_db, mode)
        c.additional_info.g1.value = pref
        return c

    @classmethod
    def pre_dis(cls, v, mode, offset):
        offset_o = offset
        pre_dis_info = {'opmode': 0,
                        'admode': 0,
                        'g1': 0,
                        'g2': 0,
                        'rex_p': 0,
                        'rex_w': 0,
                        'rex_r': 0,
                        'rex_x': 0,
                        'rex_b': 0,
                        'prefix': b"",
                        'prefixed': b"",
                        }
        while True:
            c = v.getbytes(offset)
            if c == b'\x66':
                pre_dis_info['opmode'] = 1
            elif c == b'\x67':
                pre_dis_info['admode'] = 1
            elif c == b'\xf0':
                pre_dis_info['g1'] = 1
            elif c == b'\xf2':
                pre_dis_info['g1'] = 2
            elif c == b'\xf3':
                pre_dis_info['g1'] = 12

            elif c == b'\x2e':
                pre_dis_info['g2'] = 1
            elif c == b'\x36':
                pre_dis_info['g2'] = 2
            elif c == b'\x3e':
                pre_dis_info['g2'] = 3
            elif c == b'\x26':
                pre_dis_info['g2'] = 4
            elif c == b'\x64':
                pre_dis_info['g2'] = 5
            elif c == b'\x65':
                pre_dis_info['g2'] = 6

            else:
                break
            pre_dis_info['prefix'] += c
            offset += 1
        rex_prefixes = b'@ABCDEFGHIJKLMNO'
        if mode == 64 and c in rex_prefixes:
            while c in rex_prefixes:
                # multiple REX prefixes case - use last REX prefix
                x = ord(c)
                offset += 1
                c = v.getbytes(offset)
            pre_dis_info['rex_p'] = 1
            pre_dis_info['rex_w'] = (x >> 3) & 1
            pre_dis_info['rex_r'] = (x >> 2) & 1
            pre_dis_info['rex_x'] = (x >> 1) & 1
            pre_dis_info['rex_b'] = (x >> 0) & 1
        elif pre_dis_info.get('g1', None) == 12 and c in [b'\xa6', b'\xa7', b'\xae', b'\xaf']:
            pre_dis_info['g1'] = 4
        return pre_dis_info, v, mode, offset, offset - offset_o

    @classmethod
    def get_cls_instance(cls, cc, mode, infos=None):
        for opmode in [0, 1]:
            for admode in [0, 1]:
                c = cc()
                c.init_class()

                c.reset_class()
                c.add_pre_dis_info()
                c.dup_info(infos)
                c.mode = mode
                c.opmode = opmode
                c.admode = admode

                if not hasattr(c, 'stk') and hasattr(c, "fopmode") and c.fopmode.mode == 64:
                    c.rex_w.value = 1
                yield c

    def post_dis(self):
        if self.g2.value:
            for a in self.args:
                if not isinstance(a.expr, ExprMem):
                    continue
                m = a.expr
                a.expr = ExprMem(
                    ExprOp('segm', enc2segm[self.g2.value], m.ptr), m.size)
        return self

    def dup_info(self, infos):
        if infos is not None:
            self.g1.value = infos.g1.value
            self.g2.value = infos.g2.value

    def reset_class(self):
        super(mn_x86, self).reset_class()
        if hasattr(self, "opmode"):
            del(self.opmode)
        if hasattr(self, "admode"):
            del(self.admode)

    def add_pre_dis_info(self, pre_dis_info=None):
        if pre_dis_info is None:
            return True
        if hasattr(self, "prefixed") and self.prefixed.default == b"\x66":
            pre_dis_info['opmode'] = 0
        self.opmode = pre_dis_info['opmode']
        self.admode = pre_dis_info['admode']

        if hasattr(self, 'no_xmm_pref') and\
                pre_dis_info['prefix'] and\
                pre_dis_info['prefix'][-1] in b'\x66\xf2\xf3':
            return False
        if (hasattr(self, "prefixed") and
            not pre_dis_info['prefix'].endswith(self.prefixed.default)):
            return False
        if (self.rex_w.value is not None and
            self.rex_w.value != pre_dis_info['rex_w']):
            return False
        else:
            self.rex_w.value = pre_dis_info['rex_w']
        self.rex_r.value = pre_dis_info['rex_r']
        self.rex_b.value = pre_dis_info['rex_b']
        self.rex_x.value = pre_dis_info['rex_x']
        self.rex_p.value = pre_dis_info['rex_p']

        if hasattr(self, 'no_rex') and\
           (self.rex_r.value or self.rex_b.value or
            self.rex_x.value or self.rex_p.value):
            return False


        self.g1.value = pre_dis_info['g1']
        self.g2.value = pre_dis_info['g2']
        self.prefix = pre_dis_info['prefix']
        return True

    def post_asm(self, v):
        return v


    def gen_prefix(self):
        v = b""
        rex = 0x40
        if self.g1.value is None:
            self.g1.value = 0
        if self.g2.value is None:
            self.g2.value = 0

        if self.rex_w.value:
            rex |= 0x8
        if self.rex_r.value:
            rex |= 0x4
        if self.rex_x.value:
            rex |= 0x2
        if self.rex_b.value:
            rex |= 0x1
        if rex != 0x40 or self.rex_p.value == 1:
            v = utils.int_to_byte(rex) + v
            if hasattr(self, 'no_rex'):
                return None

        if hasattr(self, 'prefixed'):
            v = self.prefixed.default + v

        if self.g1.value & 1:
            v = b"\xf0" + v
        if self.g1.value & 2:
            if hasattr(self, 'no_xmm_pref'):
                return None
            v = b"\xf2" + v
        if self.g1.value & 12:
            if hasattr(self, 'no_xmm_pref'):
                return None
            v = b"\xf3" + v
        if self.g2.value:
            v = {
                1: b'\x2e',
                2: b'\x36',
                3: b'\x3e',
                4: b'\x26',
                5: b'\x64',
                6: b'\x65'
            }[self.g2.value] + v
        # mode prefix
        if hasattr(self, "admode") and self.admode:
            v = b"\x67" + v

        if hasattr(self, "opmode") and self.opmode:
            if hasattr(self, 'no_xmm_pref'):
                return None
            v = b"\x66" + v
        return v

    def encodefields(self, decoded):
        v = super(mn_x86, self).encodefields(decoded)
        prefix = self.gen_prefix()
        if prefix is None:
            return None
        return prefix + v

    def getnextflow(self, loc_db):
        raise NotImplementedError('not fully functional')

    def ir_pre_instruction(self):
        return [ExprAssign(mRIP[self.mode],
            ExprInt(self.offset + self.l, mRIP[self.mode].size))]

    @classmethod
    def filter_asm_candidates(cls, instr, candidates):

        cand_same_mode = []
        cand_diff_mode = []
        out = []
        for c, v in candidates:
            if (hasattr(c, 'no_xmm_pref') and
                (c.g1.value & 2 or c.g1.value & 4 or c.g1.value & 8 or c.opmode)):
                continue
            if hasattr(c, "fopmode") and v_opmode(c) != c.fopmode.mode:
                continue
            if hasattr(c, "fadmode") and v_admode(c) != c.fadmode.mode:
                continue
            # relative dstflow must not have opmode set
            # (assign IP instead of EIP for instance)
            if (instr.dstflow() and
                instr.name not in ["JCXZ", "JECXZ", "JRCXZ"] and
                len(instr.args) == 1 and
                    isinstance(instr.args[0], ExprInt) and c.opmode):
                continue

            out.append((c, v))
        candidates = out
        for c, v in candidates:
            if v_opmode(c) == instr.mode:
                cand_same_mode += v
        for c, v in candidates:
            if v_opmode(c) != instr.mode:
                cand_diff_mode += v
        cand_same_mode.sort(key=len)
        cand_diff_mode.sort(key=len)
        return cand_same_mode + cand_diff_mode

def riscvop(name, fields, args=None, alias=False):
    dct = {"fields": fields}
    dct["alias"] = alias
    if args is not None:
        dct['args'] = args
    type(name, (mn_riscv,), dct)

