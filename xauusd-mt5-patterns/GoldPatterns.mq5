//+------------------------------------------------------------------+
//|                                                 GoldPatterns.mq5 |
//| Finds classic chart patterns on any MT5 chart and draws them     |
//| (made for XAUUSD, works on any symbol and timeframe).            |
//|                                                                  |
//| The same detector as the Gold Pattern Trainer app:               |
//|   - swing highs and lows (zigzag) at 1.5, 2, 3 and 4.5 ATR(14);  |
//|   - fixed geometric rules for 23 patterns: double/triple tops    |
//|     and bottoms, head and shoulders (and inverse), ascending,    |
//|     descending and symmetrical triangles, rising and falling     |
//|     wedges, rectangles, broadening, rising and falling channels, |
//|     bull and bear flags and pennants, cup and handle (and        |
//|     inverted), rounding bottoms and tops;                        |
//|   - a pattern is CONFIRMED when a candle closes beyond its line  |
//|     (neckline, trendline, rim, flag edge) by 0.1 ATR.            |
//|                                                                  |
//| Typical path: after the most recent patterns, a faint dashed     |
//| line and two dotted lines show what price usually did next on    |
//| gold (middle and middle half of 2,723 past cases). It shows the  |
//| range to expect, not a direction: tested on 2024-2026, it picked |
//| the direction no better than a coin flip.                        |
//|                                                                  |
//| On the chart: shaded area, pattern lines, key points (shoulders, |
//| head, tops...), the name, a breakout arrow, the target (measured |
//| move) and the stop, and later whether the target or the stop was |
//| hit first. FORMING patterns (shape done, no breakout yet) are    |
//| drawn dashed with the price that would confirm them.             |
//|                                                                  |
//| What can change: forming patterns appear, update and vanish as   |
//| candles close. A confirmed pattern stays once drawn (checked by  |
//| replaying 20 years of gold candle by candle). Only closed        |
//| candles are used, so nothing changes inside a candle.            |
//|                                                                  |
//| A chart-reading tool, not a trading signal. In tests on gold     |
//| these patterns reached their target before their stop 39% of the |
//| time and did not beat holding gold (see the README). No orders.  |
//+------------------------------------------------------------------+
#property copyright   "FIS Agent project"
#property version     "1.20"
#property description "Finds and draws classic chart patterns (head and shoulders, double tops, triangles, wedges, flags, cups...). Forming patterns are dashed. No orders."
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

enum ENUM_GP_SIZE
{
   SIZE_ALL   = 0,   // All sizes (swings of 1.5, 2, 3 and 4.5 ATR)
   SIZE_SMALL = 1,   // Small only (1.5 and 2 ATR)
   SIZE_LARGE = 2    // Large only (3 and 4.5 ATR)
};

//--- inputs
input group "What to find"
input int          InpMaxBars      = 3000;        // Closed candles to scan
input ENUM_GP_SIZE InpSize         = SIZE_ALL;    // Pattern sizes
input bool         InpTops         = true;        // Double/triple tops and bottoms, head and shoulders
input bool         InpTriangles    = true;        // Triangles, rectangles, broadening
input bool         InpWedges       = true;        // Wedges and channels
input bool         InpFlags        = true;        // Flags and pennants
input bool         InpCups         = true;        // Cups and rounding tops/bottoms
input bool         InpForming      = true;        // Show forming patterns (no breakout yet)

input group "Drawing"
input int          InpShowLast     = 20;          // Confirmed patterns to draw (most recent)
input bool         InpTargets      = true;        // Draw target and stop
input bool         InpOutcome      = true;        // Mark whether the target or the stop was hit first
input bool         InpPoints       = true;        // Label key points (shoulders, head, tops...)
input bool         InpPanel        = true;        // Panel with forming patterns and results on this chart
input ENUM_BASE_CORNER InpCorner   = CORNER_LEFT_LOWER; // Panel corner
input color        InpBull         = clrMediumSeaGreen; // Colour: bullish (broke up)
input color        InpBear         = clrTomato;   // Colour: bearish (broke down)
input color        InpLine         = clrGoldenrod; // Colour: pattern lines
input color        InpText         = clrNONE;     // Colour: text (None = follow the chart)
input int          InpFont         = 8;           // Font size

input group "Typical path"
input bool         InpProj         = true;        // Show what price usually did next (faint lines)
input int          InpProjLast     = 3;           // ...after this many recent patterns
input double       InpProjLen      = 1.0;         // ...over this many pattern lengths (0.25 to 2)

input group "Alerts"
input bool         InpAlertConfirm = true;        // Alert when a pattern is confirmed
input bool         InpAlertForming = false;       // Alert when a new pattern starts forming
input bool         InpPush         = false;       // Also send alerts to the MT5 phone app
input string       InpPrefix       = "GPAT";      // Object name prefix (change it to run two copies)

//--- pattern kinds
#define NKIND 23
string KNAME[NKIND] = { "Double top", "Double bottom", "Triple top", "Triple bottom", "Head and shoulders",
   "Inverse head and shoulders", "Ascending triangle", "Descending triangle", "Symmetrical triangle", "Rising wedge",
   "Falling wedge", "Rectangle", "Broadening", "Rising channel", "Falling channel", "Bull flag", "Bear flag",
   "Bull pennant", "Bear pennant", "Cup and handle", "Inverted cup and handle", "Rounding bottom", "Rounding top" };
#define K_DTOP 0
#define K_DBOT 1
#define K_TTOP 2
#define K_TBOT 3
#define K_HS 4
#define K_IHS 5
#define K_ASC 6
#define K_DESC 7
#define K_SYM 8
#define K_RWEDGE 9
#define K_FWEDGE 10
#define K_RECT 11
#define K_BROAD 12
#define K_CHUP 13
#define K_CHDN 14
#define K_BFLAG 15
#define K_SFLAG 16
#define K_BPEN 17
#define K_SPEN 18
#define K_CUP 19
#define K_ICUP 20
#define K_RBOT 21
#define K_RTOP 22
string PLAB[] = { "", "Top 1", "Top 2", "Top 3", "Bottom 1", "Bottom 2", "Bottom 3", "Neck", "Left shoulder", "Head",
   "Right shoulder", "Pole start", "Pole top", "Pole bottom", "Left rim", "Right rim", "Cup bottom", "Cup top", "Handle" };

//--- typical path after each pattern on gold (D1 2004-2026, H4, H1, M15, M5; 2,723 patterns), measured from the
//    confirmation candle: 17 points over 0 to 2 pattern lengths, in multiples of the target distance, signed so
//    that + is the pattern's direction. 25th, 50th and 75th percentiles; rare patterns use their group's numbers.
#define PJ_STEPS 17
double PJ25[] = {
   0.000, -0.391, -0.620, -0.747, -0.867, -1.020, -1.251, -1.513, -1.684, -1.749, -1.782, -1.821, -1.873, -1.923, -2.003, -2.105, -2.161,
   0.000, -0.335, -0.511, -0.609, -0.709, -0.825, -0.976, -1.151, -1.264, -1.298, -1.379, -1.461, -1.453, -1.462, -1.553, -1.688, -1.821,
   0.000, -0.347, -0.543, -0.653, -0.768, -0.890, -1.020, -1.164, -1.309, -1.425, -1.516, -1.557, -1.547, -1.560, -1.640, -1.747, -1.825,
   0.000, -0.347, -0.543, -0.653, -0.768, -0.890, -1.020, -1.164, -1.309, -1.425, -1.516, -1.557, -1.547, -1.560, -1.640, -1.747, -1.825,
   0.000, -0.347, -0.543, -0.653, -0.768, -0.890, -1.020, -1.164, -1.309, -1.425, -1.516, -1.557, -1.547, -1.560, -1.640, -1.747, -1.825,
   0.000, -0.276, -0.479, -0.524, -0.492, -0.477, -0.516, -0.634, -0.711, -0.708, -0.831, -1.070, -1.180, -1.123, -1.074, -1.089, -1.084,
   0.000, -0.172, -0.254, -0.281, -0.332, -0.395, -0.443, -0.476, -0.484, -0.487, -0.534, -0.627, -0.716, -0.770, -0.817, -0.823, -0.750,
   0.000, -0.209, -0.346, -0.436, -0.524, -0.603, -0.653, -0.678, -0.719, -0.794, -0.881, -0.946, -0.975, -0.976, -0.983, -1.045, -1.166,
   0.000, -0.124, -0.198, -0.234, -0.265, -0.314, -0.368, -0.393, -0.403, -0.430, -0.464, -0.490, -0.519, -0.570, -0.638, -0.698, -0.745,
   0.000, -0.196, -0.304, -0.356, -0.446, -0.531, -0.585, -0.670, -0.735, -0.817, -0.962, -1.029, -1.052, -1.093, -1.116, -1.173, -1.248,
   0.000, -0.235, -0.359, -0.414, -0.463, -0.482, -0.475, -0.456, -0.427, -0.392, -0.366, -0.382, -0.418, -0.417, -0.409, -0.431, -0.450,
   0.000, -0.157, -0.250, -0.295, -0.340, -0.392, -0.438, -0.472, -0.501, -0.542, -0.597, -0.648, -0.690, -0.733, -0.781, -0.816, -0.827,
   0.000, -0.200, -0.315, -0.330, -0.352, -0.420, -0.462, -0.472, -0.491, -0.541, -0.613, -0.698, -0.758, -0.775, -0.799, -0.840, -0.862,
   0.000, -0.264, -0.497, -0.722, -0.910, -1.113, -1.359, -1.627, -1.853, -2.015, -2.171, -2.239, -2.174, -2.043, -1.983, -2.100, -2.350,
   0.000, -0.238, -0.428, -0.565, -0.623, -0.688, -0.775, -0.887, -0.994, -1.071, -1.143, -1.158, -1.259, -1.451, -1.513, -1.528, -1.677,
   0.000, -0.063, -0.112, -0.144, -0.153, -0.159, -0.167, -0.175, -0.209, -0.251, -0.267, -0.275, -0.293, -0.304, -0.338, -0.391, -0.418,
   0.000, -0.068, -0.112, -0.144, -0.177, -0.208, -0.216, -0.200, -0.229, -0.283, -0.294, -0.283, -0.285, -0.292, -0.282, -0.274, -0.287,
   0.000, -0.045, -0.073, -0.083, -0.092, -0.111, -0.135, -0.147, -0.148, -0.140, -0.130, -0.138, -0.192, -0.275, -0.307, -0.279, -0.246,
   0.000, -0.040, -0.074, -0.098, -0.116, -0.133, -0.149, -0.155, -0.161, -0.162, -0.158, -0.176, -0.201, -0.211, -0.225, -0.224, -0.185,
   0.000, -0.226, -0.341, -0.432, -0.544, -0.614, -0.674, -0.754, -0.822, -0.873, -0.910, -0.949, -0.979, -0.980, -0.965, -0.975, -1.047,
   0.000, -0.226, -0.341, -0.432, -0.544, -0.614, -0.674, -0.754, -0.822, -0.873, -0.910, -0.949, -0.979, -0.980, -0.965, -0.975, -1.047,
   0.000, -0.226, -0.341, -0.432, -0.544, -0.614, -0.674, -0.754, -0.822, -0.873, -0.910, -0.949, -0.979, -0.980, -0.965, -0.975, -1.047,
   0.000, -0.226, -0.341, -0.432, -0.544, -0.614, -0.674, -0.754, -0.822, -0.873, -0.910, -0.949, -0.979, -0.980, -0.965, -0.975, -1.047 };
