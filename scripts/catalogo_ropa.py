"""Actualiza el catálogo de una tienda de ropa (Vis ta Vie o Alter Ego) con el stock y los precios del sistema.

Uso: python3 catalogo_ropa.py <vistavie|alterego> <carpeta con productos/*.json> <config.json> <index.html>
Reescribe window.CATALOGO dentro de index.html. Sale con código 3 si no cambió nada.
Fotos: las de cada prenda que ya están en fotos/<id>.jpg al lado de index.html (las baja fotos_ropa.py).
Copia las fórmulas de precio del sistema (precioCon): no publica costos ni proveedores.
"""
import datetime, glob, json, math, os, re, sys

from fotos_ropa import fotos_de

# Valores por defecto de cada sistema (DEFAULT_CFG); config/general los pisa.
DEFAULTS = {
    "vistavie": dict(dolar=1565, multLista=4.2, mult6=3.6, mult3=3.3, multContado=2.6, redondeo=0),
    "alterego": dict(dolar=1565, multLista=3.2, mult6=2.9, mult3=2.7, multContado=2.3, redondeo=100),
}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# Igual que el sistema (baseDe): los talles y colores de una prenda comparten código Possum o código base.
def base_de(p):
    return p.get("codigoPossum") or p.get("codigoBase") or str(p["codigo"]).split("-")[0]


TALLE_ORD = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "XXXL", "3XL", "4XL", "5XL", "U", "UNICO", "ÚNICO"]


def orden_talle(v):
    t = v["talle"].split(" ")[0].upper()
    if t.replace(".", "", 1).isdigit():
        return (0, float(t), v["talle"])
    return (1, TALLE_ORD.index(t) if t in TALLE_ORD else len(TALLE_ORD), v["talle"])


def cargar(f):
    j = json.load(open(f))
    return j.get("data", j) if isinstance(j, dict) else j


def main(local, dir_prod, cfg_path, html_path):
    cfg = dict(DEFAULTS[local])
    if os.path.exists(cfg_path):
        cfg.update({k: v for k, v in cargar(cfg_path).items() if v is not None})

    def red(n):
        r = num(cfg.get("redondeo"))
        return math.ceil(n / r - 1e-9) * r if r > 0 and n > 0 else n

    def costo(p):
        return num(p["costo"]) * num(cfg["dolar"]) if p.get("costo") not in (None, "") else num(p.get("costoPesos"))

    def precio(p, m):
        m, ex = num(cfg[m]), num(p.get("extra"))
        if p.get("listaFijo") is not None:
            v = (num(p["listaFijo"]) - ex) * m / num(cfg["multLista"]) + ex
        else:
            v = costo(p) * m * (num(p.get("ajusteLista")) or 1) + ex
        return round(red(v))

    dir_fotos = os.path.join(os.path.dirname(os.path.abspath(html_path)), "fotos")
    grupos, fotos = {}, {}
    for f in sorted(glob.glob(os.path.join(dir_prod, "*.json"))):
        p = cargar(f)
        if p.get("codigo") and fotos_de(p):
            fotos.setdefault(base_de(p), fotos_de(p))
        if not p.get("codigo") or not p.get("descripcion"):
            continue
        st = int(num(p.get("stock")))
        if st <= 0:
            continue
        c = precio(p, "multContado")
        if c <= 0:
            continue
        base = base_de(p)
        nom, _, var = p["descripcion"].partition(" · ")
        g = grupos.setdefault(base, dict(codigo=base, nombre=nom.strip(), categoria=p.get("categoria") or "OTROS", variantes=[]))
        g["variantes"].append(dict(codigo=p["codigo"], talle=var.strip(), stock=st, contado=c, cuotas3=precio(p, "mult3"), cuotas6=precio(p, "mult6")))
    prods = sorted(grupos.values(), key=lambda g: (g["categoria"], g["nombre"]))
    for g in prods:
        g["variantes"].sort(key=orden_talle)
        if len(g["variantes"]) > 1:
            for v in g["variantes"]:
                v["talle"] = v["talle"] or "Sin talle"
        fs = ["fotos/%s.jpg" % i for i in fotos.get(g["codigo"], []) if os.path.exists(os.path.join(dir_fotos, i + ".jpg"))]
        if fs:
            g["foto"] = fs[0]
        if len(fs) > 1:
            g["fotos"] = fs
    assert len(prods) >= 20, "muy pocos productos (%d): no actualizo" % len(prods)

    h = open(html_path).read()
    viejo = re.search(r"window\.CATALOGO=(.*?);</script>", h, re.S)
    assert viejo, "no encontré window.CATALOGO en " + html_path
    try:
        if json.loads(viejo.group(1).replace("<\\/", "</")).get("productos") == prods:
            print(local, "sin cambios")
            sys.exit(3)
    except ValueError:
        pass
    cat = dict(actualizado=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), productos=prods)
    js = json.dumps(cat, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    h = h[:viejo.start()] + "window.CATALOGO=" + js + ";</script>" + h[viejo.end():]
    open(html_path, "w").write(h)
    print(local, len(prods), "productos,", sum(len(g["variantes"]) for g in prods), "variantes")


if __name__ == "__main__":
    main(*sys.argv[1:5])
