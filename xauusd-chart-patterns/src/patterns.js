// Pattern library: names, plain explanations and schematic drawings (x 0-100 left to right, y 0-100 bottom to top).
const CAT = { rev: 'Reversal', cont: 'Continuation', bi: 'Either way' };

const BASE = {
  head_shoulders: {
    name: 'Head and shoulders', cat: 'rev', bias: -1,
    draw: { paths: [[[0, 28], [12, 62], [23, 47], [38, 84], [52, 45], [66, 63], [79, 46], [94, 18]]],
      lines: [[16, 47.5, 86, 45.5, 'Neckline']], labels: [[12, 62, 'Left shoulder'], [38, 84, 'Head'], [66, 63, 'Right shoulder']],
      target: [86, 45.5, 86, 7] },
    what: 'Three peaks after a rise. The middle one (the head) is the highest; the two either side (the shoulders) are lower and about level. A line under the two dips between them is the neckline.',
    means: 'Buyers pushed to a new high, failed, and could not even reach that high again on the next try. When price closes below the neckline, the uptrend is usually seen as over.',
    spot: ['Comes after a clear rise', 'Head clearly above both shoulders', 'Shoulders at roughly the same height', 'Confirmed only by a close below the neckline'],
    trade: 'Sell on a close below the neckline. Stop above the right shoulder. Target: the head-to-neckline distance, measured down from the break.',
    mistake: 'Calling it before the neckline breaks. Many "right shoulders" turn into a new high instead.'
  },
  double_top: {
    name: 'Double top', cat: 'rev', bias: -1,
    draw: { paths: [[[0, 22], [18, 78], [36, 50], [56, 78], [72, 48], [92, 20]]],
      lines: [[28, 50, 82, 50, 'Neckline']], labels: [[18, 78, 'Top 1'], [56, 78, 'Top 2']], target: [82, 50, 82, 22] },
    what: 'An "M" shape: price hits a high, pulls back, returns to about the same high and fails again. The low between the two tops is the neckline.',
    means: 'Sellers defended the same price twice. A close below the dip between the tops shows buyers have given up.',
    spot: ['Comes after a rise', 'Two tops at nearly the same price', 'A real pullback between them, not a few candles', 'Confirmed by a close below the middle low'],
    trade: 'Sell on a close below the neckline. Stop above the higher top. Target: top-to-neckline height, measured down.',
    mistake: 'Treating every pair of similar highs as a top. Without the neckline break it is just a range.'
  },
  triple_top: {
    name: 'Triple top', cat: 'rev', bias: -1,
    draw: { paths: [[[0, 22], [14, 78], [27, 52], [41, 78], [55, 52], [69, 78], [81, 50], [95, 22]]],
      lines: [[20, 51.5, 88, 50.5, 'Neckline']], labels: [[14, 78, 'Top 1'], [41, 78, 'Top 2'], [69, 78, 'Top 3']], target: [88, 50.5, 88, 23] },
    what: 'Like a double top with one more try: three highs at about the same price, with two dips between them.',
    means: 'A ceiling that held three times. Rare on gold; most "triple tops" break upward on the third or fourth try.',
    spot: ['Three highs within a small distance of each other', 'Two dips at a similar level form the neckline', 'Confirmed by a close below the neckline'],
    trade: 'Sell on a close below the neckline. Stop above the highest top. Target: the height of the pattern, measured down.',
    mistake: 'Selling the third top in advance. A flat ceiling tested many times is also how breakouts start.'
  },
  asc_triangle: {
    name: 'Ascending triangle', cat: 'cont', bias: 1,
    draw: { paths: [[[0, 18], [14, 75], [26, 34], [42, 75], [54, 50], [68, 75], [77, 62], [92, 92]]],
      lines: [[10, 75, 84, 75, 'Flat resistance'], [22, 32, 84, 67, 'Rising lows']], labels: [], target: [86, 75, 86, 97] },
    what: 'A flat ceiling with higher and higher lows pressing up into it.',
    means: 'Sellers wait at one price, but buyers keep stepping in earlier each time. The squeeze usually resolves upward.',
    spot: ['Highs at about the same level', 'At least two higher lows', 'Lines get closer together', 'Confirmed by a close above the ceiling'],
    trade: 'Buy on a close above the flat line. Stop below the rising line. Target: the triangle\'s height at its widest, added to the break.',
    mistake: 'Buying near the ceiling before it breaks. Wait for the close above it.'
  },
  sym_triangle: {
    name: 'Symmetrical triangle', cat: 'bi', bias: 0,
    draw: { paths: [[[0, 30], [12, 82], [26, 28], [40, 70], [52, 40], [64, 60], [74, 48], [90, 82]], [[74, 48], [90, 16]]],
      dashed: [1], lines: [[10, 84, 82, 53, 'Lower highs'], [24, 26, 82, 47, 'Higher lows']], labels: [[93, 82, 'up'], [93, 16, 'or down']] },
    what: 'Lower highs and higher lows, so price coils into a point. Neither side is winning.',
    means: 'It is a pause, not a signal by itself. The direction comes only from which line breaks first.',
    spot: ['Top line slopes down, bottom line slopes up', 'At least two touches on each line', 'Swings get smaller toward the tip'],
    trade: 'Trade the side that breaks, on a close outside the lines. Stop on the other side. Target: height at the widest part, from the break.',
    mistake: 'Guessing the direction early. On gold these break both ways often.'
  },
  rising_wedge: {
    name: 'Rising wedge', cat: 'rev', bias: -1,
    draw: { paths: [[[0, 10], [14, 50], [24, 30], [40, 66], [50, 50], [64, 77], [72, 67], [80, 80], [94, 40]]],
      lines: [[12, 52, 84, 83, 'Upper line'], [22, 28, 84, 75, 'Lower line (steeper)']], labels: [] },
    what: 'Price climbs, but between two upward lines that come together. The lows rise faster than the highs.',
    means: 'Each push higher gains less ground. The rise is tiring, and a break of the lower line often brings a quick drop.',
    spot: ['Both lines slope up', 'Lower line steeper than the upper', 'Swings get smaller', 'Confirmed by a close below the lower line'],
    trade: 'Sell on a close below the lower line. Stop above the last high. Target: the wedge\'s starting height, measured down.',
    mistake: 'Confusing it with a rising channel, where the lines stay parallel.'
  },
  bull_flag: {
    name: 'Bull flag', cat: 'cont', bias: 1,
    draw: { paths: [[[0, 15], [6, 22], [26, 80], [33, 70], [38, 74], [45, 63], [50, 67], [58, 57], [64, 62], [82, 96]]],
      lines: [[6, 22, 26, 80, 'Pole'], [26, 80, 66, 63, ''], [31, 68, 64, 53, 'Flag']], labels: [], target: [70, 66, 70, 100] },
    what: 'A sharp, fast rise (the pole), then a short, gentle drift down inside two parallel lines (the flag).',
    means: 'Traders take some profit after the burst, but nobody sells hard. When price breaks out of the flag, the rise often continues.',
    spot: ['A strong pole: big candles, few pullbacks', 'The flag is short and small compared with the pole', 'Flag slopes slightly down or sideways', 'Gives back less than half of the pole'],
    trade: 'Buy on a close above the flag. Stop below the flag. Target: the pole\'s length, added to the breakout.',
    mistake: 'Calling any pullback a flag. If it gives back more than half the pole, it is not one.'
  },
  bull_pennant: {
    name: 'Bull pennant', cat: 'cont', bias: 1,
    draw: { paths: [[[0, 15], [6, 22], [26, 80], [33, 62], [39, 76], [45, 66], [50, 72], [55, 68], [72, 96]]],
      lines: [[6, 22, 26, 80, 'Pole'], [26, 80, 60, 70, ''], [31, 60, 60, 67, 'Pennant']], labels: [], target: [62, 70, 62, 100] },
    what: 'A pole followed by a tiny triangle instead of a flag: the pause narrows to a point.',
    means: 'Same story as the flag. A short rest after a burst, then the move usually continues the same way.',
    spot: ['Strong pole first', 'Pause forms a small, short triangle', 'Lines meet; the pause is short'],
    trade: 'Buy on a close above the pennant. Stop below it. Target: the pole\'s length from the breakout.',
    mistake: 'Mixing it up with a large symmetrical triangle. A pennant is small and comes right after a pole.'
  },
  cup_handle: {
    name: 'Cup and handle', cat: 'cont', bias: 1,
    draw: { curve: [5, 80, 55, 80, 30], paths: [[[0, 74], [5, 80]], [[55, 80], [61, 68], [65, 72], [69, 66], [76, 82], [92, 96]]],
      lines: [[0, 80, 82, 80, 'Rim']], labels: [[30, 30, 'Cup'], [65, 62, 'Handle']], target: [84, 80, 84, 100] },
    what: 'A rounded "U" bottom (the cup), then a small, shallow dip (the handle) just under the old high, then a break above it.',
    means: 'A slow, calm recovery back to the old high, a last shake-out, then buyers take over.',
    spot: ['The bottom is round, not a sharp V', 'Both rims near the same price', 'Handle is small: less than about a third of the cup\'s depth', 'Confirmed by a close above the rim'],
    trade: 'Buy on a close above the rim. Stop below the handle. Target: the cup\'s depth, added to the rim.',
    mistake: 'Accepting a deep or long handle. A handle that drops near the cup bottom breaks the pattern.'
  },
  rounding_bottom: {
    name: 'Rounding bottom', cat: 'rev', bias: 1,
    draw: { curve: [8, 78, 70, 78, 28], paths: [[[0, 90], [8, 78]], [[70, 78], [90, 96]]],
      lines: [[4, 78, 80, 78, 'Neckline']], labels: [[39, 26, 'Slow U-turn']], target: [82, 78, 82, 100] },
    what: 'A long, gradual "U": the fall slows, flattens out, then turns slowly into a rise. Also called a saucer.',
    means: 'Selling dries up little by little rather than in one panic. It shows a slow change of mood.',
    spot: ['A smooth curve with no sharp low', 'The turn takes a long time', 'Confirmed by a close above the start of the curve'],
    trade: 'Buy on a close above the left rim. Stop around halfway down the bowl. Target: the depth of the bowl, added to the rim.',
    mistake: 'Seeing a curve after the fact in any V-shaped bounce.'
  },
  rectangle: {
    name: 'Rectangle (range)', cat: 'bi', bias: 0,
    draw: { paths: [[[0, 22], [10, 70], [22, 35], [36, 70], [50, 35], [64, 70], [76, 35], [86, 55], [96, 88]]],
      lines: [[8, 70, 82, 70, 'Resistance'], [8, 35, 82, 35, 'Support']], labels: [] },
    what: 'Price bounces between a flat ceiling and a flat floor several times.',
    means: 'Buyers and sellers are balanced. A close outside the box shows which side won.',
    spot: ['Two touches or more on each flat line', 'Lines roughly parallel and flat', 'Wait for a close outside the box'],
    trade: 'Trade the side that breaks. Stop back inside the box. Target: the box\'s height from the break.',
    mistake: 'Trading the first poke outside. Gold often wicks out of a range and comes back in.'
  },
  broadening: {
    name: 'Broadening (megaphone)', cat: 'bi', bias: 0,
    draw: { paths: [[[0, 50], [10, 60], [20, 42], [32, 70], [44, 32], [58, 80], [72, 22], [84, 44], [94, 12]]],
      lines: [[8, 58, 80, 88, 'Higher highs'], [18, 44, 80, 16, 'Lower lows']], labels: [] },
    what: 'The opposite of a triangle: each swing is bigger than the one before, so the lines spread apart.',
    means: 'The market is getting nervous and swinging harder in both directions. It often shows up near tops.',
    spot: ['Higher highs and lower lows at the same time', 'At least two touches on each line', 'Lines get further apart'],
    trade: 'Many traders avoid it. Others trade a close outside either line, with the stop back inside.',
    mistake: 'Fading every swing. Each swing is bigger, so stops get hit more often.'
  },
  channel_up: {
    name: 'Rising channel', cat: 'bi', bias: -1,
    draw: { paths: [[[0, 10], [12, 40], [22, 26], [36, 58], [46, 44], [60, 76], [70, 62], [80, 74], [94, 40]]],
      lines: [[0, 10, 76, 66, 'Support'], [8, 37, 80, 90, 'Resistance']], labels: [] },
    what: 'An uptrend that moves between two parallel rising lines.',
    means: 'While inside, the trend is healthy. A close below the lower line warns that the trend is losing steam.',
    spot: ['Lines rise and stay parallel', 'Several touches on each line', 'In this app, the channel ends with a close outside it'],
    trade: 'Inside: buy near the lower line. On a close below it: the trend may be ending; stop back inside.',
    mistake: 'Drawing the lines through every wick. Use the clear swing points.'
  },
  // learn-only patterns (rare on gold or need gaps/volume)
  diamond_top: {
    name: 'Diamond top', cat: 'rev', bias: -1, learnOnly: 'Rare. Not detected in the gold data well enough for practice.',
    draw: { paths: [[[0, 20], [12, 54], [20, 45], [32, 76], [42, 32], [54, 70], [62, 47], [70, 60], [76, 52], [92, 20]]],
      lines: [[10, 52, 32, 79, ''], [32, 79, 78, 56, ''], [10, 52, 42, 29, ''], [42, 29, 78, 50, 'Diamond']], labels: [] },
    what: 'Swings first widen (like a megaphone), then narrow (like a triangle), drawing a diamond.',
    means: 'Wild indecision at a top that calms down, then a break lower.',
    spot: ['Widening first half, narrowing second half', 'Comes after a rise', 'Confirmed by a close below the lower right line'],
    trade: 'Sell on a close below the lower right line. Stop above the last swing high. Target: the diamond\'s height.',
    mistake: 'Forcing four lines onto random noise.'
  },
  high_tight_flag: {
    name: 'High tight flag', cat: 'cont', bias: 1, learnOnly: 'Needs price to nearly double in weeks. Gold almost never does that.',
    draw: { paths: [[[0, 8], [18, 84], [24, 76], [30, 81], [36, 75], [42, 79], [58, 98]]],
      lines: [[0, 8, 18, 84, 'Huge pole']], labels: [[33, 70, 'Tight pause']] },
    what: 'A very steep run (price roughly doubles) followed by a tiny, shallow pause.',
    means: 'Extreme demand. Mostly seen in small stocks, not in gold.',
    spot: ['Rise of around 90-100% in a few weeks', 'Pause gives back very little', 'Short pause'],
    trade: 'Buy on a break above the pause. Stop below the pause.',
    mistake: 'Using it on markets that never move this much.'
  },
  island_reversal: {
    name: 'Island reversal', cat: 'rev', bias: -1, learnOnly: 'Needs price gaps. Gold trades nearly 24 hours, so gaps appear mostly over weekends.',
    draw: { paths: [[[0, 20], [30, 58]], [[36, 70], [42, 77], [48, 72], [54, 75]], [[60, 58], [92, 24]]],
      lines: [], labels: [[33, 64, 'Gap'], [45, 82, 'Island'], [57, 66, 'Gap']] },
    what: 'A group of candles cut off by a gap on both sides, like an island.',
    means: 'Buyers rushed in, then everyone left in a hurry. A sharp change of mood.',
    spot: ['A gap in one direction', 'A few candles trading on their own', 'A gap back the other way'],
    trade: 'Trade in the direction of the second gap. Stop beyond the island.',
    mistake: 'Counting tiny broker gaps as islands.'
  },
  measured_move: {
    name: 'Measured move', cat: 'cont', bias: 1, learnOnly: 'A way of setting targets rather than a pattern to spot.',
    draw: { paths: [[[0, 10], [30, 56], [40, 44], [46, 50], [52, 42], [84, 92]]],
      lines: [], labels: [[14, 40, 'Leg 1'], [46, 36, 'Pause'], [70, 72, 'Leg 2 ≈ Leg 1']] },
    what: 'A move, a pause, then a second move of about the same size.',
    means: 'It is the idea behind most pattern targets: the next leg tends to copy the last one.',
    spot: ['A clear first leg', 'A sideways or slight pullback pause', 'Second leg starts from the pause'],
    trade: 'Target the first leg\'s size from the end of the pause.',
    mistake: 'Treating the target as a promise. It is a guide only.'
  },
  bump_run: {
    name: 'Bump and run', cat: 'rev', bias: -1, learnOnly: 'Not detected in this app.',
    draw: { paths: [[[0, 12], [30, 24], [40, 30], [52, 72], [60, 80], [68, 58], [76, 40], [94, 18]]],
      lines: [[0, 10, 90, 46, 'Lead-in trend']], labels: [[22, 26, 'Lead-in'], [58, 84, 'Bump'], [86, 30, 'Run']] },
    what: 'A calm uptrend, then a sudden steep surge (the bump), then a fall back through the old trend line.',
    means: 'Excitement pushes price too far too fast; when it fades, price drops below where the calm trend was.',
    spot: ['A gentle lead-in trend', 'A surge at least twice as steep', 'Close below the lead-in line'],
    trade: 'Sell on a close below the lead-in line. Stop above the last high.',
    mistake: 'Selling the bump while it is still rising.'
  },
  dead_cat: {
    name: 'Dead cat bounce', cat: 'cont', bias: -1, learnOnly: 'A description of a failed rebound, not detected here.',
    draw: { paths: [[[0, 90], [22, 30], [32, 26], [42, 48], [50, 42], [60, 20], [84, 6]]],
      lines: [], labels: [[10, 60, 'Big fall'], [42, 54, 'Weak bounce'], [74, 14, 'Lower low']] },
    what: 'After a big drop, a short, weak bounce that fails, then the fall resumes.',
    means: 'Bargain hunters step in too early. The bounce looks like a recovery but is not.',
    spot: ['A sharp fall first', 'Bounce recovers only a small part of it', 'Price breaks the post-fall low'],
    trade: 'Sell when the bounce fails and price breaks the low. Stop above the bounce high.',
    mistake: 'Buying the first bounce after a crash.'
  },
  vcp: {
    name: 'Volatility contraction (VCP)', cat: 'cont', bias: 1, learnOnly: 'Close to the ascending triangle; practise that one instead.',
    draw: { paths: [[[0, 20], [10, 80], [22, 40], [34, 78], [44, 56], [54, 78], [62, 67], [70, 78], [76, 73], [90, 96]]],
      lines: [[8, 80, 84, 80, 'Resistance']], labels: [[22, 34, 'big'], [44, 50, 'smaller'], [62, 61, 'smallest']] },
    what: 'Pullbacks below the same high get smaller each time: big, smaller, smallest.',
    means: 'Sellers are running out. Each dip is bought sooner.',
    spot: ['Three or more pullbacks, each shallower', 'Same ceiling', 'Break above the ceiling'],
    trade: 'Buy on a close above the ceiling. Stop below the last, smallest pullback.',
    mistake: 'Ignoring the trend before it; this works best after a rise.'
  }
};

