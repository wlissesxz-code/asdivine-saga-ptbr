"""Traducao dos scripts de dialogo (TextAssets emstr_NNN) e tabelas de caracteres."""
import re, json, unicodedata, hashlib
from .unityfile import ser_text

SUFB = (b"\\K", b"\\E", b"\\N")

def dec(b): return b.decode("cp932", "surrogateescape")
def enc(s): return s.encode("cp932", "surrogateescape")

def split(b, estrito=True):
    i = b.find(b"\xff\xfc\xa6")
    if i < 0:
        if estrito: raise ValueError("cabecalho de script nao encontrado")
        i = -1      # script de sistema: sem marcador; cabecalho = 2 primeiros bytes
    return b[:i + 3], b[i + 3:].split(b"\x00")

def safe(it):
    try: return enc(dec(it)) == it
    except Exception: return False

def units(items):
    res = []; ev = None; start = 0
    for k, it in enumerate(items):
        s = dec(it)
        if re.fullmatch(r"\\\d+", s): ev = s; start = k + 1; continue
        if it.endswith(SUFB):
            idxs = list(range(start, k + 1)); lines = []
            for j in idxs:
                raw = items[j]; suf = ""
                if raw.endswith(SUFB): suf = raw[-2:].decode(); raw = raw[:-2]
                t = dec(raw); m = re.match(r"((?:%[^%]*%)*)(.*)$", t, re.S); c, bd = m.groups()
                lines.append((j, c, bd, suf))
            textl = [l for l in lines if l[2].strip() != "" and not re.fullmatch(r"\\B|\\G\([^)]*\)", l[2].strip())]
            u = dict(ev=ev, idxs=idxs, lines=lines, text=textl, suffix=lines[-1][3],
                     safe=all(safe(items[j]) for j in idxs))
            tj = [l[0] for l in textl]
            u["contig"] = tj == list(range(tj[0], tj[0] + len(tj))) if tj else True
            u["simple"] = bool(textl) and u["contig"] and all(l[1] == "" for l in textl[1:]) and u["safe"] \
                and "\\" not in "".join(l[2] for l in textl)
            res.append(u)
            start = k + 1
    return res

def english(u): return " ".join(l[2] for l in u["text"]).strip()

class Fmt:
    """largura de texto com os avancos da fonte do jogo."""
    def __init__(self, advances):
        self.A = advances            # codepoint -> advance (px da fonte)
        self.default = advances.get(0x3000, 60)
    def strip_acc(self, c): return unicodedata.normalize("NFD", c)[0]
    def width(self, s):
        A = self.A; w = 0
        for tok in re.split(r"(%[^%]*%)", s):
            if tok.startswith("%") and tok.endswith("%") and len(tok) > 1:
                if re.fullmatch(r"%n\d+[A-Z]%", tok): w += 6 * A[ord('m')]
                continue
            for c in tok:
                c0 = self.strip_acc(c) if c not in "ＡＢ" else c
                w += A.get(ord(c0), self.default)
        return w
    def wrap(self, text, maxw, off=0):
        words = text.split(" "); lines = []; cur = ""
        for w_ in words:
            cand = (cur + " " + w_) if cur else w_
            lim = maxw - (off if not lines else 0)
            if self.width(cand) <= lim or not cur: cur = cand
            else: lines.append(cur); cur = w_
        if cur: lines.append(cur)
        return lines
    def prefix_off(self, cmds):
        return sum(6 * self.A[ord('m')] for _ in re.findall(r"%n\d+[A-Z]%", cmds))

MAXW = 1770

