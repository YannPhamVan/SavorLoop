import { useEffect, useState } from "react";
import type { FormEvent } from "react";

type IngredientCategory = "pantry_staple" | "rotating";
type CategoryFilter = "all" | IngredientCategory;

interface Ingredient {
  id: number;
  category: IngredientCategory;
  name: string;
  available: boolean | null;
  quantity: number | null;
  unit: string | null;
  expiry_date: string | null;
}

interface IngredientDraft {
  category: IngredientCategory;
  name: string;
  available: boolean;
  quantity: string;
  unit: string;
  expiryDate: string;
}

interface InventoryUpdateResult {
  status: "updated";
  message: string;
  updated_count: number;
}

interface RecipeIngredient {
  name: string;
  quantity: number;
  unit: string;
}

interface RecipeSuggestion {
  title: string;
  ingredients: RecipeIngredient[];
  steps: string[];
  preparation_time_minutes: number;
  substitutions: string[];
  servings: number;
  missing_ingredients: RecipeIngredient[];
  stock_explanation: string;
}

interface AttemptPayload {
  attempt_date: string;
  rating: number;
  comments: string;
  changes: string[];
  substitutions: string[];
  liked_adjustments: string[];
}

interface CookingAttempt extends AttemptPayload {
  id: number;
}

interface NotebookRecipe {
  id: number;
  recipe: RecipeSuggestion;
  attempts: CookingAttempt[];
}

const emptyDraft = (category: IngredientCategory = "rotating"): IngredientDraft => ({
  category,
  name: "",
  available: true,
  quantity: "",
  unit: "",
  expiryDate: "",
});

function localToday(): string {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
}

function adjustmentLines(value: string): string[] {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}

function AttemptEditor({
  submitLabel,
  saving,
  onSave,
}: {
  submitLabel: string;
  saving: boolean;
  onSave: (attempt: AttemptPayload) => Promise<void>;
}) {
  const [attemptDate, setAttemptDate] = useState(localToday);
  const [rating, setRating] = useState("5");
  const [comments, setComments] = useState("");
  const [changes, setChanges] = useState("");
  const [substitutions, setSubstitutions] = useState("");
  const [likedAdjustments, setLikedAdjustments] = useState<string[]>([]);
  const changeItems = adjustmentLines(changes);
  const substitutionItems = adjustmentLines(substitutions);
  const adjustmentOptions = [...new Set([...changeItems, ...substitutionItems])];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const available = new Set(adjustmentOptions);
    await onSave({
      attempt_date: attemptDate,
      rating: Number(rating),
      comments,
      changes: changeItems,
      substitutions: substitutionItems,
      liked_adjustments: likedAdjustments.filter((item) => available.has(item)),
    });
  }

  return (
    <form className="attempt-editor" onSubmit={(event) => void submit(event)}>
      <div className="attempt-form-grid">
        <div>
          <label className="field-label" htmlFor="attempt-date">Cooked on</label>
          <input id="attempt-date" className="text-input" type="date" required value={attemptDate} onChange={(event) => setAttemptDate(event.target.value)} />
        </div>
        <div>
          <label className="field-label" htmlFor="attempt-rating">Rating</label>
          <select id="attempt-rating" className="text-input" value={rating} onChange={(event) => setRating(event.target.value)}>
            {[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value} / 5</option>)}
          </select>
        </div>
      </div>
      <label className="field-label" htmlFor="attempt-comments">Comments</label>
      <textarea id="attempt-comments" className="text-input attempt-textarea" maxLength={2000} rows={2} value={comments} onChange={(event) => setComments(event.target.value)} />
      <div className="attempt-form-grid">
        <div>
          <label className="field-label" htmlFor="attempt-changes">Changes you made <span>One per line</span></label>
          <textarea id="attempt-changes" className="text-input attempt-textarea" maxLength={1000} rows={3} value={changes} onChange={(event) => setChanges(event.target.value)} />
        </div>
        <div>
          <label className="field-label" htmlFor="attempt-substitutions">Substitutions used <span>One per line</span></label>
          <textarea id="attempt-substitutions" className="text-input attempt-textarea" maxLength={1000} rows={3} value={substitutions} onChange={(event) => setSubstitutions(event.target.value)} />
        </div>
      </div>
      {adjustmentOptions.length > 0 && (
        <fieldset className="liked-adjustments">
          <legend>Adjustments to use as inspiration</legend>
          {adjustmentOptions.map((item) => (
            <label key={item}>
              <input
                type="checkbox"
                checked={likedAdjustments.includes(item)}
                onChange={(event) => setLikedAdjustments((current) => event.target.checked
                  ? [...current, item]
                  : current.filter((value) => value !== item))}
              />
              <span>{item}</span>
            </label>
          ))}
        </fieldset>
      )}
      <button className="primary-button attempt-submit" type="submit" disabled={saving || !attemptDate}>
        {saving ? "Saving..." : submitLabel}
        {!saving && <span aria-hidden="true">→</span>}
      </button>
    </form>
  );
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
  } catch {
    return "The server returned an unexpected response.";
  }
  return "The request could not be completed.";
}