double PJ50[] = {
   0.000, -0.091, -0.138, -0.150, -0.122, -0.103, -0.125, -0.130, -0.136, -0.164, -0.188, -0.210, -0.178, -0.179, -0.290, -0.321, -0.189,
   0.000, -0.044, -0.068, -0.057, -0.038, -0.059, -0.070, -0.060, -0.094, -0.131, -0.127, -0.122, -0.110, -0.059, -0.020, -0.059, -0.144,
   0.000, -0.055, -0.101, -0.117, -0.095, -0.087, -0.112, -0.128, -0.143, -0.160, -0.159, -0.164, -0.150, -0.139, -0.206, -0.254, -0.190,
   0.000, -0.055, -0.101, -0.117, -0.095, -0.087, -0.112, -0.128, -0.143, -0.160, -0.159, -0.164, -0.150, -0.139, -0.206, -0.254, -0.190,
   0.000, -0.055, -0.101, -0.117, -0.095, -0.087, -0.112, -0.128, -0.143, -0.160, -0.159, -0.164, -0.150, -0.139, -0.206, -0.254, -0.190,
   0.000, -0.048, -0.135, -0.134, -0.006, 0.136, 0.195, 0.170, 0.116, 0.070, -0.017, -0.106, -0.084, 0.005, -0.048, -0.227, -0.260,
   0.000, 0.018, 0.033, 0.043, 0.077, 0.127, 0.148, 0.135, 0.115, 0.118, 0.129, 0.118, 0.105, 0.104, 0.106, 0.115, 0.146,
   0.000, -0.006, -0.038, -0.084, -0.113, -0.104, -0.088, -0.101, -0.127, -0.140, -0.137, -0.123, -0.101, -0.106, -0.128, -0.127, -0.157,
   0.000, -0.001, 0.005, 0.014, 0.015, 0.010, 0.010, 0.011, 0.016, 0.022, 0.006, -0.013, -0.021, -0.020, -0.016, -0.027, -0.041,
   0.000, -0.032, -0.035, -0.020, -0.008, -0.030, -0.061, -0.069, -0.062, -0.068, -0.100, -0.120, -0.112, -0.096, -0.107, -0.148, -0.216,
   0.000, -0.038, -0.042, -0.037, -0.033, 0.023, 0.098, 0.137, 0.160, 0.182, 0.190, 0.220, 0.270, 0.294, 0.307, 0.316, 0.308,
   0.000, -0.002, 0.000, 0.001, -0.006, -0.010, -0.005, -0.004, -0.003, 0.001, -0.007, -0.014, -0.022, -0.040, -0.046, -0.046, -0.060,
   0.000, -0.028, -0.035, -0.019, -0.020, -0.037, -0.041, -0.036, -0.021, -0.018, -0.030, -0.037, -0.071, -0.099, -0.087, -0.080, -0.115,
   0.000, 0.028, 0.012, -0.054, -0.099, -0.136, -0.207, -0.240, -0.242, -0.252, -0.260, -0.278, -0.300, -0.342, -0.388, -0.443, -0.582,
   0.000, 0.045, 0.039, 0.019, 0.004, -0.014, 0.002, 0.040, 0.057, 0.071, 0.070, 0.027, -0.007, 0.009, 0.039, 0.009, -0.136,
   0.000, -0.014, -0.017, -0.004, 0.019, 0.037, 0.036, 0.026, 0.025, 0.024, 0.017, 0.008, 0.002, 0.006, 0.006, -0.002, -0.008,
   0.000, -0.010, -0.010, 0.001, 0.011, 0.011, 0.002, -0.006, 0.003, 0.005, -0.011, -0.008, 0.005, 0.008, 0.008, 0.025, 0.075,
   0.000, 0.009, 0.019, 0.027, 0.031, 0.030, 0.026, 0.017, 0.017, 0.030, 0.037, 0.043, 0.051, 0.045, 0.045, 0.058, 0.057,
   0.000, 0.004, 0.009, 0.022, 0.045, 0.056, 0.044, 0.049, 0.047, 0.034, 0.066, 0.103, 0.091, 0.073, 0.081, 0.097, 0.105,
   0.000, -0.038, -0.077, -0.102, -0.102, -0.099, -0.131, -0.181, -0.196, -0.196, -0.186, -0.131, -0.059, -0.041, -0.097, -0.138, -0.145,
   0.000, -0.038, -0.077, -0.102, -0.102, -0.099, -0.131, -0.181, -0.196, -0.196, -0.186, -0.131, -0.059, -0.041, -0.097, -0.138, -0.145,
   0.000, -0.038, -0.077, -0.102, -0.102, -0.099, -0.131, -0.181, -0.196, -0.196, -0.186, -0.131, -0.059, -0.041, -0.097, -0.138, -0.145,
   0.000, -0.038, -0.077, -0.102, -0.102, -0.099, -0.131, -0.181, -0.196, -0.196, -0.186, -0.131, -0.059, -0.041, -0.097, -0.138, -0.145 };
double PJ75[] = {
   0.000, 0.244, 0.401, 0.498, 0.599, 0.729, 0.864, 0.999, 1.078, 1.093, 1.119, 1.160, 1.149, 1.133, 1.257, 1.403, 1.421,
   0.000, 0.274, 0.461, 0.554, 0.651, 0.763, 0.885, 1.018, 1.121, 1.217, 1.302, 1.343, 1.316, 1.288, 1.328, 1.336, 1.286,
   0.000, 0.256, 0.409, 0.488, 0.588, 0.712, 0.834, 0.952, 1.021, 1.055, 1.116, 1.171, 1.159, 1.129, 1.190, 1.264, 1.257,
   0.000, 0.256, 0.409, 0.488, 0.588, 0.712, 0.834, 0.952, 1.021, 1.055, 1.116, 1.171, 1.159, 1.129, 1.190, 1.264, 1.257,
   0.000, 0.256, 0.409, 0.488, 0.588, 0.712, 0.834, 0.952, 1.021, 1.055, 1.116, 1.171, 1.159, 1.129, 1.190, 1.264, 1.257,
   0.000, 0.160, 0.242, 0.358, 0.453, 0.516, 0.569, 0.637, 0.682, 0.766, 1.027, 1.132, 0.981, 0.883, 0.819, 0.797, 0.933,
   0.000, 0.229, 0.361, 0.458, 0.543, 0.608, 0.680, 0.746, 0.798, 0.820, 0.824, 0.887, 0.970, 0.990, 0.985, 0.987, 0.989,
   0.000, 0.200, 0.311, 0.346, 0.361, 0.412, 0.475, 0.502, 0.521, 0.563, 0.626, 0.672, 0.660, 0.667, 0.741, 0.806, 0.858,
   0.000, 0.130, 0.224, 0.286, 0.330, 0.361, 0.390, 0.429, 0.460, 0.467, 0.479, 0.517, 0.567, 0.599, 0.608, 0.604, 0.600,
   0.000, 0.152, 0.253, 0.284, 0.302, 0.362, 0.422, 0.460, 0.476, 0.481, 0.544, 0.612, 0.628, 0.684, 0.745, 0.706, 0.609,
   0.000, 0.132, 0.242, 0.346, 0.442, 0.494, 0.551, 0.637, 0.721, 0.800, 0.842, 0.874, 0.963, 1.029, 1.033, 1.042, 1.032,
   0.000, 0.166, 0.274, 0.337, 0.384, 0.431, 0.482, 0.526, 0.561, 0.588, 0.617, 0.657, 0.685, 0.709, 0.741, 0.756, 0.760,
   0.000, 0.176, 0.277, 0.336, 0.367, 0.400, 0.451, 0.487, 0.519, 0.579, 0.628, 0.653, 0.686, 0.716, 0.776, 0.870, 0.929,
   0.000, 0.324, 0.470, 0.550, 0.584, 0.561, 0.553, 0.623, 0.730, 0.758, 0.769, 0.778, 0.823, 0.964, 1.088, 1.184, 1.240,
   0.000, 0.256, 0.422, 0.526, 0.621, 0.714, 0.810, 0.891, 0.966, 1.047, 1.079, 1.114, 1.210, 1.333, 1.490, 1.678, 1.863,
   0.000, 0.034, 0.068, 0.119, 0.182, 0.245, 0.275, 0.268, 0.267, 0.271, 0.282, 0.303, 0.310, 0.308, 0.327, 0.351, 0.345,
   0.000, 0.065, 0.101, 0.118, 0.129, 0.140, 0.158, 0.183, 0.210, 0.225, 0.240, 0.270, 0.278, 0.251, 0.241, 0.278, 0.339,
   0.000, 0.052, 0.083, 0.102, 0.120, 0.141, 0.157, 0.161, 0.190, 0.259, 0.313, 0.338, 0.335, 0.297, 0.298, 0.341, 0.365,
   0.000, 0.058, 0.124, 0.165, 0.190, 0.215, 0.243, 0.266, 0.268, 0.284, 0.325, 0.344, 0.360, 0.370, 0.335, 0.315, 0.355,
   0.000, 0.159, 0.247, 0.270, 0.296, 0.359, 0.413, 0.420, 0.467, 0.573, 0.637, 0.642, 0.669, 0.741, 0.803, 0.893, 1.072,
   0.000, 0.159, 0.247, 0.270, 0.296, 0.359, 0.413, 0.420, 0.467, 0.573, 0.637, 0.642, 0.669, 0.741, 0.803, 0.893, 1.072,
   0.000, 0.159, 0.247, 0.270, 0.296, 0.359, 0.413, 0.420, 0.467, 0.573, 0.637, 0.642, 0.669, 0.741, 0.803, 0.893, 1.072,
   0.000, 0.159, 0.247, 0.270, 0.296, 0.359, 0.413, 0.420, 0.467, 0.573, 0.637, 0.642, 0.669, 0.741, 0.803, 0.893, 1.072 };