// mirror twins: same shape flipped upside down
const TWINS = {
  inv_head_shoulders: ['head_shoulders', 'Inverse head and shoulders', { 'Left shoulder': 'Left shoulder', 'Head': 'Head', 'Right shoulder': 'Right shoulder' }],
  double_bottom: ['double_top', 'Double bottom', { 'Top 1': 'Bottom 1', 'Top 2': 'Bottom 2' }],
  triple_bottom: ['triple_top', 'Triple bottom', { 'Top 1': 'Bottom 1', 'Top 2': 'Bottom 2', 'Top 3': 'Bottom 3' }],
  desc_triangle: ['asc_triangle', 'Descending triangle', { 'Flat resistance': 'Flat support', 'Rising lows': 'Falling highs' }],
  falling_wedge: ['rising_wedge', 'Falling wedge', { 'Upper line': 'Lower line', 'Lower line (steeper)': 'Upper line (steeper)' }],
  bear_flag: ['bull_flag', 'Bear flag', {}],
  bear_pennant: ['bull_pennant', 'Bear pennant', {}],
  inv_cup_handle: ['cup_handle', 'Inverted cup and handle', {}],
  rounding_top: ['rounding_bottom', 'Rounding top', { 'Slow U-turn': 'Slow turn down' }],
  channel_down: ['channel_up', 'Falling channel', { 'Support': 'Resistance', 'Resistance': 'Support' }],
  diamond_bottom: ['diamond_top', 'Diamond bottom', {}]
};
const TWIN_TEXT = {
  inv_head_shoulders: {
    what: 'Head and shoulders upside down: three lows after a fall, the middle one the deepest, the two shoulders about level. The neckline joins the two highs between them.',
    means: 'Sellers pushed to a new low, failed, and could not reach it again. A close above the neckline suggests the fall is over.',
    spot: ['Comes after a clear fall', 'Head clearly below both shoulders', 'Shoulders at roughly the same depth', 'Confirmed by a close above the neckline'],
    trade: 'Buy on a close above the neckline. Stop below the right shoulder. Target: head-to-neckline distance, added to the break.',
    mistake: 'Buying the right shoulder early. Wait for the neckline close.'
  },
  double_bottom: {
    what: 'A "W" shape: price makes a low, bounces, falls back to about the same low and holds again. The high between them is the neckline.',
    means: 'Buyers defended the same price twice. A close above the middle high shows sellers have given up.',
    spot: ['Comes after a fall', 'Two lows at nearly the same price', 'A real bounce between them', 'Confirmed by a close above the middle high'],
    trade: 'Buy on a close above the neckline. Stop below the lower bottom. Target: bottom-to-neckline height, added to the break.',
    mistake: 'Buying the second low before the neckline breaks.'
  },
  triple_bottom: {
    what: 'Three lows at about the same price, with two bounces between them.',
    means: 'A floor that held three times. Rare on gold.',
    spot: ['Three lows close together', 'Two bounce highs form the neckline', 'Confirmed by a close above the neckline'],
    trade: 'Buy on a close above the neckline. Stop below the lowest low. Target: the pattern\'s height, added to the break.',
    mistake: 'Buying the third low in advance. A floor tested many times can also give way.'
  },
  desc_triangle: {
    what: 'A flat floor with lower and lower highs pressing down onto it.',
    means: 'Buyers wait at one price, but sellers keep selling earlier each time. It usually resolves downward.',
    spot: ['Lows at about the same level', 'At least two lower highs', 'Confirmed by a close below the floor'],
    trade: 'Sell on a close below the flat line. Stop above the falling line. Target: the triangle\'s widest height, measured down.',
    mistake: 'Selling before the floor breaks.'
  },
  falling_wedge: {
    what: 'Price falls between two downward lines that come together. The highs fall faster than the lows.',
    means: 'Each push lower gains less ground. Sellers are tiring; a break above the upper line often brings a quick rise.',
    spot: ['Both lines slope down', 'Upper line steeper than the lower', 'Confirmed by a close above the upper line'],
    trade: 'Buy on a close above the upper line. Stop below the last low. Target: the wedge\'s starting height, added to the break.',
    mistake: 'Confusing it with a falling channel, where lines stay parallel.'
  },
  bear_flag: {
    what: 'A sharp, fast fall (the pole), then a short, gentle drift up inside two parallel lines (the flag).',
    means: 'Sellers take a breather, but buyers cannot push back much. A break below the flag often continues the fall.',
    spot: ['A strong falling pole', 'Small, short flag sloping up or sideways', 'Gives back less than half of the pole'],
    trade: 'Sell on a close below the flag. Stop above it. Target: the pole\'s length, measured down from the break.',
    mistake: 'Calling any bounce a flag. If it recovers more than half the pole, it is not one.'
  },
  bear_pennant: {
    what: 'A sharp fall followed by a tiny triangle that narrows to a point.',
    means: 'A short rest after a fast fall; the fall often continues.',
    spot: ['Strong falling pole first', 'Pause is a small, short triangle'],
    trade: 'Sell on a close below the pennant. Stop above it. Target: the pole\'s length from the break.',
    mistake: 'Mixing it up with a large triangle.'
  },
  inv_cup_handle: {
    what: 'An upside-down "U" (rounded top), then a small bounce (handle) just above the old low, then a break below.',
    means: 'A slow roll-over at a top, a last bounce that fails, then sellers take over.',
    spot: ['Rounded top, not a sharp spike', 'Both rims near the same price', 'Small handle', 'Confirmed by a close below the rim'],
    trade: 'Sell on a close below the rim. Stop above the handle high. Target: the cup\'s height, measured down.',
    mistake: 'A handle that climbs back near the top cancels the pattern.'
  },
  rounding_top: {
    what: 'A long, gradual upside-down "U": the rise slows, flattens, then slowly turns into a fall.',
    means: 'Buying fades little by little. A slow change of mood at a top.',
    spot: ['Smooth curve, no sharp top', 'The turn takes a long time', 'Confirmed by a close below the start of the curve'],
    trade: 'Sell on a close below the left rim. Stop around halfway up the dome. Target: the dome\'s height, measured down.',
    mistake: 'Seeing a dome in every sharp spike.'
  },
  channel_down: {
    what: 'A downtrend that moves between two parallel falling lines.',
    means: 'While inside, the fall is orderly. A close above the upper line warns the downtrend is losing steam.',
    spot: ['Lines fall and stay parallel', 'Several touches on each line', 'In this app, the channel ends with a close outside it'],
    trade: 'Inside: sell near the upper line. On a close above it: the fall may be ending; stop back inside.',
    mistake: 'Drawing lines through every wick.'
  },
  diamond_bottom: {
    what: 'After a fall, swings widen and then narrow, drawing a diamond, before a break upward.',
    means: 'Wild indecision at a bottom that calms down, then buyers take over.',
    spot: ['Widening then narrowing', 'Comes after a fall', 'Confirmed by a close above the upper right line'],
    trade: 'Buy on a close above the upper right line. Stop below the last low.',
    mistake: 'Forcing four lines onto noise.'
  }
};

