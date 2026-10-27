"""Diagnostic only, run after the picks were scored (it chooses nothing and cannot change a verdict).

The change pick is "GoldAllAgree, plus re-entries while M15 EMA5/20 is up and H1 + H4 (EMA20/80)
have stayed up since the last time all agreed". Two mapping questions:
1. Pair window (M5 EA): specs.py adds M5 to every timeframe set, so the re-entry there needs
   M5 AND M15 EMA5/20 up. What if the re-entry uses M15 alone, exactly as tuned?
2. h1_old (H1 base, only H1 + H4): the anchors H1 + H4 ARE the whole rule there, so the change
   does nothing (identical trades). The nearest testable version on H1 data: anchor H4 only,
   re-enter while H1 EMA5/20 is up. How does that do on 2016-22, and on m15_train / m15_test?
Usage: python3 -I mapping_check.py  -> printed summary."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/mnt/project-files/xauusd-more-trades/allagree-more/code')
import numpy as np
import aa_more as A
H = A.H
K = ('per_day', 'trades_day', 'max_dd', 'max_dd_mtm', 'worst_month')


def armed(base, tfs, anchors, fast_tfs, fast_emas):
    full = A.agree(base, tfs, (20, 80)); anc = A.agree(base, anchors, (20, 80))
    fst = A.agree(base, fast_tfs, fast_emas)
    out = np.zeros(len(full), bool); a = False
    for i in range(len(full)):
        a = bool(full[i]) or (a and bool(anc[i])); out[i] = a
    return full | (out & fst)


def show(label, w, tfs, anchors, fast_tfs, fe=(5, 20)):
    base = A.base_tf(w); P = H.pair_parts(w)
    t = A.trades(base, armed(base, tfs, anchors, fast_tfs, fe))
    s = H.score({'AllAgree': t, 'AsiaBreak': P['AsiaBreak']}, w, by_period=False)
    own = H.per_day(t, w) - H.per_day(P['AllAgree'], w)
    print(f'{label:58s} {w:9s}', {k: float(s[k]) for k in K}, '| own $/day %+.2f' % own.mean())


if __name__ == '__main__':
    for w in ('pair', 'm15_train', 'm15_test', 'h1_old'):
        s = H.score(H.pair_parts(w), w, by_period=False)
        print(f'{"baseline pair":58s} {w:9s}', {k: float(s[k]) for k in K})
    T5 = A.WIN_TFS['pair']
    show('pick as scored: re-entry needs M5+M15 EMA5/20', 'pair', T5, ('H1', 'H4'), ('M5', 'M15'))
    show('variant: re-entry on M15 EMA5/20 alone (as tuned)', 'pair', T5, ('H1', 'H4'), ('M15',))
    for w in ('m15_train', 'm15_test', 'h1_old'):
        show('H1 analogue: anchor H4, re-enter on H1 EMA5/20', w, A.WIN_TFS[w], ('H4',), ('H1',))
