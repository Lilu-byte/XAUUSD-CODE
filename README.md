# FIS - FLM

A self-study kit, mostly in Persian, for fundamental investing on the Tehran Stock Exchange and Farabourse using public codal.ir reports (**FIS**, Fundamental Investing System), together with investor psychology and personal finance (**FLM**, Financial Life Management). It follows the dividend-first approach that Dr. Bardia Khosravani teaches (roseoj.com). He did not make or endorse these materials.

> **Educational only, not investment advice.** No method guarantees a profit. Check every number against the latest codal.ir report before you act on it.

مجموعهٔ خودآموز تحلیل بنیادی بورس ایران با گزارش‌های کدال (FIS) و مدیریت مالی و روان‌شناسی سرمایه‌گذار (FLM). این مطالب فقط آموزشی است و توصیهٔ سرمایه‌گذاری نیست.

## Contents

| Folder | What is in it |
|---|---|
| `curriculum/` | The study guide as `FIS-FLM-study-guide.pdf` and `.docx`, 45 pages in 9 sections from beginner to independent analyst. The slide deck as `FIS-FLM-slides.pdf` and `.pptx` (30 slides, with a key-points slide and a common-mistakes slide for each section). `FIS-valuation-model.xlsx` is a linked three-statement model with DCF, sensitivity and EV/EBITDA, set up for an example company. |
| `app/` | «کدال‌خوان», a game-style learning app. `kodalkhan.html` is the whole app in one file: open it in a browser and progress is saved in that browser. It has 13 halls of lessons, practice, case files, a glossary, an FIS calculator, a simple mode and an English version (switch it in Profile). `previews/` holds screenshots. |
| `app/src/` | Source for the app. Lesson content is in `c0.js` … `c7.js`, `ck.js` (the FIS dividend-first hall), `v2_h12.js` (the rebuilt halls 1-2) and `simple/`. English text is in `en_ui.js`, `en_c.js` and `i18n/`. Run `python3 build.py` (needs Node) to check that every question is taught before it is asked and to rebuild `kodalkhan-publish-source.html`. The translation helper scripts under `i18n/tools/` still contain the paths of the machine they were written on. |
| `prompts/` | `khosravani-sources-prompt.md` is a prompt for collecting Dr. Khosravani's public teachings (videos, Telegram, papers) to extend the lessons. |
| `examples/` | A saved codal.ir page: the 9-month statement of the stock fund «جوانه کوچک گندم» (period to 1405/06/31). It is used as a report-reading example. |

## Online versions

- Study guide (Claude Doc, the most recent version of the text): https://claude.ai/artifact/XPmSdKXgRt4VAYWLtM86SU
- Slide deck: https://claude.ai/artifact/6bSWPKEA2B7Waa7PRgcEQs

These links are private to their owner unless they are shared.

## Not included

- Dr. Khosravani's 1405 FIS scoring paper (Journal of Accounting and Management Vision, jamv.ir). It is his published work, so read it at the journal rather than from a copy here.
- Raw transcripts of his videos and Telegram posts. These are kept on a personal PC, not in this repository.

## Notes

- codal.ir could not be reached while these were made. Report names, deadlines and rules that could not be checked are marked «(بررسی کنید)» ("please check").
- The `.pptx` needs the free Vazirmatn font to look like the PDF.
