import os
import json
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import pillow_heif
from moviepy.video.io.VideoFileClip import VideoFileClip  # Updated import for Render compatibility

main = Blueprint("main", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp", "heic", "mp4", "mov", "avi", "mkv"}

DESCRIPTION_FILE = "descriptions.json"
ALBUM_FILE = "albums.json"
COMMENTS_FILE = "comments.json"  # For commenting feature
THUMB_FOLDER = os.path.join("static", "thumbnails")

os.makedirs(THUMB_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def generate_video_thumbnail(video_path, thumb_path):
    """
    Generates a video thumbnail by:
      - Extracting a frame at half the video's duration (or 0.1 sec for very short videos)
      - Converting the frame to a PIL image
      - Converting to RGB if needed
      - Resizing the image to a width of 320px (maintaining aspect ratio) using Resampling.LANCZOS
      - Saving the image as a JPEG thumbnail at thumb_path
    """
    clip = VideoFileClip(video_path)
    timestamp = clip.duration / 2 if clip.duration > 1 else 0.1
    frame = clip.get_frame(timestamp)
    image = Image.fromarray(frame)
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Resize the image to a thumbnail of width 320px while maintaining the aspect ratio
    thumb_width = 320
    wpercent = thumb_width / float(image.size[0])
    thumb_height = int(float(image.size[1]) * wpercent)
    # Use the updated Resampling.LANCZOS for high-quality downsampling
    image = image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
    
    image.save(thumb_path, format="JPEG")
    clip.close()

@main.route("/")
def index():
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    descriptions = load_json(DESCRIPTION_FILE)
    albums = load_json(ALBUM_FILE)
    comments = load_json(COMMENTS_FILE)  # Load comments for each file if available

    image_files = os.listdir(upload_folder)
    image_files.sort(key=lambda x: os.path.getmtime(os.path.join(upload_folder, x)), reverse=True)

    images = []
    for file in image_files:
        ext = file.rsplit(".", 1)[-1].lower()
        image_data = {
            "filename": file,
            "description": descriptions.get(file, ""),
            "album": albums.get(file, ""),
            "type": "video" if ext in {"mp4", "mov", "avi", "mkv"} else "image",
            "thumb": f"thumbnails/{file.rsplit('.', 1)[0]}.jpg" if ext in {"mp4", "mov", "avi", "mkv"} else None,
            "comments": comments.get(file, [])
        }
        images.append(image_data)

    return render_template("gallery.html", images=images, descriptions=descriptions, albums=albums)

@main.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        files = request.files.getlist("photos")
        album = request.form.get("album")
        descriptions = load_json(DESCRIPTION_FILE)
        albums = load_json(ALBUM_FILE)
        comments = load_json(COMMENTS_FILE)

        for file in files:
            if file and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                ext = original_filename.rsplit(".", 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

                if ext == "heic":
                    try:
                        heif_file = pillow_heif.read_heif(file.stream)
                        image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
                        filename = f"{uuid.uuid4().hex}.jpg"
                        save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                        image.save(save_path, format="JPEG")
                        flash("HEIC image converted and uploaded.")
                    except Exception as e:
                        flash(f"HEIC conversion failed: {e}")
                        continue
                else:
                    file.save(save_path)

                # Generate video thumbnail if applicable
                if ext in {"mp4", "mov", "avi", "mkv"}:
                    thumb_path = os.path.join(THUMB_FOLDER, f"{filename.rsplit('.', 1)[0]}.jpg")
                    try:
                        generate_video_thumbnail(save_path, thumb_path)
                    except Exception as e:
                        flash(f"Thumbnail generation failed: {e}")

                if album:
                    albums[filename] = album

                descriptions[filename] = ""
                comments[filename] = []

        save_json(DESCRIPTION_FILE, descriptions)
        save_json(ALBUM_FILE, albums)
        save_json(COMMENTS_FILE, comments)
        flash("Upload successful.")
        return redirect(url_for("main.index"))

    return render_template("upload.html")

@main.route("/delete/<filename>", methods=["POST"])
def delete_image(filename):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(upload_folder, filename)
    thumb_path = os.path.join(THUMB_FOLDER, f"{filename.rsplit('.', 1)[0]}.jpg")

    descriptions = load_json(DESCRIPTION_FILE)
    albums = load_json(ALBUM_FILE)
    comments = load_json(COMMENTS_FILE)

    if os.path.exists(file_path):
        os.remove(file_path)
        descriptions.pop(filename, None)
        albums.pop(filename, None)
        comments.pop(filename, None)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        flash(f"{filename} deleted.")
    else:
        flash(f"{filename} not found.")

    save_json(DESCRIPTION_FILE, descriptions)
    save_json(ALBUM_FILE, albums)
    save_json(COMMENTS_FILE, comments)
    return redirect(url_for("main.index"))

@main.route("/download/<filename>")
def download_image(filename):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_folder, filename, as_attachment=True)

@main.route("/update_description/<filename>", methods=["POST"])
def update_description(filename):
    descriptions = load_json(DESCRIPTION_FILE)
    new_description = request.form.get("description", "")
    descriptions[filename] = new_description
    save_json(DESCRIPTION_FILE, descriptions)
    flash("Description updated.")
    return redirect(url_for("main.index"))

@main.route("/add_comment/<filename>", methods=["POST"])
def add_comment(filename):
    comments = load_json(COMMENTS_FILE)
    new_comment = request.form.get("comment", "").strip()
    if new_comment:
        if filename not in comments:
            comments[filename] = []
        comments[filename].append(new_comment)
        save_json(COMMENTS_FILE, comments)
        flash("Comment added.")
    else:
        flash("Empty comment not added.")
    return redirect(url_for("main.index"))