// ---------- step-by-step builds, measured-move brackets ----------
// steps: [points of the main path shown, lines shown, caption]. A final "target" step is added when the drawing has one.
const EXTRA = {
  head_shoulders: { hb: [38, 47, 84], target: [86, 45.5, 86, 8.5], steps: [
    [2, 0, 'Price is rising. A reversal pattern needs a trend to reverse.'],
    [3, 0, 'First peak and pullback: the left shoulder.'],
    [5, 0, 'A higher peak (the head), then a fall back to about the same low.'],
    [5, 1, 'Join the two lows. That line is the neckline.'],
    [7, 1, 'A lower peak: the right shoulder. Buyers could not reach the head again.'],
    [8, 1, 'A close below the neckline confirms the pattern.']] },
  double_top: { hb: [18, 50, 78], steps: [
    [2, 0, 'Price rises to a first top.'],
    [3, 0, 'It pulls back. Mark this low.'],
    [4, 0, 'A second top at about the same price fails too.'],
    [4, 1, 'The pullback low is the neckline.'],
    [6, 1, 'A close below the neckline confirms the pattern.']] },
  triple_top: { hb: [41, 51, 78], steps: [
    [2, 0, 'Price rises to a first top.'],
    [4, 0, 'A second top at the same price.'],
    [6, 0, 'A third top at the same price. Three failures at one ceiling.'],
    [6, 1, 'Join the two lows: the neckline.'],
    [8, 1, 'A close below the neckline confirms the pattern.']] },
  asc_triangle: { hb: [26, 34, 75], target: [86, 75, 86, 116], steps: [
    [2, 0, 'Price rises to a high and gets pushed back.'],
    [4, 1, 'It returns to the same high: a flat ceiling.'],
    [6, 2, 'Each low is higher than the last. Draw the rising line.'],
    [7, 2, 'Price gets squeezed toward the tip.'],
    [8, 2, 'A close above the ceiling confirms the breakout.']] },
  sym_triangle: { hb: [12, 28, 82], steps: [
    [3, 0, 'A high, then a low.'],
    [5, 2, 'A lower high and a higher low. Draw both lines.'],
    [7, 2, 'The swings keep shrinking toward the tip.'],
    [8, 2, 'Price breaks out one way. Here it went up, but it could have gone down.']] },
  rising_wedge: { hb: [24, 30, 57], target: [90, 72, 90, 45], steps: [
    [3, 0, 'Price is rising.'],
    [5, 2, 'Highs and lows both rise. Draw both lines.'],
    [7, 2, 'The bottom line is steeper, so the lines come together. Each push gains less.'],
    [8, 2, 'The squeeze is nearly at its tip.'],
    [9, 2, 'A close below the lower line confirms the pattern.']] },
  bull_flag: { hb: [3, 22, 80], target: [70, 64, 70, 122], steps: [
    [3, 1, 'A fast, strong rise: the pole.'],
    [7, 1, 'A slow, small drift down. Nobody is selling hard.'],
    [9, 3, 'The drift fits between two parallel lines: the flag.'],
    [10, 3, 'A close above the flag confirms the breakout.']] },
  bull_pennant: { hb: [3, 22, 80], target: [62, 70, 62, 128], steps: [
    [3, 1, 'A fast, strong rise: the pole.'],
    [8, 3, 'A short pause that narrows into a tiny triangle: the pennant.'],
    [9, 3, 'A close above the pennant confirms the breakout.']] },
  cup_handle: { hb: [30, 30, 80], target: [84, 80, 84, 130], steps: [
    [2, 0, 'Price reaches an old high.'],
    [14, 0, 'It falls slowly in a rounded curve, not a sharp drop.'],
    [26, 1, 'A slow, round recovery back to the old high. Both rims mark the line.'],
    [30, 1, 'A small, shallow dip: the handle.'],
    [32, 1, 'A close above the rim confirms the breakout.']] },
  rounding_bottom: { hb: [39, 28, 78], target: [82, 78, 82, 128], steps: [
    [2, 0, 'Price is falling.'],
    [14, 0, 'The fall slows and flattens out.'],
    [26, 1, 'It turns slowly back up to where the curve began.'],
    [28, 1, 'A close above that level confirms the pattern.']] },
  rectangle: { hb: [8, 35, 70], target: [92, 70, 92, 105], steps: [
    [3, 0, 'A high and a low.'],
    [5, 2, 'Price bounces between a flat ceiling and a flat floor.'],
    [8, 2, 'Several touches on each side: buyers and sellers are balanced.'],
    [9, 2, 'A close outside the box shows which side won. Here it was up.']] },
  broadening: { steps: [
    [3, 0, 'A swing up and down.'],
    [5, 2, 'A higher high and a lower low. Draw both lines.'],
    [8, 2, 'Every swing is bigger than the one before. Nerves are rising.'],
    [9, 2, 'Price breaks out of one side.']] },
  channel_up: { steps: [
    [3, 0, 'Trending up: higher highs and higher lows.'],
    [5, 2, 'Draw parallel lines through the lows and the highs.'],
    [8, 2, 'Price keeps rising inside the channel.'],
    [9, 2, 'A close below the support line warns that the trend is tiring.']] }
};
const TCAP = 'Target: measure the pattern\'s height (the bracket) and project the same distance from the breakout.';
for (const [k, e] of Object.entries(EXTRA)) {
  const d = BASE[k].draw;
  if (e.hb) d.hb = e.hb;
  if (e.target) d.target = e.target;
  BASE[k].steps = e.steps;
}
// curves become ordinary points so they can be drawn step by step and flipped
function normDraw(d) {
  if (!d.curve) return d;
  const [x1, y1, x2, y2, yb] = d.curve, xm = (x1 + x2) / 2, A = (y1 - yb) / Math.pow(x1 - xm, 2), pts = [];
  for (let i = 0; i <= 24; i++) { const x = x1 + (x2 - x1) * i / 24; pts.push([x, A * Math.pow(x - xm, 2) + yb + Math.sin(i * 1.7) * 1.6]); }
  const same = (a, b) => a && b && a[0] === b[0] && a[1] === b[1];
  let main = (d.paths[0] || []).slice();
  for (const p of pts) if (!same(main[main.length - 1], p)) main.push(p);
  for (const p of d.paths[1] || []) if (!same(main[main.length - 1], p)) main.push(p);
  return Object.assign({}, d, { curve: null, paths: [main, ...d.paths.slice(2)] });
}
for (const v of Object.values(BASE)) v.draw = normDraw(v.draw);