class Tradutor:
    def __init__(self, fmt, simples, complexas, acentos, com_acentos=True):
        self.fmt = fmt
        self.PS = simples
        self.CK = {tuple(k): v for k, v in complexas}
        self.AM = acentos
        self.acc = com_acentos
        self.trans = {ord(k): v for k, v in acentos.items()}
        # codigos novos (lo,hi) registrados nas tabelas moji_hash/emoji_hash
        self.newcode = {v: 0xE040 + i for i, v in enumerate(acentos.values())}
        self.swap = {v: bytes([c & 0xFF, c >> 8]) for v, c in self.newcode.items()}
        self.report = []

    def hash_lines(self):
        return "".join("0x%04x\t0x%04x\r\n" % (c, ord(v)) for v, c in self.newcode.items()).encode()

    def enc2(self, s):
        out = bytearray()
        for c in s:
            if c in self.swap: out += self.swap[c]
            else: out += enc(c)
        return bytes(out)

    def to_game(self, s):
        if self.acc: return s.translate(self.trans)
        return ''.join((unicodedata.normalize('NFD', c)[0] if ord(c) > 127 and c in self.AM else c) for c in s)

    def jump_const(self, items, base):
        pos = []; p = base
        for it in items: pos.append(p); p += len(it) + 1
        raw = b"\x00".join(items)
        T = sorted(set(int(m.group(1), 16) for m in re.finditer(rb"'([0-9a-f]{6})\)", raw)))
        if not T: return pos, None, 0, 0
        ps = {x: i for i, x in enumerate(pos)}
        best = (0, None)
        for k in range(len(pos)):
            C = T[0] - pos[k]; hit = sum(1 for t in T if (t - C) in ps)
            if hit > best[0]: best = (hit, C)
            if hit == len(T): break
        return pos, best[1], best[0], len(T)

    def build_script(self, b, nome=""):
        """retorna (novos_bytes, n_unidades_traduzidas, n_unidades_com_texto)"""
        fmt = self.fmt
        hdr, items = split(b); items = list(items); base = len(hdr)
        us = units(items); repl = {}; ntr = 0; ntot = 0
        for k, u in enumerate(us):
            if not u["text"]: continue
            e = english(u)
            eng = bool(re.search(r"[A-Za-z]{2}", re.sub(r"%[^%]*%", "", e))); ntot += eng
            ck = tuple(l[2] for l in u["text"])
            hasS = any('\udc80' <= c <= '\udcff' for c in e)
            if ck in self.CK and not (u["simple"] and e in self.PS and not hasS):
                newl = self.CK[ck]
                if len(newl) != len(u["text"]): continue
                for l, t in zip(u["text"], newl):
                    if fmt.width(t) > 1900: self.report.append(("LINHA_LARGA", nome, k, t))
                    repl[l[0]] = (l[0], [items[l[0]] if t == l[2] else self.enc2(l[1] + self.to_game(t) + l[3])])
                ntr += eng
            elif u["simple"] and e in self.PS and not hasS:
                lines = fmt.wrap(self.PS[e], MAXW, fmt.prefix_off(u["text"][0][1]))
                if len(lines) > 3: self.report.append(("LONGO", nome, k, self.PS[e])); continue
                first = u["text"][0][0]; last = u["text"][-1][0]
                lastline = u["lines"][-1]; suffix = u["suffix"] if lastline[0] == last else ""
                cmds = u["text"][0][1]; out = []
                for i, t in enumerate(lines):
                    s = (cmds if i == 0 else "") + self.to_game(t) + (suffix if i == len(lines) - 1 else "")
                    out.append(self.enc2(s))
                repl[first] = (last, out); ntr += eng
        if not repl: return b, 0, ntot
        new_items = []; old2new = {}; i = 0
        while i < len(items):
            if i in repl:
                last, out = repl[i]
                for j in range(i, last + 1):
                    old2new[j] = len(new_items) + min(j - i, len(out) - 1)
                new_items.extend(out); i = last + 1
            else:
                old2new[i] = len(new_items); new_items.append(items[i]); i += 1
        pos_old, C, hit, tot = self.jump_const(items, base)
        if C is not None:
            if hit != tot:
                self.report.append(("SALTO_NAO_RESOLVIDO", nome, hit, tot)); return b, 0, ntot   # nao arrisca
            pos_new = []; p = base
            for it in new_items: pos_new.append(p); p += len(it) + 1
            idx_of = {x: i for i, x in enumerate(pos_old)}
            def sub(m):
                t = int(m.group(1), 16); k = idx_of.get(t - C)
                if k is None: return m.group(0)
                return b"'" + ("%06x" % (pos_new[old2new[k]] + C)).encode() + b")"
            new_items = [re.sub(rb"'([0-9a-f]{6})\)", sub, it) for it in new_items]
        return hdr + b"\x00".join(new_items), ntr, ntot

    def mensagens_sistema(self, b, regras):
        """traducao que preserva o tamanho de cada item (script compartilhado, referenciado por posicao)."""
        hdr, items = split(b, False); items = list(items); feitas = 0
        for j, en, pt in regras:
            if j >= len(items): continue
            it = items[j]; e = en.encode("latin1")
            if it.count(e) != 1: continue
            p = self.enc2(self.to_game(pt)) if self.acc else \
                ''.join(unicodedata.normalize('NFD', c)[0] if ord(c) > 127 else c for c in pt).encode("ascii")
            if len(p) > len(e): continue
            items[j] = it.replace(e, p + b" " * (len(e) - len(p))); feitas += 1
        return hdr + b"\x00".join(items), feitas

def eh_script_sistema(b, regras):
    """script compartilhado: o item 145 contem 'Found'."""
    try:
        hdr, items = split(b, False)
        return len(items) > 145 and b"Found  %C7%" in items[145]
    except Exception:
        return False
