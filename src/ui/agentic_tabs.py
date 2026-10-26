"""Gradio tab builders for the two Agentic AI add-ons.

* :func:`build_api_config_tab` — a Cursor-style page to manage API provider
  profiles (keys, endpoints, models) backed by :class:`ProviderStore`.
* :func:`build_memory_tab` — a Codex-style local memory browser backed by the
  Hindsight :class:`HindsightStore` (projects + memories + search).

Both are built *inside* an existing ``gr.Blocks`` context and own their event
wiring. Each store is a module-level singleton, built lazily and
independently of the other on first use (see ``_ensure_provider_store`` /
``_ensure_memory_store``) so the tabs share one backend across the app's
lifetime without being able to take down the rest of the WebUI — or each
other's tab — at import time if local storage is unavailable. Every handler
funnels backend errors through ``_err`` so a failure shows up as a red
status line instead of a
stack trace.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import gradio as gr

from src.config import ProviderConfigError, ProviderStore, SUPPORTED_PROVIDERS
from src.config.provider_store import build_llm_kwargs
from src.memory import HindsightError, HindsightStore
from src.memory.models import MEMORY_TYPES
from src.qa import QAAgent, QAError
from src.utils.llm_provider import get_llm_model

logger = logging.getLogger(__name__)

# Shared singletons (local, file-backed), built lazily and INDEPENDENTLY —
# see _ensure_provider_store() / _ensure_memory_store(). Note: QAAgent is
# deliberately NOT a shared singleton — see do_ask()'s comment — a fresh,
# request-local one is built per question instead, sharing only the
# (stateless) store/retriever.
_provider_store: Optional[ProviderStore] = None
_memory_store: Optional[HindsightStore] = None
_provider_init_error: Optional[str] = None
_memory_init_error: Optional[str] = None


def _ensure_provider_store() -> bool:
    """Lazily construct the provider store on first use; returns readiness.

    Building these eagerly at import time (as module-level singletons) meant
    a read-only or otherwise unavailable ``./tmp`` directory would raise out
    of the ``import src.ui`` that ``src/webui/interface.py`` does at startup,
    taking down the *entire* WebUI (agent tabs included) over an optional
    add-on. Deferring construction to the first time a tab actually renders
    means that failure only disables the tab(s) that need it — and since a
    failure here leaves ``_provider_store`` as ``None`` rather than caching a
    permanent error, simply opening a tab again (e.g. switching away and
    back) retries construction for free.

    The provider store and the memory store are intentionally independent:
    an unavailable Hindsight directory must not also disable the unrelated
    API Config tab, and vice versa.
    """
    global _provider_store, _provider_init_error
    if _provider_store is not None:
        return True
    try:
        _provider_store = ProviderStore()
    except Exception as exc:  # noqa: BLE001 - surface as a tab-level error, never crash startup
        _provider_init_error = str(exc)
        logger.error("Could not initialize the provider store: %s", exc)
        return False
    return True


def _ensure_memory_store() -> bool:
    """Lazily construct the Hindsight memory store on first use. See
    :func:`_ensure_provider_store` for why this is lazy, independent of the
    provider store, and self-retrying."""
    global _memory_store, _memory_init_error
    if _memory_store is not None:
        return True
    try:
        _memory_store = HindsightStore()
    except Exception as exc:  # noqa: BLE001 - surface as a tab-level error, never crash startup
        _memory_init_error = str(exc)
        logger.error("Could not initialize the Hindsight memory store: %s", exc)
        return False
    return True


def _ok(msg: str) -> str:
    return f"✅ {msg}"


def _err(msg: str) -> str:
    return f"❌ {msg}"


# ====================================================================== #
# API Configuration tab
# ====================================================================== #
def _provider_rows() -> Tuple[List[list], List[str]]:
    """Return (dataframe rows, parallel id list) for the provider table."""
    rows, ids = [], []
    for p in _provider_store.list_profiles(public=True):
        rows.append([
            p["label"], p["provider"],
            "on" if p["enabled"] else "off",
            p["default_model"] or (p["models"][0] if p["models"] else ""),
            len(p["models"]),
            p["api_key"] if p["has_key"] else "—",
        ])
        ids.append(p["id"])
    return rows, ids


def _split_models(text: str) -> List[str]:
    """Parse a models textbox: split on newlines and commas."""
    if not text:
        return []
    parts: List[str] = []
    for line in text.replace(",", "\n").splitlines():
        line = line.strip()
        if line:
            parts.append(line)
    return parts


def build_api_config_tab() -> None:
    if not _ensure_provider_store():
        gr.Markdown(f"### 🔌 API Configuration\n⚠️ Unavailable: local storage for this "
                   f"feature could not be initialized ({_provider_init_error}).")
        return
    gr.Markdown(
        "### 🔌 API Configuration\n"
        "Manage LLM provider profiles — keys, endpoints and model lists — "
        "like Cursor's model settings. Keys are stored locally and shown masked."
    )
    _initial_rows, _initial_ids = _provider_rows()
    ids_state = gr.State(_initial_ids)
    selected_state = gr.State(None)

    with gr.Row():
        with gr.Column(scale=5):
            provider_table = gr.Dataframe(
                headers=["Label", "Provider", "Enabled", "Default model", "# Models", "API key"],
                datatype=["str", "str", "str", "str", "number", "str"],
                value=_initial_rows,
                interactive=False,
                label="Configured providers",
                wrap=True,
            )
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh")
                test_btn = gr.Button("🧪 Test selected")
                delete_btn = gr.Button("🗑️ Delete selected", variant="stop")
        with gr.Column(scale=4):
            gr.Markdown("#### Profile editor")
            f_label = gr.Textbox(label="Label", placeholder="e.g. My OpenAI")
            f_provider = gr.Dropdown(
                choices=list(SUPPORTED_PROVIDERS), value="openai", label="Provider type")
            f_key = gr.Textbox(label="API key", type="password",
                               placeholder="leave blank on update to keep existing key")
            f_base = gr.Textbox(label="Base URL (optional)",
                                placeholder="https://api.openai.com/v1")
            f_models = gr.Textbox(label="Models (one per line, or comma-separated)",
                                  lines=4, placeholder="gpt-4o\ngpt-4")
            f_default = gr.Textbox(label="Default model", placeholder="gpt-4o")
            f_enabled = gr.Checkbox(label="Enabled", value=True)
            with gr.Row():
                add_btn = gr.Button("➕ Add profile", variant="primary")
                update_btn = gr.Button("💾 Update selected")
                clear_btn = gr.Button("✨ Clear form")

    status = gr.Textbox(label="Status", interactive=False, lines=2)

    # ---- handlers ---------------------------------------------------- #
    def do_refresh():
        rows, ids = _provider_rows()
        return rows, ids, _ok(f"{len(ids)} provider profile(s).")

    def do_add(label, provider, key, base, models, default, enabled):
        try:
            _provider_store.add_profile(
                label=label, provider=provider, api_key=key or "",
                base_url=base or "", models=_split_models(models),
                default_model=default or "", enabled=bool(enabled))
            rows, ids = _provider_rows()
            return rows, ids, _ok(f"Added profile '{label}'.")
        except ProviderConfigError as exc:
            rows, ids = _provider_rows()
            return rows, ids, _err(str(exc))

    def do_update(selected, label, provider, key, base, models, default, enabled):
        if not selected:
            rows, ids = _provider_rows()
            return rows, ids, _err("Select a profile row first.")
        try:
            _provider_store.update_profile(
                selected, label=label, provider=provider, api_key=key or "",
                base_url=base or "", models=_split_models(models),
                default_model=default or "", enabled=bool(enabled))
            rows, ids = _provider_rows()
            return rows, ids, _ok("Profile updated.")
        except ProviderConfigError as exc:
            rows, ids = _provider_rows()
            return rows, ids, _err(str(exc))

    def do_delete(selected):
        if not selected:
            rows, ids = _provider_rows()
            return rows, ids, _err("Select a profile row first."), selected
        try:
            _provider_store.delete_profile(selected)
            rows, ids = _provider_rows()
            # Clear the selection along with the row: leaving a deleted id in
            # selected_state means Test/Update on the stale selection would
            # fail against a profile that no longer exists.
            return rows, ids, _ok("Profile deleted."), None
        except ProviderConfigError as exc:
            rows, ids = _provider_rows()
            return rows, ids, _err(str(exc)), selected

    def do_test(selected):
        if not selected:
            return _err("Select a profile row first.")
        try:
            result = _provider_store.test_profile(selected, live=False)
        except ProviderConfigError as exc:
            # e.g. the selected profile was deleted in another tab/session
            # since it was selected here.
            return _err(str(exc))
        if result.get("ok"):
            return _ok(result.get("message", "client built successfully."))
        return _err(f"[{result.get('stage')}] {result.get('error')}")

    def on_select(ids, evt: gr.SelectData):
        # evt.index is [row, col]; map the row to a profile id.
        if not ids or evt.index is None:
            return (gr.update(),) * 7 + (None,)
        row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
        if row >= len(ids):
            return (gr.update(),) * 7 + (None,)
        pid = ids[row]
        try:
            p = _provider_store.get_profile(pid)
        except ProviderConfigError:
            return (gr.update(),) * 7 + (None,)
        return (
            gr.update(value=p.label),
            gr.update(value=p.provider),
            gr.update(value=""),  # never populate the key field
            gr.update(value=p.base_url),
            gr.update(value="\n".join(p.models)),
            gr.update(value=p.default_model),
            gr.update(value=p.enabled),
            pid,
        )

    def do_clear():
        return ("", "openai", "", "", "", "", True, None)

    form = [f_label, f_provider, f_key, f_base, f_models, f_default, f_enabled]

    refresh_btn.click(do_refresh, outputs=[provider_table, ids_state, status])
    add_btn.click(do_add, inputs=form, outputs=[provider_table, ids_state, status])
    update_btn.click(do_update, inputs=[selected_state] + form,
                     outputs=[provider_table, ids_state, status])
    delete_btn.click(do_delete, inputs=[selected_state],
                     outputs=[provider_table, ids_state, status, selected_state])
    test_btn.click(do_test, inputs=[selected_state], outputs=[status])
    clear_btn.click(do_clear, outputs=form + [selected_state])
    provider_table.select(on_select, inputs=[ids_state], outputs=form + [selected_state])


# ====================================================================== #
# Hindsight memory tab
# ====================================================================== #
def _project_choices() -> List[Tuple[str, str]]:
    out = []
    try:
        for p in _memory_store.list_projects():
            out.append((f"{p.name}  ·  {p.id[-6:]}", p.id))
    except HindsightError as exc:
        logger.warning("listing projects failed: %s", exc)
    return out


def _memory_rows(project_id: str) -> Tuple[List[list], List[Tuple[str, str]]]:
    """Return (dataframe rows, parallel (project_id, memory_id) list).

    Each id is paired with its own project_id (even though every row here
    comes from the same project) so this list has the same shape as
    ``do_search``'s, which can span projects — letting row-selection code
    be project-agnostic either way.
    """
    rows, ids = [], []
    if not project_id:
        return rows, ids
    try:
        for m in _memory_store.list_memories(project_id):
            rows.append([m.title, m.type, ", ".join(m.tags),
                         (m.content[:60] + "…") if len(m.content) > 60 else m.content])
            ids.append((m.project_id, m.id))
    except HindsightError as exc:
        logger.warning("listing memories failed: %s", exc)
    return rows, ids


def build_memory_tab() -> None:
    if not _ensure_memory_store():
        gr.Markdown(f"### 🧠 Hindsight Memory\n⚠️ Unavailable: local storage for this "
                   f"feature could not be initialized ({_memory_init_error}).")
        return
    gr.Markdown(
        "### 🧠 Hindsight Memory\n"
        "A local, file-based memory system (Codex-style): organize **memories** "
        "into **projects**, search across them, all stored under `./tmp/hindsight`."
    )
    mem_ids_state = gr.State([])
    sel_mem_state = gr.State(None)
    # The query behind whatever is currently in mem_table — "" means "the
    # dropdown's project, unfiltered". Needed so Update/Delete can refresh
    # the table the same way it was populated: a cross-project search result
    # can't be refreshed with `_memory_rows(view_pid)` when view_pid is empty
    # (that call returns nothing for an empty project id), so it reruns the
    # same search instead.
    last_query_state = gr.State("")

    with gr.Row():
        project_dd = gr.Dropdown(choices=_project_choices(), label="Project",
                                 interactive=True)
        new_proj_name = gr.Textbox(label="New project name", scale=2)
        new_proj_desc = gr.Textbox(label="Description", scale=2)
        create_proj_btn = gr.Button("➕ Create project", variant="primary")
        del_proj_btn = gr.Button("🗑️ Delete project", variant="stop")

    with gr.Row():
        with gr.Column(scale=5):
            mem_table = gr.Dataframe(
                headers=["Title", "Type", "Tags", "Preview"],
                datatype=["str", "str", "str", "str"],
                interactive=False, label="Memories", wrap=True)
            with gr.Row():
                search_box = gr.Textbox(label="Search (title / content / tags)", scale=3)
                search_btn = gr.Button("🔍 Search")
                refresh_mem_btn = gr.Button("🔄 Refresh")
        with gr.Column(scale=4):
            gr.Markdown("#### Memory editor")
            m_title = gr.Textbox(label="Title")
            m_type = gr.Dropdown(choices=list(MEMORY_TYPES), value="note", label="Type")
            m_tags = gr.Textbox(label="Tags (comma-separated)")
            m_content = gr.Textbox(label="Content", lines=6)
            with gr.Row():
                add_mem_btn = gr.Button("➕ Add memory", variant="primary")
                update_mem_btn = gr.Button("💾 Update selected")
                del_mem_btn = gr.Button("🗑️ Delete selected", variant="stop")

    mem_status = gr.Textbox(label="Status", interactive=False, lines=2)

    def _tags(text: str) -> List[str]:
        return [t.strip() for t in (text or "").split(",") if t.strip()]

    # ---- project handlers ------------------------------------------- #
    def do_create_project(name, desc):
        try:
            p = _memory_store.create_project(name=name or "", description=desc or "")
            return (gr.update(choices=_project_choices(), value=p.id),
                    _ok(f"Created project '{p.name}'."), "", "")
        except HindsightError as exc:
            return gr.update(choices=_project_choices()), _err(str(exc)), name, desc

    def do_delete_project(pid):
        if not pid:
            return gr.update(), [], [], _err("Pick a project first.")
        try:
            _memory_store.delete_project(pid)
            choices = _project_choices()
            return gr.update(choices=choices, value=None), [], [], _ok("Project deleted.")
        except HindsightError as exc:
            return gr.update(), [], [], _err(str(exc))

    def _refresh_memory_view(view_pid, search_query):
        """Rebuild (rows, ids) the same way the table currently got them.

        ``search_query`` is ``None`` when the table is showing a plain
        per-project listing (``_memory_rows`` is correct and cheap), or a
        string — possibly "" — when it's showing search results, which can
        span every project. In that case ``_memory_rows(view_pid)`` would
        return nothing at all for an empty ``view_pid`` (an all-project
        search), so the same search is rerun instead.
        """
        if search_query is not None:
            try:
                results = _memory_store.search(search_query, project_id=view_pid or None)
                rows = [[m.title, m.type, ", ".join(m.tags),
                         (m.content[:60] + "…") if len(m.content) > 60 else m.content]
                        for m in results]
                ids = [(m.project_id, m.id) for m in results]
                return rows, ids
            except HindsightError as exc:
                logger.warning("re-running search to refresh the table failed: %s", exc)
                return [], []
        return _memory_rows(view_pid)

    def on_project_change(pid):
        rows, ids = _memory_rows(pid)
        # Clear the memory selection (see do_update_memory's comment) and
        # drop back to "plain listing" mode: whatever was in the search box
        # no longer describes what's on screen.
        return rows, ids, (_ok(f"{len(ids)} memories.") if pid else ""), None, None

    # ---- memory handlers -------------------------------------------- #
    def do_add_memory(pid, title, mtype, tags, content):
        if not pid:
            return gr.update(), [], _err("Pick a project first."), gr.update()
        try:
            _memory_store.add_memory(pid, title=title or "", content=content or "",
                                     type=mtype, tags=_tags(tags))
            rows, ids = _memory_rows(pid)
            # This repopulates the table via a plain per-project listing, not
            # a rerun of whatever search was active — so last_query_state
            # must drop back to None (see _refresh_memory_view), or the next
            # Update/Delete would refresh by rerunning a search the table no
            # longer reflects.
            return rows, ids, _ok("Memory added."), None
        except HindsightError as exc:
            rows, ids = _memory_rows(pid)
            return rows, ids, _err(str(exc)), None

    def do_update_memory(view_pid, sel, search_query, title, mtype, tags, content):
        if not sel:
            return gr.update(), [], _err("Select a memory row first.")
        # Use the selected row's OWN project_id for the store call, not the
        # dropdown's — a cross-project search result's project can differ
        # from whatever project the dropdown happens to show, and using the
        # dropdown's would silently update/delete the wrong (project,
        # memory) pair (or just fail with "not found").
        sel_pid, mid = sel
        try:
            _memory_store.update_memory(sel_pid, mid, title=title or "",
                                        content=content or "", type=mtype,
                                        tags=_tags(tags))
            rows, ids = _refresh_memory_view(view_pid, search_query)
            return rows, ids, _ok("Memory updated.")
        except HindsightError as exc:
            rows, ids = _refresh_memory_view(view_pid, search_query)
            return rows, ids, _err(str(exc))

    def do_delete_memory(view_pid, sel, search_query):
        if not sel:
            return gr.update(), [], _err("Select a memory row first.")
        sel_pid, mid = sel
        try:
            _memory_store.delete_memory(sel_pid, mid)
            rows, ids = _refresh_memory_view(view_pid, search_query)
            return rows, ids, _ok("Memory deleted.")
        except HindsightError as exc:
            rows, ids = _refresh_memory_view(view_pid, search_query)
            return rows, ids, _err(str(exc))

    def do_search(pid, query):
        try:
            results = _memory_store.search(query or "", project_id=pid or None)
            rows = [[m.title, m.type, ", ".join(m.tags),
                     (m.content[:60] + "…") if len(m.content) > 60 else m.content]
                    for m in results]
            # Each result's OWN project_id — `search()` can span every
            # project when `pid` is empty, and pairing every row with
            # whatever `pid` is currently selected would make a cross-project
            # match look selectable but actually open/update/delete the
            # wrong project's memory.
            ids = [(m.project_id, m.id) for m in results]
            # Remember this query (even "") so Update/Delete know to refresh
            # by rerunning the search, not by listing a single project.
            return rows, ids, _ok(f"{len(ids)} match(es)."), (query or "")
        except HindsightError as exc:
            return gr.update(), [], _err(str(exc)), gr.update()

    def on_mem_select(ids, evt: gr.SelectData):
        if not ids or evt.index is None:
            return gr.update(), gr.update(), gr.update(), gr.update(), None
        row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
        if row >= len(ids):
            return gr.update(), gr.update(), gr.update(), gr.update(), None
        sel_pid, mid = ids[row]
        try:
            m = _memory_store.get_memory(sel_pid, mid)
        except HindsightError:
            return gr.update(), gr.update(), gr.update(), gr.update(), None
        return (gr.update(value=m.title), gr.update(value=m.type),
                gr.update(value=", ".join(m.tags)), gr.update(value=m.content),
                (sel_pid, mid))

    create_proj_btn.click(do_create_project, inputs=[new_proj_name, new_proj_desc],
                          outputs=[project_dd, mem_status, new_proj_name, new_proj_desc])
    del_proj_btn.click(do_delete_project, inputs=[project_dd],
                       outputs=[project_dd, mem_table, mem_ids_state, mem_status])
    project_dd.change(on_project_change, inputs=[project_dd],
                      outputs=[mem_table, mem_ids_state, mem_status, sel_mem_state,
                              last_query_state])
    refresh_mem_btn.click(on_project_change, inputs=[project_dd],
                          outputs=[mem_table, mem_ids_state, mem_status, sel_mem_state,
                                  last_query_state])
    add_mem_btn.click(do_add_memory,
                      inputs=[project_dd, m_title, m_type, m_tags, m_content],
                      outputs=[mem_table, mem_ids_state, mem_status, last_query_state])
    update_mem_btn.click(do_update_memory,
                         inputs=[project_dd, sel_mem_state, last_query_state,
                                m_title, m_type, m_tags, m_content],
                         outputs=[mem_table, mem_ids_state, mem_status])
    del_mem_btn.click(do_delete_memory, inputs=[project_dd, sel_mem_state, last_query_state],
                      outputs=[mem_table, mem_ids_state, mem_status])
    search_btn.click(do_search, inputs=[project_dd, search_box],
                     outputs=[mem_table, mem_ids_state, mem_status, last_query_state])
    mem_table.select(on_mem_select, inputs=[mem_ids_state],
                     outputs=[m_title, m_type, m_tags, m_content, sel_mem_state])


# ====================================================================== #
# Agentic Q&A tab
# ====================================================================== #
def _provider_choices_for_qa() -> List[Tuple[str, str]]:
    out = [("(no LLM — extractive answers only)", "")]
    if not _ensure_provider_store():
        # Provider profiles just aren't offered — the QA tab itself stays
        # usable via the extractive fallback; only the memory store is a
        # hard dependency for this tab.
        return out
    try:
        for p in _provider_store.list_profiles(public=True):
            # Ollama is the one provider get_llm_model() doesn't require a
            # key for (it's a local server), so it's selectable without one;
            # every other provider still needs has_key.
            if p["enabled"] and (p["has_key"] or p["provider"] == "ollama"):
                out.append((f"{p['label']}  ·  {p['provider']}", p["id"]))
    except ProviderConfigError as exc:
        logger.warning("listing provider profiles failed: %s", exc)
    return out


def _build_llm_for_profile(profile_id: str):
    """Build a LangChain chat model for a provider profile, or None.

    Any failure (missing key, bad config, unreachable endpoint) degrades to
    "no LLM" rather than breaking the Q&A flow — the agent's extractive
    fallback still answers correctly, just less fluently.
    """
    if not profile_id:
        return None, ""
    if not _ensure_provider_store():
        return None, _err(f"Provider store unavailable ({_provider_init_error}); "
                          f"using extractive fallback instead.")
    try:
        profile = _provider_store.get_profile(profile_id)
        llm = get_llm_model(profile.provider, **build_llm_kwargs(profile))
        return llm, ""
    except (ProviderConfigError, ValueError, HindsightError) as exc:
        return None, _err(f"Could not build LLM from profile, using extractive "
                          f"fallback instead: {exc}")
    except Exception as exc:  # noqa: BLE001 - any provider SDK error
        return None, _err(f"LLM provider error, using extractive fallback instead: {exc}")


def build_qa_tab() -> None:
    # The memory store is a hard dependency (there's nothing to answer
    # questions from without it); the provider store is not — see
    # _provider_choices_for_qa()/_build_llm_for_profile(), which each
    # degrade to "no LLM" on their own if it's unavailable, so its failure
    # doesn't need to disable this whole tab.
    if not _ensure_memory_store():
        gr.Markdown(f"### 🤖 Agentic Q&A\n⚠️ Unavailable: local storage for this "
                   f"feature could not be initialized ({_memory_init_error}).")
        return
    gr.Markdown(
        "### 🤖 Agentic Q&A\n"
        "Ask a question grounded in the Hindsight memory store. The agent "
        "retrieves relevant memories, widens the search if the first pass is "
        "weak, and only answers with explicit `[memory_id]` citations — if "
        "nothing supports an answer, it says so instead of guessing."
    )
    with gr.Row():
        qa_project_dd = gr.Dropdown(choices=_project_choices(), label="Project "
                                    "(optional — searches all projects if empty)",
                                    interactive=True)
        qa_provider_dd = gr.Dropdown(choices=_provider_choices_for_qa(),
                                     value="", label="LLM provider profile")
        refresh_qa_btn = gr.Button("🔄 Refresh")

    qa_question = gr.Textbox(label="Question", lines=2,
                             placeholder="问一个这个知识库里的资料能回答的问题……")
    ask_btn = gr.Button("💬 Ask", variant="primary")

    qa_answer = gr.Textbox(label="Answer", lines=6, interactive=False)
    with gr.Row():
        qa_grounded = gr.Textbox(label="Grounded?", interactive=False, scale=1)
        qa_rounds = gr.Textbox(label="Retrieval rounds", interactive=False, scale=1)
    qa_sources = gr.Dataframe(
        headers=["memory_id", "Title", "Score", "Project"],
        datatype=["str", "str", "number", "str"],
        interactive=False, label="Sources used / retrieved")
    qa_status = gr.Textbox(label="Status", interactive=False, lines=2)

    def do_refresh():
        return (gr.update(choices=_project_choices()),
                gr.update(choices=_provider_choices_for_qa()))

    def do_ask(pid, profile_id, question):
        if not (question or "").strip():
            return "", "", "", [], _err("Type a question first.")

        llm, llm_status = _build_llm_for_profile(profile_id)
        # A fresh, request-local agent per call: `_qa_agent` is a module-level
        # singleton shared by every session, and mutating its `.llm` would be
        # a race under concurrent questions (one request's provider choice
        # could leak into another's answer). Reuse the shared store/retriever
        # (cheap, stateless) but never the agent object itself.
        agent = QAAgent(store=_memory_store, llm=llm)
        try:
            result = agent.ask(question, project_id=pid or None)
        except QAError as exc:
            return "", "", "", [], _err(str(exc))

        rows = [[s.id, s.title, s.score, s.project_id] for s in result.sources]
        grounded_label = "✅ yes" if result.grounded else "⚠️ refused (not grounded)"
        status = _ok(f"{result.rounds_used} retrieval round(s), "
                     f"{len(result.sources)} source(s).")
        if llm_status:
            status = f"{status}\n{llm_status}"
        return result.answer, grounded_label, str(result.rounds_used), rows, status

    refresh_qa_btn.click(do_refresh, outputs=[qa_project_dd, qa_provider_dd])
    ask_btn.click(do_ask, inputs=[qa_project_dd, qa_provider_dd, qa_question],
                 outputs=[qa_answer, qa_grounded, qa_rounds, qa_sources, qa_status])
