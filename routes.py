from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_file, url_for

from services.candidature import (
    CATEGORIES,
    PRIORITES,
    STATUTS,
    TYPES,
    create_candidature,
    delete_candidature,
    list_candidatures,
    load_candidature,
    load_historique,
    render_markdown,
    update_candidature,
    validate_status,
)
from services.cibles import CATEGORIES as CIBLE_CATEGORIES
from services.cibles import (
    create_cible,
    create_contact,
    delete_cible,
    delete_contact,
    get_cible_detail,
    list_all_cibles,
    load_cibles,
    toggle_cible,
    update_cible,
    update_contact,
)
from services.dashboard import regenerate_dashboard
from services.database import Cible, db
from services.fichiers import delete_fichier, get_fichier_path, upload_fichier
from services.search import search_candidatures
from services.settings import get_all_settings, get_cv_reference_html, get_setting, set_setting, upload_cv_reference

bp = Blueprint("main", __name__)


def is_htmx_request():
    """Check if the current request is an HTMX request."""
    return request.headers.get("HX-Request") == "true"


def render_htmx(*templates, **kwargs):
    """Render partials + OOB flash for HTMX responses."""
    html = "".join(render_template(t, **kwargs) for t in templates)
    return html + render_template("partials/flash.html")


# ---------------------------------------------------------------------------
# US1 - Dashboard
# ---------------------------------------------------------------------------


@bp.route("/")
def dashboard():
    candidatures = list_candidatures()
    return render_template(
        "dashboard.html",
        candidatures=candidatures,
        statuts=STATUTS,
        types=TYPES,
        priorites=PRIORITES,
        categories=CATEGORIES,
    )


# ---------------------------------------------------------------------------
# US2 - Detail (placeholder route for url_for, full template later)
# ---------------------------------------------------------------------------


@bp.route("/candidature/<slug>")
def detail(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)
    html_content = render_markdown(c["contenu"]) if c["contenu"] else ""
    historique = load_historique(slug)
    for h in historique:
        h["commentaire_html"] = render_markdown(h["commentaire"]) if h["commentaire"] else None
    cv_ref_configured = bool(get_cv_reference_html())
    return render_template(
        "detail.html",
        c=c,
        html_content=html_content,
        historique=historique,
        statuts=STATUTS,
        priorites=PRIORITES,
        categories=CATEGORIES,
        cv_reference_configured=cv_ref_configured,
    )


@bp.route("/candidature/<slug>/fichier/<path:filename>")
def fichier(slug, filename):
    file_path = get_fichier_path(slug, filename)
    if file_path is None:
        abort(404)

    if file_path.suffix.lower() == ".md":
        content = file_path.read_text(encoding="utf-8")
        html_content = render_markdown(content)
    else:
        html_content = None

    return render_template(
        "file_view.html", slug=slug, filename=filename, html_content=html_content, c=load_candidature(slug)
    )


