# Safety Rails

## Retry logic

- POIDH client operations retry with exponential backoff.

## Dispute handling

- If the top score is below `min_score_to_award`, the bot does not pay out.
- The decision is still logged for review.

## Manual override

- Set `MANUAL_OVERRIDE_PATH` to a JSON file with:

```json
{"bounty_id": 123, "action": "accept", "claim_id": 456}
```

Use `action: "skip"` to halt payouts for a specific bounty.
