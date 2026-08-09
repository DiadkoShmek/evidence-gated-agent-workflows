# Артур Онисько — надійність AI-workflow та операторських систем

Я беру один нечіткий або ненадійний процес і перетворюю його на малий
перевірюваний контур:

`вхід → рішення → межа повноважень → виконання → receipt → людський handoff`

Моя роль — не обіцяти «автономність» словами. Я формую контракт, координую AI
coding agents, перевіряю реалізацію hostile-тестами та залишаю власнику
відтворюваний доказ того, що система зробила, чого не зробила і де зупинилась.

## Перший оплачуваний етап

**П’ять робочих днів, один workflow, один named owner, один вимірюваний критерій.**

- audit і карта failure modes: **$300–700**;
- audit + обмежений proof of concept: **$700–1,500**;
- більша реалізація оцінюється лише після перевіреного першого етапу.

Результат: карта процесу, typed input/output contract, один runnable slice,
hostile cases, decision trace, відомі межі, rollback/handoff і короткий план
наступного спринту. Якщо безпечний proof неможливий у погодженій межі,
результатом буде чесний hold report із точним blocker-ом, а не false-success.

## Що можна перевірити зараз

- публічний Python reference для evidence-gated рішень і bounded async polling;
- відмова від promotion на missing, stale або conflicting evidence;
- persisted request fingerprint, bounded retries та explicit terminal states;
- synthetic stress proof без network access та зовнішніх дій;
- відтворення однією командою: `python3 run_proof.py`.

Код і інструкція відтворення зафіксовані на exact public commit `f60c8a8`:
<https://github.com/DiadkoShmek/evidence-gated-agent-workflows/tree/f60c8a811088a72ca69fe17e5e1c5d3165303ad4>

## Де це корисно

- внутрішня AI/workflow automation;
- operator-assist і reviewable approval flows;
- reliability layer для інтеграцій, агентів та async jobs;
- контроль replay, stale evidence, partial failure і duplicate effects;
- технічний handoff між власником процесу, інженерами й оператором.

## Доказова межа

Публічні матеріали доводять локальні synthetic reference workflows і тести.
Вони не доводять production deployment, роботу із закритими даними, SOC/IR,
військову інтеграцію, прибуток клієнта або senior commercial tenure. Жодної
live mutation, credential access чи зовнішньої дії без окремої письмової
влади власника системи.

Українська — вільно. Англійська — письмово з AI-assisted translation;
spoken/listening обмежені. Доступність — 20–30 годин на тиждень,
remote/async-first.

## Одне питання для старту

Який один workflow зараз коштує вашій команді найбільше ручного часу або дає
найдорожчий повторюваний збій — і який факт через п’ять днів доведе, що перший
slice був корисним?
