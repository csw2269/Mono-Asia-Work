#!/usr/bin/env python3
SHM_SIZE = 0x85F80
assert 0x00100 + 1024 * 6 * 8 == 0x0C100
assert 0x0C100 + 1024 * 109 * 4 == 0x79100
assert 0x79100 + 1024 == 0x79500
assert 0x79500 + 1024 == 0x79900
assert 0x79F00 + 128 * 128 * 2 == 0x81F00
assert 0x81F00 + 128 * 128 == 0x85F00
assert 0x85F40 + 0x28 <= SHM_SIZE
print("PLSM v3 layout arithmetic passed")