// swap direction words for the upside-down twins
const SWAP = [['rise', 'fall'], ['rises', 'falls'], ['rising', 'falling'], ['peak', 'trough'], ['peaks', 'troughs'], ['high', 'low'], ['highs', 'lows'],
  ['higher', 'lower'], ['highest', 'lowest'], ['top', 'bottom'], ['tops', 'bottoms'], ['ceiling', 'floor'], ['above', 'below'], ['up', 'down'],
  ['buyers', 'sellers'], ['buying', 'selling'], ['resistance', 'support'], ['uptrend', 'downtrend']];
const SWAPMAP = {}; SWAP.forEach(([a, b]) => { SWAPMAP[a] = b; SWAPMAP[b] = a; });
function swapWords(s) {
  return s.replace(/[A-Za-z]+/g, w => {
    const lw = w.toLowerCase(), r = SWAPMAP[lw];
    if (!r) return w;
    return w[0] === w[0].toUpperCase() ? r[0].toUpperCase() + r.slice(1) : r;
  });
}

function flipDraw(d, relabel) {
  const f = y => 100 - y;
  const lab = t => (relabel && relabel[t]) || t;
  return {
    paths: (d.paths || []).map(p => p.map(([x, y]) => [x, f(y)])), dashed: d.dashed,
    curve: d.curve ? [d.curve[0], f(d.curve[1]), d.curve[2], f(d.curve[3]), f(d.curve[4])] : null,
    lines: (d.lines || []).map(([a, b, c, e, t]) => [a, f(b), c, f(e), lab(t)]),
    labels: (d.labels || []).map(([x, y, t, pos]) => [x, f(y), lab(t), pos === 'b' ? '' : 'b']),
    target: d.target ? [d.target[0], f(d.target[1]), d.target[2], f(d.target[3])] : null,
    hb: d.hb ? [d.hb[0], f(d.hb[1]), f(d.hb[2])] : null
  };
}

