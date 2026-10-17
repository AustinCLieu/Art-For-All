# Stand-ins until paintings.py (Austin) and board.py (Teammate 3) are ready.

def to_ascii(grid):
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)

def show_grid(grid):
    print(to_ascii(grid))

def _grid(rows):
    return [[int(c) for c in row] for row in rows]

MONA_LISA = {
    "title": "Mona Lisa",
    "artist": "Leonardo da Vinci",
    "year": "c. 1503-1519",
    "summary": "A half-length portrait of a seated woman, painted by Leonardo da Vinci "
               "and famous for her faint smile. It hangs in the Louvre in Paris.",
    "image": "cache/mona-lisa.jpg",
    "sections": [
        {"number": 1, "name": "her face", "bbox": [0.38, 0.12, 0.62, 0.38], "location": "top center",
         "description": "Her calm face with the famous faint smile, framed by dark hair.",
         "grid": _grid(["0001111000",
                        "0011111100",
                        "0110000110",
                        "0100000010",
                        "0100000010",
                        "0100000010",
                        "0110000110",
                        "0011001100",
                        "0001111000",
                        "0000110000"])},
        {"number": 2, "name": "her hands", "bbox": [0.30, 0.70, 0.75, 0.92], "location": "bottom center",
         "description": "Her right hand rests lightly on her left wrist, relaxed and soft.",
         "grid": _grid(["0000000000",
                        "0000000000",
                        "0011110000",
                        "0111111000",
                        "0111111110",
                        "0001111111",
                        "0000011110",
                        "0000000000",
                        "0000000000",
                        "0000000000"])},
        {"number": 3, "name": "the landscape", "bbox": [0.00, 0.10, 1.00, 0.70], "location": "center",
         "description": "A misty, dreamlike landscape of winding roads and water behind her.",
         "grid": _grid(["0000000000",
                        "1100000011",
                        "0011000110",
                        "0000111000",
                        "0000010000",
                        "0000100000",
                        "0001000000",
                        "0000100000",
                        "0000010000",
                        "0000000000"])},
    ],
}

def load_painting(name):
    return MONA_LISA if "mona lisa" in name.lower() else None
