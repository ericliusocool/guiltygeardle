# Import the tools we need from Flask
# Flask = the web app framework
# render_template = allows us to send HTML files to the browser
# request = lets us access form data sent by the user
# redirect + url_for = used to send the user to another page
# sqlite3 lets us connect to and query our SQLite database
from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import os
from pathlib import Path 
from datetime import date, timedelta
from random import Random


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "guiltygeardle.db")

# Create the Flask app
app = Flask(__name__)
app.secret_key = "0H_GoLLY_0H--G33!!##I5ur3d0h0p31d0ntg3th@ck3d"

UPLOAD_FOLDER = Path(__file__).resolve().parent / "static" / "images" / "characters"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# This function creates and returns a connection to the database
def get_db_connection():
    conn = sqlite3.connect(db_path)

    # This lets us treat rows like dictionaries (row["column_name"])
    conn.row_factory = sqlite3.Row
    return conn

def get_today_character():
    today = date.today().isoformat()

    conn = get_db_connection()

    # Already assigned today?
    row = conn.execute("""
        SELECT characterID
        FROM tbldailycharacter
        WHERE datePlayed = ?
    """, (today,)).fetchone()

    if row:
        conn.close()
        return row["characterID"]

    # Get all characters
    characters = conn.execute("""
        SELECT characterID
        FROM tblcharacters
        ORDER BY characterID
    """).fetchall()

    character_ids = [row["characterID"] for row in characters]

    # Get yesterday's character (if there was one)
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    row = conn.execute("""
        SELECT characterID
        FROM tbldailycharacter
        WHERE datePlayed = ?
    """, (yesterday,)).fetchone()

    yesterday_character = row["characterID"] if row else None

    # Deterministic random seed based on today's date
    rng = Random(today)

    while True:
        character_id = rng.choice(character_ids)
        if character_id != yesterday_character:
            break

    conn.execute("""
        INSERT INTO tbldailycharacter (datePlayed, characterID)
        VALUES (?, ?)
    """, (today, character_id))

    conn.commit()
    conn.close()

    return character_id

