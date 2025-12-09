import sys
sys.path.insert(0, "/home/jvle/Desktop/works/sec/miasm")


from miasm.core.locationdb import LocationDB
# x86
from miasm.arch.x86.arch import mn_x86

loc_db = LocationDB()
l = mn_x86.fromstring('XOR ECX, ECX', loc_db, 32)
print(l)
print(mn_x86.asm(l))

# aarch64
"""
from miasm.arch.aarch64.arch import mn_aarch64

loc_db = LocationDB()
l = mn_aarch64.fromstring('EOR X0, X0, X0', loc_db, 64)
print(l)
print(mn_aarch64.asm(l))
"""

# arm
"""
from miasm.arch.arm.arch import mn_arm

loc_db = LocationDB()

l = mn_arm.fromstring("EOR R0, R0, R0", loc_db, 32)
print(l)
print(mn_arm.asm(l))
"""
