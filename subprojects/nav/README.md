# NAV — 일일 순자산 추적 (Daily Net Asset Value)

Status: implemented (`subprojects/nav`, branch `subproject/nav`). `symbols.yaml`
and `categories.yaml` ship as starters, not yet reconciled against a real 0650
export — see Symbol resolution and Transaction taxonomy, below.

## Purpose

Track the daily net asset value of a single 미래에셋증권 brokerage account —
stock holdings (KR and US) plus cash (원화예수금 and 외화예수금) — and report it
in both KRW and USD.

Non-goals: bank accounts, crypto, pension/IRP, real estate, debts. This is one
account. It is also read-only: nav never places orders.

## Background: why there is no API

미래에셋증권 offers no programmatic account access to individuals. This was
verified in September 2026:

| Route | Verdict |
| --- | --- |
| Official REST OpenAPI | None. 2026 roundups of Korean brokerage APIs list 한국투자 (REST), 키움 (REST + OCX), LS (xingAPI), 대신 (Creon), 토스 (REST), 메리츠 (internal testing). 미래에셋 is absent. |
| Windows OCX/COM | No public developer center or 신청 page. |
| 마이데이터 | Requires a 금융위원회 license (최소자본금 5억). Not available to individuals. |
| Community libraries | None. Everything (`python-kis`, `open-trading-api`) targets 한국투자. |

Consequently the only inputs are files the user exports by hand. nav is
designed around **transaction replay**: export 거래내역 occasionally, replay it
into positions, and price those positions daily from a public market data
source. Day-to-day operation requires no interaction with 미래에셋 at all.

If API access ever becomes a binding constraint, the standard workaround is a
secondary 한국투자증권 account used purely as an API-accessible mirror. Out of
scope here; recorded so the constraint is understood as a brokerage choice
rather than a technical wall.

## Architecture

```
seed.yaml (opening 잔고)  ──┐
                            ├─► replay ─► daily positions + cash ─┐
imports/*.csv (0650) ─► transactions ─┘                           ├─► NAV(date)
historical parquet (close per symbol, KRW=X) ─────────────────────┘
                                                                   │
                                              nav show / nav report ┘
```

### Where the code lives

The generic portfolio math already has a home in the parent package and is
extended there. nav owns only what is specific to 미래에셋 and to presentation.

| Concern | Location |
| --- | --- |
| Inventory replay, NAV series, multi-currency cash, FX | `finance/ext/models.py` (`Portfolio`) |
| Price/FX fetching and parquet warehouse | `finance/ext/warehouse.py` (existing, unchanged) |
| 0650 CSV parsing | `finance/providers/miraeasset.py` (existing, modified) |
| 0650 → transactions bridge, 거래종류 taxonomy, symbol map | `subprojects/nav/nav/` |
| CLI and HTML report | `subprojects/nav/nav/` |

This seam keeps broker-specific knowledge out of the parent package and keeps
portfolio math out of the subproject. The dependency runs one way: nav imports
`finance`, never the reverse.

## Data model

There is no database. Storage follows the parent's existing convention: YAML
for what a human authors, parquet for what the machine accumulates.

| Path | Authored by | Contents |
| --- | --- | --- |
| `seed.yaml` | human | Opening positions and cash on the seed date. |
| `symbols.yaml` | human | 종목명 → ticker + currency. |
| `categories.yaml` | human | 거래종류 → effect on positions and cash. |
| `imports/*.csv` | 미래에셋 | Raw 0650 exports, dropped in as-is. |
| `data/transaction.parquet` | nav | Normalized transactions, deduplicated. |
| `data/nav_daily.parquet` | nav | The output series. |
| `historical.parquet` (repo root) | `finance.ext.warehouse` | Daily OHLCV per symbol, shared with the rest of the repo. |

Naming is singular (`transaction`, not `transactions`), matching the parent
package's table and file naming.

Everything under `data/` is regenerable: `nav rebuild` reconstructs it from
`imports/` plus the three YAML files. Nothing that cannot be regenerated is
stored there, which means a suspect `data/` can always be deleted.

`data/transaction.parquet` retains each source row verbatim in a `raw` column.
When a 거래종류 turns out to have been mishandled months later, the fix is a
re-derivation from local data rather than a re-export from a broker that may no
longer offer that date range.

### `seed.yaml`

```yaml
seed_date: 2026-09-14
positions:
  - {ticker: AAPL, quantity: 10}
  - {ticker: 005930.KS, quantity: 100}
cash:
  KRW: 1234567
  USD: 890.12
```

### `symbols.yaml`

```yaml
- {name: 애플, ticker: AAPL, currency: USD}
- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}
```