export default function App() {
  const [activeView, setActiveView] = useState<"inventory" | "suggestions" | "notebook">("inventory");
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [draft, setDraft] = useState<IngredientDraft>(() => emptyDraft());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [filter, setFilter] = useState<CategoryFilter>("all");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [naturalRequest, setNaturalRequest] = useState("");
  const [updatingInventory, setUpdatingInventory] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<{ kind: "pending" | "success" | "error"; message: string } | null>(null);
  const [error, setError] = useState("");
  const [requestedServings, setRequestedServings] = useState("2");
  const [recipe, setRecipe] = useState<RecipeSuggestion | null>(null);
  const [recipeLoading, setRecipeLoading] = useState(false);
  const [recipeError, setRecipeError] = useState("");
  const [notebook, setNotebook] = useState<NotebookRecipe[]>([]);
  const [notebookLoading, setNotebookLoading] = useState(false);
  const [notebookError, setNotebookError] = useState("");
  const [notebookSaving, setNotebookSaving] = useState(false);
  const [openAttemptId, setOpenAttemptId] = useState<number | null>(null);

  async function loadInventory() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/inventory");
      if (!response.ok) throw new Error(await readError(response));
      setIngredients(await response.json() as Ingredient[]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Inventory could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  async function loadNotebook() {
    setNotebookLoading(true);
    setNotebookError("");
    try {
      const response = await fetch("/api/notebook");
      if (!response.ok) throw new Error(await readError(response));
      setNotebook(await response.json() as NotebookRecipe[]);
    } catch (cause) {
      setNotebookError(cause instanceof Error ? cause.message : "The notebook could not be loaded.");
    } finally {
      setNotebookLoading(false);
    }
  }

  useEffect(() => {
    void loadInventory();
  }, []);

  useEffect(() => {
    if (activeView === "notebook") void loadNotebook();
  }, [activeView]);

  const visibleIngredients = ingredients.filter(
    (ingredient) => filter === "all" || ingredient.category === filter,
  );
  const pantryCount = ingredients.filter((item) => item.category === "pantry_staple").length;
  const rotatingCount = ingredients.filter((item) => item.category === "rotating").length;

  function chooseCategory(category: IngredientCategory) {
    setDraft((current) => ({ ...emptyDraft(category), name: current.name }));
  }

  function beginEdit(ingredient: Ingredient) {
    setEditingId(ingredient.id);
    setDraft({
      category: ingredient.category,
      name: ingredient.name,
      available: ingredient.available ?? true,
      quantity: ingredient.quantity === null ? "" : String(ingredient.quantity),
      unit: ingredient.unit ?? "",
      expiryDate: ingredient.expiry_date ?? "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft(emptyDraft());
  }

  async function submitIngredient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");

    const payload = draft.category === "pantry_staple"
      ? { category: draft.category, name: draft.name, available: draft.available }
      : {
          category: draft.category,
          name: draft.name,
          quantity: Number(draft.quantity),
          unit: draft.unit,
          ...(draft.expiryDate ? { expiry_date: draft.expiryDate } : {}),
        };

    try {
      const response = await fetch(
        editingId === null ? "/api/inventory" : `/api/inventory/${editingId}`,
        {
          method: editingId === null ? "POST" : "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!response.ok) throw new Error(await readError(response));
      setEditingId(null);
      setDraft(emptyDraft());
      await loadInventory();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The ingredient could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteIngredient(ingredient: Ingredient) {
    if (!window.confirm(`Remove ${ingredient.name} from inventory?`)) return;
    setError("");
    try {
      const response = await fetch(`/api/inventory/${ingredient.id}`, { method: "DELETE" });
      if (!response.ok) throw new Error(await readError(response));
      if (editingId === ingredient.id) cancelEdit();
      await loadInventory();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The ingredient could not be deleted.");
    }
  }

  async function submitNaturalUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUpdatingInventory(true);
    setUpdateStatus({ kind: "pending", message: "Checking your update..." });

    try {
      const response = await fetch("/api/inventory/natural-language", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: naturalRequest }),
      });
      if (!response.ok) throw new Error(await readError(response));

      const result = await response.json() as InventoryUpdateResult;
      if (result.status !== "updated" || typeof result.updated_count !== "number") {
        throw new Error("The update was not confirmed. Check inventory before trying again.");
      }

      setNaturalRequest("");
      setUpdateStatus({ kind: "success", message: result.message });
      await loadInventory();
    } catch (cause) {
      setUpdateStatus({
        kind: "error",
        message: cause instanceof Error
          ? cause.message
          : "The update could not be completed. Check the item name and details, then try again.",
      });
    } finally {
      setUpdatingInventory(false);
    }
  }

  async function submitRecipeRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const servings = Number(requestedServings);
    if (!Number.isInteger(servings) || servings < 1 || servings > 12) {
      setRecipeError("Choose a serving count from 1 to 12.");
      return;
    }

    setRecipe(null);
    setRecipeError("");
    setRecipeLoading(true);
    try {
      const response = await fetch("/api/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ servings }),
      });
      if (!response.ok) throw new Error(await readError(response));
      setRecipe(await response.json() as RecipeSuggestion);
    } catch (cause) {
      setRecipeError(cause instanceof Error ? cause.message : "A recipe could not be generated.");
    } finally {
      setRecipeLoading(false);
    }
  }

  async function confirmCooked(attempt: AttemptPayload) {
    if (!recipe) return;
    setNotebookSaving(true);
    setNotebookError("");
    try {
      const response = await fetch("/api/notebook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipe, attempt }),
      });
      if (!response.ok) throw new Error(await readError(response));
      setRecipe(null);
      await loadNotebook();
      setActiveView("notebook");
    } catch (cause) {
      setNotebookError(cause instanceof Error ? cause.message : "The cooked recipe could not be saved.");
    } finally {
      setNotebookSaving(false);
    }
  }

  async function appendAttempt(recipeId: number, attempt: AttemptPayload) {
    setNotebookSaving(true);
    setNotebookError("");
    try {
      const response = await fetch(`/api/notebook/${recipeId}/attempts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(attempt),
      });
      if (!response.ok) throw new Error(await readError(response));
      setOpenAttemptId(null);
      await loadNotebook();
    } catch (cause) {
      setNotebookError(cause instanceof Error ? cause.message : "The cooking attempt could not be saved.");
    } finally {
      setNotebookSaving(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="SavorLoop home">
          <span className="wordmark-mark" aria-hidden="true">S</span>
          <span>SavorLoop</span>
        </a>
        <nav className="view-nav" aria-label="Kitchen views">
          <button className={activeView === "inventory" ? "view-tab active" : "view-tab"} type="button" aria-current={activeView === "inventory" ? "page" : undefined} onClick={() => setActiveView("inventory")}>Inventory</button>
          <button className={activeView === "suggestions" ? "view-tab active" : "view-tab"} type="button" aria-current={activeView === "suggestions" ? "page" : undefined} onClick={() => setActiveView("suggestions")}>Suggestions</button>
          <button className={activeView === "notebook" ? "view-tab active" : "view-tab"} type="button" aria-current={activeView === "notebook" ? "page" : undefined} onClick={() => setActiveView("notebook")}>Notebook</button>
        </nav>
        <span className="topbar-dot" aria-label="Single-user kitchen" />
      </header>

      <section className="page-heading" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">YOUR KITCHEN / {activeView.toUpperCase()}</p>
          <h1 id="page-title">{activeView === "inventory" ? <>What's on hand<span>?</span></> : activeView === "suggestions" ? <>What's for dinner<span>?</span></> : <>What you've cooked<span>.</span></>}</h1>
        </div>
        {activeView === "inventory" && (
          <div className="inventory-summary" aria-label="Inventory totals">
            <div><strong>{pantryCount.toString().padStart(2, "0")}</strong><span>Pantry</span></div>
            <div><strong>{rotatingCount.toString().padStart(2, "0")}</strong><span>Fresh &amp; rotating</span></div>
            <div><strong>{ingredients.length.toString().padStart(2, "0")}</strong><span>Total items</span></div>
          </div>
        )}
      </section>

      {activeView === "inventory" && error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button className="text-button" type="button" onClick={() => void loadInventory()}>
            Retry
          </button>
        </div>
      )}

      {activeView === "inventory" ? (
      <section className="inventory-workspace" aria-label="Inventory management">
        <div className="inventory-panel">
          <form className="natural-update" onSubmit={(event) => void submitNaturalUpdate(event)}>
            <div className="natural-update-heading">
              <div>
                <p className="eyebrow">QUICK UPDATE</p>
                <h2>What changed?</h2>
              </div>
              <span>Inventory</span>
            </div>
            <label className="field-label" htmlFor="natural-inventory-update">Describe the stock change</label>
            <div className="natural-update-controls">
              <textarea
                id="natural-inventory-update"
                className="text-input natural-update-input"
                maxLength={1000}
                placeholder="Mark olive oil unavailable, or use 50 g mushrooms"
                required
                rows={2}
                value={naturalRequest}
                onChange={(event) => setNaturalRequest(event.target.value)}
              />
              <button className="primary-button natural-update-button" type="submit" disabled={updatingInventory || !naturalRequest.trim()}>
                {updatingInventory ? "Updating..." : "Update stock"}
                {!updatingInventory && <span aria-hidden="true">→</span>}
              </button>
            </div>
            {updateStatus && (
              <p className={`update-feedback ${updateStatus.kind}`} role={updateStatus.kind === "error" ? "alert" : "status"}>
                {updateStatus.kind === "pending" && <span className="loader" aria-hidden="true" />}
                {updateStatus.message}
              </p>
            )}
          </form>

          <div className="list-toolbar">
            <div>
              <p className="eyebrow">STOCK LIST</p>
              <h2>Ingredients <span className="count-mark">{ingredients.length}</span></h2>
            </div>
            <div className="filter-tabs" role="group" aria-label="Filter ingredients">
              {(["all", "pantry_staple", "rotating"] as const).map((value) => (
                <button
                  className={filter === value ? "filter-tab active" : "filter-tab"}
                  key={value}
                  type="button"
                  aria-pressed={filter === value}
                  onClick={() => setFilter(value)}
                >
                  {value === "all" ? "All" : value === "pantry_staple" ? "Pantry" : "Rotating"}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="list-state" role="status"><span className="loader" />Loading inventory</div>
          ) : visibleIngredients.length === 0 ? (
            <div className="list-state empty-state">
              <span className="empty-symbol" aria-hidden="true">+</span>
              <h3>{ingredients.length === 0 ? "A fresh start." : "Nothing in this view."}</h3>
              <p>{ingredients.length === 0 ? "Add what you have in the kitchen." : "Try another category filter."}</p>
            </div>
          ) : (
            <ul className="ingredient-list">
              {visibleIngredients.map((ingredient) => (
                <li className="ingredient-row" key={ingredient.id}>
                  <span className={`ingredient-marker ${ingredient.category}`} aria-hidden="true" />
                  <div className="ingredient-info">
                    <strong>{ingredient.name}</strong>
                    <span>{ingredient.category === "pantry_staple" ? "Pantry staple" : "Rotating ingredient"}</span>
                  </div>
                  <div className="ingredient-detail">
                    {ingredient.category === "pantry_staple" ? (
                      <span className={ingredient.available ? "availability available" : "availability unavailable"}>
                        <i aria-hidden="true" />{ingredient.available ? "Available" : "Unavailable"}
                      </span>
                    ) : (
                      <>
                        <strong>{ingredient.quantity} <span>{ingredient.unit}</span></strong>
                        <span>{ingredient.expiry_date ? `Use by ${ingredient.expiry_date}` : "No expiry date"}</span>
                      </>
                    )}
                  </div>
                  <div className="row-actions">
                    <button className="icon-button" type="button" aria-label={`Edit ${ingredient.name}`} title="Edit" onClick={() => beginEdit(ingredient)}>
                      <span aria-hidden="true">✎</span>
                    </button>
                    <button className="icon-button delete-button" type="button" aria-label={`Delete ${ingredient.name}`} title="Delete" onClick={() => void deleteIngredient(ingredient)}>
                      <span aria-hidden="true">×</span>
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {!loading && ingredients.length > 0 && (
            <footer className="list-footer">Showing {visibleIngredients.length} of {ingredients.length} ingredients</footer>
          )}
        </div>

        <aside className="editor-panel" aria-labelledby="editor-title">
          <div className="editor-heading">
            <p className="eyebrow">{editingId === null ? "ADD TO YOUR STOCK" : "UPDATE YOUR STOCK"}</p>
            <h2 id="editor-title">{editingId === null ? "New ingredient" : "Edit ingredient"}</h2>
          </div>
          <form onSubmit={(event) => void submitIngredient(event)}>
            <fieldset className="category-picker">
              <legend>Ingredient type</legend>
              <label className={draft.category === "pantry_staple" ? "category-option selected" : "category-option"}>
                <input type="radio" name="category" value="pantry_staple" checked={draft.category === "pantry_staple"} onChange={() => chooseCategory("pantry_staple")} />
                <span className="category-icon pantry-icon" aria-hidden="true">P</span>
                <span>Pantry staple</span>
              </label>
              <label className={draft.category === "rotating" ? "category-option selected" : "category-option"}>
                <input type="radio" name="category" value="rotating" checked={draft.category === "rotating"} onChange={() => chooseCategory("rotating")} />
                <span className="category-icon rotating-icon" aria-hidden="true">R</span>
                <span>Rotating</span>
              </label>
            </fieldset>

            <label className="field-label" htmlFor="ingredient-name">Ingredient name</label>
            <input
              id="ingredient-name"
              className="text-input"
              autoComplete="off"
              maxLength={120}
              placeholder={draft.category === "pantry_staple" ? "e.g. Olive oil" : "e.g. Cherry tomatoes"}
              required
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />

            {draft.category === "pantry_staple" ? (
              <label className="availability-toggle">
                <span><strong>Available</strong><small>Is this staple currently in stock?</small></span>
                <input type="checkbox" checked={draft.available} onChange={(event) => setDraft({ ...draft, available: event.target.checked })} />
              </label>
            ) : (
              <>
                <div className="field-pair">
                  <div>
                    <label className="field-label" htmlFor="ingredient-quantity">Quantity</label>
                    <input
                      id="ingredient-quantity"
                      className="text-input"
                      type="number"
                      min="0.000001"
                      step="any"
                      placeholder="0"
                      required
                      value={draft.quantity}
                      onChange={(event) => setDraft({ ...draft, quantity: event.target.value })}
                    />
                  </div>
                  <div>
                    <label className="field-label" htmlFor="ingredient-unit">Unit</label>
                    <input
                      id="ingredient-unit"
                      className="text-input"
                      maxLength={40}
                      placeholder="g, ml, pcs"
                      required
                      value={draft.unit}
                      onChange={(event) => setDraft({ ...draft, unit: event.target.value })}
                    />
                  </div>
                </div>
                <label className="field-label" htmlFor="ingredient-expiry">Expiry date <span>Optional</span></label>
                <input
                  id="ingredient-expiry"
                  className="text-input date-input"
                  type="date"
                  value={draft.expiryDate}
                  onChange={(event) => setDraft({ ...draft, expiryDate: event.target.value })}
                />
              </>
            )}

            <div className="form-actions">
              <button className="primary-button" type="submit" disabled={saving}>
                {saving ? "Saving..." : editingId === null ? "Add ingredient" : "Save changes"}
                {!saving && <span aria-hidden="true">→</span>}
              </button>
              {editingId !== null && <button className="text-button cancel-button" type="button" onClick={cancelEdit}>Cancel</button>}
            </div>
          </form>
        </aside>
      </section>
      ) : activeView === "suggestions" ? (
        <section className="suggestion-workspace" aria-label="Recipe suggestions">
          {notebookError && <div className="error-banner" role="alert">{notebookError}</div>}
          <form className="suggestion-controls" onSubmit={(event) => void submitRecipeRequest(event)}>
            <div>
              <p className="eyebrow">ON-DEMAND RECIPE</p>
              <h2>Cook from what you have</h2>
            </div>
            <label className="field-label" htmlFor="requested-servings">Servings</label>
            <input
              id="requested-servings"
              className="text-input servings-input"
              type="number"
              min="1"
              max="12"
              step="1"
              required
              value={requestedServings}
              onChange={(event) => setRequestedServings(event.target.value)}
            />
            <button className="primary-button" type="submit" disabled={recipeLoading}>
              {recipeLoading ? "Finding a recipe..." : "Suggest a recipe"}
              {!recipeLoading && <span aria-hidden="true">→</span>}
            </button>
            <p className="suggestion-note">Uses available inventory. Suggestions are not saved.</p>
          </form>

          <div className="suggestion-result" aria-live="polite">
            {recipeLoading ? (
              <div className="suggestion-state" role="status"><span className="loader" />Building a recipe from your stock</div>
            ) : recipeError ? (
              <div className="suggestion-state suggestion-error" role="alert">{recipeError}</div>
            ) : recipe ? (
              <article className="recipe-result">
                <header className="recipe-heading">
                  <div>
                    <p className="eyebrow">YOUR SUGGESTION / {recipe.servings} SERVINGS</p>
                    <h2>{recipe.title}</h2>
                  </div>
                  <span className="recipe-time">{recipe.preparation_time_minutes} min</span>
                </header>
                <div className="recipe-columns">
                  <div className="recipe-ingredients">
                    <h3>Ingredients</h3>
                    <ul>
                      {recipe.ingredients.map((item, index) => (
                        <li key={`${item.name}-${index}`}><span>{item.name}</span><strong>{item.quantity} {item.unit}</strong></li>
                      ))}
                    </ul>
                    {recipe.missing_ingredients.length > 0 && (
                      <div className="missing-list">
                        <h3>To pick up</h3>
                        <ul>
                          {recipe.missing_ingredients.map((item) => (
                            <li key={item.name}><span>{item.name}</span><strong>{item.quantity} {item.unit}</strong></li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  <div className="recipe-method">
                    <h3>Method</h3>
                    <ol>
                      {recipe.steps.map((step, index) => <li key={index}>{step}</li>)}
                    </ol>
                  </div>
                </div>
                <footer className="recipe-notes">
                  <p><strong>Why it fits</strong>{recipe.stock_explanation}</p>
                  {recipe.substitutions.length > 0 && (
                    <p><strong>Substitutions</strong>{recipe.substitutions.join(" · ")}</p>
                  )}
                </footer>
                <section className="confirm-cooked" aria-labelledby="confirm-cooked-title">
                  <div>
                    <p className="eyebrow">COOKED THIS RECIPE?</p>
                    <h3 id="confirm-cooked-title">Save your first attempt</h3>
                  </div>
                  <AttemptEditor submitLabel="Confirm cooked" saving={notebookSaving} onSave={confirmCooked} />
                </section>
              </article>
            ) : (
              <div className="suggestion-state suggestion-empty">
                <span className="empty-symbol" aria-hidden="true">+</span>
                <h2>Start with your stock.</h2>
                <p>Choose a serving count to get a recipe suggestion.</p>
              </div>
            )}
          </div>
        </section>
      ) : (
        <section className="notebook-workspace" aria-label="Cooking notebook">
          <header className="notebook-toolbar">
            <div>
              <p className="eyebrow">COOKING NOTEBOOK</p>
              <h2>Recipes you have made</h2>
            </div>
            <button className="icon-button" type="button" aria-label="Refresh notebook" title="Refresh" disabled={notebookLoading} onClick={() => void loadNotebook()}>
              <span aria-hidden="true">↻</span>
            </button>
          </header>
          {notebookError && <div className="error-banner" role="alert">{notebookError}</div>}
          {notebookLoading ? (
            <div className="notebook-state" role="status"><span className="loader" />Loading notebook</div>
          ) : notebook.length === 0 ? (
            <div className="notebook-state notebook-empty">
              <h3>Your first cooked recipe goes here.</h3>
              <p>Suggestions stay out of the notebook until you confirm you cooked them.</p>
              <button className="text-button" type="button" onClick={() => setActiveView("suggestions")}>Find a recipe</button>
            </div>
          ) : (
            <div className="notebook-list">
              {notebook.map((entry) => (
                <article className="notebook-recipe" key={entry.id}>
                  <header className="notebook-recipe-heading">
                    <div>
                      <p className="eyebrow">{entry.recipe.servings} SERVINGS / {entry.recipe.preparation_time_minutes} MIN</p>
                      <h3>{entry.recipe.title}</h3>
                    </div>
                    <button className="text-button" type="button" aria-expanded={openAttemptId === entry.id} onClick={() => setOpenAttemptId(openAttemptId === entry.id ? null : entry.id)}>
                      {openAttemptId === entry.id ? "Cancel" : "Add attempt"}
                    </button>
                  </header>
                  <div className="notebook-recipe-details">
                    <div>
                      <h4>Ingredients</h4>
                      <ul>{entry.recipe.ingredients.map((item, index) => <li key={`${item.name}-${index}`}>{item.quantity} {item.unit} {item.name}</li>)}</ul>
                    </div>
                    <div>
                      <h4>Method</h4>
                      <ol>{entry.recipe.steps.map((step, index) => <li key={index}>{step}</li>)}</ol>
                    </div>
                  </div>
                  <div className="notebook-recipe-notes">
                    {entry.recipe.missing_ingredients.length > 0 && (
                      <div>
                        <h4>To pick up</h4>
                        <p>{entry.recipe.missing_ingredients.map((item) => `${item.quantity} ${item.unit} ${item.name}`).join(" · ")}</p>
                      </div>
                    )}
                    {entry.recipe.substitutions.length > 0 && (
                      <div>
                        <h4>Suggested substitutions</h4>
                        <p>{entry.recipe.substitutions.join(" · ")}</p>
                      </div>
                    )}
                    <div>
                      <h4>Why it fits</h4>
                      <p>{entry.recipe.stock_explanation}</p>
                    </div>
                  </div>
                  <div className="attempt-history">
                    <h4>Attempt history <span>{entry.attempts.length}</span></h4>
                    {entry.attempts.map((item, index) => (
                      <article className="attempt-record" key={item.id}>
                        <header><strong>Attempt {index + 1}</strong><span>{item.attempt_date} · {item.rating} / 5</span></header>
                        {item.comments && <p>{item.comments}</p>}
                        {item.changes.length > 0 && <p><strong>Changes</strong>{item.changes.join(" · ")}</p>}
                        {item.substitutions.length > 0 && <p><strong>Substitutions</strong>{item.substitutions.join(" · ")}</p>}
                        {item.liked_adjustments.length > 0 && <p className="liked-record"><strong>Liked</strong>{item.liked_adjustments.join(" · ")}</p>}
                      </article>
                    ))}
                  </div>
                  {openAttemptId === entry.id && (
                    <AttemptEditor key={`attempt-${entry.id}`} submitLabel="Save attempt" saving={notebookSaving} onSave={(attempt) => appendAttempt(entry.id, attempt)} />
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      )}
      <footer className="app-footer"><span>Simple stock. Better cooking.</span><span>SAVORLOOP <i>·</i> {activeView.toUpperCase()}</span></footer>
    </main>
  );
}