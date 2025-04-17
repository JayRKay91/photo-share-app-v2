# ... (all previous imports and configuration remain exactly the same) ...

@main.route("/add_tag/<filename>", methods=["POST"])
def add_tag(filename):
    tags = load_json(TAGS_FILE)
    new_tag = request.form.get("tag", "").strip()
    if new_tag:
        tags.setdefault(filename, [])
        if new_tag not in tags[filename]:
            tags[filename].append(new_tag)
            save_json(TAGS_FILE, tags)
            flash(f"Tag '{new_tag}' added.")
        else:
            flash(f"Tag '{new_tag}' already exists.")
    else:
        flash("Empty tag not added.")
    return redirect(url_for("main.index"))

@main.route("/remove_tag/<filename>/<tag>", methods=["POST"])
def remove_tag(filename, tag):
    tags = load_json(TAGS_FILE)
    if filename in tags:
        updated = [t for t in tags[filename] if t.lower() != tag.lower()]
        tags[filename] = updated
        save_json(TAGS_FILE, tags)
        flash(f"Tag '{tag}' removed.")
    return redirect(url_for("main.index"))

@main.route("/rename_tag/<filename>", methods=["POST"])
def rename_tag_for_image(filename):
    tags = load_json(TAGS_FILE)
    old_tag = request.form.get("old_tag", "").strip()
    new_tag = request.form.get("new_tag", "").strip()

    if not old_tag or not new_tag:
        flash("Both old and new tag values are required.")
        return redirect(url_for("main.index"))

    if filename in tags:
        updated_tags = []
        changed = False
        for tag in tags[filename]:
            if tag.strip().lower() == old_tag.lower():
                updated_tags.append(new_tag)
                changed = True
            else:
                updated_tags.append(tag)
        if changed:
            tags[filename] = updated_tags
            save_json(TAGS_FILE, tags)
            flash(f"Tag '{old_tag}' renamed to '{new_tag}' for {filename}.")
        else:
            flash(f"Tag '{old_tag}' not found on {filename}.")

    return redirect(url_for("main.index"))

@main.route("/rename_tag_single", methods=["POST"])
def rename_tag_single():
    filename = request.form.get("filename")
    old_tag = request.form.get("old_tag", "").strip().lower()
    new_tag = request.form.get("new_tag", "").strip()

    tags = load_json(TAGS_FILE)

    if not filename or not old_tag or not new_tag:
        flash("Missing information for tag rename.")
        return redirect(url_for("main.index"))

    if filename in tags:
        updated_tags = [new_tag if t.lower() == old_tag else t for t in tags[filename]]
        tags[filename] = updated_tags
        save_json(TAGS_FILE, tags)
        flash(f"Renamed tag '{old_tag}' to '{new_tag}' for {filename}.")

    return redirect(url_for("main.index"))

@main.route("/rename_tag_global", methods=["POST"])
def rename_tag_global():
    tags = load_json(TAGS_FILE)
    old_tag = request.form.get("old_tag", "").strip().lower()
    new_tag = request.form.get("new_tag", "").strip()

    if not old_tag or not new_tag:
        flash("Both old and new tag names must be provided.")
        return redirect(url_for("main.index"))

    updated = False
    for filename, taglist in tags.items():
        updated_tags = []
        changed = False
        for tag in taglist:
            if tag.strip().lower() == old_tag:
                updated_tags.append(new_tag)
                changed = True
            else:
                updated_tags.append(tag)
        if changed:
            tags[filename] = updated_tags
            updated = True

    if updated:
        save_json(TAGS_FILE, tags)
        flash(f"Tag '{old_tag}' renamed to '{new_tag}' across the gallery.")
    else:
        flash(f"No tags found matching '{old_tag}'.")

    return redirect(url_for("main.index"))

# ... (all remaining routes stay exactly the same) ...