Many names map to one ticker. 미래에셋 truncates 종목명 inconsistently across
export vintages — the existing `name_code_mappings` dict in
`finance/providers/miraeasset.py` already carries three spellings of AMD. That
dict is the seed for this file, extended with a currency column.

## Pipeline

### 1. Ingest

`finance.providers.miraeasset.Miraeasset.read_records()` parses the euc-kr,
25-column 거래내역조회 (0650) export. nav consumes its `Record` objects and
normalizes them.

`finance/providers/miraeasset.py` was modified, not used as-is: the hand-rolled
`line.split(",")` could not parse quoted fields containing thousands
separators, and is replaced with `csv.reader`. `Record.quantity` is widened
from `Integer` to `Decimal` to hold fractional overseas share quantities.
`finance/providers/record.py` gained comma-tolerant `Decimal`/`Integer` fields
to match (a plain `int(value)`/`decimal.Decimal(value)` rejects `"1,234"`).

Deduplication is on `(created_at, seq)`. Re-importing the same file is a no-op
and overlapping exports are safe, so the user never has to track which date
ranges have already been imported.

nav does not use `Record.code` or `synthesize_datetime()`. The former falls
back to the string `"(unknown)"` on an unrecognized 종목명, and the latter adds
`seq` seconds to a timestamp to dodge a uniqueness constraint that no longer
exists. nav resolves symbols itself (below) and keys on `(created_at, seq)`
directly.

### 2. Symbol resolution

Every 종목명 must resolve through `symbols.yaml` to a ticker and a currency.
An unmapped name aborts the import with the offending names listed and a
paste-ready YAML stub.

nav never guesses. The `"버크셔해서웨이.B": "BRK-B"` entry in the existing
mappings carries the comment `FIXME: This is a dangerous assumption (could've
been BRK-A)`, which is precisely what guessing produces. A NAV series that is
silently wrong is worse than one that refuses to build.

The committed `symbols.yaml` is seeded from `name_code_mappings` in
`finance/providers/miraeasset.py`, but its own header comment says it has NOT
been reconciled against a live account export, so it may still be missing
names the account actually holds.

### 3. Transaction taxonomy

`categories.yaml` maps each 거래종류 string to the name of a handler:

```yaml
- {category: 현금매수, handler: buy}
- {category: 현금매도, handler: sell}
- {category: 입금,     handler: cash_in}
- {category: 출금,     handler: cash_out}
- {category: 배당금,   handler: dividend}
```

The handlers — `buy`, `sell`, `cash_in`, `cash_out`, `dividend`, `interest`,
`fee`, `noop` — are ordinary Python functions taking a normalized record and
returning inventory deltas. `buy` yields
`{ticker: +quantity, _CCY: -(amount + fees + tax)}`; `dividend` yields
`{_CCY: +(amount - tax)}`; and so on. There is no `fx_exchange` handler: 환전
is a pair of rows, one per currency, and each row maps independently to
`cash_out` (the paying currency) or `cash_in` (the receiving currency) — see
below.

The YAML deliberately holds no arithmetic. What varies per deployment is which
Korean string means what, and that belongs in data; the arithmetic is fixed and
belongs in tested code. Encoding formulas in YAML would mean inventing an
expression language and an evaluator for it, and neither is testable the way a
function is.

An unrecognized `handler` name is an error, exactly as an unmapped `category`
is.

The actual 거래종류 vocabulary of a 미래에셋 export is not documented and is not
assumed here. `nav categories` prints the distinct 거래종류 values in a real
export with counts and a sample row each, and is meant to drive
`categories.yaml`. That step has not actually been run against a live
account export: the committed `categories.yaml` is a five-entry starter
covering only the redacted test fixture (its header comment says so), and
`nav import` will report any 거래종류 it does not recognize.

An unhandled 거래종류 is a hard error, never a silent skip. Skipping a category
produces a NAV that is quietly wrong, which is the failure mode this whole
design is organized against.

환전 is the one 거래종류 that needs two cash legs (KRW down, USD up or the
reverse), and it gets them from two ordinary rows rather than a dedicated
handler: the export already emits 환전 as a pair of rows, one per currency,
and `categories.yaml` maps the paying row to `cash_out` and the receiving row
to `cash_in`. No handler needs to know about FX at all.

### 4. Replay

`Portfolio.eval_inventory(evaluated_at)` already replays transactions into an
inventory. nav seeds it with `seed.yaml` and applies transactions dated after
the seed date, forward-filling to today.

Cash is inventory, using the existing pseudo-ticker convention extended to two
currencies: `_KRW` and `_USD`. A 매수 of AAPL is one transaction pair —
`AAPL +10`, `_USD -1500.00` — so cash and holdings replay through one code path
with no special casing.

