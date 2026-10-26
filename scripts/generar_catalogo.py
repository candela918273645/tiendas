"""Arma catalogo.json (lo que ve la tienda) a partir de los productos del sistema.

Uso: python3 generar_catalogo.py <carpeta con productos/*.json> <config.json> <salida.json> [código de revendedoras]
Copia las fórmulas de precio del sistema (precioLista, conDesc, precioMayor).
No publica costos ni proveedores. Los precios por mayor van cifrados con el código de revendedoras
(AES-GCM, clave PBKDF2-SHA256 del código en mayúsculas): sin el código no se pueden leer.
"""
import hashlib
import base64, glob, json, math, os, re, sys
from datetime import datetime, timezone

DEFAULT_CFG = {"dolar": 1565, "multLista": 3.225, "fijoLista": 2500, "multMayor": 1.5, "descCuotas3": 20,
               "descContado": 30, "descPromo": 40, "mayorMinimo": 200000, "descMayor": 5, "redondeo": 100}
EXCLUIR_PREFIJOS = ("VTV",)  # productos de Vis ta Vie, otro negocio


def num(x, d=0.0):
    try:
        return float(x) if x not in (None, "") else d
    except (TypeError, ValueError):
        return d


def cifrar(datos, codigo):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    sal, iv = os.urandom(16), os.urandom(12)
    clave = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=150000).derive(codigo.strip().upper().encode())
    b64 = lambda b: base64.b64encode(b).decode()
    return {"sal": b64(sal), "iv": b64(iv), "datos": b64(AESGCM(clave).encrypt(iv, json.dumps(datos, separators=(",", ":")).encode(), None))}


def main(dir_prod, cfg_path, out, codigo=None):
    cfg = dict(DEFAULT_CFG)
    c = json.load(open(cfg_path))
    cfg.update(c.get("data", c))

    def red_up(n):
        r = num(cfg.get("redondeo"))
        return math.ceil(n / r - 1e-9) * r if r > 0 and n > 0 else n

    def costo_ars(p):
        return num(p.get("costo")) * cfg["dolar"] if p.get("costo") not in (None, "") else num(p.get("costoPesos"))

    def lista(p):
        if p.get("listaFijo") is not None:
            return red_up(num(p["listaFijo"]))
        return red_up((costo_ars(p) * cfg["multLista"] + num(cfg["fijoLista"])) * (num(p.get("ajusteLista")) or 1))

    def con_desc(p, d):
        return red_up(lista(p) * (1 - num(d) / 100))

    def mayor(p):
        if costo_ars(p) > 0:
            aj = p.get("ajusteMayor") if p.get("ajusteMayor") is not None else p.get("ajusteLista")
            return red_up(costo_ars(p) * cfg["multMayor"] * (num(aj) or 1) * (1 + num(p.get("ivaPossum")) / 100))
        return con_desc(p, cfg["descContado"])

    # Fotos: fotos/<docId>.jpg al lado de la salida (las baja la sincronización desde el sistema).
    dir_fotos = os.path.join(os.path.dirname(os.path.abspath(out)), "fotos")
    doc_id = lambda c: re.sub(r"[^A-Za-z0-9_.\-~:@+]+", "_", c.strip())[:200] or "_"
    prods, mayores = [], {}
    for f in sorted(glob.glob(os.path.join(dir_prod, "*.json"))):
        d = json.load(open(f))
        p = d.get("data", d)
        cod = (p.get("codigo") or "").strip()
        stock = int(num(p.get("stock")))
        if not cod or cod.upper().startswith(EXCLUIR_PREFIJOS) or stock <= 0 or not p.get("categoria"):
            continue
        l = lista(p)
        if l <= 0:
            continue
        prods.append({
            "codigo": cod,
            "nombre": (p.get("descripcion") or cod).strip(),
            "categoria": p["categoria"].strip().upper(),
            "material": (p.get("material") or "").strip().upper(),
            "stock": stock,
            "lista": l,
            "cuotas3": con_desc(p, cfg["descCuotas3"]),
            "contado": con_desc(p, cfg["descContado"]),
        })
        # Variantes: productos con el mismo "grupo" se muestran como una sola tarjeta en la web.
        if (p.get("grupo") or "").strip() and (p.get("variante") or "").strip():
            prods[-1]["grupo"] = " ".join(p["grupo"].split())
            prods[-1]["variante"] = p["variante"].strip()
            prods[-1]["tipoVariante"] = (p.get("tipoVariante") or "Modelo").strip()
        # Opciones dentro de un mismo código (ej. talles de un anillo): el stock es compartido.
        opciones = [{"nombre": str(v.get("nombre", "")).strip(), "opciones": [str(o).strip() for o in v.get("opciones") or [] if str(o).strip()]}
                    for v in (p.get("variantes") or []) if isinstance(v, dict)]
        opciones = [v for v in opciones if v["nombre"] and len(v["opciones"]) >= 2][:3]
        if opciones:
            prods[-1]["opciones"] = opciones
        # La principal es fotos/<docId>.jpg; las demás, fotos/<docId>__f2.jpg, __f3...
        fotos = []
        for n in ["%s.jpg" % doc_id(cod)] + ["%s__f%d.jpg" % (doc_id(cod), i) for i in range(2, 13)]:
            foto = os.path.join(dir_fotos, n)
            if not os.path.exists(foto):
                break
            with open(foto, "rb") as f:
                fotos.append("fotos/%s?v=%s" % (n, hashlib.sha1(f.read()).hexdigest()[:10]))
        if fotos:
            prods[-1]["foto"] = fotos[0]
        if len(fotos) > 1:
            prods[-1]["fotos"] = fotos
        mayores[cod] = mayor(p)
    json.dump({
        "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reglas": {k: cfg[k] for k in ("descCuotas3", "descContado", "mayorMinimo", "descMayor")},
        "productos": prods,
        "mayorista": cifrar(mayores, codigo) if codigo else None,
    }, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
    print(len(prods), "productos ->", out)


if __name__ == "__main__":
    main(*sys.argv[1:5])
