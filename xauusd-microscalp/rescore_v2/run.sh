#!/bin/bash
# Re-run round-1 final tests on copies of the family code with mlib v2
R=/mnt/project-files/xauusd-microscalp/rescore_v2
for f in classic-patterns forming-candle smart-money momentum-reversion; do
  ( cd $R/$f && timeout 1800 nice -n 10 python3 final_test.py > $R/$f.out 2>&1 )
done
( cd $R/trend-session && timeout 1800 nice -n 10 python3 final.py > $R/trend-session.out 2>&1 )
echo done > $R/DONE
