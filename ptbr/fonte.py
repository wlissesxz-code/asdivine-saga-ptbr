"""Acentos: compoe glifos acentuados e grava em area vazia do atlas da fonte do jogo,
reaproveitando 25 caracteres CJK raros (stand-ins) cujos retangulos sao redirecionados."""
import struct, os
import numpy as np
from PIL import Image

W = 4096

def _tight(g):
    ys, xs = np.where(g > 0); return g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

def _scale(g, w=None, h=None, f=None):
    im = Image.fromarray(g)
    if f: w, h = max(1, round(g.shape[1] * f)), max(1, round(g.shape[0] * f))
    return np.array(im.resize((w, h), Image.LANCZOS))

class Atlas:
    def __init__(self, res, game_data):
        if not res.fonts: raise RuntimeError("Font nao encontrada em resources.assets")
        self.fo = None
        for fo in res.fonts:
            tt = fo.read_typetree()
            if tt["m_CharacterRects"]: self.fo = fo; self.F = tt; break
        if self.fo is None: raise RuntimeError("Font com CharacterRects nao encontrada")
        self.R = {c['index']: c for c in self.F['m_CharacterRects']}
        self.idxpos = {c['index']: i for i, c in enumerate(self.F['m_CharacterRects'])}
        # textura do atlas: Alpha8 4096x4096 em resS
        self.tex = None
        for t in res.textures:
            x = t.read()
            if x.m_Width == W and x.m_Height == W and int(x.m_TextureFormat) == 1 and x.m_StreamData.size == W * W:
                if self.tex is None or "Font" in x.m_Name: self.tex = x
        if self.tex is None: raise RuntimeError("textura Alpha8 4096x4096 da fonte nao encontrada")
        sd = self.tex.m_StreamData
        self.res_s = os.path.join(game_data, os.path.basename(sd.path))
        self.atlas_off = sd.offset
        with open(self.res_s, "rb") as f:
            f.seek(sd.offset); self.a = np.frombuffer(f.read(W * W), dtype=np.uint8).reshape(W, W).copy()
        self.res = res

    @property
    def advances(self): return {k: c['advance'] for k, c in self.R.items()}

    def glyph(self, cp):
        c = self.R[cp]; u = c['uv']
        x = round(u['x'] * W); w = round(u['width'] * W)
        y0 = round(u['y'] * W); h = round(u['height'] * W)
        lo, hi = sorted((y0, y0 + h))
        if c['flipped']: g = self.a[lo:hi, x:x + abs(round(u['width'] * W))]
        else: g = self.a[lo:hi, x:x + w]
        return c, g

    def compor(self):
        G = lambda ch: self.glyph(ord(ch))
        grave = _tight(G('`')[1]); acute = grave[:, ::-1].copy()
        grave = _scale(grave, f=0.9); acute = _scale(acute, f=0.9)
        circ = _scale(_tight(G('^')[1]), w=22, h=14)
        til = _scale(_tight(np.rot90(G('~')[1])), w=22, h=10)
        ct = _tight(G(':')[1]); rows = (ct > 0).any(axis=1); end = np.argmax(~rows)
        dot = _scale(_tight(ct[:end]), f=0.75)
        dia = np.zeros((dot.shape[0], dot.shape[1] * 2 + 6), np.uint8); dia[:, :dot.shape[1]] = dot; dia[:, -dot.shape[1]:] = dot
        ced = _scale(_tight(G(',')[1]), w=9, h=13)
        marks = {'`': grave, "'": acute, '^': circ, '~': til, ':': dia}
        spec = {'á': ('a', "'"), 'à': ('a', '`'), 'â': ('a', '^'), 'ã': ('a', '~'), 'é': ('e', "'"), 'ê': ('e', '^'),
                'í': ('i', "'"), 'ó': ('o', "'"), 'ô': ('o', '^'), 'õ': ('o', '~'), 'ú': ('u', "'"), 'ü': ('u', ':'), 'ç': ('c', 'c'),
                'Á': ('A', "'"), 'À': ('A', '`'), 'Â': ('A', '^'), 'Ã': ('A', '~'), 'É': ('E', "'"), 'Ê': ('E', '^'),
                'Í': ('I', "'"), 'Ó': ('O', "'"), 'Ô': ('O', '^'), 'Õ': ('O', '~'), 'Ú': ('U', "'"), 'Ç': ('C', 'c')}
        out = {}; OX, OY = 30, 110
        for ch, (base, m) in spec.items():
            c, g = G(base); vx, vy = c['vert']['x'], c['vert']['y']
            canvas = np.zeros((160, 120), np.uint8); bg = g
            if base == 'i':
                rows = (g > 0).any(axis=1); st = int(np.argmax(rows)); first_gap = st + int(np.argmax(~rows[st:]))
                bg = g.copy(); bg[:first_gap + 1] = 0
            px, py = int(OX + vx), int(OY - vy)
            canvas[py:py + bg.shape[0], px:px + bg.shape[1]] = np.maximum(canvas[py:py + bg.shape[0], px:px + bg.shape[1]], bg)
            ys, xs = np.where(canvas > 0); cx = (xs.min() + xs.max()) / 2; basetop = ys.min()
            if m == 'c':
                mk = ced; mx = int(round(cx - mk.shape[1] / 2)); my = ys.max() - 3
            else:
                mk = marks[m]; my = basetop - 4 - mk.shape[0]; mx = int(round(cx - mk.shape[1] / 2))
                if m == "'": mx += 2
            canvas[my:my + mk.shape[0], mx:mx + mk.shape[1]] = np.maximum(canvas[my:my + mk.shape[0], mx:mx + mk.shape[1]], mk)
            ys, xs = np.where(canvas > 0)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            out[ch] = dict(bm=canvas[y0:y1, x0:x1], vx=x0 - OX, vy=OY - y0, adv=c['advance'])
        return out

    @staticmethod
    def _rec(c):
        u, v = c['uv'], c['vert']
        return struct.pack("<i4f4ff i", c['index'], u['x'], u['y'], u['width'], u['height'],
                           v['x'], v['y'], v['width'], v['height'], c['advance'], int(c['flipped']))

    def localizar_registros(self):
        """offset absoluto (no resources.assets) do registro de CharacterRect de indice `pos`."""
        raw = self.fo.get_raw_data()
        first = self.F['m_CharacterRects'][0]
        rec = self._rec(first)
        k = raw.find(rec)
        if k < 0 or raw.find(rec, k + 1) >= 0:
            raise RuntimeError("nao foi possivel localizar a tabela CharacterRects na fonte")
        # confere o segundo registro
        if raw[k + 44:k + 88] != self._rec(self.F['m_CharacterRects'][1]):
            raise RuntimeError("layout de CharacterRect inesperado")
        return self.fo.byte_start + k

    def planejar(self, standins):
        """standins: acento -> char CJK. Retorna (edits_res, band_row0, band_bytes)."""
        out = self.compor(); chars = list(out)
        rect0 = self.localizar_registros()
        # bitmaps em faixa
        cx = 4; cy = 4; rowh = 0; place = []
        for ch in chars:
            h, w = out[ch]['bm'].shape
            if cx + w + 4 > W: cx = 4; cy += rowh + 4; rowh = 0
            place.append((ch, cx, cy, w, h)); cx += w + 4; rowh = max(rowh, h)
        used = cy + rowh + 4
        # faixa vazia (linhas totalmente zeradas), preferindo 3000
        empty = ~(self.a.any(axis=1))
        band0 = None
        for cand in [3000] + list(range(W - used, 2000, -1)):
            if cand + used <= W and empty[cand:cand + used].all(): band0 = cand; break
        if band0 is None: raise RuntimeError("sem area vazia suficiente no atlas da fonte")
        new = np.zeros((used, W), np.uint8); edits = []
        for ch, x, y, w, h in place:
            st = standins[ch]; cp = ord(st)
            if cp not in self.R: raise RuntimeError(f"stand-in U+{cp:04X} ausente na fonte")
            o = out[ch]; new[y:y + h, x:x + w] = o['bm']
            hi = band0 + y + h
            rec = struct.pack("<i4f4ff i", cp, x / W, hi / W, w / W, -h / W, float(o['vx']), float(o['vy']),
                              float(w), float(-h), float(o['adv']), 0)
            pos = self.idxpos[cp]; off = rect0 + pos * 44
            old = self.res.raw[off:off + 44]
            if struct.unpack_from("<i", old)[0] != cp: raise RuntimeError("registro de fonte inesperado")
            edits.append((off, rec, f"{ch}<-{st}"))
        return edits, self.atlas_off + band0 * W, new.tobytes()