@app.route("/search_characters")
def search_characters():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify([])

    conn = sqlite3.connect("guiltygeardle.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            characterName,
            characterAlias,
            characterImage
        FROM tblcharacters
        WHERE characterName LIKE ?
        OR characterAlias LIKE ?
        ORDER BY
            CASE
                WHEN LOWER(characterName) = LOWER(?) THEN 0
                WHEN LOWER(characterName) LIKE LOWER(?) THEN 1
                WHEN LOWER(characterAlias) LIKE LOWER(?) THEN 2
                WHEN LOWER(characterName) LIKE LOWER(?) THEN 3
                WHEN LOWER(characterAlias) LIKE LOWER(?) THEN 4
                ELSE 5
            END,
            characterName
        LIMIT 10
    """, (
        f"%{query}%",          # WHERE name contains
        f"%{query}%",          # WHERE alias contains
        query,                 # exact name
        f"{query}%",           # name starts with
        f"{query}%",           # alias starts with
        f"%{query}%",          # name contains
        f"%{query}%",          # alias contains
    ))

    characters = []

    for row in cur.fetchall():
        characters.append({
            "name": row["characterName"],
            "alias": row["characterAlias"],
            "image": row["characterImage"]
        })

    conn.close()

    return jsonify(characters)

# This function compares two lists of archetypes and returns a string indicating whether the guess is correct, partially correct, or incorrect
def compare_archetypes(guess_list, answer_list):

    if set(guess_list) == set(answer_list):
        return "correct"

    if set(guess_list) & set(answer_list):
        return "partial"

    return "incorrect"

# This function compares two numbers and returns a string indicating whether the guess is correct, too high, or too low
def compare_number(guess, answer):
    # both unknown → correct match
    if guess is None and answer is None:
        return "correct"

    # one unknown → cannot compare properly
    if guess is None or answer is None:
        return "incorrect"

    if guess == answer:
        return "correct"

    if guess < answer:
        return "higher"

    return "lower"

# This function compares two game IDs and returns a string indicating whether the guess is correct, too high, or too low
def compare_characters(guess, answer, conn):

    def to_int(value):
        try:
            if value in ("Unknown", None, ""):
                return None
            return int(value)
        except:
            return None

    guess_age = to_int(guess["characterAge"])
    answer_age = to_int(answer["characterAge"])

    guess_height = to_int(guess["characterHeight"])
    answer_height = to_int(answer["characterHeight"])

    def compare_number(guess_val, answer_val):
        if guess_val is None and answer_val is None:
            return "correct"
        if guess_val is None or answer_val is None:
            return "incorrect"
        if guess_val == answer_val:
            return "correct"
        if guess_val < answer_val:
            return "higher"
        return "lower"

    def compare_game(guess_id, answer_id):
                
        games = cur.execute("SELECT gameID, gameOrder FROM tblgames").fetchall()
        GAME_ORDER = {g["gameID"]: g["gameOrder"] for g in games}

        if guess_id is None or answer_id is None:
            return "incorrect"

        guess_index = GAME_ORDER.get(guess_id)
        answer_index = GAME_ORDER.get(answer_id)

        if guess_index is None or answer_index is None:
            return "incorrect"

        if guess_index == answer_index:
            return "correct"
        if guess_index < answer_index:
            return "higher"
        return "lower"

    cur = conn.cursor()

    def lookup(query, params):
        row = cur.execute(query, params).fetchone()
        return row[0] if row else "Unknown"

    gender_correct = guess["characterGender"] == answer["characterGender"]
    hair_correct = guess["characterHair"] == answer["characterHair"]
    def get_affiliations(character_id):
        rows = cur.execute("""
            SELECT a.affiliationName
            FROM tblcharacteraffiliations ca
            JOIN tblaffiliations a
                ON ca.affiliationID = a.affiliationID
            WHERE ca.characterID = ?
            ORDER BY a.affiliationName
        """, (character_id,)).fetchall()

        return [row["affiliationName"] for row in rows]

    def get_archetypes(character_id):
        rows = cur.execute("""
            SELECT a.archetypeName
            FROM tblcharacterarchetype ca
            JOIN tblarchetypes a
                ON ca.archetypeID = a.archetypeID
            WHERE ca.characterID = ?
            ORDER BY a.archetypeName
        """, (character_id,)).fetchall()

        return [row["archetypeName"] for row in rows]

    guess_affiliations = get_affiliations(guess["characterID"])
    answer_affiliations = get_affiliations(answer["characterID"])

    affiliation_status = compare_archetypes(
        guess_affiliations,
        answer_affiliations
    )

    guess_archetypes = get_archetypes(guess["characterID"])
    answer_archetypes = get_archetypes(answer["characterID"])

    archetype_status = compare_archetypes(
        guess_archetypes,
        answer_archetypes
    )

    if set(guess_affiliations) == set(answer_affiliations):
        affiliation_status = "correct"
    elif set(guess_affiliations) & set(answer_affiliations):
        affiliation_status = "partial"
    else:
        affiliation_status = "incorrect"

    game_status = compare_game(
        guess["characterGame"],
        answer["characterGame"]
    )

    age_status = compare_number(guess_age, answer_age)
    height_status = compare_number(guess_height, answer_height)

    age_display = "Unknown" if guess_age is None else str(guess_age)
    height_display = "Unknown" if guess_height is None else f"{guess_height}cm"

    return {
        "name": guess["characterName"],
        "image": guess["characterImage"],
        "targetImage": answer["characterImage"],
        "targetName": answer["characterName"],

        "genderStatus": "correct" if gender_correct else "incorrect",
        "genderDisplay": lookup("SELECT genderName FROM tblgenders WHERE genderID = ?", (guess["characterGender"],)),

        "hairStatus": "correct" if hair_correct else "incorrect",
        "hairDisplay": lookup("SELECT hairColour FROM tblhairs WHERE hairID = ?", (guess["characterHair"],)),

        "gameStatus": game_status,
        "gameDisplay": lookup("SELECT gameName FROM tblgames WHERE gameID = ?", (guess["characterGame"],)),

        "affiliationStatus": affiliation_status,
        "affiliationDisplay": ", ".join(guess_affiliations) if guess_affiliations else "None",

        "archetypeStatus": archetype_status,
        "archetypeDisplay": ", ".join(guess_archetypes) if guess_archetypes else "None",

        "age": age_status,
        "ageDisplay": age_display,

        "heightStatus": height_status,
        "heightDisplay": height_display,

        "correct": guess["characterID"] == answer["characterID"]
    }

# This function compares the guessed character with the target character and returns a dictionary with the comparison results
@app.route("/guess", methods=["POST"])
def guess():

    data = request.get_json()
    guess_name = data["guess"]

    conn = get_db_connection()

    # Get the guessed character
    guessed = conn.execute("""
        SELECT *
        FROM tblcharacters
        WHERE characterName = ?
    """, (guess_name,)).fetchone()

    if guessed is None:
        conn.close()
        return jsonify({"error": "Character not found"}), 404

    # Get today's character ID
    target_id = get_today_character()

    # Fetch today's character
    target = conn.execute("""
        SELECT *
        FROM tblcharacters
        WHERE characterID = ?
    """, (target_id,)).fetchone()

    if target is None:
        conn.close()
        return jsonify({"error": "Target character not found"}), 404

    result = compare_characters(guessed, target, conn)

    conn.close()

    return jsonify(result)

# Home page route
@app.route("/")
def index():
    # Render the index.html template
    return render_template("index.html")

# Classic game route
@app.route("/classic")
def classic():
    # Render the classic.html template
    return render_template("classic.html")

#####DELETE LATER#####
@app.route("/add-character", methods=["POST"])
def add_character():

    game = request.form["gameName"]
    archetype1 = request.form["archetype1"]
    archetype2 = request.form.get("archetype2")
    affiliations = request.form.getlist("affiliationId")  # CHANGED
    hair = request.form["hairColour"]
    name = request.form["characterName"].strip()
    gender = request.form["genderId"]
    age = request.form["characterAge"]
    height = request.form["characterHeight"].strip()

    conn = get_db_connection()
    cur = conn.cursor()

    # =========================
    # GAME
    # =========================
    cur.execute("""
        SELECT gameID FROM tblgames WHERE gameName = ?
    """, (game,))
    g = cur.fetchone()

    if not g:
        conn.close()
        return "Game not found in database", 400

    game_id = g["gameID"]

    # =========================
    # HAIR COLOUR
    # =========================
    cur.execute("""
        SELECT hairID FROM tblhairs WHERE hairColour = ?
    """, (hair,))
    h = cur.fetchone()

    if not h:
        conn.close()
        return "Hair colour not found in database", 400

    hair_id = h["hairID"]

    # =========================
    # INSERT CHARACTER (NO AFFILIATION HERE ANYMORE)
    # =========================
    cur.execute("""
        INSERT INTO tblcharacters (
            characterName,
            characterImage,
            characterGender,
            characterAge,
            characterGame,
            characterHeight,
            characterHair
        )
        VALUES (?, 'none.png', ?, ?, ?, ?, ?)
    """, (name, gender, age, game_id, height, hair_id))

    character_id = cur.lastrowid

    # =========================
    # AFFILIATIONS (NEW MANY-TO-MANY)
    # =========================
    for aff_name in affiliations:
        aff_name = aff_name.strip()
        if not aff_name:
            continue

        cur.execute("""
            SELECT affiliationID
            FROM tblaffiliations
            WHERE affiliationName = ?
        """, (aff_name,))
        a = cur.fetchone()

        if a:
            cur.execute("""
                INSERT INTO tblcharacteraffiliations (characterID, affiliationID)
                VALUES (?, ?)
            """, (character_id, a["affiliationID"]))

    # =========================
    # ARCHETYPE 1
    # =========================
    cur.execute("""
        SELECT archetypeID FROM tblarchetypes WHERE archetypeName = ?
    """, (archetype1,))
    a1 = cur.fetchone()

    if a1:
        cur.execute("""
            INSERT OR IGNORE INTO tblcharacterarchetype (characterID, archetypeID)
            VALUES (?, ?)
        """, (character_id, a1["archetypeID"]))

    # =========================
    # ARCHETYPE 2 (OPTIONAL)
    # =========================
    if archetype2:
        archetype2 = archetype2.strip()
        if archetype2 != "":
            cur.execute("""
                SELECT archetypeID FROM tblarchetypes WHERE archetypeName = ?
            """, (archetype2,))
            a2 = cur.fetchone()

            if a2:
                cur.execute("""
                    INSERT OR IGNORE INTO tblcharacterarchetype (characterID, archetypeID)
                    VALUES (?, ?)
                """, (character_id, a2["archetypeID"]))

    conn.commit()
    conn.close()

    return redirect("/add-data")

@app.route("/add-data")
def add_data():
    conn = get_db_connection()
    cur = conn.cursor()

    games = cur.execute("SELECT * FROM tblgames").fetchall()
    affiliations = cur.execute("SELECT * FROM tblaffiliations").fetchall()
    archetypes = cur.execute("SELECT * FROM tblarchetypes").fetchall()
    hairColours = cur.execute("SELECT * FROM tblhairs").fetchall()

    conn.close()

    return render_template(
        "adddata.html",
        games=games,
        affiliations=affiliations,
        archetypes=archetypes,
        hairColour=hairColours
    )

@app.route("/edit-characters", methods=["GET", "POST"])
def edit_characters():

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":

        character_id = request.form["characterID"]
        name = request.form["characterName"]
        alias = request.form["characterAlias"]

        cur.execute("""
            UPDATE tblcharacters
            SET characterName = ?,
                characterAlias = ?
            WHERE characterID = ?
        """, (name, alias, character_id))

        # Update affiliations
        selected_affiliations = request.form.getlist("affiliations")

        cur.execute("""
            DELETE FROM tblcharacteraffiliations
            WHERE characterID = ?
        """, (character_id,))

        for affiliation_id in selected_affiliations:
            cur.execute("""
                INSERT INTO tblcharacteraffiliations (characterID, affiliationID)
                VALUES (?, ?)
            """, (character_id, affiliation_id))

        if "resetImage" in request.form:
            cur.execute("""
                UPDATE tblcharacters
                SET characterImage = 'none.png'
                WHERE characterID = ?
            """, (character_id,))

        import os
        import re

        image = request.files.get("image")

        if image and image.filename:

            cur.execute("""
                SELECT characterName
                FROM tblcharacters
                WHERE characterID = ?
            """, (character_id,))
            character = cur.fetchone()

            base_name = re.sub(r"[ .]", "", character["characterName"])
            extension = os.path.splitext(image.filename)[1].lower()
            filename = f"{base_name}{extension}"

            image.save(app.config["UPLOAD_FOLDER"] / filename)

            cur.execute("""
                UPDATE tblcharacters
                SET characterImage = ?
                WHERE characterID = ?
            """, (filename, character_id))

        conn.commit()

    characters = cur.execute("""
        SELECT *
        FROM tblcharacters
        ORDER BY characterName
    """).fetchall()

    affiliations = cur.execute("""
        SELECT *
        FROM tblaffiliations
        ORDER BY affiliationName
    """).fetchall()

    character_affiliations = {}

    for character in characters:
        rows = cur.execute("""
            SELECT affiliationID
            FROM tblcharacteraffiliations
            WHERE characterID = ?
        """, (character["characterID"],)).fetchall()

        character_affiliations[character["characterID"]] = [
            row["affiliationID"] for row in rows
        ]

    conn.close()

    return render_template(
        "editcharacters.html",
        characters=characters,
        affiliations=affiliations,
        character_affiliations=character_affiliations
    )

# Only run the app if this file is executed directly
if __name__ == "__main__":
    # debug=True automatically reloads the server when you save changes
    app.run(debug=True)