const PAT = {};
for (const [k, v] of Object.entries(BASE)) PAT[k] = Object.assign({ key: k }, v);
for (const [k, [src, name, relabel]] of Object.entries(TWINS)) {
  const b = BASE[src];
  PAT[k] = Object.assign({}, b, TWIN_TEXT[k] || {}, { key: k, name, bias: -b.bias, draw: flipDraw(b.draw, relabel),
    steps: b.steps ? b.steps.map(([n, l, t]) => [n, l, swapWords(t)]) : null });
  if (k === 'channel_down') PAT[k].bias = 1;
}
PAT.sym_triangle.bias = 0; PAT.rectangle.bias = 0; PAT.broadening.bias = 0;

const ORDER = ['head_shoulders', 'inv_head_shoulders', 'double_top', 'double_bottom', 'triple_top', 'triple_bottom',
  'rounding_top', 'rounding_bottom', 'cup_handle', 'inv_cup_handle', 'rising_wedge', 'falling_wedge',
  'asc_triangle', 'desc_triangle', 'sym_triangle', 'rectangle', 'broadening', 'channel_up', 'channel_down',
  'bull_flag', 'bear_flag', 'bull_pennant', 'bear_pennant',
  'diamond_top', 'diamond_bottom', 'high_tight_flag', 'island_reversal', 'measured_move', 'bump_run', 'dead_cat', 'vcp'];

