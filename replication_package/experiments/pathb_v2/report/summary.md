# Path B v2.1 results (adjudicated, primary)

## C1: 34 failures (6 unassessable, 22 silent); controls {'fixed_observed': 10, 'fixed_recommended': 45, 'warning_only': 8}
- ECM: right reason 6/34 (18%, [8, 34]), FA observed 4/10 (40%)
- NT: right reason 0/34 (0%, [0, 10]), FA observed 2/10 (20%)
- DI: right reason 0/34 (0%, [0, 10]), FA observed 2/10 (20%)
- DQ: right reason 0/34 (0%, [0, 10]), FA observed 2/10 (20%)
- SV: right reason 0/34 (0%, [0, 10]), FA observed 2/10 (20%)
## C2: 12 failures (3 unassessable, 5 silent); controls {'fixed_observed': 2, 'fixed_recommended': 10, 'warning_only': 1}
- ECM: right reason 3/12 (25%, [9, 53]), FA observed 0/2 (0%)
- NT: right reason 1/12 (8%, [1, 35]), FA observed 0/2 (0%)
- DI: right reason 3/12 (25%, [9, 53]), FA observed 0/2 (0%)
- DQ: right reason 3/12 (25%, [9, 53]), FA observed 0/2 (0%)
- SV: right reason 0/12 (0%, [0, 24]), FA observed 0/2 (0%)
## C3: 40 failures (10 unassessable, 26 silent); controls {'fixed_observed': 6, 'fixed_recommended': 44, 'warning_only': 6}
- ECM: right reason 3/40 (8%, [3, 20]), FA observed 1/6 (17%)
- NT: right reason 0/40 (0%, [0, 9]), FA observed 1/6 (17%)
- DI: right reason 1/40 (2%, [0, 13]), FA observed 1/6 (17%)
- DQ: right reason 1/40 (2%, [0, 13]), FA observed 1/6 (17%)
- SV: right reason 0/40 (0%, [0, 9]), FA observed 1/6 (17%)
## C3N: 7 failures (0 unassessable, 4 silent); controls {'fixed_observed': 1, 'fixed_recommended': 6, 'warning_only': 0}
- ECM: right reason 2/7 (29%, [8, 64]), FA observed 0/1 (0%)
- NT: right reason 0/7 (0%, [0, 35]), FA observed 0/1 (0%)
- DI: right reason 0/7 (0%, [0, 35]), FA observed 0/1 (0%)
- DQ: right reason 0/7 (0%, [0, 35]), FA observed 0/1 (0%)
- SV: right reason 0/7 (0%, [0, 35]), FA observed 0/1 (0%)

## H1
{
 "hypothesis": "H1: ECM right-reason detection > DQ on eligible C3 failures (pre-specified)",
 "n_eligible_failures": 40,
 "planned_n": 40,
 "underpowered": false,
 "b_ecm_only": 2,
 "c_dq_only": 0,
 "both": 1,
 "neither": 37,
 "mcnemar_exact_two_sided_p": 0.5,
 "alpha": 0.05,
 "min_relevant_gain": 4,
 "gain_b_minus_c": 2,
 "wilson95_b_over_discordant": [
  0.34237195288961925,
  1.0
 ]
}