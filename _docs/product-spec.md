# SavorLoop Product Specification

## Purpose and scope

SavorLoop helps one user cook with ingredients they already have, reduce avoidable food waste, and improve meals using feedback from recipes they have actually cooked. The MVP contains three areas: Inventory, Suggestions, and Cooking Notebook. It has no accounts, shared households, initial taste questionnaire, recipe catalogue, or model training.

## Inventory

- Pantry staples have available/unavailable status and do not require quantities.
- Rotating ingredients can have a quantity and unit; expiry/use-by dates are optional.
- The user can view and edit inventory through ordinary controls or natural-language requests.
- Natural-language input is interpreted into an allowlisted structured operation. AI cannot write to the database.
- Deterministic backend validation checks ingredient identity, category, unit, and quantity before applying a change.
- A rejected operation leaves all stored data unchanged. Successful operations are applied atomically.

## Suggestions

- Recipes are generated on demand from available inventory; uncooked suggestions are not persisted.
- When date information exists, ingredients with nearer expiry dates are prioritized where suitable.
- A suggestion may use current stock alone or identify up to two missing ingredients.
- Each suggestion contains ingredient quantities, ordered steps, preparation time, serving count, missing ingredients, possible substitutions, and a short explanation tied to stock or urgency.
- The user can request a different serving count and receive appropriately scaled quantities.
- A small selection of highly rated cooked recipes and user-approved adjustments may inform generation. The selection rule is deterministic and explainable.

## Cooking Notebook

- The user explicitly confirms that a suggested recipe was cooked before it enters the notebook.
- One notebook recipe keeps its recipe details and a history of attempts.
- Each attempt records its date, rating, comments, changes, and substitutions.
- New attempts do not erase earlier attempts. A suggestion alone never creates a notebook record.

## AI reliability and incidents

- AI outputs conform to typed schemas and are validated before use.
- One bounded correction retry is permitted. A second invalid result is reported clearly and does not mutate data.
- User-visible errors explain what action failed without exposing secrets or internal diagnostics.
- Operational incidents may be shown in-app when user intervention is needed. External notifications are out of scope.

## Acceptance scenarios

1. Marking olive oil unavailable through natural language changes its status only after backend validation succeeds.
2. Consuming more mushrooms than are in stock is rejected, and the stored quantity remains exactly unchanged.
3. A recipe request uses current stock, favors a suitable ingredient with an imminent optional expiry date, and returns all required recipe fields.
4. Changing servings yields a recipe response for the requested count with scaled ingredient quantities.
5. Generating a suggestion does not create a notebook record; confirming it was cooked creates one recipe with an initial attempt.
6. Adding a second attempt preserves the first attempt and its feedback.
7. A malformed AI response is retried at most once, reported if still invalid, and cannot change inventory or notebook records.

## Data and platform decisions

The initial database is SQLite behind SQLAlchemy. Hosting must preserve the SQLite file across restarts and redeployments; a named local volume alone does not prove hosted persistence. Hosting and telemetry providers remain undecided until their current storage, deployment, and OTLP support are verified. PostgreSQL migration is not in MVP scope unless a concrete platform constraint requires it and the owner approves the change.