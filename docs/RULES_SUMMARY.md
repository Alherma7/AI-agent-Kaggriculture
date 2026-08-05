# Competition rules — operational summary

Full legal text: `https://www.kaggle.com/competitions/kaggriculture/rules`
(must be accepted on the website — "Join Competition" — before submitting).
This file only extracts the parts that constrain how the project should be
built. It is not a substitute for the official rules.

## Format

- **Simulation competition.** No public/private leaderboard split — score
  comes directly from aggregated episode results ("There is no Private
  Leaderboard in Simulation competitions").
- Episode replays may be made public (actions your agent took are visible).

## Hard constraint on the agent itself

- **No ingress or egress.** During an episode, your submitted agent may not
  pull in or use any information external to the Submission + Environment,
  and may not send information out. In practice: no network calls, no file
  I/O outside what the environment provides, inside `agent(obs)`. Anything
  that needs external data (an LLM call, a lookup) must happen at
  *development* time, baked into the submitted code/weights, not at
  inference time during a match.

## Submission limits

- Max 5 submissions/day.
- Up to 2 Final Submissions selected for judging.
- Submission = a `main.py` (or tarball with `main.py` at root) with an
  `agent` function — see `AGENTS.md` for exact packaging.

## Team

- Max team size: 5. Mergers allowed pre-deadline under submission-count caps.
- No private sharing of competition code outside your team; public sharing
  only via the Kaggle competition forum/notebooks (and it becomes
  open-source licensed for everyone if you do).

## Prizes

- 10 prizes of $5,000 each (top 10 on final leaderboard).
- Winners must open-source their winning submission under CC-BY 4.0 and be
  able to reproduce it from a documented methodology + code repo link.

## Dates

- Entry deadline reported around **2026-09-23** — verify the exact date and
  the Final Submission Deadline on the competition's Overview > Timeline
  page before relying on it; this file was not able to fetch that page
  directly (Kaggle requires a logged-in session).