const MIRROR_KIND = { head_shoulders: 'inv_head_shoulders', double_top: 'double_bottom', triple_top: 'triple_bottom',
  asc_triangle: 'desc_triangle', rising_wedge: 'falling_wedge', bull_flag: 'bear_flag', bull_pennant: 'bear_pennant',
  cup_handle: 'inv_cup_handle', rounding_bottom: 'rounding_top', channel_up: 'channel_down' };
for (const [a, b] of Object.entries(MIRROR_KIND)) MIRROR_KIND[b] = a;

const CONFUSE = [
  ['head_shoulders', 'double_top', 'triple_top', 'rounding_top', 'inv_cup_handle', 'rising_wedge'],
  ['inv_head_shoulders', 'double_bottom', 'triple_bottom', 'rounding_bottom', 'cup_handle', 'falling_wedge'],
  ['asc_triangle', 'desc_triangle', 'sym_triangle', 'rising_wedge', 'falling_wedge', 'rectangle', 'broadening', 'channel_up', 'channel_down'],
  ['bull_flag', 'bull_pennant', 'bear_flag', 'bear_pennant', 'asc_triangle', 'desc_triangle']
];

// ---------- basics course ----------
const PRIMER = [
  { title: 'Trend', draw: { paths: [[[0, 10], [15, 36], [26, 24], [43, 56], [53, 44], [70, 78], [80, 66], [96, 94]]],
      labels: [[15, 36, 'high'], [26, 24, 'higher low', 'b'], [43, 56, 'higher high'], [53, 44, 'higher low', 'b'], [70, 78, 'higher high']] },
    text: 'An uptrend makes higher highs and higher lows. A downtrend makes lower highs and lower lows. Reversal patterns only mean something after a clear trend; continuation patterns need a trend to continue.',
    q: 'Which of these is an uptrend?', options: ['Higher highs and higher lows', 'Lower highs and higher lows', 'Equal highs and equal lows'], a: 0 },
  { title: 'Support and resistance', draw: { paths: [[[0, 50], [10, 70], [22, 30], [36, 70], [50, 30], [64, 70], [76, 32], [88, 52]]],
      lines: [[4, 70, 92, 70, 'resistance'], [4, 30, 92, 30, 'support']], labels: [] },
    text: 'Resistance is a price where rises keep stopping. Support is a price where falls keep stopping. Most patterns are built from these lines: a neckline, a flat top, a floor.',
    q: 'Price fell to $2,300 three times and bounced each time. $2,300 is…', options: ['Support', 'Resistance', 'A target'], a: 0 },
  { title: 'Breakout: wait for the close', draw: { paths: [[[0, 30], [18, 58], [26, 78], [31, 60], [44, 48], [58, 62], [70, 82], [92, 94]]],
      lines: [[4, 68, 94, 68, 'line']], labels: [[26, 78, 'wick only'], [70, 82, 'close above']] },
    text: 'A breakout counts only when a candle closes beyond the line. Wicks poke through lines all the time on gold and snap back. Every pattern in this app was confirmed by a close.',
    q: 'A candle\'s wick goes above resistance but it closes below. Is that a breakout?', options: ['No, it closed back inside', 'Yes, price traded above it', 'Only on the daily chart'], a: 0 },
  { title: 'Drawing lines', draw: { paths: [[[0, 60], [12, 28], [24, 52], [38, 38], [50, 64], [64, 48], [78, 74], [94, 60]]],
      lines: [[6, 25, 92, 61, 'trendline']], labels: [[12, 28, 'touch 1', 'b'], [38, 38, 'touch 2', 'b'], [64, 48, 'touch 3', 'b']] },
    text: 'Draw lines through clear swing points (the obvious turning points), not through every wick. Two touches make a line; three make it trustworthy. If you have to force it, it is not there.',
    q: 'How many touches make a line worth trusting?', options: ['Three or more', 'One', 'Any line you can draw'], a: 0 },
  { title: 'Entry, stop and target', draw: { paths: [[[0, 90], [18, 40], [34, 68], [52, 40], [68, 70], [84, 98]]],
      lines: [[28, 68, 96, 68, 'entry'], [44, 37, 96, 37, 'stop']], labels: [],
      hb: [52, 40, 68], target: [90, 70, 90, 98] },
    text: 'Enter on the breakout close. Put the stop on the other side of the pattern, where the idea is clearly wrong. The target is the pattern\'s height projected from the breakout. "R" is the amount you risk: a trade that makes twice its risk made +2R.',
    q: 'Entry $2,400, stop $2,390, target $2,430. If the target is hit, the trade made…', options: ['+3R', '+1R', '+30R'], a: 0 },
  { title: 'Patterns fail often', draw: { paths: [[[0, 30], [20, 64], [32, 40], [48, 66], [56, 74], [62, 60], [72, 36], [90, 18]]],
      lines: [[4, 68, 94, 68, 'neckline']], labels: [[56, 74, 'breakout'], [90, 18, 'stop hit', 'b']] },
    text: 'On real gold, only 39% of these patterns reached their target before their stop. That is why the stop matters more than the shape. Risk a small amount on each trade so a run of failures cannot hurt you.',
    q: 'On gold, about how often did a pattern hit its target before its stop?', options: ['About 4 in 10', 'About 8 in 10', 'Almost always'], a: 0 },
  { title: 'Timeframes', draw: null,
    text: 'The same shapes appear on 5-minute and daily charts. In the gold tests, patterns on daily and 1-hour charts did best, and patterns on 5-minute charts did no better than random entries once the spread was paid. Small timeframes have more noise and costs weigh more.',
    q: 'In the gold tests, on which chart were patterns weakest?', options: ['5-minute', 'Daily', '1-hour'], a: 0 }
];

