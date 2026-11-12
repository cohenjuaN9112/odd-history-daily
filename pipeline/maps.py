"""Render vertical map images (2160x3840, i.e. 2x the video size) from a story's "maps" spec.

Usage: python3 maps.py stories/<dir>
story.json -> "maps": {
  "<key>": {
    "type": "region",                    # a projected map of an area
    "center": [lon, lat],                # projection centre (Lambert azimuthal equal-area)
    "width_km": 6000,                    # visible width at the centre of the image
    "y_offset": 0.0,                     # shift the centre up (+) or down (-) as a fraction of the height
    "highlight": [{"state": "Alaska", "color": "amber"}, {"country": "Russia", "color": "red"}],
    "labels": [{"text": "RUSSIA", "lonlat": [100, 62], "size": 90, "color": "paper"}],
    "lines": [{"lonlat": [[-169, 58], [-169, 72]], "color": "paper", "dash": true, "width": 6}],
    "dots": [{"lonlat": [-168.95, 65.76], "r": 14, "color": "amber"}],
    "title": "THE BERING STRAIT"         # optional small heading at the top
  },
  "<key2>": {
    "type": "compare",                   # same-scale shapes side by side (equal-area), e.g. Alaska vs 3 states
    "groups": [[{"state": "Alaska", "color": "amber", "label": "ALASKA"}],
               [{"state": "Texas", "label": "TEXAS"}, {"state": "California", "label": "CALIFORNIA"},
                {"state": "Montana", "label": "MONTANA"}]],
    "title": "SAME SCALE"
  }
}
Names: "state" = Natural Earth admin-1 name (U.S. states, provinces...), "country" = Natural Earth ADMIN name.
Colors: amber, paper, red, blue, land, or any #hex.
Data: Natural Earth (public domain), downloaded once into pipeline/data/.
"""
import json, os, sys, urllib.request
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from shapely.affinity import translate, scale as sscale

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = f"{HERE}/data"
NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
FILES = {"countries": "ne_50m_admin_0_countries.geojson", "states": "ne_50m_admin_1_states_provinces.geojson",
         "countries10": "ne_10m_admin_0_countries.geojson"}
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
COL = {"ink": "#1b120b", "land": "#3b2e22", "edge": "#6b5643", "amber": "#ffb400", "paper": "#f0ece4",
       "red": "#a8432f", "blue": "#3f6e9e", "sea": "#1b120b", "muted": "#8a7560"}
W, H, DPI = 2160, 3840, 200

def col(c): return COL.get(c, c)

def data(name):
    os.makedirs(DATA, exist_ok=True)
    p = f"{DATA}/{FILES[name]}"
    if not os.path.exists(p):
        open(p, "wb").write(urllib.request.urlopen(NE + FILES[name], timeout=180).read())
    return gpd.read_file(p)

_cache = {}
def layer(name):
    if name not in _cache: _cache[name] = data(name)
    return _cache[name]

def feature(item):
    if "state" in item:
        df = layer("states"); g = df[df["name"] == item["state"]]
    else:
        df = layer("countries10" if item.get("fine") else "countries"); g = df[df["ADMIN"] == item["country"]]
    if g.empty: raise ValueError(f"not found: {item}")
    return g

def fig():
    f = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    ax = f.add_axes([0, 0, 1, 1]); ax.set_axis_off(); f.patch.set_facecolor(COL["ink"]); ax.set_facecolor(COL["ink"])
    return f, ax

def fprop(size): return font_manager.FontProperties(fname=FONT, size=size)