Replay is a pure function of `(seed, transactions)`. It performs no I/O.

### 5. Prices and FX

`finance.ext.warehouse.fetch_historical_data()` fetches daily OHLCV via
yfinance into the shared parquet warehouse. nav requests:

- each held ticker, `region="US"` or `region="KR"` (yfinance suffixes: `.KS`, `.KQ`)
- `KRW=X`, `region="FX"` — KRW per 1 USD

FX is therefore just another symbol in the same warehouse, fetched and cached
by the same code. No separate FX subsystem exists.

Every symbol is refetched in full on every `nav sync` — `period="5y"`, the
warehouse's own default — and the warehouse deduplicates on
`(date, region, symbol)` afterwards. Nothing works out which dates are
already held. That is wasteful, but self-healing: a revised or backfilled
close replaces the stored one rather than being skipped as already-present.
Calls are spaced by a randomized delay of up to two seconds, matching
`finance.ext.warehouse.refresh_tickers_and_historical_data`, so a
thirty-holding account does not hit Yahoo thirty times back to back.

The `5y` window is a real constraint on how far back a NAV series can start.
A `seed_date` more than five years old has no close to value its opening
positions against, and the failure surfaces late and obscurely, as
`No close for <ticker> at or before <date>`.

### 6. Valuation

```
NAV_KRW(d) = Σ qty(s,d) × close(s,d) × fx(currency(s), d)
           + cash_KRW(d)
           + cash_USD(d) × fx(USD, d)

NAV_USD(d) = NAV_KRW(d) / fx(USD, d)
```

Both are stored so the report does not re-derive them.

The set of currencies to price is derived from the account, not hardcoded:
the seed's cash keys, the currency of every row in the ledger, and the
currency of every held ticker, plus KRW and USD. `symbols.yaml` already ships
`넥슨 일본 → 3659.T, JPY`, and a holding in a third currency is valued
correctly — it is converted at its own rate and lands in `holdings_krw` with
everything else.

*Cash* in a third currency is different, and is refused rather than dropped.
The daily series has one column per currency (`cash_krw`, `cash_usd`) while
`nav_krw` sums the whole inventory, so a JPY balance would be inside the
total and missing from the breakdown. A report that does not sum to its own
total is the failure mode this design exists to prevent, so `nav sync` stops
and names the currency. Supporting one means adding its column here.

A missing close — market holiday, trading halt, delisting — carries forward the
last known price and marks the day with the affected symbols in a `stale`
column. KR and US market calendars differ, so on most days one side is stale by
construction; this is normal and is surfaced rather than hidden.

## CLI

`nav`, a click group, following the parent's `finance` CLI structure including
its lazy-import-inside-command pattern.

| Command | Purpose |
| --- | --- |
| `nav categories <file>` | Print distinct 거래종류 with counts and sample rows. Drives `categories.yaml`. |
| `nav import imports/*.csv` | Parse and normalize into `data/transaction.parquet`. Idempotent. |
| `nav sync` | Fetch missing closes and FX, recompute `data/nav_daily.parquet`. |
| `nav show [--date]` | Terminal output: NAV in KRW and USD, change vs. prior day, holdings with weights. Uses `rich`, already a dependency. |
| `nav report [-o nav.html]` | Write the self-contained dashboard. |
| `nav check <statement.yaml>` | Reconcile computed positions against a real 잔고, given as a YAML file in the same shape as `seed.yaml`; report per-symbol differences. |
| `nav rebuild` | Delete `data/`, re-derive from `imports/` and the YAML files. |

The 잔고 export format is undocumented, so the statement is supplied as YAML in
the same shape as `seed.yaml` rather than as a broker CSV. Transcribing a few
positions is a minute's work, it is done rarely, and it keeps reconciliation
independent of a format that has never been observed.

## Dashboard

`nav report` writes **one self-contained HTML file**: the NAV curve with a
KRW/USD toggle, the day-change figure, a holdings table with weights, and
stale-price badges.

Data is inlined as a `<script type="application/json">` blob rather than
fetched from a sibling file, because a `file://` page cannot fetch local
resources. The file opens by double-click with no server and no build step.

Chart.js is loaded pinned from a CDN. Vendoring that one file next to the HTML
is the only change needed to make the report work offline.

## Packaging

`subprojects/nav/pyproject.toml` declares a `nav` package with a
`nav = nav.cli:cli` console script, installed into the same environment as the
parent:

```
pip install -e .                    # repo root, provides `finance`
pip install -e subprojects/nav      # provides `nav`
```

nav imports `finance`, so the two must share an environment. Its declared
dependencies (`click`, `pandas`, `pyarrow`, `rich`, `PyYAML`) are already a
subset of the parent's.

## Version control

