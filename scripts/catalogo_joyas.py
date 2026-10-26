"""Actualiza joyas/catalogo.json con el stock y los precios del sistema de Catamarca Joyas.

Uso: python3 catalogo_joyas.py <carpeta con productos/*.json> <config.json> <catalogo.json del repo tienda-catamarca-joyas> <joyas/catalogo.json>
Arma el catálogo con generar_catalogo.py y le deja los precios por mayor cifrados que trae el repo
tienda-catamarca-joyas (el código de revendedoras no está acá). Sale con código 3 si no cambió nada.
"""
import json, os, subprocess, sys, tempfile

dir_prod, cfg, cat_joyas, out = sys.argv[1:5]
tmp = os.path.join(os.path.dirname(os.path.abspath(out)), ".catalogo_nuevo.json")
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "generar_catalogo.py"), dir_prod, cfg, tmp], check=True)
nuevo = json.load(open(tmp)); os.remove(tmp)
nuevo["mayorista"] = json.load(open(cat_joyas)).get("mayorista")
assert len(nuevo["productos"]) >= 20, "muy pocos productos (%d): no actualizo" % len(nuevo["productos"])
if os.path.exists(out):
    viejo = json.load(open(out))
    if {k: v for k, v in viejo.items() if k != "actualizado"} == {k: v for k, v in nuevo.items() if k != "actualizado"}:
        print("joyas sin cambios"); sys.exit(3)
json.dump(nuevo, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
print("joyas", len(nuevo["productos"]), "productos")