def region(spec, out):
    lon0, lat0 = spec["center"]
    crs = f"+proj=laea +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m"
    f, ax = fig()
    world = layer("countries10" if spec.get("fine") else "countries").to_crs(crs)
    world.plot(ax=ax, color=COL["land"], edgecolor=COL["edge"], linewidth=0.8)
    if spec.get("states_borders"):
        layer("states").to_crs(crs).plot(ax=ax, color="none", edgecolor=COL["edge"], linewidth=0.5)
    for h in spec.get("highlight", []):
        feature(h).to_crs(crs).plot(ax=ax, color=col(h.get("color", "amber")), edgecolor=COL["ink"], linewidth=0.6)
    half_w = spec["width_km"] * 500; half_h = half_w * H / W
    yo = spec.get("y_offset", 0.0) * 2 * half_h
    ax.set_xlim(-half_w, half_w); ax.set_ylim(-half_h - yo, half_h - yo)
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    for ln in spec.get("lines", []):
        xs, ys = zip(*[tr.transform(*p) for p in ln["lonlat"]])
        ax.plot(xs, ys, color=col(ln.get("color", "paper")), linewidth=ln.get("width", 5),
                linestyle=(0, (4, 3)) if ln.get("dash") else "-", solid_capstyle="round")
    for d in spec.get("dots", []):
        x, y = tr.transform(*d["lonlat"])
        ax.scatter([x], [y], s=d.get("r", 12) ** 2, color=col(d.get("color", "amber")), zorder=5,
                   edgecolors=COL["ink"], linewidths=2)
    for lb in spec.get("labels", []):
        x, y = tr.transform(*lb["lonlat"])
        ax.text(x, y, lb["text"], fontproperties=fprop(lb.get("size", 60)), color=col(lb.get("color", "paper")),
                ha="center", va="center", zorder=6)
    if spec.get("title"):
        f.text(0.5, spec.get("title_y", 0.94), spec["title"], fontproperties=fprop(54), color=COL["muted"], ha="center", va="center")
    f.savefig(out, dpi=DPI, facecolor=COL["ink"]); plt.close(f)

def compare(spec, out):
    f, ax = fig()
    groups = []
    for grp in spec["groups"]:
        shapes = []
        for it in grp:
            g = feature(it)
            c = g.to_crs("EPSG:4326").geometry.union_all().centroid
            geom = g.to_crs(f"+proj=laea +lat_0={c.y} +lon_0={c.x} +datum=WGS84 +units=m").geometry.union_all()
            shapes.append((geom, it))
        groups.append(shapes)
    # layout: each group is a row; shapes in a row sit side by side, rows stacked top to bottom
    gap = 150e3; rows = []; y = 0
    for shapes in groups:
        x = 0; placed = []; row_h = 0
        for geom, it in shapes:
            minx, miny, maxx, maxy = geom.bounds
            g2 = translate(geom, xoff=x - minx, yoff=-maxy)
            placed.append((g2, it)); x += (maxx - minx) + gap; row_h = max(row_h, maxy - miny)
        rows.append((placed, x - gap, row_h))
    total_h = sum(r[2] for r in rows) + gap * 2 * (len(rows) - 1)
    max_w = max(r[1] for r in rows)
    cur = 0
    for placed, rw, rh in rows:
        for g2, it in placed:
            g3 = translate(g2, xoff=(max_w - rw) / 2, yoff=-cur)
            gpd.GeoSeries([g3]).plot(ax=ax, color=col(it.get("color", "paper")), edgecolor=COL["ink"], linewidth=1.0)
            if it.get("label") and it.get("inside"):
                rp = g3.representative_point() if g3.area <= 0 else g3.centroid
                ax.text(rp.x, rp.y, it["label"], fontproperties=fprop(it.get("size", 44)), color=col(it.get("label_color", "ink")),
                        ha="center", va="center")
            elif it.get("label"):
                cx, cy = g3.centroid.x, g3.bounds[1] - 0.06 * total_h
                ax.text(cx, cy, it["label"], fontproperties=fprop(it.get("size", 44)), color=col(it.get("label_color", "paper")),
                        ha="center", va="center")
        cur += rh + gap * 2
    pad_w = max_w * 0.08; span_h = total_h * 1.25
    span_w = max(max_w + 2 * pad_w, span_h * W / H); span_h = span_w * H / W
    cxm, cym = max_w / 2, -total_h / 2 + spec.get("y_offset", 0) * span_h
    ax.set_xlim(cxm - span_w / 2, cxm + span_w / 2); ax.set_ylim(cym - span_h / 2, cym + span_h / 2)
    ax.set_aspect("equal")
    if spec.get("title"):
        f.text(0.5, spec.get("title_y", 0.94), spec["title"], fontproperties=fprop(54), color=COL["muted"], ha="center", va="center")
    f.savefig(out, dpi=DPI, facecolor=COL["ink"]); plt.close(f)

def main(story_dir):
    story = json.load(open(f"{story_dir}/story.json"))
    os.makedirs(f"{story_dir}/img", exist_ok=True)
    for key, spec in story.get("maps", {}).items():
        out = f"{story_dir}/img/{key}.png"
        (compare if spec["type"] == "compare" else region)(spec, out)
        print("map", key, out)

if __name__ == "__main__":
    main(sys.argv[1])
