// Build check for v2 lessons: nothing is asked before it is taught.
// Each question has c (the card it follows) and w (phrases it relies on). Every phrase must appear in the main text of
// cards 0..c (heading, points, formula, table, example, quote; never «جزئیات بیشتر»), at least one in card c itself
// (written answers may sum up earlier cards), and every card needs at least one question.
const C = require('../../audit/load.js');
const norm = s => String(s).replace(/[⁦-⁩‎‏]/g, '').replace(/‌/g, '').replace(/ي/g, 'ی').replace(/ك/g, 'ک')
  .replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)).replace(/[٠-٩]/g, d => '٠١٢٣٤٥٦٧٨٩'.indexOf(d)).replace(/\s+/g, ' ').trim();
const main = c => norm([c.h, ...(c.b || []), c.f || '', c.ex || '', c.qt || '', ...(c.tb ? [...c.tb.h, ...c.tb.r.flat()] : [])].join(' \n '));
let bad = 0, nl = 0, nx = 0;
const err = (l, m) => { bad++; console.log(`✗ ${l.id} ${m}`); };
for (const u of C.UNITS) for (const l of u.lessons) {
  if (!l.v2) continue;
  nl++;
  const txt = l.cards.map(main), per = l.cards.map(() => 0);
  l.ex.forEach((x, i) => {
    nx++;
    const tag = `#${i} «${String(x.q).slice(0, 50)}»`;
    if (!Number.isInteger(x.c) || x.c < 0 || x.c >= l.cards.length) return err(l, `${tag}: no valid card index c`);
    if (!Array.isArray(x.w) || !x.w.length) return err(l, `${tag}: no phrases w`);
    per[x.c]++;
    const upto = txt.slice(0, x.c + 1).join(' \n ');
    x.w.forEach(p => { if (!upto.includes(norm(p))) err(l, `${tag}: «${p}» is not taught in cards 1..${x.c + 1}`); });
    if (x.t !== 'own' && !x.w.some(p => txt[x.c].includes(norm(p)))) err(l, `${tag}: none of its phrases is on card ${x.c + 1}`);
  });
  per.forEach((n, i) => { if (!n) err(l, `card ${i + 1} «${l.cards[i].h}» has no question`); });
  l.cards.forEach((c, i) => { const n = norm([...(c.b || []), c.ex || ''].join(' ')).split(' ').length; if (n > 110) err(l, `card ${i + 1} «${c.h}» is long (${n} words)`); });
}
console.log(bad ? `check_taught: ${bad} problem(s) in ${nl} v2 lessons` : `check_taught: OK (${nl} v2 lessons, ${nx} questions, all taught before asked)`);
process.exit(bad ? 1 : 0);