int    PJN[]    = { 236, 208, 538, 538, 538, 45, 243, 257, 604, 165, 113, 1322, 180, 103, 113, 74, 67, 66, 51, 111, 111, 111, 111 };   // cases behind each path
int    PJPOOL[] = { 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1 };   // 1 = pooled with its group
double PJWAY[]  = { 0.470, 0.457, 0.454, 0.454, 0.454, 0.400, 0.543, 0.424, 0.487, 0.442, 0.655, 0.480, 0.456, 0.417, 0.469, 0.473, 0.567, 0.606, 0.627, 0.450, 0.450, 0.450, 0.450 };   // share that moved the pattern's way after 2 lengths
double PJRAND[] = { 0.467, 0.534, 0.498, 0.498, 0.498, 0.547, 0.543, 0.455, 0.497, 0.461, 0.556, 0.497, 0.493, 0.477, 0.542, 0.538, 0.452, 0.536, 0.477, 0.493, 0.493, 0.493, 0.493 };   // same for random entries

struct SPat
{
   int    kind, s, e, brk, dir, conf, forming;
   double entry, stop, target;
   int    np, pi[5], pl[5];
   double pp[5];
   int    nl, lx1[3], lx2[3];
   double ly1[3], ly2[3];
   int    cup, cupL, cupW;
   double qa, qb, qc;
   double tUp, tDn;            // forming: close needed to confirm (0 = no such side)
   int    res, resBar;         // outcome: 1 target first, -1 stop first, 0 open
   int    keep;
};

//--- data of the scanned window (index 0 = oldest)
int      gN = 0;
double   gH[], gL[], gC[], gA[];
datetime gT[];
int      pvI[], pvT[], pvC[];
double   pvP[];
int      gNP = 0;
SPat     gP[];
int      gNPat = 0;
datetime gLastBar = 0;
bool     gFirst = true;
string   gAlerted[];
int      gNAlerted = 0;
int      gObj = 0;
int      gWarm = 0;            // first candles of the window: used to settle ATR and swings, never drawn
datetime gTLive = 0;           // open time of the live candle
color    gTxt = clrSilver;
#define WARMUP 300

//+------------------------------------------------------------------+
int OnInit()
{
   ObjectsDeleteAll(0, InpPrefix + "_");
   gLastBar = 0; gFirst = true; gNAlerted = 0;
   return(INIT_SUCCEEDED);
}
void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, InpPrefix + "_");
   ChartRedraw(0);
}

//+------------------------------------------------------------------+
//| flipped prices: sg = 1 normal, -1 upside down                    |
//+------------------------------------------------------------------+
double FH(int i, int sg) { return sg == 1 ? gH[i] : -gL[i]; }
double FL(int i, int sg) { return sg == 1 ? gL[i] : -gH[i]; }
double FC(int i, int sg) { return sg * gC[i]; }

void CalcATR()
{
   for(int i = 0; i < gN; i++)
   {
      double pc = i > 0 ? gC[i - 1] : gC[0];
      double tr = MathMax(gH[i] - gL[i], MathMax(MathAbs(gH[i] - pc), MathAbs(gL[i] - pc)));
      gA[i] = i == 0 ? tr : gA[i - 1] + (tr - gA[i - 1]) / 14.0;
   }
}

void PushPiv(int i, double p, int t, int cf)
{
   ArrayResize(pvI, gNP + 1, 256); ArrayResize(pvP, gNP + 1, 256); ArrayResize(pvT, gNP + 1, 256); ArrayResize(pvC, gNP + 1, 256);
   pvI[gNP] = i; pvP[gNP] = p; pvT[gNP] = t; pvC[gNP] = cf; gNP++;
}

// swing highs and lows; a swing is confirmed once price reverses k ATR
void ZigZag(double k)
{
   gNP = 0;
   int d = 0, ei = 0, li = 0;
   double ep = gH[0], lp = gL[0];
   for(int i = 1; i < gN; i++)
   {
      if(d >= 0)
      {
         if(gH[i] > ep) { ei = i; ep = gH[i]; }
         if(d == 0 && gL[i] < lp) { li = i; lp = gL[i]; }
         if(ep - gL[i] >= k * gA[i] && (d == 1 || ei < i))
         {
            if(d == 0 && li < ei) PushPiv(li, lp, -1, ei);
            PushPiv(ei, ep, 1, i);
            d = -1; ei = i; ep = gL[i];
            continue;
         }
      }
      if(d <= 0)
      {
         if(d == 0)
         {
            if(gH[i] - lp >= k * gA[i] && li < i) { PushPiv(li, lp, -1, i); d = 1; ei = i; ep = gH[i]; }
            continue;
         }
         if(gL[i] < ep) { ei = i; ep = gL[i]; }
         if(gH[i] - ep >= k * gA[i]) { PushPiv(ei, ep, -1, i); d = 1; ei = i; ep = gH[i]; }
      }
   }
}

// least squares line through n points
void LinFit(const double &xs[], const double &ys[], int n, double &m, double &b)
{
   if(n == 2) { m = (ys[1] - ys[0]) / (xs[1] - xs[0]); b = ys[0] - m * xs[0]; return; }
   double sx = 0, sy = 0, sxx = 0, sxy = 0;
   for(int i = 0; i < n; i++) { sx += xs[i]; sy += ys[i]; sxx += xs[i] * xs[i]; sxy += xs[i] * ys[i]; }
   double den = n * sxx - sx * sx;
   m = (n * sxy - sx * sy) / den;
   b = (sy - m * sx) / n;
}

// first candle in [start, end) whose close is beyond the line m*i+b by margin (side 1 above, -1 below)
int FirstClose(int start, int end, double m, double b, int side, double margin)
{
   int stop = MathMin(end, gN);
   for(int i = start; i < stop; i++)
   {
      double f = m * i + b;
      if(side == 1 && gC[i] > f + margin) return i;
      if(side == -1 && gC[i] < f - margin) return i;
   }
   return -1;
}

int AddPat(int kind, int s, int e, int brk, int dir, int conf, double entry, double stop, double target, int forming)
{
   ArrayResize(gP, gNPat + 1, 128);
   int x = gNPat++;
   gP[x].kind = kind; gP[x].s = s; gP[x].e = e; gP[x].brk = brk; gP[x].dir = dir; gP[x].conf = conf;
   gP[x].entry = entry; gP[x].stop = stop; gP[x].target = target; gP[x].forming = forming;
   gP[x].np = 0; gP[x].nl = 0; gP[x].cup = 0; gP[x].cupL = 0; gP[x].cupW = 0; gP[x].qa = 0; gP[x].qb = 0; gP[x].qc = 0;
   gP[x].tUp = 0; gP[x].tDn = 0; gP[x].res = 0; gP[x].resBar = -1; gP[x].keep = 0;
   return x;
}
void AddPt(int x, int i, double p, int lab)
{
   int k = gP[x].np; if(k >= 5) return;
   gP[x].pi[k] = i; gP[x].pp[k] = p; gP[x].pl[k] = lab; gP[x].np = k + 1;
}
void SetTrig(int x, int side, double price)
{
   if(side == 1) gP[x].tUp = price; else gP[x].tDn = price;
}
void AddLn(int x, int x1, double y1, int x2, double y2)
{
   int k = gP[x].nl; if(k >= 3) return;
   gP[x].lx1[k] = x1; gP[x].ly1[k] = y1; gP[x].lx2[k] = x2; gP[x].ly2[k] = y2; gP[x].nl = k + 1;
}

