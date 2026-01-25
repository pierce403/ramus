# Winner Selection Logic

Ramus uses a deterministic scoring rubric with an optional AI boost. The goal is to keep the logic clear and explainable.

## Deterministic rubric (default)

Each claim is scored on:

- Clear description (minimum length)
- Presence of a link (photo/video proof)
- Mentions of "before" and "after"
- Mentions of a location (park, trail, street, river, beach, neighborhood)

The claim with the highest total score wins.

## Optional AI assist (Venice)

If `VENICE_API_KEY` is set, the bot scores claims using Venice AI (chat completions) and expects a JSON response like:

```json
{"score": 0.0, "reason": "short reason"}
```

The returned score (0-1) is combined with the deterministic score using a small weight. The AI score (and brief reason, when present) is reported in the reasoning output. `AI_SCORE_ENDPOINT` remains as a legacy override for custom scoring services.

## Transparency

The bot writes a reasoning report for every decision, listing each claim and its score breakdown.