// ---------- look-alikes ----------
const LOOKALIKES = [
  ['double_top', 'head_shoulders', 'Two level peaks make a double top. Three peaks with a clearly higher middle one make a head and shoulders.'],
  ['double_top', 'triple_top', 'Count the failed tries at the same price: two or three.'],
  ['double_bottom', 'inv_head_shoulders', 'Two level lows make a double bottom. A clearly deeper middle low makes an inverse head and shoulders.'],
  ['bull_flag', 'bull_pennant', 'Both start with a pole. A flag\'s lines are parallel; a pennant\'s lines meet.'],
  ['rising_wedge', 'channel_up', 'A wedge\'s lines come together; a channel\'s lines stay parallel.'],
  ['asc_triangle', 'rising_wedge', 'An ascending triangle has a flat top. In a rising wedge the top line rises too.'],
  ['sym_triangle', 'bull_pennant', 'A pennant is small and comes right after a sharp pole. A symmetrical triangle is bigger and needs no pole.'],
  ['rectangle', 'broadening', 'A rectangle\'s lines are flat and parallel. A broadening pattern\'s lines spread apart.'],
  ['cup_handle', 'rounding_bottom', 'Both are round bottoms. The cup has a small dip (the handle) before the breakout.'],
  ['falling_wedge', 'bull_flag', 'A bull flag is small and follows a fast rise. A falling wedge is a longer fall whose lines come together.'],
  ['desc_triangle', 'falling_wedge', 'A descending triangle has a flat floor. In a falling wedge the bottom line falls too.'],
  ['bear_flag', 'bear_pennant', 'Both start with a falling pole. Parallel lines make a flag; lines that meet make a pennant.']
];
function lookalikeFor(a, b) { return LOOKALIKES.find(l => (l[0] === a && l[1] === b) || (l[0] === b && l[1] === a)); }

