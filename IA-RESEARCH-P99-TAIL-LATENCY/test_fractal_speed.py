import numpy as np
import sys
sys.path.insert(0, '..\\..\\..\\scripts')
from fractal_engine import FractalControlEngine
import time

np.random.seed(42)
data = list(np.random.exponential(30, 5000))
engine = FractalControlEngine()

start = time.time()
for i in range(3):
    r = engine.run_fractal_canary_test(data)
    print(f'Iter {i}: H={r["hurst_exponent"]:.4f}, status={r["stability_status"]}')
print(f'Tempo total: {time.time()-start:.2f}s')