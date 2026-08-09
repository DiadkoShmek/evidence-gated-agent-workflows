# Артур Онисько — надійність AI-workflow та операторських систем

Я беру один нечіткий або ненадійний процес і перетворюю його на малий
перевірюваний контур:

`вхід → рішення → межа повноважень → виконання → receipt → людський handoff`

Моя роль — не обіцяти «автономність» словами. Я формую контракт, координую AI
coding agents, перевіряю реалізацію hostile-тестами та залишаю власнику
відтворюваний доказ того, що система зробила, чого не зробила і де зупинилась.

## Перший оплачуваний етап

**3–5 робочих днів, один workflow, один named owner, один вимірюваний критерій: $1,500 fixed-scope sprint.**

Перший оплачуваний крок — лише цей fixed sprint. Більша реалізація може бути
окремо описана лише після письмового evidence першого етапу; вона не включена,
не оцінена і не обіцяна цим brief.

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

Код і інструкція відтворення доступні в public repository; локальна команда
`python3 run_proof.py` перевіряє checked-in synthetic proof без network access
чи зовнішніх дій.

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