//+------------------------------------------------------------------+
//| double tops/bottoms                                              |
//+------------------------------------------------------------------+
void FindDouble(int j)
{
   if(!(j + 2 < gNP && j >= 1)) return;
   int sg = pvT[j];
   double x1 = pvP[j] * sg, yn = pvP[j + 1] * sg, x2 = pvP[j + 2] * sg;
   double top = MathMax(x1, x2), hgt = top - yn, A = gA[pvI[j]];
   if(!(hgt >= 3 * A && MathAbs(x1 - x2) <= 0.12 * hgt && pvI[j + 2] - pvI[j] >= 8 && pvP[j - 1] * sg < yn - 0.3 * hgt)) return;
   for(int i = pvI[j]; i <= pvI[j + 2]; i++) if(FH(i, sg) > top + 1e-9) return;
   bool trip = j + 4 < gNP && MathAbs(pvP[j + 4] * sg - x1) <= 0.12 * hgt && pvP[j + 3] * sg > yn - 0.25 * hgt;
   int lim = pvI[j + 2] + (pvI[j + 2] - pvI[j]) + 3;
   int brk = FirstClose(pvI[j + 2] + 1, lim, 0.0, pvP[j + 1], -sg, 0.1 * A);
   int end = brk >= 0 ? brk : gN - 1;
   bool clean = true;
   for(int i = pvI[j + 2] + 1; i <= end; i++) if(FH(i, sg) > top) { clean = false; break; }
   if(!clean) return;
   int kind = sg == 1 ? K_DTOP : K_DBOT, x = -1;
   if(brk >= 0)
   {
      if(trip && pvC[j + 4] <= MathMax(brk, pvC[j + 2])) return;   // a third top already confirmed: triple, not double
      x = AddPat(kind, pvI[j - 1], brk, brk, -sg, MathMax(brk, pvC[j + 2]), gC[brk], top * sg, (yn - hgt) * sg, 0);
      AddLn(x, pvI[j], pvP[j + 1], brk, pvP[j + 1]);
   }
   else if(InpForming && lim > gN - 1 && !trip)
   {
      x = AddPat(kind, pvI[j - 1], gN - 1, -1, -sg, pvC[j + 2], 0.0, top * sg, (yn - hgt) * sg, 1);
      AddLn(x, pvI[j], pvP[j + 1], gN - 1, pvP[j + 1]);
      SetTrig(x, -sg, pvP[j + 1] - sg * 0.1 * A);
   }
   else return;
   AddPt(x, pvI[j], pvP[j], sg == 1 ? 1 : 4); AddPt(x, pvI[j + 1], pvP[j + 1], 7); AddPt(x, pvI[j + 2], pvP[j + 2], sg == 1 ? 2 : 5);
}

//+------------------------------------------------------------------+
//| triple tops/bottoms, head and shoulders                          |
//+------------------------------------------------------------------+
void FindFive(int j)
{
   if(!(j + 4 < gNP && j >= 1)) return;
   int sg = pvT[j];
   double X[5]; int I[5];
   for(int t = 0; t < 5; t++) { X[t] = pvP[j + t] * sg; I[t] = pvI[j + t]; }
   double pkMax = MathMax(X[0], MathMax(X[2], X[4])), pkMin = MathMin(X[0], MathMin(X[2], X[4]));
   double trMin = MathMin(X[1], X[3]), trMax = MathMax(X[1], X[3]);
   double hgt = pkMax - trMin, A = gA[I[0]];
   int span = I[4] - I[0];
   int legs = I[1] - I[0];
   for(int t = 1; t < 4; t++) legs = MathMin(legs, I[t + 1] - I[t]);
   if(!(hgt >= 3 * A && span >= 15 && pvP[j - 1] * sg < trMin - 0.3 * hgt && legs >= MathMax(3.0, 0.1 * span))) return;
   // triple
   if(pkMax - pkMin <= 0.12 * hgt && MathAbs(X[1] - X[3]) <= 0.25 * hgt && MathMin(I[2] - I[0], I[4] - I[2]) >= 5)
   {
      double neck = trMin;
      int lim = I[4] + (int)(0.6 * span) + 3;
      int brk = FirstClose(I[4] + 1, lim, 0.0, neck * sg, -sg, 0.1 * A);
      int end = brk >= 0 ? brk : gN - 1;
      bool clean = true;
      for(int i = I[4] + 1; i <= end; i++) if(FH(i, sg) > pkMax) { clean = false; break; }
      int kind = sg == 1 ? K_TTOP : K_TBOT, x = -1;
      if(clean && brk >= 0)
      {
         x = AddPat(kind, pvI[j - 1], brk, brk, -sg, MathMax(brk, pvC[j + 4]), gC[brk], pkMax * sg, (neck - hgt) * sg, 0);
         AddLn(x, I[0], neck * sg, brk, neck * sg);
      }
      else if(clean && InpForming && lim > gN - 1)
      {
         x = AddPat(kind, pvI[j - 1], gN - 1, -1, -sg, pvC[j + 4], 0.0, pkMax * sg, (neck - hgt) * sg, 1);
         AddLn(x, I[0], neck * sg, gN - 1, neck * sg);
         SetTrig(x, -sg, (neck - 0.1 * A) * sg);
      }
      if(x >= 0)
      {
         AddPt(x, I[0], pvP[j], sg == 1 ? 1 : 4); AddPt(x, I[2], pvP[j + 2], sg == 1 ? 2 : 5); AddPt(x, I[4], pvP[j + 4], sg == 1 ? 3 : 6);
      }
   }
   // head and shoulders
   double LS = X[0], HD = X[2], RS = X[4];
   double headH = HD - (X[1] + X[3]) / 2;
   double ratio = (double)(I[2] - I[0]) / MathMax(1, I[4] - I[2]);
   if(HD - MathMax(LS, RS) >= 0.2 * headH && MathAbs(LS - RS) <= 0.3 * headH && MathAbs(X[1] - X[3]) <= 0.3 * headH
      && headH >= 3 * A && MathMin(LS, RS) - trMax >= 0.25 * headH && ratio >= 0.4 && ratio <= 2.5)
   {
      double ms = (pvP[j + 3] - pvP[j + 1]) / (I[3] - I[1]);
      double bs = pvP[j + 1] - ms * I[1];
      int lim = I[4] + (int)(0.5 * span) + 3;
      int brk = FirstClose(I[4] + 1, lim, ms, bs, -sg, 0.1 * A);
      int end = brk >= 0 ? brk : gN - 1;
      bool clean = true;
      for(int i = I[4] + 1; i <= end; i++) if(FH(i, sg) > pvP[j + 4] * sg) { clean = false; break; }
      int kind = sg == 1 ? K_HS : K_IHS, x = -1;
      if(clean && brk >= 0)
      {
         double nb = ms * brk + bs;
         x = AddPat(kind, pvI[j - 1], brk, brk, -sg, MathMax(brk, pvC[j + 4]), gC[brk], pvP[j + 4], nb - sg * headH, 0);
         AddLn(x, I[0], ms * I[0] + bs, brk, nb);
      }
      else if(clean && InpForming && lim > gN - 1)
      {
         double nb = ms * (gN - 1) + bs;
         x = AddPat(kind, pvI[j - 1], gN - 1, -1, -sg, pvC[j + 4], 0.0, pvP[j + 4], nb - sg * headH, 1);
         AddLn(x, I[0], ms * I[0] + bs, gN - 1, nb);
         SetTrig(x, -sg, ms * gN + bs - sg * 0.1 * A);
      }
      if(x >= 0)
      {
         AddPt(x, I[0], pvP[j], 8); AddPt(x, I[1], pvP[j + 1], 7); AddPt(x, I[2], pvP[j + 2], 9);
         AddPt(x, I[3], pvP[j + 3], 7); AddPt(x, I[4], pvP[j + 4], 10);
      }
   }
}

