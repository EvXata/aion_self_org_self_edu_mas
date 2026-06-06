# Экскурсия: первые шаги и первый эксперимент

Это пошаговый тур по AION Populations: от установки до первого **сертифицированного**
улучшения на ваших собственных данных. Минут на 10. Все выводы ниже — настоящие, их
можно воспроизвести командами из этого же файла.

> **Главная идея в одном предложении.** Большинство «само-улучшающихся» систем оценивают
> сами себя и дрейфуют; AION ничего не «промоутит», пока улучшение не пройдёт честную
> статистическую проверку против **внешнего якоря** (ground-truth, который придумали не вы).

---

## 0. Установка (60 секунд)

```bash
git clone https://github.com/EvXata/aion_self_org_self_edu_mas aion-populations && cd aion-populations
python -m pip install -U pip     # нужен pip ≥ 21.3
pip install -e ".[dev]"          # ядро только на stdlib; [dev] добавляет pytest
```

Не технарь? Один файл всё сделает сам:
```bash
curl -fsSL https://raw.githubusercontent.com/EvXata/aion_self_org_self_edu_mas/main/aion-populations-setup.py | python3
```

Проверка, что всё на месте (по желанию): `pytest -q` → **50 passed**.

---

## 1. Шаг первый — «просто увидеть, как это работает» (demo)

```bash
aionpop demo
```

```
  Run demo · scenario=demo · seed=42
  Anchor: synthetic  (external=False)  ·  FDR q=0.05
  ...
  candidates=12  certified=4  promoted=0  seeds=20
  vs ground truth → FDR=0.000 (target ≤ 0.05)  power=0.667
  NOTE: synthetic anchor → certified mechanisms ABSTAIN at the gate (self-graded evidence is never promoted).
```

Что здесь произошло. Движок взял 12 механизмов-кандидатов и прогнал их против
**синтетического** мира с заранее заложенной истиной. Он восстановил настоящих победителей
(`certified=4`) с **FDR = 0.000** — то есть среди отобранных нет ложных открытий. Но
`promoted=0`: якорь синтетический, а само-оценённые данные **никогда не промоутятся**. Это
не баг — это и есть суть. Гейт сработал.

---

## 2. Шаг второй — первый НАСТОЯЩИЙ PROMOTE (init)

`aionpop init` создаёт реалистичный пример лога флота агентов (это уже **внешний** якорь) и
сертифицирует механизмы против него:

```bash
aionpop init
```

```
wrote a sample fleet log → outcomes.csv (280 rows, 4 mechanisms). It's an EXTERNAL anchor, so certified mechanisms PROMOTE.

  Run init · scenario=init · seed=42
  Anchor: my-data  (external=True)  ·  FDR q=0.05
  ------------------------------------------------------------------------------------
  mechanism                    measΔ     dz       p  scr cnf rep  CERT   stab  gate
  ------------------------------------------------------------------------------------
  contradiction_detector      +0.435   0.86  0.0025   ✓   ✓   ✓   YES    100%  PROMOTE
  source_backed_alert         +0.000   0.00  1.0000   ·   ·   ·            0%  ABSTAIN
  aggressive_autoclose        -0.043  -0.07  1.0000   ·   ·   ·            0%  ABSTAIN
  verbose_logging             -0.174  -0.27  1.0000   ·   ·   ·            0%  ABSTAIN
  ------------------------------------------------------------------------------------
  candidates=4  certified=1  promoted=1  seeds=20
```

Теперь якорь внешний (`external=True`) → сертифицированный механизм получает **PROMOTE**.
`contradiction_detector` реально улучшил исход (+0.435, p = 0.0025, устойчив на 100% сидов);
декоративный и вредные механизмы — честно `ABSTAIN`.

---

## 3. Шаг третий — подпись и проверка (share + verify)

Каждый прогон **подписан**. Можно отрендерить карточку, которой не стыдно поделиться, и
доказать, что её не редактировали:

