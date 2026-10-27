# TVNavigation: TradingView-style chart navigation for MT5

`TVNavigation.mq5` is a small chart tool (an indicator with nothing to draw). It never places, changes or closes orders. It changes how the mouse moves the chart so it feels closer to TradingView.

## Install

1. In MT5 open MetaEditor (F4), then File > Open Data Folder, and copy `TVNavigation.mq5` into `MQL5\Indicators\`.
2. Open it in MetaEditor and press F7. If anything other than "0 errors" appears, paste the messages back in this thread.
3. Drag **TVNavigation** from the Navigator onto a chart.
4. To get it on every new chart: with it attached, right-click the chart > Templates > Save Template, and name it `default`. MT5 uses `default.tpl` for every new chart.

## What changes

| Action | TradingView | MT5 before | MT5 with TVNavigation |
|---|---|---|---|
| Mouse wheel | Zoom | Scrolls through time | **Zooms**, keeping the bar under the cursor in place (or keeping the latest bar in view if it is on screen) |
| Shift + wheel | Scroll through time | Varies | **Scrolls through time** (wheel up = back in time) |
| Ctrl + wheel | (wheel over the price axis) | Varies | **Zooms the price axis** around the price under the cursor |
| Drag the chart up/down | Pans prices, turns off auto | Only moves left/right | **Pans prices too** (after 6 px of up/down movement, auto scale turns off) |
| Drag the price axis | Stretches prices | Same | Same (MT5 already does this) |
| Double-click the price axis | Back to auto scale | Nothing | **Back to auto scale** |
| "A" button, bottom right | Auto scale on/off | None | **Same**: blue = auto scale on |
| ">>" button | Jump to the latest bar | End key | **Same**: blue when you are scrolled back |
| Key R (TradingView: Alt+R) | Reset chart | None | **Auto scale + jump to the latest bar** |
| Scrolled back in history | Chart stays where you put it | Jumps to the end on new bars (autoscroll) | **Stays put**; it only follows new bars while the latest bar is on screen |
| Space right of the last bar | Yes | Off unless "Chart shift" is on | **On**, 20% of the chart by default |

Every one of these can be switched off in the inputs (right-click the chart > Indicators List > TVNavigation > Edit).

## Inputs

- **Wheel zooms at the cursor**: off gives MT5's own wheel scrolling back.
- **Ctrl+wheel zooms the price axis**, and **Price zoom per wheel notch** (0.15 = 15%).
- **Drag up/down pans the price axis**, and the **dead zone** in pixels before it kicks in, so a left/right drag with a wobble doesn't switch off auto scale.
- **Bars per Shift+wheel notch**: 0 means 10% of the screen.
- **Right margin** on/off and its size (MT5 allows 10% to 50%).
- **Follow new bars only while the last bar is on screen.**
- **Buttons** and **key R** on/off.

## What MT5 cannot do (plain limits)

- **Zoom has only 6 steps.** MT5 bars come in 6 fixed widths, so each wheel notch jumps one step. TradingView zooms smoothly; MT5 cannot.
- **The wheel can jump for a split second.** MT5 has no setting to switch off its own wheel scrolling. It scrolls first and the tool then puts the view where it should be, so you may see a brief flicker on each notch.
- **No free scrolling into the future.** The empty space right of the last bar is MT5's "chart shift", capped at 50% of the chart. You can't drag the last bar to the middle of the screen beyond that.
- **Axis dragging stays MT5's own.** Dragging the price or time axis behaves as MT5 already does; the tool doesn't change it.
- **No log scale.** MT5 charts have no logarithmic price axis.
- **No trackpad pinch.** MT5 only reports the wheel.
- **Dragging objects and trade lines.** A press on a selected object, or within 6 px of a position or order line (entry, SL, TP), never starts a price pan, so moving lines works as before. If you set MT5 to select objects with a single click (Tools > Options > Charts), a drag that starts on an unselected line may still pan; switch "Drag up/down pans" off if that bothers you.
- **Once auto scale is off**, MT5 itself pans in both directions when you drag (that's built in when "Scale fix" is on). The tool steps back and lets MT5 do it.
- **Key R**: if R ever opens MT5's quick navigation box on your build, press Esc and switch "Key R" off in the inputs; the A and >> buttons do the same.

## MT5 settings that already help (no tool needed)

- **F8 > Show / Common**: "Chart shift" (empty space right of the last bar; drag the small grey triangle at the top of the chart to size it), "Chart autoscroll" (off = chart stays where you scroll it), "Scale fix" (off = auto scale).
- **Scroll**: left/right arrows, Page Up / Page Down, Home (oldest bar), End (latest bar).
- **Zoom**: `+` and `-` keys, or the zoom buttons on the Charts toolbar.
- **Crosshair**: press the mouse wheel (middle button) or Ctrl+F. Like TradingView's measure tool, drag with it to see bars, pips and price change.
- **Quick navigation**: press Enter on a chart and type a symbol or timeframe, e.g. `XAUUSD` or `M15`.
- **Look**: right-click > Properties > Colors to give the chart a TradingView-like colour scheme, and save it in the `default` template too.

## Not checked yet

MetaEditor isn't available in the cloud, so this hasn't been compiled in MT5. The code was checked by translating it to C++ against the documented MQL5 function signatures (0 errors), and every behaviour above was reasoned from the MQL5 documentation, not watched on a live chart. The wheel and the price-axis double-click depend on what events your MT5 build sends, so tell me if any row of the table doesn't behave as described.