//+------------------------------------------------------------------+
//| triangles, wedges, rectangles, broadening, channels              |
//+------------------------------------------------------------------+
void FindLines(int j, int cnt)
{
   if(j + cnt > gNP || j < 1) return;
   double hx[], hy[], lx[], ly[];
   ArrayResize(hx, 7); ArrayResize(hy, 7); ArrayResize(lx, 7); ArrayResize(ly, 7);
   int nh = 0, nlw = 0;
   for(int t = 0; t < cnt; t++)
   {
      if(pvT[j + t] == 1) { hx[nh] = pvI[j + t]; hy[nh] = pvP[j + t]; nh++; }
      else { lx[nlw] = pvI[j + t]; ly[nlw] = pvP[j + t]; nlw++; }
   }
   if(nh < 2 || nlw < 2) return;
   int s0 = pvI[j], s1 = pvI[j + cnt - 1], span = s1 - s0;
   if(span < 12) return;
   double mh, bh, ml, bl;
   LinFit(hx, hy, nh, mh, bh);
   LinFit(lx, ly, nlw, ml, bl);
   double rh = 0, rl = 0;
   if(nh > 2) for(int t = 0; t < nh; t++) rh = MathMax(rh, MathAbs(hy[t] - (mh * hx[t] + bh)));
   if(nlw > 2) for(int t = 0; t < nlw; t++) rl = MathMax(rl, MathAbs(ly[t] - (ml * lx[t] + bl)));
   double w0 = (mh * s0 + bh) - (ml * s0 + bl), w1 = (mh * s1 + bh) - (ml * s1 + bl), A = gA[s0];
   if(w0 <= 0 || w1 <= 0 || MathMax(w0, w1) < 3 * A) return;
   double W = MathMax(w0, w1);
   if(rh > 0.12 * W || rl > 0.12 * W) return;
   for(int i = s0; i <= s1; i++)
   {
      double fh = mh * i + bh, fl = ml * i + bl;
      if(gC[i] > fh + 0.1 * W || gC[i] < fl - 0.1 * W || gH[i] > fh + 0.2 * W || gL[i] < fl - 0.2 * W) return;
   }
   int qn = MathMax(3, span / 4);
   for(int part = 0; part < 2; part++)
   {
      int u0 = part == 0 ? s0 : s1 - qn, u1 = part == 0 ? s0 + qn : s1;
      double dl = DBL_MAX, dh = DBL_MAX;
      for(int i = u0; i <= u1; i++) { dl = MathMin(dl, gL[i] - (ml * i + bl)); dh = MathMin(dh, (mh * i + bh) - gH[i]); }
      if(dl > 0.15 * W || dh > 0.15 * W) return;
   }
   double sh = mh * span / W, sl = ml * span / W, ratio = w1 / w0, FLAT = 0.12;
   int kind = -1;
   if(MathAbs(sh) < FLAT && sl > 0.3 && ratio < 0.6) kind = K_ASC;
   else if(MathAbs(sl) < FLAT && sh < -0.3 && ratio < 0.6) kind = K_DESC;
   else if(sh < -0.25 && sl > 0.25 && ratio < 0.55) kind = K_SYM;
   else if(sh > 0.2 && sl > 0.2 && sl > sh && ratio < 0.6) kind = K_RWEDGE;
   else if(sh < -0.2 && sl < -0.2 && sh < sl && ratio < 0.6) kind = K_FWEDGE;
   else if(MathAbs(sh) < FLAT && MathAbs(sl) < FLAT && ratio > 0.75 && ratio < 1.33 && cnt >= 6) kind = K_RECT;
   else if(sh > 0.25 && sl < -0.25 && ratio > 1.6) kind = K_BROAD;
   else if(sh > 0.6 && sl > 0.6 && ratio > 0.8 && ratio < 1.25 && cnt >= 6) kind = K_CHUP;
   else if(sh < -0.6 && sl < -0.6 && ratio > 0.8 && ratio < 1.25 && cnt >= 6) kind = K_CHDN;
   if(kind < 0) return;
   if(kind == K_RWEDGE && !(pvP[j - 1] < ml * s0 + bl)) return;
   if(kind == K_FWEDGE && !(pvP[j - 1] > mh * s0 + bh)) return;
   int lim = s1 + MathMax(5, (int)(0.6 * span));
   int bu = FirstClose(s1 + 1, lim, mh, bh, 1, 0.1 * A);
   int bd = FirstClose(s1 + 1, lim, ml, bl, -1, 0.1 * A);
   int expected = 0;
   if(kind == K_ASC || kind == K_FWEDGE || kind == K_CHDN) expected = 1;
   if(kind == K_DESC || kind == K_RWEDGE || kind == K_CHUP) expected = -1;
   int x = -1;
   if(bu < 0 && bd < 0)
   {
      if(!(InpForming && lim > gN - 1)) return;
      int e = gN - 1;
      x = AddPat(kind, s0, e, -1, expected, pvC[j + cnt - 1], 0.0, 0.0, 0.0, 1);
      AddLn(x, s0, mh * s0 + bh, e, mh * e + bh); AddLn(x, s0, ml * s0 + bl, e, ml * e + bl);
      if(expected >= 0) SetTrig(x, 1, mh * gN + bh + 0.1 * A);
      if(expected <= 0) SetTrig(x, -1, ml * gN + bl - 0.1 * A);
      return;
   }
   int brk, dr;
   if(bd < 0 || (bu >= 0 && bu < bd)) { brk = bu; dr = 1; } else { brk = bd; dr = -1; }
   if(expected != 0 && dr != expected) return;
   double ref = dr == 1 ? mh * brk + bh : ml * brk + bl;
   double tgtH = kind == K_BROAD ? w1 : w0;
   double stop = dr == 1 ? ml * brk + bl : mh * brk + bh;
   if(kind == K_RWEDGE) { stop = hy[0]; for(int t = 1; t < nh; t++) stop = MathMax(stop, hy[t]); }
   if(kind == K_FWEDGE) { stop = ly[0]; for(int t = 1; t < nlw; t++) stop = MathMin(stop, ly[t]); }
   x = AddPat(kind, s0, brk, brk, dr, MathMax(brk, pvC[j + cnt - 1]), gC[brk], stop, ref + dr * tgtH, 0);
   AddLn(x, s0, mh * s0 + bh, brk, mh * brk + bh); AddLn(x, s0, ml * s0 + bl, brk, ml * brk + bl);
}

//+------------------------------------------------------------------+
//| flags and pennants                                               |
//+------------------------------------------------------------------+
void FlagLines(int pe, double pep, int e, int dr, double &mh, double &bh, double &ml, double &bl)
{
   int n = e - pe;
   double xs[], ys[];
   ArrayResize(xs, n); ArrayResize(ys, n);
   for(int t = 0; t < n; t++) { int i = pe + 1 + t; xs[t] = i; ys[t] = dr == 1 ? gL[i] : gH[i]; }
   if(dr == 1)
   {
      mh = -DBL_MAX;
      for(int i = pe + 1; i <= e; i++) mh = MathMax(mh, (gH[i] - pep) / (i - pe));
      bh = pep - mh * pe;
      LinFit(xs, ys, n, ml, bl);
      double sh = DBL_MAX;
      for(int i = pe + 1; i <= e; i++) sh = MathMin(sh, gL[i] - (ml * i + bl));
      bl += sh;
   }
   else
   {
      ml = DBL_MAX;
      for(int i = pe + 1; i <= e; i++) ml = MathMin(ml, (gL[i] - pep) / (i - pe));
      bl = pep - ml * pe;
      LinFit(xs, ys, n, mh, bh);
      double sh = -DBL_MAX;
      for(int i = pe + 1; i <= e; i++) sh = MathMax(sh, gH[i] - (mh * i + bh));
      bh += sh;
   }
}

void FindFlag(int j)
{
   if(!(j + 1 < gNP)) return;
   int ps = pvI[j], pe = pvI[j + 1];
   double psp = pvP[j], pep = pvP[j + 1];
   int dr = pvT[j + 1] == 1 ? 1 : -1;
   int plen = pe - ps;
   double pole = MathAbs(pep - psp), A = gA[ps];
   if(!(plen >= 2 && plen <= 15 && pole >= 5 * A && pole >= 1.5 * plen * A * 0.6)) return;
   int best = -1; bool reachedEnd = false;
   for(int L = 5; L <= 25; L++)
   {
      int e = pe + L;
      if(e + 1 >= gN) { reachedEnd = true; break; }
      double hmax = -DBL_MAX, lmin = DBL_MAX;
      for(int i = pe + 1; i <= e; i++) { hmax = MathMax(hmax, gH[i]); lmin = MathMin(lmin, gL[i]); }
      if(dr == 1 && (hmax > pep || pep - lmin > 0.5 * pole)) break;
      if(dr == -1 && (lmin < pep || hmax - pep > 0.5 * pole)) break;
      best = e;
   }
   if(best < 0) return;
   double mh = 0, bh = 0, ml = 0, bl = 0;
   int fe = -1, nb = -1;
   for(int e = pe + 5; e <= best; e++)
   {
      FlagLines(pe, pep, e, dr, mh, bh, ml, bl);
      int b = e + 1;
      if(b >= gN) break;
      if(dr == 1 && gC[b] > mh * b + bh + 0.1 * A && gC[b] > gH[e]) { fe = e; nb = b; break; }
      if(dr == -1 && gC[b] < ml * b + bl - 0.1 * A && gC[b] < gL[e]) { fe = e; nb = b; break; }
   }
   int form = 0;
   if(fe < 0)
   {
      if(!(InpForming && reachedEnd && best == gN - 2 && best - pe >= 5)) return;
      fe = best; nb = gN - 1;
      FlagLines(pe, pep, fe, dr, mh, bh, ml, bl);
      form = 1;
   }
   double w0 = (mh * pe + bh) - (ml * pe + bl), w1 = (mh * fe + bh) - (ml * fe + bl);
   if(w0 <= 0 || w1 <= 0 || w0 > 0.6 * pole) return;
   int span = fe - pe;
   double sh = mh * span / w0, sl = ml * span / w0;
   int kind;
   if(w1 / w0 < 0.6 && sh * sl < 0) kind = dr == 1 ? K_BPEN : K_SPEN;
   else if(w1 / w0 >= 0.6 && w1 / w0 <= 1.5 && sh * dr < 0 && sl * dr < 0) kind = dr == 1 ? K_BFLAG : K_SFLAG;
   else return;
   int x = -1;
   if(form)
   {
      x = AddPat(kind, ps, nb, -1, dr, pvC[j + 1], 0.0, 0.0, 0.0, 1);
      // next candle confirms if it closes beyond the flag edge (refitted with the latest candle) and the latest candle's extreme
      double m2 = 0, b2 = 0, m3 = 0, b3 = 0;
      FlagLines(pe, pep, gN - 1, dr, m2, b2, m3, b3);
      if(dr == 1) SetTrig(x, 1, MathMax(m2 * gN + b2 + 0.1 * A, gH[gN - 1]));
      else SetTrig(x, -1, MathMin(m3 * gN + b3 - 0.1 * A, gL[gN - 1]));
   }
   else x = AddPat(kind, ps, nb, nb, dr, MathMax(nb, pvC[j + 1]), gC[nb], dr == 1 ? ml * nb + bl : mh * nb + bh, gC[nb] + dr * pole, 0);
   AddPt(x, ps, psp, 11); AddPt(x, pe, pep, dr == 1 ? 12 : 13);
   AddLn(x, pe, mh * pe + bh, nb, mh * nb + bh); AddLn(x, pe, ml * pe + bl, nb, ml * nb + bl); AddLn(x, ps, psp, pe, pep);
}

