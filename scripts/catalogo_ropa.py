"""Actualiza el catálogo de una tienda de ropa (Vis ta Vie o Alter Ego) con el stock y los precios del sistema.

Uso: python3 catalogo_ropa.py <vistavie|alterego> <carpeta con productos/*.json> <config.json> <index.html>
Reescribe window.CATALOGO dentro de index.html. Sale con código 3 si no cambió nada.
Copia las fórmulas de precio del sistema (precioCon): no publica costos ni proveedores.
"""
import datetime, glob, json, math, os, re, sys

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

    grupos = {}
    for f in glob.glob(os.path.join(dir_prod, "*.json")):
        p = cargar(f)
        if not p.get("codigo") or not p.get("descripcion"):
            continue
        st = int(num(p.get("stock")))
        if st <= 0:
            continue
        c = precio(p, "multContado")
        if c <= 0:
            continue
        base = p.get("codigoBase") or p["codigo"]
        nom, _, var = p["descripcion"].partition(" · ")
        g = grupos.setdefault(base, dict(codigo=base, nombre=nom.strip(), categoria=p.get("categoria") or "OTROS", variantes=[]))
        g["variantes"].append(dict(codigo=p["codigo"], talle=var.strip(), stock=st, contado=c, cuotas3=precio(p, "mult3"), cuotas6=precio(p, "mult6")))
    prods = sorted(grupos.values(), key=lambda g: (g["categoria"], g["nombre"]))
    for g in prods:
        g["variantes"].sort(key=lambda v: v["codigo"])
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
