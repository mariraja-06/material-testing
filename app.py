from flask import Flask, render_template, request
import csv
import os

app = Flask(__name__)

CSV_FILE = "materials.csv"


def load_materials():
    """Load materials from CSV file. Returns a list of dicts."""
    materials = []
    if not os.path.exists(CSV_FILE):
        return materials
    try:
        with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    materials.append({
                        "Material":    row["Material"].strip(),
                        "Strength":    float(row["Strength (MPa)"]),
                        "Density":     float(row["Density (kg/m3)"]),  # Keep in kg/m³
                        "Temperature": float(row["Max Temp (C)"]),
                        "Cost":        float(row["Cost (Rs/kg)"]),
                    })
                except (ValueError, KeyError):
                    continue  # skip rows with missing/invalid data
    except Exception:
        pass
    return materials


def compute_scores(materials):
    """Add a Score field to each material dict using normalised formula."""
    if not materials:
        return materials

    max_strength = max(m["Strength"]    for m in materials)
    min_density  = min(m["Density"]     for m in materials)
    max_temp     = max(m["Temperature"] for m in materials)

    for m in materials:
        strength_norm    = m["Strength"]    / max_strength   if max_strength  else 0
        density_norm     = min_density      / m["Density"]   if m["Density"]  else 0
        temperature_norm = m["Temperature"] / max_temp       if max_temp      else 0

        m["Score"] = round(
            (strength_norm * 0.5) +
            (density_norm  * 0.3) +
            (temperature_norm * 0.2),
            4
        )
    return materials


def filter_materials(materials, req_strength, max_density, req_temp):
    """Return materials that are within ±100 of all required values."""
    return [
        m for m in materials
        if abs(m["Strength"] - req_strength) <= 100
        and abs(m["Density"] - max_density) <= 100
        and abs(m["Temperature"] - req_temp) <= 100
    ]


@app.route("/", methods=["GET", "POST"])
def index():
    results      = []
    chart_data   = {}
    error        = None
    searched     = False

    materials = load_materials()

    if not materials:
        error = "No materials found. Make sure 'materials.csv' exists and is not empty."

    if request.method == "POST" and materials:
        searched = True
        try:
            req_strength = float(request.form["strength"])
            max_density  = float(request.form["density"])
            req_temp     = float(request.form["temperature"])
        except ValueError:
            error = "Please enter valid numbers for all fields."
            return render_template("index.html", results=results,
                                   chart_data=chart_data, error=error,
                                   searched=searched)

        # Score full dataset first
        scored = compute_scores([m.copy() for m in materials])

        # Calculate distance to inputs for each material
        for m in scored:
            m["Distance"] = (
                (m["Strength"] - req_strength) ** 2 +
                (m["Density"] - max_density) ** 2 +
                (m["Temperature"] - req_temp) ** 2
            ) ** 0.5

        # Select top 5 closest materials
        closest = sorted(scored, key=lambda m: m["Distance"])[:5]

        # Rank them by score
        results = sorted(closest, key=lambda m: m["Score"], reverse=True)

        # Chart data for Chart.js
        chart_data = {
            "labels":      [m["Material"]    for m in results],
            "strength":    [m["Strength"]    for m in results],
            "density":     [m["Density"]     for m in results],
            "temperature": [m["Temperature"] for m in results],
        }

    return render_template("index.html",
                           results=results,
                           chart_data=chart_data,
                           error=error,
                           searched=searched)


if __name__ == "__main__":
    app.run(debug=True)