//+------------------------------------------------------------------+
//| cups and rounding turns (sg 1: cup / rounding bottom,            |
//| sg -1: inverted cup / rounding top) on the current pivots        |
//+------------------------------------------------------------------+
bool QuadFit(const double &xs[], const double &ys[], int n, double &qa, double &qb, double &qc)
{
   double s1 = 0, s2 = 0, s3 = 0, s4 = 0, t0 = 0, t1 = 0, t2 = 0;
   for(int i = 0; i < n; i++)
   {
      double x = xs[i], y = ys[i], x2 = x * x;
      s1 += x; s2 += x2; s3 += x2 * x; s4 += x2 * x2; t0 += y; t1 += x * y; t2 += x2 * y;
   }
   double M[3][4];
   M[0][0] = s4; M[0][1] = s3; M[0][2] = s2; M[0][3] = t2;
   M[1][0] = s3; M[1][1] = s2; M[1][2] = s1; M[1][3] = t1;
   M[2][0] = s2; M[2][1] = s1; M[2][2] = n;  M[2][3] = t0;
   for(int col = 0; col < 3; col++)
   {
      int pv = col;
      for(int r = col + 1; r < 3; r++) if(MathAbs(M[r][col]) > MathAbs(M[pv][col])) pv = r;
      if(pv != col) for(int cc = 0; cc < 4; cc++) { double tmp = M[col][cc]; M[col][cc] = M[pv][cc]; M[pv][cc] = tmp; }
      if(M[col][col] == 0) return false;
      for(int r = 0; r < 3; r++)
      {
         if(r == col) continue;
         double f = M[r][col] / M[col][col];
         for(int cc = col; cc < 4; cc++) M[r][cc] -= f * M[col][cc];
      }
   }
   qa = M[0][3] / M[0][0]; qb = M[1][3] / M[1][1]; qc = M[2][3] / M[2][2];
   return true;
}

void FindCups(int sg)
{
   for(int j = 0; j + 2 < gNP; j++)
   {
      // flipped pivots: price * sg, type * sg
      if(!(pvT[j] * sg == 1 && pvT[j + 1] * sg == -1 && pvT[j + 2] * sg == 1)) continue;
      int Li = pvI[j], Bi = pvI[j + 1], Ri = pvI[j + 2];
      double Lp = pvP[j] * sg, Bp = pvP[j + 1] * sg, Rp = pvP[j + 2] * sg;
      int width = Ri - Li;
      double depth = MathMin(Lp, Rp) - Bp, A = gA[Li];
      if(width < 20 || depth < 3.5 * A) continue;
      if(Rp > Lp + 0.1 * depth || Rp < Lp - 0.15 * depth) continue;
      int n = width + 1;
      double xs[], cc[];
      ArrayResize(xs, n); ArrayResize(cc, n);
      double mean = 0;
      for(int t = 0; t < n; t++) { int i = Li + t; xs[t] = (double)t / width; cc[t] = (FH(i, sg) + FL(i, sg)) / 2; mean += cc[t]; }
      mean /= n;
      double qa, qb, qc;
      if(!QuadFit(xs, cc, n, qa, qb, qc)) continue;
      if(qa <= 0) continue;
      double vx = -qb / (2 * qa), ssr = 0, sst = 0;
      for(int t = 0; t < n; t++) { double pr = qa * xs[t] * xs[t] + qb * xs[t] + qc; ssr += (cc[t] - pr) * (cc[t] - pr); sst += (cc[t] - mean) * (cc[t] - mean); }
      double r2 = 1 - ssr / sst;
      if(r2 < 0.65 || vx < 0.3 || vx > 0.7) continue;
      int low3 = 0;
      for(int i = Li; i <= Ri; i++) if(FL(i, sg) < Bp + depth / 3) low3++;
      if((double)low3 / n < 0.3) continue;
      double rim = MathMax(Lp, Rp);
      bool over = false;
      for(int i = Li; i <= Ri; i++) if(FH(i, sg) > rim + 1e-9) { over = true; break; }
      if(over) continue;
      int lim = Ri + MathMax(5, (int)(0.4 * width));
      int brk = -1, stopAt = MathMin(lim, gN);
      for(int i = Ri + 1; i < stopAt; i++) if(FC(i, sg) > rim + 0.1 * A) { brk = i; break; }
      int x = -1;
      if(brk < 0)
      {
         if(!(InpForming && lim > gN - 1)) continue;
         int e = gN - 1;
         double hl = DBL_MAX;
         for(int i = Ri; i <= e; i++) hl = MathMin(hl, FL(i, sg));
         if(rim - hl > 0.5 * depth) continue;
         x = AddPat(sg == 1 ? K_CUP : K_ICUP, Li, e, -1, sg, pvC[j + 2], 0.0, sg * hl, sg * (rim + depth), 1);
         AddLn(x, Li, sg * rim, e, sg * rim);
         SetTrig(x, sg, sg * (rim + 0.1 * A));
      }
      else
      {
         double hl = DBL_MAX; int hi = Ri;
         for(int i = Ri; i <= brk; i++) if(FL(i, sg) < hl) { hl = FL(i, sg); hi = i; }
         int hlen = brk - Ri;
         if(hlen >= MathMax(3.0, 0.08 * width) && rim - hl >= 0.12 * depth && rim - hl <= 0.5 * depth)
         {
            x = AddPat(sg == 1 ? K_CUP : K_ICUP, Li, brk, brk, sg, MathMax(brk, pvC[j + 2]), gC[brk], sg * hl, sg * (rim + depth), 0);
            AddPt(x, hi, sg * hl, 18);
         }
         else if(hlen <= MathMax(3.0, 0.08 * width) + 2)
            x = AddPat(sg == 1 ? K_RBOT : K_RTOP, Li, brk, brk, sg, MathMax(brk, pvC[j + 2]), gC[brk], sg * (Bp + depth * 0.5), sg * (rim + depth), 0);
         else continue;
         AddLn(x, Li, sg * rim, brk, sg * rim);
      }
      // cup points go first so the handle (added above for confirmed cups) is moved behind them
      int hk = gP[x].np; int hpi = hk > 0 ? gP[x].pi[0] : 0; double hpp = hk > 0 ? gP[x].pp[0] : 0; int hpl = hk > 0 ? gP[x].pl[0] : 0;
      gP[x].np = 0;
      AddPt(x, Li, sg * Lp, 14); AddPt(x, Bi, sg * Bp, sg == 1 ? 16 : 17); AddPt(x, Ri, sg * Rp, 15);
      if(hk > 0) AddPt(x, hpi, hpp, hpl);
      gP[x].cup = 1; gP[x].cupL = Li; gP[x].cupW = width; gP[x].qa = qa * sg; gP[x].qb = qb * sg; gP[x].qc = qc * sg;
   }
}

//+------------------------------------------------------------------+
//| keep one of each overlapping group (earliest confirmed wins)     |
//+------------------------------------------------------------------+
bool Before(int a, int b)
{
   if(gP[a].forming != gP[b].forming) return gP[a].forming < gP[b].forming;
   if(gP[a].conf != gP[b].conf) return gP[a].conf < gP[b].conf;
   int la = gP[a].e - gP[a].s, lb = gP[b].e - gP[b].s;
   if(la != lb) return la > lb;
   return a < b;
}
void Dedupe()
{
   int ord[];
   ArrayResize(ord, gNPat);
   for(int i = 0; i < gNPat; i++) ord[i] = i;
   for(int i = 1; i < gNPat; i++)
   {
      int v = ord[i], k = i - 1;
      while(k >= 0 && Before(v, ord[k])) { ord[k + 1] = ord[k]; k--; }
      ord[k + 1] = v;
   }
   for(int u = 0; u < gNPat; u++)
   {
      int r = ord[u]; bool ok = true;
      for(int w = 0; w < u && ok; w++)
      {
         int q = ord[w];
         if(!gP[q].keep || gP[q].kind != gP[r].kind) continue;
         int ov = MathMin(gP[q].e, gP[r].e) - MathMax(gP[q].s, gP[r].s);
         if(ov > 0.4 * MathMin(gP[q].e - gP[q].s, gP[r].e - gP[r].s)) ok = false;
      }
      gP[r].keep = ok ? 1 : 0;
   }
   // patterns in the warm-up candles still block overlapping ones (so nothing pops up when they scroll away) but are not drawn
   for(int r = 0; r < gNPat; r++) if(gP[r].s < gWarm) gP[r].keep = 0;
}

bool KindOn(int k)
{
   if(k <= K_IHS) return InpTops;
   if(k == K_ASC || k == K_DESC || k == K_SYM || k == K_RECT || k == K_BROAD) return InpTriangles;
   if(k == K_RWEDGE || k == K_FWEDGE || k == K_CHUP || k == K_CHDN) return InpWedges;
   if(k >= K_BFLAG && k <= K_SPEN) return InpFlags;
   return InpCups;
}

void Detect()
{
   gNPat = 0;
   double scales[4] = { 1.5, 2.0, 3.0, 4.5 };
   int a0 = InpSize == SIZE_LARGE ? 2 : 0, a1 = InpSize == SIZE_SMALL ? 1 : 3;
   for(int si = a0; si <= a1; si++)
   {
      ZigZag(scales[si]);
      for(int j = 0; j < gNP; j++)
      {
         FindDouble(j);
         FindFive(j);
         for(int cnt = 5; cnt <= 7; cnt++) FindLines(j, cnt);
         FindFlag(j);
      }
      FindCups(1);
      FindCups(-1);
   }
   Dedupe();
   // outcome after the breakout: which came first, target or stop
   for(int x = 0; x < gNPat; x++)
   {
      if(!gP[x].keep || gP[x].forming) continue;
      int hz = MathMax(20, 3 * (gP[x].e - gP[x].s)), d = gP[x].dir;
      for(int i = gP[x].conf + 1; i < gN && i <= gP[x].conf + hz; i++)
      {
         bool st = d == 1 ? gL[i] <= gP[x].stop : gH[i] >= gP[x].stop;
         bool tg = d == 1 ? gH[i] >= gP[x].target : gL[i] <= gP[x].target;
         if(st) { gP[x].res = -1; gP[x].resBar = i; break; }
         if(tg) { gP[x].res = 1; gP[x].resBar = i; break; }
      }
   }
}

