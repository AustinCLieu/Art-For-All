import sys, time
from paintings import load_painting

def to_ascii(grid):
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)

names = sys.argv[1:] or ["Mona Lisa", "mona lisa by leonardo da vinci", "asdfgh"]
for name in names:
    start = time.time()
    p = load_painting(name)
    print(f"\n=== {name!r} ({time.time() - start:.1f}s) ===")
    if not p:
        print("None")
        continue
    print(f"{p['title']} - {p['artist']} - {p['year']}")
    for s in p["sections"]:
        print(f"\n{s['number']}. {s['name']} ({s['location']})")
        print(to_ascii(s["grid"]))
