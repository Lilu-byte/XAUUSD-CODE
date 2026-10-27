"""Stage 3a (TRAIN only): committee scores from the stage-1 walk-forward OOS scores. Each member's score is divided by its
trailing std over the previous 3960 scored rows (live-implementable), then members are averaged.
Writes tmp_s1E_ens.npz; evaluate with: python3 s2_eval.py 'tmp_s1E_*.npz' _ens"""
import sys, glob
sys.path.insert(0, '/mnt/project-files/xauusd-microscalp/families/ml-model')
from ml2 import *

scores = {}
for f in sorted(glob.glob(FAM + 'tmp_s1_[AB]*.npz')):
    z = np.load(f); idx = z['idx']
    for k in z.files:
        if k != 'idx': scores[k] = z[k].astype(float)


def norm(s):
    sd = pd.Series(s).shift(1).rolling(3960, min_periods=500).std().values
    return s / sd


def members(pred):
    return [k for k in scores if pred(k.split('|'))]


ENS = {
    'A_cf_std': members(lambda p: p[0] == 'A' and p[3] == 'cf' and p[4] == 'std' and p[2] != 'logit'),
    'A_cf_235': members(lambda p: p[0] == 'A' and p[1] in ('2', '3', '5') and p[3] == 'cf' and p[4] == 'std' and p[2] != 'logit'),
    'A_cf_all': members(lambda p: p[0] == 'A' and p[3] == 'cf' and p[2] != 'logit'),
    'A_all_std': members(lambda p: p[0] == 'A' and p[4] == 'std' and p[2] != 'logit'),
    'A_reg_cf': members(lambda p: p[0] == 'A' and p[1] in ('2', '3', '5', '10') and p[2] in ('reg', 'zreg') and p[3] == 'cf' and p[4] == 'std'),
    'AB_cf_std': members(lambda p: p[3] == 'cf' and p[4] == 'std' and p[2] != 'logit'),
    'B_std': members(lambda p: p[0] == 'B' and p[4] == 'std'),
}
out = {}
for name, mem in ENS.items():
    print(name, len(mem), 'members')
    out[f'E|{name}|ens|-|-'] = np.nanmean(np.stack([norm(scores[k]) for k in mem]), axis=0).astype(np.float32)
np.savez(FAM + 'tmp_s1E_ens.npz', idx=idx, **out)
