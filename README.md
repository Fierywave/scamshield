# ScamShield

A fraud-defense platform for India: checks suspicious messages and links, scores a simulated transaction stream in real time, and links related reports into cases for analyst review.

**Live demo:** https://scamshield-mukesh.duckdns.org

## What it does
1. **Message and link checker:** rules + ML classifiers give a verdict with reasons.
2. **Transaction risk scoring:** hybrid of rules and XGBoost on a simulated stream (Redis Streams worker).
3. **Connected investigation:** reports sharing a URL, domain, or message pattern are grouped into cases; analysts confirm or reject them.
4. **Analyst dashboard:** login, audit log, case review, model metrics.

## Architecture
FastAPI backend, Postgres, Redis Streams, scoring worker, Next.js frontend, Docker Compose. (Add a diagram here.)

## Results
### Message classifier (trained on UCI SMS Spam + hand-labeled Indian-style messages)
| Model | Test set | Accuracy | Spam recall |
|---|---|---|---|
| Baseline trained on UCI only | UCI test (1,115) | 0.98 | 0.93 |
| Same baseline | Indian-style test (56) | 0.61 | 0.50 |
| Combined training data | Indian-style test (56) | 0.91 | 1.00 |

Small test set (56 messages), so treat these as indicative, not final.

### URL classifier (Kaggle malicious URLs dataset)
| Model | Bad recall | Bad precision |
|---|---|---|
| v1: hand-made features + XGBoost | 0.55 | 0.88 |
| v2: character n-grams + features | (fill in) | (fill in) |

### Transaction scoring (SIMULATED data, not real bank data)
| Approach | Precision | Recall | False-positive rate |
|---|---|---|---|
| Rules | 0.78 | 0.81 | 0.0055 |
| XGBoost | 0.98 | 0.86 | 0.0005 |
| Hybrid (rules OR model) | 0.80 | 1.00 | 0.0057 |

The model alone missed an unseen fraud pattern (3% recall); the rules missed another (0% on test_then_drain). The hybrid covers both at the cost of more false alarms.

### Throughput (single worker, laptop)
| Requested rate | Measured | p50 | p99 |
|---|---|---|---|
| 100 tx/s | about 100 | 4 ms | 35 ms |
| 500 tx/s | 501 | 9.5 ms | 53 ms |
| 1000 tx/s | 1005 | 19.3 ms | 114 ms |
| 2000 tx/s (requested) | 1258 | 24.6 ms | 101 ms |

The 2000 tx/s run was limited by the single-process producer (it reached only 1,258 tx/s), so it is not a measure of the worker's maximum.

Deployed on an AWS t3.small (2 GB RAM): the same 5,763 simulated transactions replayed at 100 tx/s scored with p50 3.3 ms and p99 14.7 ms, with precision 0.787 and recall 0.987 matching the local run.

## Limitations
- Transaction data is simulated; fraud patterns were written by me, so results show how well the system learns those patterns, not real-world bank performance.
- Rules were written knowing the simulated patterns, so their results are not independent.
- Per-user history is held in worker memory (one worker, lost on restart).
- Case linking uses exact domain and message-fingerprint matches; scammers who change domains evade it.
- Personal-data masking covers phone and long account numbers only, not names or addresses.
- No login rate limiting; `/reports` is open and unthrottled.
- Message training data is small and partly self-labeled.


