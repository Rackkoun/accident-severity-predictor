"""
Human-readable labels used by the frontend
Backend values remain unchanged; only the displayed labels are translated
"""

FEATURES_LABELS = {
    "place": "Seat Position",
    "catu": "Road User",
    "sexe": "Sex",
    "secu1": "Safety Equipment",
    "year_acc": "Accident Year",
    "victim_age": "Victim Age",
    "nb_victim": "Number of Victims",
    "catv": "Vehicle Category",
    "obsm": "Mobile Obstacle",
    "motor": "Engine Type",
    "nb_vehicles": "Number of Vehicles",
    "catr": "Road Category",
    "circ": "Traffic Direction",
    "surf": "Road Surface",
    "situ": "Accident Location",
    "vma": "Speed Limit (km/h)",
    "jour": "Day",
    "mois": "Month",
    "lum": "Lighting",
    "dep": "Department",
    "com": "Municipality",
    "agg": "Urban Area",
    "int": "Intersection",
    "atm": "Weather",
    "col": "Collision Type",
    "lat": "Latitude",
    "lon": "Longitude",
    "hour": "Hour",
}

# mapping
FEATURE_MAPS = {
    "place": {
        1: "Seat Position 1",
        2: "Seat Position 2",
        3: "Seat Position 3",
        4: "Seat Position 4",
        5: "Seat Position 5",
        6: "Seat Position 6",
        7: "Seat Position 7",
        8: "Seat Position 8",
        9: "Seat Position 9",
        10: "Seat Position 10 / Other",
    },
    "catu": {
        1: "Driver",
        2: "Passenger",
        3: "Pedestrian",
    },
    "sexe": {
        1: "Male",
        2: "Female",
    },
    "atm": {
        0: "Good Weather",
        1: "Adverse Weather",
    },
}