// ---------- learning path ----------
const STAGES = [
  { id: 'basics', name: 'Basics', blurb: 'Trends, lines, breakouts, stops and targets', kinds: [] },
  { id: 'tops', name: 'Tops and bottoms', blurb: 'Reversals at the end of a move', kinds: ['double_top', 'double_bottom', 'head_shoulders', 'inv_head_shoulders', 'triple_top', 'triple_bottom'] },
  { id: 'tri', name: 'Triangles and ranges', blurb: 'Price squeezed between lines', kinds: ['asc_triangle', 'desc_triangle', 'sym_triangle', 'rectangle', 'broadening'] },
  { id: 'wedge', name: 'Wedges and channels', blurb: 'Sloping lines, tiring trends', kinds: ['rising_wedge', 'falling_wedge', 'channel_up', 'channel_down'] },
  { id: 'flags', name: 'Flags and pennants', blurb: 'Short pauses after fast moves', kinds: ['bull_flag', 'bear_flag', 'bull_pennant', 'bear_pennant'] },
  { id: 'curves', name: 'Cups and curves', blurb: 'Slow, rounded turns', kinds: ['cup_handle', 'inv_cup_handle', 'rounding_bottom', 'rounding_top'] },
  { id: 'rare', name: 'Rare patterns', blurb: 'Good to know, learn only', kinds: ['diamond_top', 'diamond_bottom', 'high_tight_flag', 'island_reversal', 'measured_move', 'bump_run', 'dead_cat', 'vcp'] }
];