```bash
aionpop share init --out card.html
aionpop verify card.html
```

```
✓ VALID signature · key 643b636a8bcf337c…
  certified=1 promoted=1 external_anchor=True
  → External-Anchor Verified (signed, untampered).
```

Бейдж «External-Anchor Verified» — настоящий, а не наклейка: `verify` проверяет подпись.

---

## 4. Пример эксперимента на ВАШИХ данных (ingest → run)

У большинства нет готового `mechanism_id,unit_id,predicted,actual` — есть сырой лог задач.
`aionpop ingest` — это мост. Возьмём «длинный» лог (одна строка на задачу + флаг
`before/after`, исход `yes/no`):

```csv
task_id,mechanism_id,phase,reconciled
con-000,contradiction_detector,before,no
con-000,contradiction_detector,after,yes
...
```

Превращаем его в готовый для движка парный CSV и сертифицируем:

```bash
aionpop ingest --source raw_log.csv --out from_log.csv \
  --variant-col phase --control before --treatment after --outcome-col reconciled
aionpop run --anchor from_log.csv --seeds 30
```

```
wrote from_log.csv: 120 paired rows across 2 mechanism(s)

  mechanism                    measΔ     dz       p  scr cnf rep  CERT   stab  gate
  ------------------------------------------------------------------------------------
  contradiction_detector      +0.450   0.74  0.0120   ✓   ✓   ✓   YES    100%  PROMOTE
  verbose_logging             +0.050   0.08  1.0000   ·   ·   ·            0%  ABSTAIN
  ------------------------------------------------------------------------------------
  candidates=2  certified=1  promoted=1  seeds=30
```

`yes/pass/✓` нормализуются в 1, `no/fail` — в 0. Есть и «широкая» форма (оба исхода в одной
строке): `--control-col before --treatment-col after`. Любой механизм с **< 30 парными
строками** помечается как недостаточно мощный — слишком мало данных, чтобы судить честно.

Для реального флота агентов «исход» — это ваш настоящий сигнал: сошёлся ли реестр, прошла
ли нотаризация, доля ошибок, часы до закрытия. Это и есть внешний якорь, к которому метод
привязывает каждое «улучшение».

---

## 5. Как читать вердикт (шпаргалка по колонкам)

| колонка | что значит |
|---|---|
| `measΔ` | измеренный средний эффект (с механизмом − без), на независимом confirm-фолде |
| `dz` | размер эффекта (Cohen's dz) |
| `p` | p-value парного перестановочного теста |
| `scr` / `cnf` / `rep` | прошёл **s**creen → **c**onfirm (BH-FDR) → **r**eplicate (знак держится на отложенном фолде) |
| `CERT` | сертифицирован — все три этапа пройдены |
| `stab` | доля сидов, где механизм сертифицировался (multi-seed устойчивость) |
| `gate` | вердикт anchor-gate: **PROMOTE** (внешний якорь + сертифицирован) или **ABSTAIN** |

Три этапа идут на **3 непересекающихся фолдах** данных — screen и confirm никогда не делят
строки, поэтому нет «двойного зачёта» (double-dipping).

---

## 6. Что дальше

```bash
aionpop dashboard                         # дашборд из 5 секций → http://localhost:8092
aionpop anchor add mine --source you.csv  # подключить свой якорь
aionpop run --anchor mine --seeds 30      # сертифицировать против ваших исходов
aionpop feedback "что зашло / что сломалось"   # обратная связь в один клик (без токена)
```

- Справочник команд: [docs/QUICKSTART.md](QUICKSTART.md)
- Как устроен сертификатор: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- Перед масштабом — обязательно: [SAFETY.md](../SAFETY.md) (sandbox и anchor-gate включены по умолчанию)

**Ваша петля обратной связи реальна** — `aionpop feedback` заводит issue прямо в репозитории,
а `aionpop heartbeat --url <sink>` шлёт статус на ваш приёмник и пишет `sink=ok` при успехе.
