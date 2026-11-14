# Matching Decision Matrix

| Condition | Result |
|---|---|
| Dataset missing, malformed, digest mismatch | System error / Unable to verify |
| Batch absent, ambiguous, or conflicting across OCR passes | Unable to verify |
| Fuzzy batch candidate only | Unable to verify |
| Exact batch but product/strength/formulation conflicts | Unable to verify |
| Exact batch plus corroborating identity confirms NSQ row | Alert found |
| Confirmed NSQ row and expiry also applies | Alert found + separate expiry caveat |
| Successful unambiguous lookup with no qualifying row | No alert found (August 2026 snapshot only) |
| No NSQ match and expiry reliably expired under approved policy | Expired |
| Expiry ambiguous and outcome depends on it | Unable to verify |

Rules: product-name similarity alone never triggers Alert found. Fuzzy batch similarity is retrieval-only. Do not auto-correct O/0, I/1, S/5, B/8. Preserve raw source strings and detect normalized collisions. A confirmed NSQ alert takes precedence over expiry. Expiry cutoff for month-year values is unresolved; see `EXPIRY_POLICY.md`.