//+------------------------------------------------------------------+
//| drawing                                                          |
//+------------------------------------------------------------------+
datetime TT(int i)
{
   if(i < gN) return gT[MathMax(0, i)];
   return gTLive + (datetime)((i - gN) * PeriodSeconds(_Period));
}
color Blend(color c, color bg, double w)   // w of c, rest background
{
   int ci = (int)c, bi = (int)bg;
   int r = (int)((ci & 0xFF) * w + (bi & 0xFF) * (1 - w));
   int g = (int)(((ci >> 8) & 0xFF) * w + ((bi >> 8) & 0xFF) * (1 - w));
   int b = (int)(((ci >> 16) & 0xFF) * w + ((bi >> 16) & 0xFF) * (1 - w));
   return (color)(r | (g << 8) | (b << 16));
}
string NewName() { return InpPrefix + "_" + IntegerToString(gObj++); }
void Line(int x1, double y1, int x2, double y2, color c, int width, int style)
{
   LineT(x1, y1, x2, y2, c, width, style, "");
}
void LineT(int x1, double y1, int x2, double y2, color c, int width, int style, string tip)
{
   string nm = NewName();
   if(!ObjectCreate(0, nm, OBJ_TREND, 0, TT(x1), y1, TT(x2), y2)) return;
   if(tip != "") ObjectSetString(0, nm, OBJPROP_TOOLTIP, tip);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, style);
   ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}
void Text(int x, double y, string txt, color c, int size, ENUM_ANCHOR_POINT anchor, string tip)
{
   string nm = NewName();
   if(!ObjectCreate(0, nm, OBJ_TEXT, 0, TT(x), y)) return;
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetString(0, nm, OBJPROP_FONT, "Arial");
   ObjectSetString(0, nm, OBJPROP_TOOLTIP, tip);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, anchor);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}
void Box(int x1, double y1, int x2, double y2, color c, bool dashed)
{
   string nm = NewName();
   if(!ObjectCreate(0, nm, OBJ_RECTANGLE, 0, TT(x1), y1, TT(x2), y2)) return;
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_FILL, !dashed);
   ObjectSetInteger(0, nm, OBJPROP_BACK, true);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, dashed ? STYLE_DOT : STYLE_SOLID);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}
void Arrow(int i, int dir, color c)
{
   string nm = NewName();
   double y = dir == 1 ? gL[i] : gH[i];
   if(!ObjectCreate(0, nm, dir == 1 ? OBJ_ARROW_UP : OBJ_ARROW_DOWN, 0, TT(i), y)) return;
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, dir == 1 ? ANCHOR_TOP : ANCHOR_BOTTOM);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}
void Mark(int i, double y, bool hit, color c, string tip)   // check sign = target first, stop sign = stop first
{
   string nm = NewName();
   if(!ObjectCreate(0, nm, hit ? OBJ_ARROW_CHECK : OBJ_ARROW_STOP, 0, TT(i), y)) return;
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_BOTTOM);
   ObjectSetString(0, nm, OBJPROP_TOOLTIP, tip);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}
string Px(double p) { return DoubleToString(p, _Digits); }

// "confirms on a close above X" / "below Y" / "above X or below Y"
string TrigText(int x, bool shortForm)
{
   string up = gP[x].tUp != 0 ? (shortForm ? "above " : "a close above ") + Px(gP[x].tUp) : "";
   string dn = gP[x].tDn != 0 ? (shortForm ? "below " : "a close below ") + Px(gP[x].tDn) : "";
   if(up != "" && dn != "") return (shortForm ? "confirms " : "confirms on ") + up + " or " + dn;
   if(up != "") return (shortForm ? "confirms " : "confirms on ") + up;
   if(dn != "") return (shortForm ? "confirms " : "confirms on ") + dn;
   return "";
}

void DrawPattern(int x)
{
   int k = gP[x].kind, form = gP[x].forming, dir = gP[x].dir;
   bool flag = k >= K_BFLAG && k <= K_SPEN;
   color bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   color dc = dir == 1 ? InpBull : dir == -1 ? InpBear : InpLine;
   // area: from the first key point (or first line point) to the breakout / latest candle
   int a = gP[x].np > 0 ? gP[x].pi[0] : gP[x].lx1[0];
   if(gP[x].nl > 0) a = MathMin(a, gP[x].lx1[0]);
   int b = form ? gN - 1 : gP[x].brk;
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = a; i <= b; i++) { hi = MathMax(hi, gH[i]); lo = MathMin(lo, gL[i]); }
   Box(a, hi, form ? gN : b, lo, form ? Blend(dc, bg, 0.6) : Blend(dc, bg, 0.16), form);
   int style = form ? STYLE_DASH : STYLE_SOLID;
   for(int l = 0; l < gP[x].nl; l++)
   {
      int x2 = gP[x].lx2[l]; double y2 = gP[x].ly2[l];
      if(form && x2 == gN - 1 && !(flag && l == 2))   // extend forming lines to the live candle
      {
         y2 = gP[x].ly1[l] + (y2 - gP[x].ly1[l]) * (double)(gN - gP[x].lx1[l]) / MathMax(1, x2 - gP[x].lx1[l]);
         x2 = gN;
      }
      Line(gP[x].lx1[l], gP[x].ly1[l], x2, y2, (flag && l == 2) ? Blend(InpLine, bg, 0.5) : InpLine, 2, style);
   }
   if(gP[x].cup)   // fitted curve of the cup
   {
      int steps = 12; int px = gP[x].cupL; double py = gP[x].qc;
      for(int t = 1; t <= steps; t++)
      {
         double u = (double)t / steps;
         int ix = gP[x].cupL + (int)MathRound(u * gP[x].cupW);
         double iy = gP[x].qa * u * u + gP[x].qb * u + gP[x].qc;
         Line(px, py, ix, iy, InpLine, 1, STYLE_DOT);
         px = ix; py = iy;
      }
   }
   if(InpPoints)
      for(int p = 0; p < gP[x].np; p++)
      {
         int lab = gP[x].pl[p];
         if(lab >= 11 && lab <= 13) continue;   // the pole line speaks for itself; its labels crowd short flags
         int i = gP[x].pi[p]; bool top = MathAbs(gH[i] - gP[x].pp[p]) <= MathAbs(gL[i] - gP[x].pp[p]);
         Text(i, gP[x].pp[p], PLAB[lab], gTxt, InpFont, top ? ANCHOR_LOWER : ANCHOR_UPPER, PLAB[lab]);
      }
   string nm = KNAME[k] + (form ? " (forming)" : "");
   string tip = KNAME[k] + ", from " + TimeToString(TT(a)) + (form ? ", not confirmed yet" : ", broke out " + TimeToString(TT(b)));
   if(!form && gP[x].conf > b) tip += ", confirmed " + TimeToString(TT(gP[x].conf)) + " when its last swing was complete";
   // name at the left edge, on the side away from the first labelled point (tops are labelled above, so the name goes below)
   bool below = false;
   if(InpPoints && gP[x].np > 0)
   {
      int i0 = gP[x].pi[0];
      if(!(gP[x].pl[0] >= 11 && gP[x].pl[0] <= 13)) below = MathAbs(gH[i0] - gP[x].pp[0]) <= MathAbs(gL[i0] - gP[x].pp[0]);
   }
   Text(a, below ? lo : hi, nm, form ? gTxt : dc, InpFont + 1, below ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER, tip);
   if(form)
   {
      string tt = TrigText(x, false);
      if(tt != "") Text(gN, gP[x].tDn != 0 && gP[x].tUp == 0 ? gP[x].tDn : (gP[x].tUp != 0 ? gP[x].tUp : gC[gN - 1]), "  " + tt, gTxt, InpFont, ANCHOR_LEFT, KNAME[k] + " forming");
      return;
   }
   Arrow(b, dir, dc);
   if(InpTargets && gP[x].target != 0)
   {
      int len = MathMax(10, (b - a) / 2), e2 = b + len;
      string th = InpOutcome && gP[x].res == 1 ? ", hit first" : "", sh = InpOutcome && gP[x].res == -1 ? ", hit first" : "";
      Line(b, gP[x].target, e2, gP[x].target, dc, 1, STYLE_DASH);
      Line(b, gP[x].stop, e2, gP[x].stop, Blend(gTxt, bg, 0.6), 1, STYLE_DOT);
      Text(e2, gP[x].target, " target " + Px(gP[x].target) + th, dc, InpFont, ANCHOR_LEFT, KNAME[k] + " target (measured move)");
      Text(e2, gP[x].stop, " stop " + Px(gP[x].stop) + sh, gTxt, InpFont, ANCHOR_LEFT, KNAME[k] + " stop (other side of the pattern)");
   }
   if(InpOutcome && gP[x].res != 0)
   {
      bool hit = gP[x].res == 1;
      Mark(gP[x].resBar, hit ? gP[x].target : gP[x].stop, hit, hit ? dc : gTxt,
           KNAME[k] + (hit ? ": target reached first, " : ": stop reached first, ") + TimeToString(TT(gP[x].resBar)));
   }
}

