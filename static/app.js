// Frontend mínimo: consume la API REST con el JWT guardado en localStorage.
// Todo el contenido (incluido el que genera el LLM) se inserta con textContent
// para evitar XSS.

const TOKEN_KEY = "recetas_token";
const page = document.body.dataset.page;

const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// ------------------------------------------------------------- utilidades
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of [].concat(children)) {
    if (c == null || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

function toast(msg, type = "ok") {
  const box = document.getElementById("toast");
  box.textContent = msg;
  box.className = `toast ${type === "error" ? "error" : ""}`;
  box.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (box.hidden = true), type === "error" ? 6000 : 3000);
}

function errorMessage(data, fallback) {
  if (!data || !data.detail) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((d) => d.msg.replace(/^Value error, /, "")).join(". ");
  }
  return fallback;
}

async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) {
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(path, { method, headers, body: payload });
  } catch {
    throw new Error("No hay conexión con el servidor. Revisa tu internet e inténtalo de nuevo.");
  }
  if (res.status === 401 && page !== "login") {
    clearToken();
    location.href = "/login";
    throw new Error("Tu sesión expiró. Inicia sesión de nuevo.");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, `Error ${res.status}`));
  return data;
}

const fmtFecha = (iso) =>
  new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short", year: "numeric" });

const fmtCantidad = (it) =>
  it.cantidad != null ? `${Number(it.cantidad).toLocaleString("es-CO")} ${it.unidad || ""}`.trim() : "Sin cantidad";

function setBusy(btn, busy, label) {
  btn.disabled = busy;
  btn.replaceChildren(...(busy ? [el("span", { class: "spinner", "aria-hidden": "true" }), label] : [label]));
}

// ------------------------------------------------------------- sesión
async function requireAuth() {
  if (!getToken()) {
    location.href = "/login";
    return null;
  }
  const user = await api("/api/auth/me");
  document.getElementById("nav-user").textContent = user.nombre;
  return user;
}

document.getElementById("logout")?.addEventListener("click", () => {
  clearToken();
  location.href = "/login";
});

async function doLogin(email, password) {
  const data = await api("/api/auth/login", { method: "POST", form: { username: email, password } });
  setToken(data.access_token);
  location.href = "/ingredientes";
}

function initLogin() {
  if (getToken()) location.href = "/ingredientes";
  const form = document.getElementById("login-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(form);
    const btn = form.querySelector("button[type=submit]");
    setBusy(btn, true, "Entrando…");
    try {
      await doLogin(f.get("email"), f.get("password"));
    } catch (err) {
      toast(err.message, "error");
      setBusy(btn, false, "Entrar");
    }
  });
}

function initRegister() {
  const form = document.getElementById("register-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(form);
    const btn = form.querySelector("button[type=submit]");
    setBusy(btn, true, "Creando cuenta…");
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: { nombre: f.get("nombre"), email: f.get("email"), password: f.get("password") },
      });
      await doLogin(f.get("email"), f.get("password"));
    } catch (err) {
      toast(err.message, "error");
      setBusy(btn, false, "Crear cuenta");
    }
  });
}

// ------------------------------------------------------------- ficha de receta
function starsWidget(recipe, onRated) {
  const wrap = el("span", { class: "stars", role: "group", "aria-label": "Calificar receta" });
  const paint = () =>
    [...wrap.children].forEach((b, i) => b.classList.toggle("on", i < (recipe.calificacion || 0)));
  for (let i = 1; i <= 5; i++) {
    wrap.append(
      el("button", {
        type: "button",
        class: "star",
        text: "★",
        "aria-label": `${i} de 5 estrellas`,
        onclick: async () => {
          try {
            await api(`/api/recipes/${recipe.id}/rating`, { method: "PUT", body: { estrellas: i } });
            recipe.calificacion = i;
            paint();
            toast(`Calificaste la receta con ${i} de 5 estrellas`);
            onRated?.();
          } catch (err) {
            toast(err.message, "error");
          }
        },
      })
    );
  }
  paint();
  return wrap;
}

