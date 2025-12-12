import sys
sys.path.insert(0, "/home/jvle/Desktop/works/sec/miasm/build/lib.linux-x86_64-cpython-311")

from miasm.analysis.machine import Machine
from miasm.analysis.binary import Container
from miasm.core.locationdb import LocationDB
from miasm.jitter.csts import PAGE_READ, PAGE_WRITE

code = (
    b'\x00\x10\x00\x11\x21\x04\x00\x11\x1f\x04\x00\x71\x60\x00\x00\x54'
    b'\x21\x04\x00\x51\x02\x00\x00\x14\x21\x04\x00\x11\x20\x00\x00\x11'
    b'\xc0\x03\x5f\xd6'
)

loc_db = LocationDB()
machine = Machine('aarch64l')
jitter = machine.jitter(loc_db, jit_type='python')

jitter.init_stack()

run_addr = 0x40000000
jitter.vm.add_memory_page(run_addr, PAGE_READ | PAGE_WRITE, code)

# 1. 设置“返回地址哨兵”
SENTINEL = 0x1337beef
jitter.cpu.LR = SENTINEL  # AArch64 的 LR 是 X30

# 2. 定义当 PC == SENTINEL 时的回调
def code_sentinelle(jit):
    print("Hit sentinel!")
    print("X0 =", hex(jit.cpu.X0))
    jit.run = False  # 停止执行

jitter.add_breakpoint(SENTINEL, code_sentinelle)

# 3. 初始化 PC 并运行
jitter.set_trace_log()
jitter.init_run(run_addr)
jitter.continue_run()

