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

const emptyDraft = (category: IngredientCategory = "rotating"): IngredientDraft => ({
  category,
  name: "",
  available: true,
  quantity: "",
  unit: "",
  expiryDate: "",
});

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
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [draft, setDraft] = useState<IngredientDraft>(() => emptyDraft());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [filter, setFilter] = useState<CategoryFilter>("all");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

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

  useEffect(() => {
    void loadInventory();
  }, []);

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

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="SavorLoop home">
          <span className="wordmark-mark" aria-hidden="true">S</span>
          <span>SavorLoop</span>
        </a>
        <span className="topbar-label">Kitchen inventory</span>
        <span className="topbar-dot" aria-label="Single-user kitchen" />
      </header>

      <section className="page-heading" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">YOUR KITCHEN / INVENTORY</p>
          <h1 id="page-title">What's on hand<span>?</span></h1>
        </div>
        <div className="inventory-summary" aria-label="Inventory totals">
          <div><strong>{pantryCount.toString().padStart(2, "0")}</strong><span>Pantry</span></div>
          <div><strong>{rotatingCount.toString().padStart(2, "0")}</strong><span>Fresh &amp; rotating</span></div>
          <div><strong>{ingredients.length.toString().padStart(2, "0")}</strong><span>Total items</span></div>
        </div>
      </section>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button className="text-button" type="button" onClick={() => void loadInventory()}>
            Retry
          </button>
        </div>
      )}

      <section className="inventory-workspace" aria-label="Inventory management">
        <div className="inventory-panel">
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
      <footer className="app-footer"><span>Simple stock. Better cooking.</span><span>SAVORLOOP <i>·</i> INVENTORY</span></footer>
    </main>
  );
}