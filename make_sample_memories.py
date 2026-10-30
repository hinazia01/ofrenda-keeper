#!/usr/bin/env python3
"""Create fictional sample memory files so the demo runs out of the box.

Every person here is invented. Replace the folder's contents with your
own real memories — the memories/ folder is gitignored, so private
stories are never pushed anywhere.
"""
from pathlib import Path

SAMPLES = {
    "rashid_mahmood.txt": """Name: Rashid Mahmood (fictional)
Dates: 1940 - 2019
Place: Bahawalpur
Memory: He woke before sunrise every day and read the newspaper aloud on the veranda, translating the hard words for whoever sat beside him. His chai had to be kadak, and his stories always started with "suno, ek zamana tha..."
""",
    "amina_siddiqui.txt": """Name: Amina Siddiqui (fictional)
Dates: 1975 - 2022
Place: Lahore
Memory: She taught mathematics like it was a magic trick, and stayed an hour late whenever a student was stuck. Half the engineers in this town can trace their confidence back to her red pen.
""",
    "moti_the_cat.txt": """Name: Moti (fictional)
Dates: 2018 - 2026
Place: Home
Memory: A white cat who believed every keyboard was a bed and every important phone call was an invitation to sit on the speaker's lap. He is missed most during quiet evenings.
""",
}

d = Path("memories")
d.mkdir(exist_ok=True)
for name, text in SAMPLES.items():
    (d / name).write_text(text, encoding="utf-8")
print(f"Created {len(SAMPLES)} fictional sample memories in memories/ — "
      "now run:  python ofrenda.py memories")
