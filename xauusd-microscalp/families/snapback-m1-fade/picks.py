"""The three picks, fixed on TRAIN by s4_select.py (neighbour-smoothed min-half score inside the risk limits).
Each pick: signal definition (fade_signal arguments) + simulator settings."""
PICKS = {
    'P1_snap_time3': dict(group='time', sig=(3, 'usd', 7.0, 'none', False, 0.0),
                          sim='x', kw=dict(tps=(1000.0,), sl=10.0, timeout=3, max_open=2, cooldown=0)),
    'P2_vwap_pullback_time15': dict(group='time', sig=(3, 'atr', 2.5, 'toward', False, 0.15),
                                    sim='x', kw=dict(tps=(1000.0,), sl=25.0, timeout=15, max_open=3, cooldown=0)),
    'P3_ladder_tp1': dict(group='tp1', sig=(3, 'atr', 3.0, 'toward', False, 0.0),
                          sim='lad', kw=dict(tp=1.0, sl=10.0, timeout=3, lad_max=10, lad_q=0.5, lad_window=10, mode=1)),
}
