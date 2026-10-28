"""Traducao dos literais de string de global-metadata.dat (por valor) e ajuste de tela cheia."""
import struct, unicodedata
import UnityPy

def strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def patch_metadata(orig_bytes, literais, nomes_assets, acentos, com_acentos):
    b = bytearray(orig_bytes)
    sl_off, sl_size, sd_off = struct.unpack_from("<iii", b, 8)
    n = sl_size // 8
    extra = bytearray(); base = len(b); mudou = 0
    tr = {ord(k): v for k, v in acentos.items()}
    for i in range(n):
        ln, di = struct.unpack_from("<II", b, sl_off + i * 8)
        try: s = bytes(b[sd_off + di:sd_off + di + ln]).decode("utf8")
        except UnicodeDecodeError: continue
        c = s.strip()
        v = literais["exatos"].get(s)
        if v is None: v = literais["aparados"].get(c)
        if v is not None:
            lead = s[:len(s) - len(s.lstrip())]; trail = s[len(s.rstrip()):]
            v = v.translate(tr) if com_acentos else strip_acc(v)
            raw = (lead + v + trail).encode("utf8")
            struct.pack_into("<II", b, sl_off + i * 8, len(raw), (base - sd_off) + len(extra))
            extra += raw; mudou += 1
    b += extra
    return bytes(b), mudou

def patch_fullscreen(ggm_path):
    env = UnityPy.load(ggm_path)
    ok = False
    for o in env.objects:
        if o.type.name == "PlayerSettings":
            t = o.read_typetree()
            t["allowFullscreenSwitch"] = True      # Alt+Enter
            t["fullscreenMode"] = 1                # janela sem borda em tela cheia
            t["resizableWindow"] = True
            o.save_typetree(t); ok = True
    if not ok: raise RuntimeError("PlayerSettings nao encontrado em globalgamemanagers")
    return env.file.save()
