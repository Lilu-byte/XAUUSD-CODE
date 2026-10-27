// ═════════════ simple mode: every lesson card retold in plain words, with an everyday example
// S(lessonId, ...cards) in card order. sp(bullets, example, {h, f: keep formula, tb: keep table})
const SIMPLE = {};
const S = (id, ...cs) => { SIMPLE[id] = cs; };
const sp = (b, ex, o) => Object.assign({ b, ex }, o || {});