`subprojects/nav` is tracked in this repository on branch `subproject/nav`,
following the convention set by `subproject/etf-overlap`.

Committed: `nav/`, `tests/`, `pyproject.toml`, `README.md`, `symbols.yaml`,
`categories.yaml`, `seed.example.yaml`, and the redacted 0650 test fixture.

Gitignored via `subprojects/nav/.gitignore`: `seed.yaml`, `imports/`, `data/`,
`nav.html`. These hold real balances and real transactions.

The distinction is deliberate. `symbols.yaml` and `categories.yaml` accumulate
hard-won knowledge about how 미래에셋 formats its exports and are worth having
history on; they contain no financial data. `seed.yaml` is the opposite.

## Testing

pytest under `subprojects/nav/tests/`.

Replay and valuation are pure functions and are tested with literal inputs, no
fixtures required:

- carry-forward across a KR market holiday while the US side trades
- a day where only the FX rate moves — NAV changes, positions do not
- a 환전 that nets to zero NAV change
- a 배당 in USD crediting `_USD`
- an unknown 종목명 and an unknown 거래종류 each raising rather than skipping

Ingest is tested against one redacted 0650 fixture committed to the repo.

One golden test pins a known seed plus known transactions to a known NAV,
guarding the taxonomy table against regressions.

## Known limitations

**Stock splits.** yfinance closes are split-adjusted; replayed quantities are
not. A split after the seed date makes NAV jump incorrectly. nav does not
correct this automatically — it detects it: `nav check` diffs computed
positions against a real 잔고 statement (YAML, in the `seed.yaml` shape), and
any single-day per-symbol price move beyond ±40% is flagged as a suspected
corporate action.

**Seeded history.** NAV history begins at `seed_date`. Earlier history would
require replaying from account inception, which is only correct if the export
covers every 입출금, 배당, 환전, 권리락 and 액면분할 — not assumed here.

**Manual export cadence.** Positions are only as current as the last import.
Between imports, prices update daily but a trade made yesterday is invisible
until its export is dropped in. `nav show` displays the latest transaction date
so the staleness is visible.

**Single account.** No support for multiple accounts or brokerages.

## Upstream changes to `finance/ext/models.py`

More landed here than originally scoped. All of it is additive; existing
callers keep working.

- `is_cash()` / `CASH_PREFIX`, replacing the hardcoded `_USD` check in
  `apply_plan()` and the by-name exclusion in `make_rebalancing_plan()`, so
  any underscore-prefixed pseudo-ticker (`_KRW` included) is recognized as
  cash.
- A `base_currency` constructor parameter with a derived `cash_ticker`
  attribute, so a `Portfolio` knows which pseudo-ticker is its own cash
  without the caller repeating `"_" + currency` everywhere.
- `eval_nav()`, which previously read `return 0`, actually implemented: net
  asset value at a point in time from an already-single-currency price dict.
- `MissingPriceException`, raised by `eval_nav()` instead of letting a bare
  `KeyError` escape when a ticker has no price.
- `QUANTITY_EPSILON`, replacing an exact float-zero comparison: repeated
  float `+=` on a fully-closed position lands on something like `1e-13`
  rather than exact zero, so valuation now treats anything within this
  tolerance of zero as closed instead of demanding a price for it.
- A pure `_replay_transactions()` helper factored out of `eval_inventory()`,
  so valuing a historical date (as `eval_nav()` routinely does on a live
  `Portfolio`) no longer clobbers `self.inventory` as a side effect.
- A fix to `eval_inventory()`'s default argument: it was
  `evaluated_at=datetime.now(timezone.utc)`, a mutable default bound once at
  import time, which froze "now" for the lifetime of the process. It is now
  evaluated per call.

`finance/ext/warehouse.py` is used as-is and is not modified.
`finance/providers/miraeasset.py` and `finance/providers/record.py` were
modified — see Ingest, above.

The parent README lists 총 자산 가치 추적 under 잠시 뒤로 미루어둔 주제. This
work resumes it.

## Implementation order

1. `nav categories` against a real export — discover the 거래종류 vocabulary.
2. `categories.yaml` and `symbols.yaml` from observed data.
3. Ingest and normalization, with the fixture test.
4. Upstream `Portfolio` changes: multi-currency cash, FX, NAV series.
5. Replay and valuation wiring, with the pure-function tests.
6. `nav sync` and `nav show`.
7. `nav report`.
8. `nav check`.

Step 1 was meant to gate steps 2 and 3, deriving the taxonomy from a real
export rather than assuming it. In practice steps 2-8 were built and tested
against the redacted fixture without step 1 ever being run against a live
account export, so `categories.yaml` and `symbols.yaml` remain starters —
see Symbol resolution and Transaction taxonomy, above.
