import sys, time
from paintings import load_painting

def to_ascii(grid):
    return "\n".join("".join("#" if v else "." for v in row) for row in grid)

names = sys.argv[1:] or ["Mona Lisa", "mona lisa by leonardo da vinci", "asdfgh"]
for name in names:
    start = time.time()
    p = load_painting(name)
    took = time.time() - start
    print(f"\n=== {name!r} ({took:.1f}s) ===")
    if not sys.argv[1:]:  # the default run checks the brief: aliases hit the cache, nonsense is None
        assert (p is None) == (name == "asdfgh"), name
        assert p is None or (p["title"] == "Mona Lisa" and took < 0.1), (name, took)
    if not p:
        print("None")
        continue
    print(f"{p['title']} - {p['artist']} - {p['year']}")
    for s in p["sections"]:
        print(f"\n{s['number']}. {s['name']} ({s['location']})")
        print(to_ascii(s["grid"]))
