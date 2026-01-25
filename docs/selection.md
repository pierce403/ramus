# Winner Selection Logic

Ramus uses a deterministic scoring rubric with an optional AI boost. The goal is to keep the logic clear and explainable.

## Deterministic rubric (default)

Each claim is scored on:

- Clear description (minimum length)
- Presence of a link (photo/video proof)
- Mentions of "before" and "after"
- Mentions of a location (park, trail, street, river, beach, neighborhood)

The claim with the highest total score wins.

## Optional AI assist

If `AI_SCORE_ENDPOINT` is set, the bot sends a JSON payload containing the claim title and description. The endpoint should respond with:

```json
{"score": 0.0}
```

The returned score (0-1) is combined with the deterministic score using a small weight. The AI score is reported in the reasoning output.

## Transparency

The bot writes a reasoning report for every decision, listing each claim and its score breakdown.
