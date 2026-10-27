"""OANDA 2007-2016 rerun with the swap scaled to that era's price (0.126 * price/4000), to check the loss is not just swap."""
import sys, runpy
sys.argv = ['oanda.py', sys.argv[1]]
sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/code'); sys.path.insert(0, '/mnt/project-files/xauusd-github-bots/capitalize/trend-exits')
import tx
_orig = tx.tsim
def tsim_scaled(d, sig, atr_live, **kw):
    kw.setdefault('swap_l', 0.126 * float(d.close.mean()) / 4000)
    t = _orig(d, sig, atr_live, **kw)
    return t
tx.tsim = tsim_scaled
print('swap per night used:', round(0.126 * 1100 / 4000, 3), '(approx; exact uses mean price)')
runpy.run_path('/mnt/project-files/xauusd-github-bots/capitalize/trend-exits/oanda.py', run_name='__main__')
