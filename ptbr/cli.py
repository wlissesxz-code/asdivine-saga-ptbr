import os, sys, json, shutil, argparse, hashlib, time
from . import __version__

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def carregar(nome):
    with open(os.path.join(DATA, nome), encoding="utf-8") as f: return json.load(f)

def achar_jogo(caminho):
    cands = [caminho] if caminho else [os.getcwd(), os.path.dirname(os.getcwd()),
                                       os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
    cands += [os.path.dirname(c) for c in list(cands)]
    for c in cands:
        if not c or not os.path.isdir(c): continue
        for d in os.listdir(c):
            p = os.path.join(c, d)
            if d.endswith("_Data") and os.path.isfile(os.path.join(p, "resources.assets")):
                return c, p
        if c.endswith("_Data") and os.path.isfile(os.path.join(c, "resources.assets")):
            return os.path.dirname(c), c
    return None, None

def sha(path, n=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 22)
            if not b: break
            h.update(b)
    return h.hexdigest()

def reverter(jogo, data, bk, quieto=False):
    undo_p = os.path.join(bk, "desfazer.json")
    if os.path.isfile(undo_p):
        from .unityfile import undo
        info = json.load(open(undo_p))
        res = os.path.join(data, "resources.assets")
        undo(res, info["resources"])
        if info.get("resS"):
            with open(os.path.join(data, info["resS"]["arquivo"]), "r+b") as f:
                f.seek(info["resS"]["offset"]); f.write(bytes.fromhex(info["resS"]["old"]) if "old" in info["resS"]
                                                          else b"\0" * info["resS"]["length"])
        os.remove(undo_p)
        if not quieto: print("  resources.assets restaurado.")
    meta = os.path.join(data, "il2cpp_data", "Metadata", "global-metadata.dat")
    for nome, dst in (("globalgamemanagers", os.path.join(data, "globalgamemanagers")),
                      ("global-metadata.dat", meta)):
        src = os.path.join(bk, nome)
        if os.path.isfile(src):
            shutil.copyfile(src, dst)
            if not quieto: print(f"  {nome} restaurado.")

def aplicar(jogo, data, com_acentos=True, so_fullscreen=False, verificar=False):
    from .unityfile import Res, Patch, ser_text
    from . import meta as M
    bk = os.path.join(jogo, "PTBR_backup")
    if not verificar: os.makedirs(bk, exist_ok=True)
    res_p = os.path.join(data, "resources.assets")
    ggm_p = os.path.join(data, "globalgamemanagers")
    meta_p = os.path.join(data, "il2cpp_data", "Metadata", "global-metadata.dat")
    if not os.path.isfile(meta_p): sys.exit("global-metadata.dat nao encontrado (este jogo usa IL2CPP?)")
    if verificar and (os.path.isfile(os.path.join(bk, "desfazer.json"))):
        sys.exit("O patch ja esta instalado; restaure o jogo antes de usar 'verificar'.")
    # 1) garante estado original
    if not verificar and (os.path.isfile(os.path.join(bk, "desfazer.json")) or os.path.isfile(os.path.join(bk, "globalgamemanagers"))):
        print("Revertendo patch anterior..."); reverter(jogo, data, bk)
    # 2) backups dos arquivos pequenos
    for src, nome in ((ggm_p, "globalgamemanagers"), (meta_p, "global-metadata.dat")):
        dst = os.path.join(bk, nome)
        if not verificar and not os.path.isfile(dst): shutil.copyfile(src, dst)
    for p in (res_p, os.path.join(data, "resources.assets.resS")):
        if os.path.isfile(p):
            try: os.chmod(p, 0o666)
            except OSError: pass

    print("Tela cheia (Alt+Enter)...")
    ggm_new = M.patch_fullscreen(ggm_p if verificar else os.path.join(bk, "globalgamemanagers"))
    if verificar: pass
    else:
        with open(ggm_p, "wb") as f: f.write(ggm_new)
    if so_fullscreen:
        print("Pronto (somente tela cheia)."); return

    print("Lendo resources.assets (pode levar um minuto)...")
    res = Res(res_p)
    if "emstr_001" not in res.by_name:
        sys.exit("Scripts de dialogo (emstr_*) nao encontrados: versao do jogo nao suportada.")
    acentos = carregar("acentos.json")
    from .historia import Fmt, Tradutor, eh_script_sistema
    adv = None; atlas = None; edits_font = None
    if com_acentos or True:
        from .fonte import Atlas
        atlas = Atlas(res, data); adv = atlas.advances
    fmt = Fmt(adv)
    tr = Tradutor(fmt, carregar("falas_simples.json"), carregar("falas_complexas.json"), acentos, com_acentos)
    regras0 = carregar("mensagens_sistema.json")
    patch = Patch(res)

    # 3) scripts de dialogo
    grupos = {}
    for nome, objs in res.by_name.items():
        if not nome.startswith("emstr_"): continue
        for o in objs:
            grupos.setdefault(res.script_of(o), []).append((nome, o))
    tot_u = tot_t = n_scripts = msgs_sis = 0
    for b, lst in sorted(grupos.items(), key=lambda kv: kv[1][0][0]):
        nome = lst[0][0]
        try:
            if eh_script_sistema(b, regras0):
                novo, feitas = tr.mensagens_sistema(b, regras0)
                ntr = ntot = 0; msgs_sis = feitas
            else:
                novo, ntr, ntot = tr.build_script(b, nome)
        except Exception as e:
            if len(b) > 64: print(f"  aviso: {nome} ignorado ({e})")
            continue
        tot_u += ntot; tot_t += ntr
        if novo != b:
            n_scripts += 1
            for nm, o in lst:
                patch.replace_object(o, ser_text(nm, novo), nm)
    print(f"  dialogos: {tot_t} de {tot_u} falas traduzidas ({n_scripts} scripts) + {msgs_sis} mensagens de sistema")
    if tot_u and tot_t < 0.9 * tot_u:
        print("  ATENCAO: muitas falas nao casaram com a traducao - sua versao do jogo pode ser diferente.")
        print("           O jogo continua utilizavel (as falas restantes ficam em ingles). Abra uma issue no GitHub.")
    for r in tr.report: print("  aviso:", r)

    # 4) tabelas de caracteres (acentos) + fonte
    undo_res_s = None
    if com_acentos:
        for hn in ("emoji_hash", "moji_hash"):
            if hn not in res.by_name: sys.exit(f"{hn} nao encontrado")
            o = res.by_name[hn][0]; old = res.script_of(o)
            if not old.endswith(b"\r\n"): old += b"\r\n"
            patch.replace_object(o, ser_text(hn, old + tr.hash_lines()), hn)
        edits_f, band_off, band = atlas.planejar(acentos)
        for off, rec, nota in edits_f: patch.add_edit(off, rec, "fonte " + nota)
        print(f"  fonte: {len(edits_f)} glifos acentuados")
    new_size = patch.finalize()

    # 5) metadata
    print("Traduzindo textos de interface (global-metadata.dat)...")
    literais = carregar("literais.json"); nomes = None
    meta_new, mudou = M.patch_metadata(open(meta_p if verificar else os.path.join(bk, "global-metadata.dat"), "rb").read(),
                                       literais, nomes, acentos, com_acentos)
    print(f"  {mudou} textos de interface traduzidos")

    if verificar:
        print("Verificacao concluida (nada foi gravado)."); return
    # 6) grava (resources.assets: edicoes in-place + anexo; metadata)
    undo_info = dict(resources=dict(orig_size=patch.orig_size,
                                    edits=[[off, old.hex()] for off, old, new, _ in patch.edits]))
    if com_acentos:
        rs = os.path.basename(atlas.res_s)
        undo_info["resS"] = dict(arquivo=rs, offset=band_off, length=len(band))
        with open(atlas.res_s, "r+b") as f:
            f.seek(band_off); undo_info["resS"]["old"] = f.read(len(band)).hex(); f.seek(band_off); f.write(band)
    json.dump(undo_info, open(os.path.join(bk, "desfazer.json"), "w"))
    patch.apply_to(res_p)
    with open(meta_p, "wb") as f: f.write(meta_new)
    json.dump(dict(versao=__version__, acentos=com_acentos, data=time.strftime("%Y-%m-%d %H:%M")),
              open(os.path.join(bk, "estado.json"), "w"))
    print("Pronto! Abra o jogo. Alt+Enter alterna tela cheia.")

def main(argv=None):
    ap = argparse.ArgumentParser(description="Patch PT-BR de Asdivine Saga")
    ap.add_argument("comando", choices=["instalar", "restaurar", "verificar"])
    ap.add_argument("--jogo", help="pasta do jogo (a que contem a pasta *_Data)")
    ap.add_argument("--sem-acentos", action="store_true", help="portugues sem acentos (nao altera a fonte)")
    ap.add_argument("--so-fullscreen", action="store_true", help="apenas habilita tela cheia (jogo em ingles)")
    a = ap.parse_args(argv)
    jogo, data = achar_jogo(a.jogo)
    if not data and sys.stdin.isatty():
        p = input("Pasta do jogo (a que contem 'Asdivine Saga_Data'): ").strip().strip('"')
        jogo, data = achar_jogo(p)
    if not data: sys.exit("Pasta do jogo nao encontrada. Use --jogo \"C:\\caminho\\Asdivine Saga\"")
    print("Jogo:", jogo)
    bk = os.path.join(jogo, "PTBR_backup")
    if a.comando == "restaurar":
        if not os.path.isdir(bk): sys.exit("Nada a restaurar (nenhum backup encontrado).")
        reverter(jogo, data, bk); print("Jogo restaurado ao estado original."); return
    aplicar(jogo, data, com_acentos=not a.sem_acentos, so_fullscreen=a.so_fullscreen, verificar=a.comando == "verificar")