function recipeSheet(recipe, { onDelete, onRated } = {}) {
  return el("article", { class: "sheet" }, [
    el("header", { class: "sheet-head" }, [
      el("h2", { text: recipe.nombre }),
      el("dl", { class: "facts" }, [
        el("div", {}, [el("dt", { text: "Tiempo" }), el("dd", { text: `${recipe.tiempo_minutos} min` })]),
        el("div", {}, [el("dt", { text: "Dificultad" }), el("dd", { class: "cap", text: recipe.dificultad })]),
        el("div", {}, [el("dt", { text: "Ingredientes" }), el("dd", { text: recipe.ingredientes.length })]),
        el("div", {}, [el("dt", { text: "Tu calificación" }), el("dd", {}, starsWidget(recipe, onRated))]),
      ]),
    ]),
    el("div", { class: "sheet-body" }, [
      el("section", {}, [
        el("h3", { text: "Ingredientes" }),
        el(
          "ul",
          { class: "checklist" },
          recipe.ingredientes.map((i) =>
            el("li", {}, el("label", {}, [
              el("input", { type: "checkbox" }),
              el("span", { class: "ing", text: i.nombre }),
              el("span", { class: "amount", text: i.cantidad }),
            ]))
          )
        ),
      ]),
      el("section", {}, [
        el("h3", { text: "Preparación" }),
        el("ol", { class: "steps" }, recipe.pasos.map((p) => el("li", {}, el("span", { text: p })))),
      ]),
    ]),
    el("footer", { class: "sheet-foot" }, [
      el("span", { text: `Generada el ${fmtFecha(recipe.creado_en)} con el modelo ${recipe.modelo_llm}` }),
      onDelete
        ? el("button", {
            type: "button",
            class: "btn btn-danger btn-sm",
            text: "Eliminar receta",
            onclick: async () => {
              if (!confirm(`¿Eliminar «${recipe.nombre}» de tu historial?`)) return;
              try {
                await api(`/api/recipes/${recipe.id}`, { method: "DELETE" });
                toast("Receta eliminada");
                onDelete();
              } catch (err) {
                toast(err.message, "error");
              }
            },
          })
        : null,
    ]),
  ]);
}

// ------------------------------------------------------------- inventario
async function initIngredients() {
  if (!(await requireAuth())) return;
  const form = document.getElementById("ingredient-form");
  const list = document.getElementById("ingredient-list");
  const empty = document.getElementById("ingredient-empty");
  const submit = document.getElementById("ingredient-submit");
  const cancel = document.getElementById("ingredient-cancel");
  const genBtn = document.getElementById("generate-btn");
  const genSummary = document.getElementById("gen-summary");
  let editingId = null;

  const resetForm = () => {
    form.reset();
    form.elements.id.value = "";
    editingId = null;
    submit.textContent = "Agregar";
    cancel.hidden = true;
    list.querySelector(".editing")?.classList.remove("editing");
  };

  async function load() {
    const items = await api("/api/ingredients");
    empty.hidden = items.length > 0;
    genBtn.disabled = items.length === 0;
    genSummary.textContent =
      items.length === 0
        ? "Agrega ingredientes para empezar."
        : items.length === 1
          ? "Tienes 1 ingrediente. Agrega más para obtener mejores recetas."
          : `Tienes ${items.length} ingredientes disponibles.`;

    list.replaceChildren(
      ...items.map((it) =>
        el("li", { class: it.id === editingId ? "editing" : "" }, [
          el("span", { class: "name", text: it.nombre }),
          el("span", { class: "qty", text: fmtCantidad(it) }),
          el("span", { class: "row-actions" }, [
            el("button", {
              type: "button",
              class: "icon-btn",
              text: "Editar",
              "aria-label": `Editar ${it.nombre}`,
              onclick: (e) => {
                list.querySelector(".editing")?.classList.remove("editing");
                e.target.closest("li").classList.add("editing");
                editingId = it.id;
                form.elements.id.value = it.id;
                form.elements.nombre.value = it.nombre;
                form.elements.cantidad.value = it.cantidad ?? "";
                form.elements.unidad.value = it.unidad ?? "";
                submit.textContent = "Guardar cambios";
                cancel.hidden = false;
                form.elements.nombre.focus();
              },
            }),
            el("button", {
              type: "button",
              class: "icon-btn del",
              text: "Quitar",
              "aria-label": `Quitar ${it.nombre}`,
              onclick: async () => {
                try {
                  await api(`/api/ingredients/${it.id}`, { method: "DELETE" });
                  if (editingId === it.id) resetForm();
                  toast(`Quitaste ${it.nombre} del inventario`);
                  await load();
                } catch (err) {
                  toast(err.message, "error");
                }
              },
            }),
          ]),
        ])
      )
    );
  }

  // Autocompletado con el catálogo de ingredientes reconocidos
  api("/api/ingredients/catalogo")
    .then((nombres) =>
      document.getElementById("catalogo").replaceChildren(...nombres.map((n) => el("option", { value: n })))
    )
    .catch(() => {});

  cancel.addEventListener("click", resetForm);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(form);
    const body = {
      nombre: f.get("nombre"),
      cantidad: f.get("cantidad") ? Number(f.get("cantidad")) : null,
      unidad: f.get("unidad") || null,
    };
    const id = f.get("id");
    try {
      const guardado = await api(id ? `/api/ingredients/${id}` : "/api/ingredients", {
        method: id ? "PUT" : "POST",
        body,
      });
      toast(id ? "Cambios guardados" : `Agregaste ${guardado.nombre} al inventario`);
      resetForm();
      await load();
      form.elements.nombre.focus();
    } catch (err) {
      toast(err.message, "error");
    }
  });

  const genForm = document.getElementById("generate-form");
  const output = document.getElementById("generated");
  genForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(genForm);
    setBusy(genBtn, true, "Generando receta…");
    try {
      const recipe = await api("/api/recipes/generate", {
        method: "POST",
        body: {
          porciones: Number(f.get("porciones") || 2),
          preferencias: f.get("preferencias") || null,
          tipo: f.get("tipo") || null,
        },
      });
      output.replaceChildren(
        el("div", { class: "generated-head" }, [
          el("h2", { text: "Tu receta" }),
          el("a", { href: "/recetas", text: "Ver todas mis recetas" }),
        ]),
        recipeSheet(recipe)
      );
      output.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(genBtn, false, "Generar receta");
    }
  });

  await load();
}