@bp.route("/candidature/<slug>/upload", methods=["POST"])
def upload(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)

    file = request.files.get("file")
    if file is None or file.filename == "":
        flash("Aucun fichier selectionne.", "danger")
        if is_htmx_request():
            c = load_candidature(slug)
            return render_htmx("partials/file_list.html", c=c)
        return redirect(url_for("main.detail", slug=slug))

    try:
        upload_fichier(slug, file)
        flash(f"Fichier '{file.filename}' ajoute.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    if is_htmx_request():
        c = load_candidature(slug)
        return render_htmx("partials/file_list.html", c=c)
    return redirect(url_for("main.detail", slug=slug))


@bp.route("/candidature/<slug>/fichier/<path:filename>/delete", methods=["POST"])
def fichier_delete(slug, filename):
    c = load_candidature(slug)
    if c is None:
        abort(404)

    success = delete_fichier(slug, filename)
    if success:
        flash(f"Fichier '{filename}' supprime.", "success")
    else:
        flash(f"Fichier '{filename}' introuvable.", "danger")

    if is_htmx_request():
        c = load_candidature(slug)
        return render_htmx("partials/file_list.html", c=c)
    return redirect(url_for("main.detail", slug=slug))


@bp.route("/candidature/<slug>/fichier/<path:filename>/download")
def fichier_download(slug, filename):
    file_path = get_fichier_path(slug, filename)
    if file_path is None:
        abort(404)

    return send_file(file_path, as_attachment=True)


@bp.route("/candidature/<slug>/delete", methods=["POST"])
def candidature_delete(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)

    entreprise = c["entreprise"]
    delete_candidature(slug)
    flash(f"Candidature '{entreprise}' supprimee.", "success")
    return redirect(url_for("main.dashboard"))


@bp.route("/candidature/<slug>/archive", methods=["POST"])
def candidature_archive(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)

    if not validate_status(c["statut"], "archivee"):
        flash("Cette candidature ne peut pas etre archivee.", "danger")
        return redirect(url_for("main.detail", slug=slug))

    update_candidature(slug, {"statut": "archivee"})
    flash(f"Candidature '{c['entreprise']}' archivee.", "success")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# US3 - Update candidature
# ---------------------------------------------------------------------------


@bp.route("/candidature/<slug>/update", methods=["POST"])
def update(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)

    fields = {}

    # Statut
    new_statut = request.form.get("statut")
    if new_statut:
        if new_statut not in STATUTS:
            flash("Statut invalide.", "danger")
            return redirect(url_for("main.detail", slug=slug))
        if not validate_status(c.get("statut", ""), new_statut):
            flash(f"Transition de statut non autorisee: {c.get('statut')} -> {new_statut}", "danger")
            return redirect(url_for("main.detail", slug=slug))
        fields["statut"] = new_statut

    # Priorite
    new_priorite = request.form.get("priorite")
    if new_priorite:
        if new_priorite not in PRIORITES:
            flash("Priorite invalide.", "danger")
            return redirect(url_for("main.detail", slug=slug))
        fields["priorite"] = new_priorite

    # Categorie entreprise
    new_categorie = request.form.get("categorie_entreprise")
    if new_categorie:
        if new_categorie not in CATEGORIES:
            flash("Categorie invalide.", "danger")
            return redirect(url_for("main.detail", slug=slug))
        fields["categorie_entreprise"] = new_categorie

    # Dates
    for date_field in ("date_candidature", "date_relance"):
        val = request.form.get(date_field)
        if val is not None:
            # Accept empty string or YYYY-MM-DD
            if val and not _is_valid_date(val):
                flash(f"Format de date invalide pour {date_field} (attendu: AAAA-MM-JJ).", "danger")
                return redirect(url_for("main.detail", slug=slug))
            fields[date_field] = val

    if fields:
        # Read commentaire from modal hidden input (only relevant when statut changes)
        commentaire = request.form.get("commentaire", "").strip() or None
        update_candidature(slug, fields, commentaire=commentaire)
        flash("Candidature mise a jour.", "success")

    if is_htmx_request():
        c = load_candidature(slug)
        historique = load_historique(slug)
        for h in historique:
            h["commentaire_html"] = render_markdown(h["commentaire"]) if h["commentaire"] else None
        meta_html = render_template("partials/detail_meta.html", c=c)
        timeline_html = render_template("partials/timeline.html", historique=historique)
        flash_html = render_template("partials/flash.html")
        # OOB swaps for timeline and header badge
        statut = c["statut"]
        oob_timeline = f'<div id="timeline-container" hx-swap-oob="outerHTML:#timeline-container">{timeline_html}</div>'
        oob_badge = (
            f'<span id="header-badge" class="badge badge-{statut}"'
            f' hx-swap-oob="outerHTML:#header-badge">{statut}</span>'
        )
        return meta_html + oob_timeline + oob_badge + flash_html
    return redirect(url_for("main.detail", slug=slug))


def _is_valid_date(s: str) -> bool:
    """Validate YYYY-MM-DD format."""
    import re

    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", s))


# ---------------------------------------------------------------------------
# US4 - Create candidature
# ---------------------------------------------------------------------------


@bp.route("/candidature/new", methods=["GET"])
def create_candidature_form():
    prefill_cible = None
    cible_id_str = request.args.get("cible_id")
    if cible_id_str:
        try:
            cible_id = int(cible_id_str)
        except ValueError:
            flash("Identifiant de cible invalide.", "danger")
            return redirect(url_for("main.cibles"))
        prefill_cible = db.session.get(Cible, cible_id)
        if prefill_cible is None:
            flash("Cible introuvable.", "danger")
            return redirect(url_for("main.cibles"))
    return render_template(
        "create.html", types=TYPES, priorites=PRIORITES, cibles=list_all_cibles(), prefill_cible=prefill_cible
    )


@bp.route("/candidature/new", methods=["POST"])
def create_candidature_submit():
    # Extract cible_id early to preserve it in error redirects
    cible_id_str = request.form.get("cible_id", "")
    redirect_kwargs = {}
    if cible_id_str:
        try:
            redirect_kwargs["cible_id"] = int(cible_id_str)
        except ValueError:
            pass

    def _redirect_back():
        return redirect(url_for("main.create_candidature_form", **redirect_kwargs))

    entreprise = request.form.get("entreprise", "").strip()
    if not entreprise:
        flash("Le nom de l'entreprise est requis.", "danger")
        return _redirect_back()

    ctype = request.form.get("type", "offre")
    if ctype not in TYPES:
        flash("Type invalide.", "danger")
        return _redirect_back()

    priorite = request.form.get("priorite", "moyenne")
    if priorite not in PRIORITES:
        flash("Priorite invalide.", "danger")
        return _redirect_back()

    if not cible_id_str:
        flash("La cible est requise.", "danger")
        return _redirect_back()
    try:
        cible_id = int(cible_id_str)
    except ValueError:
        flash("Cible invalide.", "danger")
        return _redirect_back()

    data = {
        "entreprise": entreprise,
        "poste": request.form.get("poste", ""),
        "type": ctype,
        "localisation": request.form.get("localisation", ""),
        "priorite": priorite,
        "cible_id": cible_id,
        "contenu": request.form.get("contenu", ""),
    }

    try:
        slug = create_candidature(data)
        flash(f"Candidature '{entreprise}' creee.", "success")

        # Upload attached files
        for file in request.files.getlist("fichiers"):
            if file and file.filename:
                try:
                    upload_fichier(slug, file)
                except ValueError as e:
                    flash(f"Fichier '{file.filename}' : {e}", "warning")

        return redirect(url_for("main.detail", slug=slug))
    except FileExistsError:
        flash(f"Une candidature pour '{entreprise}' existe deja.", "warning")
        return _redirect_back()
    except ValueError as e:
        flash(str(e), "danger")
        return _redirect_back()


# ---------------------------------------------------------------------------
# US5 - Statistics
# ---------------------------------------------------------------------------


@bp.route("/stats")
def stats():
    candidatures = list_candidatures()

    by_statut = {}
    for s in STATUTS:
        by_statut[s] = sum(1 for c in candidatures if c.get("statut") == s)

    by_type = {}
    for t in TYPES:
        by_type[t] = sum(1 for c in candidatures if c.get("type") == t)

    by_priorite = {}
    for p in PRIORITES:
        by_priorite[p] = sum(1 for c in candidatures if c.get("priorite") == p)

    by_categorie = {}
    for cat in CATEGORIES:
        by_categorie[cat] = sum(1 for c in candidatures if c.get("categorie_entreprise", "entreprise") == cat)

    # Timeline: sorted by date_candidature (exclude empty)
    timeline = sorted(
        [c for c in candidatures if c.get("date_candidature")],
        key=lambda c: c["date_candidature"],
    )

    return render_template(
        "stats.html",
        total=len(candidatures),
        by_statut=by_statut,
        by_type=by_type,
        by_priorite=by_priorite,
        by_categorie=by_categorie,
        timeline=timeline,
    )


# ---------------------------------------------------------------------------
# US6 - Dashboard regeneration
# ---------------------------------------------------------------------------


@bp.route("/dashboard/regenerate", methods=["POST"])
def dashboard_regenerate():
    regenerate_dashboard()
    flash("Dashboard 00-Dashboard.md regenere avec succes.", "success")
    if is_htmx_request():
        return render_template("partials/flash.html")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------------------------------
# US7 - Cibles
# ---------------------------------------------------------------------------


@bp.route("/cibles")
def cibles():
    data = load_cibles()
    return render_template("cibles.html", cibles=data)


@bp.route("/cibles/toggle", methods=["POST"])
def cibles_toggle():
    company = request.form.get("company", "").strip()
    checked_str = request.form.get("checked", "false")
    if not company:
        return jsonify({"ok": False, "error": "company is required"}), 400
    checked = checked_str.lower() == "true"
    result = toggle_cible(company, checked)
    if result is False:
        return jsonify({"ok": False, "error": "company not found"}), 404
    if result is None:
        return jsonify({"ok": False, "error": "cible verrouillee par des candidatures existantes"}), 409
    return jsonify({"ok": True})


@bp.route("/cibles/add", methods=["POST"])
def cibles_add():
    nom = request.form.get("nom", "").strip()
    categorie = request.form.get("categorie", "").strip()
    url = request.form.get("url", "").strip()
    description = request.form.get("description", "").strip()
    email = request.form.get("email", "").strip()
    linkedin = request.form.get("linkedin", "").strip()
    if not nom:
        flash("Le nom est requis.", "danger")
        if is_htmx_request():
            return render_htmx("partials/cibles_list.html", cibles=load_cibles())
        return redirect(url_for("main.cibles"))
    if categorie not in CIBLE_CATEGORIES:
        flash("Categorie invalide.", "danger")
        if is_htmx_request():
            return render_htmx("partials/cibles_list.html", cibles=load_cibles())
        return redirect(url_for("main.cibles"))
    try:
        create_cible(nom, categorie, url=url, description=description, email=email, linkedin=linkedin)
        flash(f"'{nom}' ajoutee.", "success")
    except Exception:
        flash(f"Erreur lors de l'ajout de '{nom}'.", "danger")
    if is_htmx_request():
        return render_htmx("partials/cibles_list.html", cibles=load_cibles())
    return redirect(url_for("main.cibles"))


@bp.route("/cibles/<int:cible_id>/edit", methods=["POST"])
def cibles_edit(cible_id):
    fields = {}
    nom = request.form.get("nom", "").strip()
    if nom:
        fields["nom"] = nom
    url = request.form.get("url")
    if url is not None:
        fields["url"] = url.strip()
    description = request.form.get("description")
    if description is not None:
        fields["description"] = description.strip()
    email = request.form.get("email")
    if email is not None:
        fields["email"] = email.strip()
    linkedin = request.form.get("linkedin")
    if linkedin is not None:
        fields["linkedin"] = linkedin.strip()
    if not fields:
        flash("Aucun champ a mettre a jour.", "danger")
        if is_htmx_request():
            return render_htmx("partials/cibles_list.html", cibles=load_cibles())
        return redirect(url_for("main.cibles"))
    cible = update_cible(cible_id, **fields)
    if cible is None:
        flash("Cible introuvable.", "danger")
    else:
        flash("Cible mise a jour.", "success")
    if is_htmx_request():
        return render_htmx("partials/cibles_list.html", cibles=load_cibles())
    return redirect(url_for("main.cibles"))


@bp.route("/cibles/<int:cible_id>/delete", methods=["POST"])
def cibles_delete(cible_id):
    success = delete_cible(cible_id)
    if not success:
        flash("Cible introuvable.", "danger")
    else:
        flash("Cible supprimee.", "success")
    if is_htmx_request():
        return render_htmx("partials/cibles_list.html", cibles=load_cibles())
    return redirect(url_for("main.cibles"))


# ---------------------------------------------------------------------------
# Fiche cible + Contacts
# ---------------------------------------------------------------------------

CIBLE_CATEGORIES_LIST = list(CIBLE_CATEGORIES)


@bp.route("/cible/<int:cible_id>")
def cible_detail(cible_id):
    data = get_cible_detail(cible_id)
    if data is None:
        abort(404)
    tavily_configured = bool(get_setting("tavily_api_key"))
    llm_configured = bool(get_setting("llm_provider"))
    return render_template(
        "cible_detail.html",
        cible=data,
        categories=CIBLE_CATEGORIES_LIST,
        enrichment_available=tavily_configured and llm_configured,
    )


@bp.route("/cible/<int:cible_id>/edit", methods=["POST"])
def cible_detail_edit(cible_id):
    fields = {}
    nom = request.form.get("nom", "").strip()
    if nom:
        fields["nom"] = nom
    categorie = request.form.get("categorie")
    if categorie and categorie in CIBLE_CATEGORIES:
        fields["categorie"] = categorie
    url = request.form.get("url")
    if url is not None:
        fields["url"] = url.strip()
    description = request.form.get("description")
    if description is not None:
        fields["description"] = description.strip()
    email = request.form.get("email")
    if email is not None:
        fields["email"] = email.strip()
    linkedin = request.form.get("linkedin")
    if linkedin is not None:
        fields["linkedin"] = linkedin.strip()
    if not fields:
        flash("Aucun champ a mettre a jour.", "danger")
        return redirect(url_for("main.cible_detail", cible_id=cible_id))
    cible = update_cible(cible_id, **fields)
    if cible is None:
        abort(404)
    flash("Cible mise a jour.", "success")
    return redirect(url_for("main.cible_detail", cible_id=cible_id))


@bp.route("/cible/<int:cible_id>/delete", methods=["POST"])
def cible_detail_delete(cible_id):
    success = delete_cible(cible_id)
    if not success:
        abort(404)
    flash("Cible supprimee.", "success")
    return redirect(url_for("main.cibles"))


@bp.route("/cible/<int:cible_id>/contact/add", methods=["POST"])
def contact_add(cible_id):
    nom = request.form.get("nom", "").strip()
    if not nom:
        flash("Le nom du contact est requis.", "danger")
        if is_htmx_request():
            data = get_cible_detail(cible_id)
            return render_htmx("partials/contacts_list.html", cible=data)
        return redirect(url_for("main.cible_detail", cible_id=cible_id))
    fields = {
        "nom": nom,
        "prenom": request.form.get("prenom", "").strip(),
        "email": request.form.get("email", "").strip(),
        "telephone": request.form.get("telephone", "").strip(),
        "linkedin": request.form.get("linkedin", "").strip(),
        "fonction": request.form.get("fonction", "").strip(),
    }
    contact = create_contact(cible_id, **fields)
    if contact is None:
        abort(404)
    flash(f"Contact '{nom}' ajoute.", "success")
    if is_htmx_request():
        data = get_cible_detail(cible_id)
        return render_htmx("partials/contacts_list.html", cible=data)
    return redirect(url_for("main.cible_detail", cible_id=cible_id))


@bp.route("/cible/<int:cible_id>/contact/<int:contact_id>/edit", methods=["POST"])
def contact_edit(cible_id, contact_id):
    fields = {}
    for field in ("nom", "prenom", "email", "telephone", "linkedin", "fonction"):
        val = request.form.get(field)
        if val is not None:
            fields[field] = val.strip()
    if not fields:
        flash("Aucun champ a mettre a jour.", "danger")
        if is_htmx_request():
            data = get_cible_detail(cible_id)
            return render_htmx("partials/contacts_list.html", cible=data)
        return redirect(url_for("main.cible_detail", cible_id=cible_id))
    contact = update_contact(contact_id, **fields)
    if contact is None:
        abort(404)
    flash("Contact mis a jour.", "success")
    if is_htmx_request():
        data = get_cible_detail(cible_id)
        return render_htmx("partials/contacts_list.html", cible=data)
    return redirect(url_for("main.cible_detail", cible_id=cible_id))


@bp.route("/cible/<int:cible_id>/contact/<int:contact_id>/delete", methods=["POST"])
def contact_delete(cible_id, contact_id):
    success = delete_contact(contact_id)
    if not success:
        abort(404)
    flash("Contact supprime.", "success")
    if is_htmx_request():
        data = get_cible_detail(cible_id)
        return render_htmx("partials/contacts_list.html", cible=data)
    return redirect(url_for("main.cible_detail", cible_id=cible_id))


# ---------------------------------------------------------------------------
# US8 - Search
# ---------------------------------------------------------------------------


@bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = []
    if query:
        results = search_candidatures(query)
    if is_htmx_request():
        return render_template("partials/search_results.html", query=query, results=results)
    return render_template("search.html", query=query, results=results)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CV Adaptation
# ---------------------------------------------------------------------------


@bp.route("/candidature/<slug>/cv/adapt")
def cv_loading(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)
    cv_source = request.args.get("cv_source", "auto")
    return render_template(
        "cv_loading.html",
        slug=slug,
        entreprise=c["entreprise"],
        poste=c.get("poste", ""),
        cv_source=cv_source,
    )


@bp.route("/candidature/<slug>/cv/preview")
def cv_preview(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)
    return render_template(
        "cv_preview.html",
        slug=slug,
        entreprise=c["entreprise"],
    )


@bp.route("/candidature/<slug>/cv/save", methods=["POST"])
def cv_save(slug):
    c = load_candidature(slug)
    if c is None:
        abort(404)

    adapted_html = request.form.get("adapted_html", "")
    if not adapted_html:
        flash("Aucun contenu HTML a sauvegarder.", "danger")
        return redirect(url_for("main.detail", slug=slug))

    try:
        from services.cv_adapter import save_adapted_cv

        save_adapted_cv(slug, adapted_html)
        flash("CV adapte sauvegarde (PDF + DOCX).", "success")
    except ValueError as e:
        flash(str(e), "danger")

    return redirect(url_for("main.detail", slug=slug))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@bp.route("/settings")
def settings_page():
    from services.cv_adapter import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT_TEMPLATE

    all_settings = get_all_settings()
    return render_template(
        "settings.html",
        cv_reference_configured=bool(all_settings.get("cv_reference_html")),
        cv_reference_date=all_settings.get("cv_reference_date", ""),
        llm_provider=all_settings.get("llm_provider", ""),
        llm_ollama_url=all_settings.get("llm_ollama_url", "http://localhost:11434"),
        llm_ollama_model=all_settings.get("llm_ollama_model", "llama3.2"),
        llm_claude_model=all_settings.get("llm_claude_model", "claude-sonnet-4-20250514"),
        llm_claude_api_key_configured=bool(all_settings.get("llm_claude_api_key")),
        tavily_api_key_configured=bool(all_settings.get("tavily_api_key")),
        system_prompt=all_settings.get("cv_adapt_system_prompt", ""),
        user_prompt_template=all_settings.get("cv_adapt_user_prompt", ""),
        default_system_prompt=DEFAULT_SYSTEM_PROMPT,
        default_user_prompt_template=DEFAULT_USER_PROMPT_TEMPLATE,
    )


@bp.route("/settings/cv-reference", methods=["POST"])
def upload_cv_reference_route():
    file = request.files.get("file")
    if file is None or not file.filename:
        flash("Aucun fichier selectionne.", "danger")
        if is_htmx_request():
            return render_template("partials/flash.html")
        return redirect(url_for("main.settings_page"))

    if not file.filename.endswith(".html"):
        flash("Le fichier doit etre au format HTML (.html).", "danger")
        if is_htmx_request():
            return render_template("partials/flash.html")
        return redirect(url_for("main.settings_page"))

    content = file.read().decode("utf-8", errors="replace")
    try:
        upload_cv_reference(content)
        flash("CV de reference mis a jour.", "success")
    except ValueError as e:
        flash(str(e), "danger")

    if is_htmx_request():
        return render_template("partials/flash.html")
    return redirect(url_for("main.settings_page"))


@bp.route("/settings/llm", methods=["POST"])
def update_llm_config():
    from services.schemas import LLMConfigUpdate

    try:
        config = LLMConfigUpdate(
            provider=request.form.get("provider", "ollama"),
            ollama_url=request.form.get("ollama_url", "http://localhost:11434"),
            ollama_model=request.form.get("ollama_model", "llama3.2"),
            claude_api_key=request.form.get("claude_api_key", ""),
            claude_model=request.form.get("claude_model", "claude-sonnet-4-20250514"),
        )
    except ValueError as e:
        flash(str(e), "danger")
        if is_htmx_request():
            return render_template("partials/flash.html")
        return redirect(url_for("main.settings_page"))

    set_setting("llm_provider", config.provider)
    if config.provider == "ollama":
        set_setting("llm_ollama_url", config.ollama_url)
        set_setting("llm_ollama_model", config.ollama_model)
    elif config.provider == "claude":
        if config.claude_api_key:
            set_setting("llm_claude_api_key", config.claude_api_key)
        set_setting("llm_claude_model", config.claude_model)

    flash("Configuration LLM mise a jour.", "success")
    if is_htmx_request():
        return render_template("partials/flash.html")
    return redirect(url_for("main.settings_page"))


@bp.route("/settings/prompts", methods=["POST"])
def update_prompts():
    system_prompt = request.form.get("system_prompt", "").strip()
    user_prompt = request.form.get("user_prompt", "").strip()

    if system_prompt:
        set_setting("cv_adapt_system_prompt", system_prompt)
    else:
        set_setting("cv_adapt_system_prompt", "")

    if user_prompt:
        set_setting("cv_adapt_user_prompt", user_prompt)
    else:
        set_setting("cv_adapt_user_prompt", "")

    flash("Prompts LLM mis a jour.", "success")
    if is_htmx_request():
        return render_template("partials/flash.html")
    return redirect(url_for("main.settings_page"))


@bp.route("/settings/llm/health", methods=["POST"])
def llm_health_check_route():
    from services.llm import get_provider

    try:
        provider = get_provider()
        result = provider.health_check()
        flash(f"Fournisseur LLM accessible ({result.get('provider', 'ok')})", "success")
    except (ValueError, ConnectionError) as e:
        flash(str(e), "danger")

    return redirect(url_for("main.settings_page"))


# ---------------------------------------------------------------------------
# Settings: Tavily
# ---------------------------------------------------------------------------


@bp.route("/settings/tavily", methods=["POST"])
def update_tavily_config():
    api_key = request.form.get("tavily_api_key", "").strip()
    if api_key:
        set_setting("tavily_api_key", api_key)
        flash("Configuration Tavily mise a jour.", "success")
    else:
        flash("Cle API Tavily requise.", "danger")

    if is_htmx_request():
        return render_template("partials/flash.html")
    return redirect(url_for("main.settings_page"))


# ---------------------------------------------------------------------------
# Cible enrichment (AI)
# ---------------------------------------------------------------------------


@bp.route("/cible/<int:cible_id>/enrich")
def cible_enrich_loading(cible_id):
    data = get_cible_detail(cible_id)
    if data is None:
        abort(404)
    return render_template("cible_enrich_loading.html", cible=data)


@bp.route("/cible/<int:cible_id>/enrich/preview")
def cible_enrich_preview(cible_id):
    data = get_cible_detail(cible_id)
    if data is None:
        abort(404)
    return render_template("cible_enrich_preview.html", cible=data)
