"""Fotos de las tiendas de ropa (Vis ta Vie y Alter Ego) a partir de las fotos cargadas en el sistema.

Las fotos están en los archivos del sistema; cada producto guarda sus ids en `fotos` (en orden, la primera es la
principal) y en `foto` (la principal, de cuando había una sola). En la web quedan como <carpeta>/<id>.jpg.

Uso:
  python3 fotos_ropa.py faltan <carpeta con productos/*.json> <carpeta de fotos de la web>
      Lista (una por renglón) las fotos de prendas con stock que todavía no están en la web.
      La sincronización las baja del sistema con Artifact action "read", path = id.
  python3 fotos_ropa.py achicar <carpeta con las bajadas> <carpeta de fotos de la web>
      Achica cada foto bajada a 1000 px y la guarda como <id>.jpg en la carpeta de la web.
"""
import glob, json, os, re, sys

ID = re.compile(r"^[0-9a-f]{32}$")


def fotos_de(p):
    fs = p.get("fotos") if isinstance(p.get("fotos"), list) and p.get("fotos") else [p.get("foto")] if p.get("foto") else []
    return [f for f in fs if isinstance(f, str) and ID.match(f)]


def faltan(dir_prod, dir_web):
    ids = []
    for f in sorted(glob.glob(os.path.join(dir_prod, "*.json"))):
        j = json.load(open(f))
        p = j.get("data", j)
        try:
            stock = float(p.get("stock") or 0)
        except (TypeError, ValueError):
            stock = 0
        if stock > 0:
            ids += [i for i in fotos_de(p) if i not in ids]
    for i in ids:
        if not os.path.exists(os.path.join(dir_web, i + ".jpg")):
            print(i)


def achicar(dir_bajadas, dir_web):
    from PIL import Image, ImageOps
    os.makedirs(dir_web, exist_ok=True)
    n = 0
    for f in sorted(glob.glob(os.path.join(dir_bajadas, "*"))):
        i = os.path.splitext(os.path.basename(f))[0]
        if not ID.match(i):
            continue
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        im.thumbnail((1000, 1000))
        im.save(os.path.join(dir_web, i + ".jpg"), "JPEG", quality=82, optimize=True, progressive=True)
        n += 1
    print(n, "fotos ->", dir_web)


if __name__ == "__main__":
    {"faltan": faltan, "achicar": achicar}[sys.argv[1]](*sys.argv[2:4])