// ------------------------------------------------------------- historial
async function initRecipes() {
  if (!(await requireAuth())) return;
  const view = document.getElementById("recipes-view");
  const list = document.getElementById("recipe-list");
  const detail = document.getElementById("recipe-detail");
  const empty = document.getElementById("recipes-empty");
  const summary = document.getElementById("recipes-summary");

  let recipes = await api("/api/recipes?limit=100");
  let selectedId = Number(new URLSearchParams(location.search).get("id")) || recipes[0]?.id;

  const starsText = (n) =>
    el("span", { class: "stars-static", "aria-label": n ? `${n} de 5 estrellas` : "Sin calificar" }, [
      "★".repeat(n || 0),
      el("span", { class: "off", text: "★".repeat(5 - (n || 0)) }),
    ]);

  function render() {
    const hay = recipes.length > 0;
    view.hidden = !hay;
    empty.hidden = hay;
    summary.textContent = hay
      ? `Tienes ${recipes.length} receta${recipes.length > 1 ? "s" : ""} guardada${recipes.length > 1 ? "s" : ""}.`
      : "Recetas que has generado, de la más reciente a la más antigua.";
    if (!hay) return;
    if (!recipes.some((r) => r.id === selectedId)) selectedId = recipes[0].id;

    list.replaceChildren(
      ...recipes.map((r) =>
        el("li", {}, el("button", {
          type: "button",
          "aria-current": r.id === selectedId ? "true" : "false",
          onclick: () => {
            selectedId = r.id;
            history.replaceState(null, "", `?id=${r.id}`);
            render();
            if (matchMedia("(max-width: 960px)").matches) detail.scrollIntoView();
          },
        }, [
          el("span", { class: "r-name", text: r.nombre }),
          el("span", { class: "r-meta" }, [
            el("span", { text: `${fmtFecha(r.creado_en)}, ${r.tiempo_minutos} min` }),
            starsText(r.calificacion),
          ]),
        ]))
      )
    );

    const actual = recipes.find((r) => r.id === selectedId);
    detail.replaceChildren(
      recipeSheet(actual, {
        onRated: render,
        onDelete: () => {
          recipes = recipes.filter((r) => r.id !== actual.id);
          render();
        },
      })
    );
  }

  render();
}

const inits = {
  login: initLogin,
  register: initRegister,
  ingredients: initIngredients,
  recipes: initRecipes,
};
if (inits[page]) {
  Promise.resolve()
    .then(inits[page])
    .catch((err) => toast(err.message, "error"));
}
