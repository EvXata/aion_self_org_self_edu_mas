# AION Populations — само-организующиеся, само-обучающиеся популяции агентов

> Выращивайте популяцию агентов, которая сама себя организует, сама изобретает улучшения —
> и, что обычно пропускают, **сертифицирует, какие улучшения реально работают против внешнего
> якоря, а не «оценивает сама себя».**

[![ci](https://github.com/EvXata/aion_self_org_self_edu_mas/actions/workflows/ci.yml/badge.svg)](https://github.com/EvXata/aion_self_org_self_edu_mas/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![promotions: external-anchor gated](https://img.shields.io/badge/promotions-external--anchor%20gated-blue)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/EvXata/aion_self_org_self_edu_mas)
**Sandbox по умолчанию · anchor-gate по умолчанию · перед масштабированием прочитайте [SAFETY.md](SAFETY.md).**

**Consciousness-OS** оживляет **одного** агента. **AION Populations — это их общество.**

---

## Чем AION Populations отличается

Большинство демо «само-улучшающихся агентов» оценивают сами себя — и дрейфуют. Передовые
оценщики предупреждают о том же: в *Frontier Risk Report* (METR, 2026) признаётся, что
самостоятельно выставленные оценки поведения агентов могут вводить в заблуждение (компании
переобучаются под собственные детекторы; проверяющие смягчают невыгодные выводы). AION Populations
построен вокруг единственного вывода, который выдерживает любой разбор в его исследовательской
родословной:

> **Само-оценивающиеся системы дрейфуют. Связывающее ограничение — внешний якорь истины (ground-truth).**

Поэтому в AION Populations **ни один механизм не «промоутится», пока не пройдёт статистически
валидную, FDR-контролируемую, кросс-валидированную проверку против ВАШЕГО якоря.** Этот гейт
включён по умолчанию.

## Что вы получаете (дашборд из 5 секций)

| ① Запущенные популяции | ② Само-организация | ③ Само-обучение | ④ Настройки | ⑤ Social |
|---|---|---|---|---|
| история прогонов + сертифицированный каталог *(живые эволюционирующие популяции: [роадмап](docs/MIGRATION.md))* | отбор, мутация, видообразование, поиск сигналов, маркетплейсы | харнесс сертификации (multi-seed FDR + перестановочный тест + репликация) + anchor-gate | подключите свой якорь, адаптеры, лимиты безопасности | `aionpop share` → **подписанная** автономная карточка (`aionpop verify`) |

## Демо за 60 секунд (без настройки, без якоря)

```bash
git clone https://github.com/EvXata/aion_self_org_self_edu_mas aion-populations && cd aion-populations
python -m pip install -U pip   # нужен pip ≥ 21.3 (старый pip не умеет editable-установки)
pip install -e .               # ядро только на stdlib — ставится мгновенно
aionpop demo                   # multi-seed сертификация против синтетического якоря (~3 с)
aionpop dashboard              # откройте http://localhost:8092
aionpop share                  # отрендерить прогон в HTML-карточку, которой можно делиться
```

**Не технарь?** Скачайте [`aion-populations-setup.py`](aion-populations-setup.py) и запустите
`python3 aion-populations-setup.py` — он создаст окружение, всё установит, прогонит демо и откроет
дашборд. Один файл, больше ничего делать не нужно.

Реальный вывод (движок оценивает себя против заложенной истины, а затем **отказывается
промоутить**, потому что демо-якорь синтетический — в этом и суть):

```
  mechanism                    measΔ     dz       p  scr cnf rep  CERT   stab  trueΔ  gate
  ------------------------------------------------------------------------------------
  ecosystem_leverage          +0.404   0.47  0.0010   ✓   ✓   ✓   YES    100%  +0.40  ABSTAIN
  micro_niche_finder          +0.308   0.36  0.0010   ✓   ✓   ✓   YES    100%  +0.28  ABSTAIN
  demand_signal_aggregator    +0.199   0.23  0.0010   ✓   ✓   ✓   YES     80%  +0.20  ABSTAIN
  bounded_competency          +0.174   0.20  0.0080   ✓   ✓   ✓   YES     65%  +0.16  ABSTAIN
  marketplace                 +0.007   0.01  0.71     ✓   ·   ·            0%  +0.00  ABSTAIN
  unbounded_skill_gen         -0.310  -0.36  1.0000   ·   ·   ·            0%  -0.30  ABSTAIN
  ------------------------------------------------------------------------------------
  candidates=12  certified=4  promoted=0  seeds=20  (screen/confirm/replicate on 3 disjoint folds)
  vs ground truth → FDR=0.000 (target ≤ 0.05)  power=0.667
  NOTE: synthetic anchor → certified mechanisms ABSTAIN (self-graded evidence is never promoted).
```

**Проверьте сами (30 с):** `pip install -e ".[dev]" && pytest -q` → 50 проходит. Демо держит
FDR = 0.000 на каждом прогоне. Каждый результат **подписан** — `aionpop verify <run.json>` доказывает,
что его не редактировали (бейдж «External-Anchor Verified» настоящий, а не наклейка).

## Свой якорь (главная ценность)

**Ещё нет данных?** `aionpop init` создаёт реалистичный примерный якорь и сертифицирует его — ваш
первый **PROMOTE** (настоящий внешний якорь, в отличие от синтетического демо). Затем направьте его
на свои данные:

Каждая строка вашего CSV — это одна задача/единица: исход **без** механизма и **с** ним.

```csv
mechanism_id,unit_id,predicted,actual
ecosystem_leverage,inv-001,0,1
ecosystem_leverage,inv-002,1,1
...
```

```bash
aionpop anchor add my-ledger --source outcomes.csv     # колонки выше (или control_outcome,treatment_outcome)
aionpop run --anchor my-ledger --seeds 30 --fdr 0.05
# → ранжированный, FDR-сертифицированный список механизмов, которые реально улучшили ВАШИ исходы
```

**Есть только сырые логи задач, а не парный CSV?** `aionpop ingest` — это мост: он превращает сырой
лог в готовый для движка формат выше (`pass`/`yes`/`✓` → 1, `fail`/`no` → 0). Две формы:

```bash
# WIDE — оба исхода уже в одной строке:
aionpop ingest --source log.csv --out outcomes.csv --control-col before --treatment-col after
# LONG — одна строка на задачу плюс флаг варианта:
aionpop ingest --source log.csv --out outcomes.csv --variant-col phase --control off --treatment on --outcome-col reconciled
```

`run` помечает любой механизм с **< 30 парных строк** как недостаточно мощный (underpowered) —
слишком мало данных, чтобы сертифицировать честно.

Для **флота агентов** (например, бухгалтерский/нотариальный бэк-офис из агентов) «исход» — это ваш
реальный сигнал: сошёлся ли реестр, прошла ли нотаризация, доля ошибок, часы до закрытия. Это и есть
внешний якорь, который нужен всему методу; AION Populations привязывает к нему каждое «улучшение».

## Факторные эксперименты: главные эффекты + взаимодействия (`aionpop experiment`)

Когда механизм раскладывается на **факторы** (например, go-to-market = канал × цена × онбординг ×
ICP × активация), мало знать «эта комбинация сработала». Команда `aionpop experiment` сертифицирует:

- **какие отдельные уровни факторов двигают ценность** (главные эффекты), и
- **какие ПАРЫ факторов синергируют/мешают** сверх своих главных эффектов (2-way взаимодействия),

— под FDR-контролем по Бенджамини-Хохбергу с устойчивыми (HC3) ошибками, плюс **валидацию метрик**:
какие KPI реально отслеживают ценность, а какие — правдоподобный мусор. Это, по сути, power-анализ
вашего эксперимента **до** того, как вы потратите бюджет: что вообще можно сертифицировать и при каком
объёме данных.

```bash
aionpop experiment --list                         # готовые наборы
aionpop experiment saas_growth --calibrate --quick  # сначала проверка валидности (A/A + power)
aionpop experiment saas_growth --quick              # сертификация механизмов/эффектов/взаимодействий/KPI
aionpop experiment --new my_experiment.json         # завести свой набор и отредактировать
aionpop experiment my_experiment.json --quick
```

Мир в этом режиме синтетический и **аддитивный** (истинный прирост = сумма эффектов уровней + заложенные
бонусы взаимодействий), поэтому полная структура взаимодействий известна и FDR измерим точно. Когда дизайн
проходит проверку — подключайте реальный якорь (см. «Свой якорь») вместо синтетического мира.

## Как начать

- **Один файл:** `curl -fsSL https://raw.githubusercontent.com/EvXata/aion_self_org_self_edu_mas/main/aion-populations-setup.py | python3` (или скачайте [`aion-populations-setup.py`](aion-populations-setup.py) и запустите).
- **pip, без клонирования:** `pipx install "git+https://github.com/EvXata/aion_self_org_self_edu_mas.git"` → `aionpop demo`.
- **Облако:** [Open in Codespaces](https://codespaces.new/EvXata/aion_self_org_self_edu_mas) — демо запускается при подключении.
- **Docker:** `git clone … && docker compose up`.

## Как это работает (один абзац)

`levers.py` задаёт настройки само-организации и само-обучения; *механизм* — это одна такая настройка.
`certify.py` выполняет **screen → confirm → replicate** на **3 непересекающихся фолдах данных** (screen
и confirm никогда не делят строки — без «double-dipping»): оставляем механизмы, чей средний прирост
проходит скрин, подтверждаем парным перестановочным тестом под контролем FDR по Бенджамини-Хохбергу
и требуем, чтобы знак сохранился на отложенном (held-out) фолде. Затем `safety/anchor_gate.py`
отказывается промоутить всё, что не сертифицировано **против внешнего якоря**. См.
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Обратная связь — отправляется и доходит

Само-улучшающемуся инструменту нужна собственная петля обратной связи — и она замыкается end-to-end:

```bash
aionpop feedback "что зашло / что сломалось"      # открывает заполненный GitHub issue — один клик, без токена
aionpop heartbeat --note "попробовал демо"        # пишет локальный статус-beat в ~/.aionpop/heartbeats.jsonl
aionpop heartbeat --url "$AIONPOP_FEEDBACK_URL"   # …и POST'ит этот beat (версия, платформа, последний прогон) на приёмник
aionpop claude-init                               # ставит навык Claude Code, который сам отправляет фидбэк
```

- **Отправляется → доходит.** `feedback` заводит issue с лейблом в этом репозитории (Issues включены);
  `heartbeat --url` POST'ит JSON-beat на любой приёмник, который вы контролируете, и при успехе пишет `sink=ok`.
- **Приватно по умолчанию.** Без `--url` / `$AIONPOP_FEEDBACK_URL` ничего не покидает вашу машину.

## Безопасность

AION Populations запускает автономные популяции. Значения по умолчанию — только sandbox и
anchor-gate. Прочитайте [SAFETY.md](SAFETY.md). Не запускайте несэндбоксенные популяции против
продакшн-систем.

## Лицензия

MIT (движок). Проприетарный каталог механизмов и любые данные владельца лежат в отдельном приватном
репозитории (`aionpop-core`) и не распространяются. **Протокол открыт; ваша популяция — ваша.**
