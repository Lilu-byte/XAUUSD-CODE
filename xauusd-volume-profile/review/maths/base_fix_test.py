# Line 293 with a small tolerance: base = MathFloor(lo/step + 1e-9) * step, every cent price 1000.00-5000.00
import math
for step in (0.05, 0.10, 0.20, 0.25, 0.50, 1.00, 5.00):
    sc = int(round(step * 100)); low = high = 0
    for c in range(100000, 500001):
        lo = c / 100.0; exact = (c // sc) * sc / 100.0
        b = math.floor(lo / step + 1e-9) * step
        if b < exact - 1e-9: low += 1
        if b > exact + 1e-9: high += 1
    print(f"step {step:4.2f}: one step too low {low}, one step too high {high}")