// what price usually did after this kind of pattern: middle path (dashed) and middle half (dotted), from the confirmation candle
// over up to twice the pattern's length, scaled by the distance to its target
void Projection(int x)
{
   int k = gP[x].kind, dir = gP[x].dir, c0i = gP[x].conf, L = gP[x].e - gP[x].s;
   double D = MathAbs(gP[x].target - gP[x].entry), c0 = gC[c0i];
   if(D <= 0 || L < 4 || dir == 0) return;
   color bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   color dc = dir == 1 ? InpBull : InpBear;
   color cm = Blend(dc, bg, 0.55), cb = Blend(dc, bg, 0.35);
   string tip = "Typical path after a " + KNAME[k] + ": " + (PJPOOL[k] == 1 ? "from " + IntegerToString(PJN[k]) + " similar past patterns on gold" : IntegerToString(PJN[k]) + " past cases on gold")
                + ". Half the time price stayed between the dotted lines; the dashed line is the middle. "
                + IntegerToString((int)MathRound(100 * PJWAY[k])) + "% had moved the pattern's way after twice its length (random entries: "
                + IntegerToString((int)MathRound(100 * PJRAND[k])) + "%). A range to expect, not a forecast.";
   int px = c0i; double p25 = c0, p50 = c0, p75 = c0;
   int steps = (int)MathRound(MathMax(0.25, MathMin(2.0, InpProjLen)) * (PJ_STEPS - 1) / 2.0);
   for(int t = 1; t <= steps; t++)
   {
      int ix = c0i + (int)MathFloor(t * 2.0 * L / (PJ_STEPS - 1) + 0.5);
      double q25 = c0 + dir * D * PJ25[k * PJ_STEPS + t], q50 = c0 + dir * D * PJ50[k * PJ_STEPS + t], q75 = c0 + dir * D * PJ75[k * PJ_STEPS + t];
      LineT(px, p25, ix, q25, cb, 1, STYLE_DOT, tip);
      LineT(px, p75, ix, q75, cb, 1, STYLE_DOT, tip);
      LineT(px, p50, ix, q50, cm, 1, STYLE_DASH, tip);
      px = ix; p25 = q25; p50 = q50; p75 = q75;
   }
   Text(px, p50, " typical", cb, MathMax(6, InpFont - 1), ANCHOR_LEFT, tip);
}

void Notify(string key, string msg)
{
   for(int i = 0; i < gNAlerted; i++) if(gAlerted[i] == key) return;
   ArrayResize(gAlerted, gNAlerted + 1, 64); gAlerted[gNAlerted++] = key;
   if(gFirst) return;   // no alerts for what was already on the chart when it loaded
   string full = _Symbol + " " + StringSubstr(EnumToString(_Period), 7) + ": " + msg;
   Alert(full);
   if(InpPush) SendNotification(full);
}

// panel rows are collected first so the background can be sized to the text
string gRowT[];
color  gRowC[];
int    gRows = 0;
void AddRow(string txt, color c)
{
   ArrayResize(gRowT, gRows + 1, 8); ArrayResize(gRowC, gRows + 1, 8);
   gRowT[gRows] = txt; gRowC[gRows] = c; gRows++;
}
void DrawPanel()
{
   if(gRows == 0) return;
   TextSetFont("Arial", -10 * (InpFont + 1));
   uint w = 0, h = 0, tw = 0, th = 0;
   for(int r = 0; r < gRows; r++) { TextGetSize(gRowT[r], tw, th); w = MathMax(w, tw); h = MathMax(h, th); }
   int lh = (int)h + 4, pad = 8, mg = 10, W = (int)w + 2 * pad, H = gRows * lh + 2 * pad - 4;
   bool right = InpCorner == CORNER_RIGHT_UPPER || InpCorner == CORNER_RIGHT_LOWER;
   bool lower = InpCorner == CORNER_LEFT_LOWER || InpCorner == CORNER_RIGHT_LOWER;
   color bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   string nm = InpPrefix + "_panelbg";
   if(ObjectCreate(0, nm, OBJ_RECTANGLE_LABEL, 0, 0, 0))
   {
      ObjectSetInteger(0, nm, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, right ? mg + W : mg);   // a rectangle label is placed by its upper left corner
      ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, lower ? mg + H : mg);
      ObjectSetInteger(0, nm, OBJPROP_XSIZE, W);
      ObjectSetInteger(0, nm, OBJPROP_YSIZE, H);
      ObjectSetInteger(0, nm, OBJPROP_BGCOLOR, bg);
      ObjectSetInteger(0, nm, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, nm, OBJPROP_COLOR, Blend(gTxt, bg, 0.3));
      ObjectSetInteger(0, nm, OBJPROP_BACK, false);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   }
   ENUM_ANCHOR_POINT anc = right ? (lower ? ANCHOR_RIGHT_LOWER : ANCHOR_RIGHT_UPPER) : (lower ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER);
   for(int r = 0; r < gRows; r++)
   {
      nm = InpPrefix + "_panel" + IntegerToString(r);
      if(!ObjectCreate(0, nm, OBJ_LABEL, 0, 0, 0)) continue;
      ObjectSetInteger(0, nm, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, nm, OBJPROP_ANCHOR, anc);
      ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, mg + pad);
      ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, mg + pad + (lower ? gRows - 1 - r : r) * lh);
      ObjectSetString(0, nm, OBJPROP_TEXT, gRowT[r]);
      ObjectSetString(0, nm, OBJPROP_FONT, "Arial");
      ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, InpFont + 1);
      ObjectSetInteger(0, nm, OBJPROP_COLOR, gRowC[r]);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   }
}

int Horizon(int x) { return MathMax(20, 3 * (gP[x].e - gP[x].s)); }

void Redraw()
{
   ObjectsDeleteAll(0, InpPrefix + "_");
   gObj = 0;
   color bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   gTxt = InpText != clrNONE ? InpText : Blend((color)ChartGetInteger(0, CHART_COLOR_FOREGROUND), bg, 0.75);
   int wins = 0, losses = 0, total = 0;
   for(int x = 0; x < gNPat; x++) if(gP[x].keep && !gP[x].forming && KindOn(gP[x].kind)) { total++; if(gP[x].res == 1) wins++; if(gP[x].res == -1) losses++; }
   int lastIdx = -1;
   // the most recent confirmed patterns, then every forming one on top
   for(int pass = 0; pass < 2; pass++)
      for(int x = gNPat - 1; x >= 0; x--)
      {
         if(!gP[x].keep || !KindOn(gP[x].kind)) continue;
         if(pass == 0 && !gP[x].forming)
         {
            int rank = 0;
            for(int y = 0; y < gNPat; y++) if(gP[y].keep && !gP[y].forming && KindOn(gP[y].kind) && gP[y].conf > gP[x].conf) rank++;
            if(rank >= InpShowLast) continue;
            DrawPattern(x);
            if(InpProj && rank < InpProjLast) Projection(x);
            if(lastIdx < 0 || gP[x].conf > gP[lastIdx].conf) lastIdx = x;
            if(InpAlertConfirm && gP[x].conf == gN - 1)
            {
               int ago = gN - 1 - gP[x].brk;
               string when = ago > 0 ? " " + IntegerToString(ago) + (ago == 1 ? " candle ago" : " candles ago") + " at " + Px(gP[x].entry) + ", now " + Px(gC[gN - 1]) : " at " + Px(gP[x].entry);
               Notify("C" + IntegerToString(gP[x].kind) + " " + TimeToString(TT(gP[x].s)) + " " + TimeToString(TT(gP[x].brk)),
                      KNAME[gP[x].kind] + " confirmed, broke " + (gP[x].dir == 1 ? "up" : "down") + when
                      + ", target " + Px(gP[x].target) + ", stop " + Px(gP[x].stop));
            }
         }
         if(pass == 1 && gP[x].forming && InpForming)
         {
            DrawPattern(x);
            if(InpAlertForming)
            {
               string tt = TrigText(x, true);
               Notify("F" + IntegerToString(gP[x].kind) + " " + TimeToString(TT(gP[x].s)),
                      KNAME[gP[x].kind] + " forming since " + TimeToString(TT(gP[x].s)) + (tt != "" ? ", " + tt : ""));
            }
         }
      }
   if(InpPanel)
   {
      gRows = 0;
      AddRow("Gold Patterns: " + IntegerToString(total) + " confirmed in the last " + IntegerToString(gN - gWarm) + " candles", gTxt);
      if(wins + losses > 0)
         AddRow("Target hit first " + IntegerToString(wins) + ", stop first " + IntegerToString(losses)
                + " (" + IntegerToString((int)MathRound(100.0 * wins / (wins + losses))) + "% targets)", gTxt);
      if(lastIdx >= 0)
      {
         int r = gP[lastIdx].res;
         string st = r == 1 ? ", target hit" : r == -1 ? ", stop hit" : gP[lastIdx].conf + Horizon(lastIdx) < gN - 1 ? ", neither hit in time" : ", still open";
         AddRow("Latest: " + KNAME[gP[lastIdx].kind] + ", broke " + (gP[lastIdx].dir == 1 ? "up " : "down ") + TimeToString(TT(gP[lastIdx].brk)) + st,
                gP[lastIdx].dir == 1 ? InpBull : InpBear);
      }
      int shown = 0;
      for(int x = gNPat - 1; x >= 0 && shown < 4; x--)
         if(gP[x].keep && gP[x].forming && KindOn(gP[x].kind) && InpForming)
         {
            string tt = TrigText(x, true);
            AddRow("Forming: " + KNAME[gP[x].kind] + (tt != "" ? ", " + tt : ""), InpLine);
            shown++;
         }
      if(shown == 0 && InpForming) AddRow("Nothing forming right now", gTxt);
      DrawPanel();
   }
   ChartRedraw(0);
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   ArraySetAsSeries(time, false); ArraySetAsSeries(high, false); ArraySetAsSeries(low, false); ArraySetAsSeries(close, false);
   if(rates_total < 60) return(rates_total);
   int last = rates_total - 2;                     // last closed candle
   if(time[last] == gLastBar && prev_calculated > 0) return(rates_total);
   gLastBar = time[last];
   gTLive = time[rates_total - 1];
   int want = MathMax(200, InpMaxBars);
   int start = MathMax(0, last + 1 - want - WARMUP);   // extra candles in front settle the ATR and swings
   gN = last + 1 - start;
   gWarm = MathMax(0, gN - want);
   ArrayResize(gH, gN); ArrayResize(gL, gN); ArrayResize(gC, gN); ArrayResize(gA, gN); ArrayResize(gT, gN);
   for(int i = 0; i < gN; i++) { gH[i] = high[start + i]; gL[i] = low[start + i]; gC[i] = close[start + i]; gT[i] = time[start + i]; }
   CalcATR();
   Detect();
   Redraw();
   gFirst = false;
   return(rates_total);
}
//+------------------------------------------------------------------+
