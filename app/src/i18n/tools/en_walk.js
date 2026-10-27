// Shared by the build tools and (copied) by the app: which strings get translated and how they are keyed.
const LETTERS = /[\u0620-\u064A\u0671-\u06D3\u06FA-\u06FF]/;
const PERS = /[\u0600-\u06FF]/;
function enKey(s) { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(36) + s.length.toString(36); }
function enDigits(s) { return s.replace(/[۰-۹]/g, d => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/٬/g, ",").replace(/٫/g, ".").replace(/٪/g, "%").replace(/،/g, ",").replace(/؛/g, ";").replace(/؟/g, "?").replace(/«/g, "“").replace(/»/g, "”"); }
// visit(obj, fn): fn(str, parent, key) for every string reachable from obj (arrays and plain objects only)
function enVisit(o, fn, seen = new Set()) {
  if (!o || typeof o !== "object" || seen.has(o)) return; seen.add(o);
  for (const k of Object.keys(o)) { const v = o[k]; if (k === "w") continue; /* build-check phrases, never shown */ if (typeof v === "string") { if (PERS.test(v)) fn(v, o, k); } else if (v && typeof v === "object") enVisit(v, fn, seen); }
}
module.exports = { LETTERS, PERS, enKey, enDigits, enVisit };
