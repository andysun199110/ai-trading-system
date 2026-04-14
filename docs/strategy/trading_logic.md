# Trading Logic (Stage 2)

## Multi-timeframe responsibility
- H1: regime and trend strength.
- M15: setup and zone interaction.
- M5: closed-bar trigger only.

## Entry pipeline
1. H1 regime filter.
2. M15 setup filter.
3. M5 trigger confirmation.
4. spread guard.
5. event block guard.
6. kill switch guard.
7. optional AI candidate review.

## Risk
- Initial SL from ATR/structure.
- Fixed-RR TP.
- Breakeven near 0.8R (configurable).
- Structure-first trailing, ATR fallback.
- No time-stop exits.
