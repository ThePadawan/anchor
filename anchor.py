from collections import defaultdict
import logging
import os
from typing import Any, DefaultDict, Dict, Set

from genanki import Deck, Note, Model, Package

HTML_PREFIX = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
</head>
<body>
"""

HTML_SUFFIX = """
</body>
</html>
"""

ENDINGS = {".front.html": "front", ".back.html": "back"}

logger = logging.getLogger()


def validate_notes(
    notes: DefaultDict[str, Set[str]]
) -> DefaultDict[str, Set[str]]:
    keys_to_delete = set()
    for prefix, endings in notes.items():
        if endings != ENDINGS.keys():
            logger.warning(f"Note with name {prefix} does not have two sides!")
            keys_to_delete.add(prefix)

    for key in keys_to_delete:
        del notes[key]

    return notes


def read_raw_decks() -> Dict[str, Any]:
    decks = dict()

    for deck_folder in os.scandir("./decks"):
        if not deck_folder.is_dir():
            continue

        abs_deck_folder = os.path.abspath(deck_folder)
        note_filenames = set(os.listdir(abs_deck_folder))

        # Match up front and back files
        notes = defaultdict(set)

        for filename in note_filenames:
            for ending in ENDINGS.keys():
                if filename.endswith(ending):
                    notes[filename[: -len(ending)]].add(ending)

        notes = validate_notes(notes)

        # Read all relevant file contents into dict.
        note_contents: DefaultDict[str, Any] = defaultdict(dict)

        for file_prefix, endings in notes.items():
            for ending in endings:
                target_filename = f"{file_prefix}{ending}"
                target_filename = os.path.join(abs_deck_folder, target_filename)

                with open(target_filename, "r", encoding="utf8") as f:
                    note_contents[file_prefix][ENDINGS[ending]] = f.read()

        decks[deck_folder.name] = note_contents

    return decks


def generate_decks(raw_decks: Dict[str, Any]) -> Dict[str, Any]:
    result = {}

    default_model = Model(
        13524624,
        "Default Layout",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
        ],
        templates=[
            {"name": "Default", "qfmt": "{{Front}}", "afmt": "{{Back}}"}
        ],
    )

    reversed_model = Model(
        13524625,
        "Reverse Layout",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
        ],
        templates=[
            {"name": "Default", "qfmt": "{{Back}}", "afmt": "{{Front}}"}
        ],
    )

    for deck_name, note_dict in raw_decks.items():
        deck = Deck(356246245, deck_name)

        for note_name, contents in note_dict.items():
            models = [default_model]
            if note_name.endswith(".reversible"):
                models.append(reversed_model)

            for model in models:
                deck.add_note(
                    Note(
                        model=model,
                        fields=[contents["front"], contents["back"]],
                    )
                )

        result[deck_name] = Package(deck)

    return result


def save_decks(decks: dict) -> None:
    if not os.path.exists("./dist"):
        os.makedirs("dist")

    for deck_name, deck in decks.items():
        deck.write_to_file(f"./dist/{deck_name}.apkg")


# TODO: No support for media files yet.
# TODO: Umlauts are broken, because of course they are.
# TODO: Take flag whether to create N decks or combine all notes into one.
def main() -> None:
    raw_decks = read_raw_decks()
    decks = generate_decks(raw_decks)
    save_decks(decks)


if __name__ == "__main__":
    main()