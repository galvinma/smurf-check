import json
import os

from flask import Flask, redirect, render_template, request

from app.static import IMAGES_DIR, PROFILES_DIR
from app.utils.date_utils import timestamp
from app.utils.file_utils import get_player_notes, write_json
from app.matches import empty_match_stats

app = Flask(__name__)


@app.route("/")
def index():
    profiles = []
    file_names = [f for f in os.listdir(f"{PROFILES_DIR}/stats") if f.endswith(".json")]
    for name in file_names:
        with open(f"{PROFILES_DIR}/stats/{name}") as f:
            profile = json.load(f)
            profiles.append({"character_id": profile["character_id"], "name": profile["name"]})

    profiles = sorted(profiles, key=lambda profile: profile["name"].lower())
    return render_template("index.html", profiles=profiles)


@app.route("/profile/<id>", methods=["GET", "POST"])
def profile(id):

    if request.method == "GET":
        with open(f"{PROFILES_DIR}/stats/{id}.json") as f:
            profile = json.load(f)

        notes = get_player_notes(id)
        mmr_plot = IMAGES_DIR / f"mmr_plot/{id}.png"

        if not profile.get("stats"):
            profile["stats"] = empty_match_stats()

        return render_template("profile.html", profile=profile, mmr_plot=mmr_plot, notes=notes)

    if request.method == "POST":
        notes = get_player_notes(id)
        notes[timestamp(format="%Y-%m-%d %H:%M:%S")] = request.form["player_notes"]
        write_json(notes, f"{PROFILES_DIR}/notes/{id}.json")
        return redirect(request.url)


@app.context_processor
def mmr_delta_utility_processor():
    def mmr_delta_background_color(mmr_delta=None):
        if mmr_delta is None:
            return "gray-background"

        if mmr_delta <= 300:
            return "green-background"
        elif 300 < mmr_delta < 500:
            return "yellow-background"
        else:
            return "red-background"

    return dict(mmr_delta_background_color=mmr_delta_background_color)


@app.context_processor
def smurf_result_ratio_utility_processor():
    def smurf_result_ratio_background_color(ratio=None):
        if ratio is None:
            return "gray-background"

        if ratio >= 0.95:
            return "green-background"
        elif 0.75 < ratio < 0.95:
            return "yellow-background"
        else:
            return "red-background"

    return dict(smurf_result_ratio_background_color=smurf_result_ratio_background_color)


@app.context_processor
def duration_ratio_utility_processor():
    def duration_ratio_background_color(ratio=None):
        if ratio is None:
            return "gray-background"

        if ratio <= 1.3:
            return "green-background"
        elif 1.3 < ratio < 1.7:
            return "yellow-background"
        else:
            return "red-background"

    return dict(duration_ratio_background_color=duration_ratio_background_color)


@app.context_processor
def smurf_loss_percent_background_color_utility_processor():
    def smurf_loss_percent_background_color(percent=None):
        if percent is None:
            return "gray-background"

        if percent <= 10:
            return "green-background"
        elif 10 < percent < 17.5:
            return "yellow-background"
        else:
            return "red-background"

    return dict(smurf_loss_percent_background_color=smurf_loss_percent_background_color)


@app.context_processor
def same_race_loss_percent_background_color_utility_processor():
    def same_race_loss_percent_background_color(percent=None):
        if percent is None:
            return "gray-background"

        if percent <= 60:
            return "green-background"
        elif 60 < percent < 70:
            return "yellow-background"
        else:
            return "red-background"

    return dict(same_race_loss_percent_background_color=same_race_loss_percent_background_color)


if __name__ == "__main__":
    app.run()
