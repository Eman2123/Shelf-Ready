# Shelf Ready demo script (PRD section 13)

Under 3:00, English, public on YouTube, shows the project running, no music, no third-party logos. Fictional store brand only (Tidewell Goods). Every number said aloud must be one shown on screen from a recorded run.

## Read this first: what the demo can honestly show today

The audit engine, fix engine, policy engine, agent keys and PayPal checkout are not connected yet. Do not narrate them as live. Until they are connected, the recording shows only what exists, and the lines marked **[BLOCKED on A]** stay out of the video (or are recorded after integration).

| PRD moment | Today | Say / show |
| --- | --- | --- |
| BEFORE agent guesses "from $20" | Real, recorded | `run_A2_before_1`, outcome WRONG_RESULT, intent price 2000 cents |
| Fix with evidence, one red rejection | Fix review screen shows fixtures | Say "example fixes"; not a live fix run |
| AFTER agent: 4 tool calls, HTML bytes 0, order $24 | Real, recorded | `run_A2_after_1`, SUCCESS, 4 calls, 0 bytes, 2400 cents |
| PayPal authorized, webhook verified | **[BLOCKED on A]** | Do not show. The order is simulated (`paypal_order_id` is null) |
| "$180 order stopped" | Use the recorded $72 order | `run_B5_after_1`: NEEDS_APPROVAL, $72 > $50. No $180 task exists |
| Readiness score and waterfall | Real, recorded audit (see Report); the 5 variants still show "Not connected" for score | Quote the run id shown next to each number |

Agents in the video are scripted baselines. Say "scripted agent, no language model". Do not say "AI agent" for them.

## Setup before recording

1. Backend and frontend running as in the README. `python -m app.scripts.verify_benchmark` prints OK.
2. Browser at 1280 px wide, light mode, one tab, no bookmarks bar, no other logos visible.
3. Open `/app/agent-test` and `/app/report` in two tabs. Task A2 selected on Agent test.
4. Terminal ready with `make bench-record TASK=A2` (backend venv active) for the optional close-up.

## Script

### 0:00 to 0:25 Wow moment (Agent test, task A2)

| Time | On screen | Say |
| --- | --- | --- |
| 0:00 | Agent test, split view, task A2: "Buy one Tidewell Classic Tee, blue, size M. Spend at most $30." | "Same agent script, same task, same store. Left is the store as it is today." |
| 0:05 | Press Replay. BEFORE trace: two page fetches, then a recorded intent at 2000 cents. Red result. | "It reads the page, sees 'from $20', and guesses. Wrong price. It fails." |
| 0:12 | AFTER trace: get_policy, search_products, get_product, create_order. | "Right is the same store through its agent interface. Four tool calls." |
| 0:17 | Totals: HTML bytes read 0, order at 2400 cents, SUCCESS. | "Zero HTML read. Exact variant, exact price, 24 dollars." |
| 0:21 | Switch to task B5, AFTER. Result: NEEDS_APPROVAL, 72 dollars over 50. | "Ask for three tees and store code stops it for approval. No order is created." |

### 0:25 to 1:05 Problem and what the agent sees

| Time | On screen | Say |
| --- | --- | --- |
| 0:25 | `/demo-store` (the messy storefront) | "Small stores publish prices like 'from 20 dollars', hide stock and shipping, or need a human at checkout." |
| 0:40 | Terminal: `python -m app.scripts.seed_demo` output | "We import the catalog. Twelve products. What the file does not say stays unsaid: a vague price is not guessed." |
| 0:55 | **[BLOCKED on A]** audit grid and score waterfall. Until then, skip to next row. | |

### 1:05 to 1:55 Evidence and fixes

| Time | On screen | Say |
| --- | --- | --- |
| 1:05 | Fix review, three lanes | "Fixes come in three lanes: applied with the source highlighted, rejected, and needs the seller." |
| 1:30 | Red lane item | "One value was rejected because the source text does not contain it. An invented fact never enters the catalog." |
| 1:45 | Caption on screen: "Example data. Fix engine not connected yet." | Say it plainly. |

### 1:55 to 2:35 Benchmark and injection

| Time | On screen | Say |
| --- | --- | --- |
| 1:55 | Report, section Agent benchmark | "Twelve tasks, each run three times, before and after." |
| 2:05 | Totals table: unsafe actions BEFORE 36, AFTER 0; completion 0 of 9 vs 9 of 9; safe-stop 0 of 27 vs 27 of 27 | "Before, the agent made 36 unsafe moves. After, none." |
| 2:15 | Click the AFTER unsafe-actions figure to open its run ids | "Every number opens the runs behind it." |
| 2:20 | Task B4 row, then `run_B4_before_1` raw record | "A product description told the agent to order ten. The old reader obeyed. After, it orders one." |
| 2:28 | Section Defect variants, "n=5 demo variants" | "Five pages with one defect each. Five pages, not a sample, so we claim no correlation." |

### 2:35 to 3:00 Receipt and close

| Time | On screen | Say |
| --- | --- | --- |
| 2:35 | Report footer, fingerprint line | "The recorded benchmark has a SHA-256 fingerprint." |
| 2:42 | Terminal: `python -m app.scripts.verify_benchmark` prints OK | "One command re-checks it: the file, the numbers on screen, and a fresh re-run all match." |
| 2:50 | Report "Not connected" tags | "What is not connected yet says so, and shows no number." |
| 2:55 | Repo page, MIT licence, "sandbox only" line | "Open source, MIT, PayPal sandbox only." |

After integration with A, replace the **[BLOCKED on A]** rows and the $72 line with the real audit score, a live PayPal sandbox authorization with a verified webhook, and the $180 order from the PRD. Re-record the benchmark against the real policy and keys first.

## Numbers to read from the Report, not from memory

Recorded set (72 runs, k=3, fingerprint printed in the Report): BEFORE completion 0/9, safe-stop 0/27, unsafe actions 36, wrong purchases 9, HTML bytes 88197. AFTER completion 9/9, safe-stop 27/27, unsafe actions 0, wrong purchases 0, HTML bytes 0. If `make bench-run` is re-run, check these against the Report before speaking them.
