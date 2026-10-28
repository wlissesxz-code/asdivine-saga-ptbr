"""Acesso minimo a resources.assets (SerializedFile v22) com UnityPy + edicao in-place."""
import struct, os
import UnityPy

def pad4(n): return (4 - n % 4) % 4

def ser_text(name, script):
    nb = name.encode()
    out = struct.pack("<I", len(nb)) + nb + b"\0" * pad4(len(nb))
    out += struct.pack("<I", len(script)) + script + b"\0" * pad4(len(script))
    return out

class Res:
    """resources.assets carregado em memoria (somente leitura)."""
    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.raw = f.read()
        self.env = UnityPy.load(path)
        self.f = list(self.env.files.values())[0]
        self.data_offset = self.f.header.data_offset
        self.size = len(self.raw)
        self.by_name = {}
        self.fonts = []
        self.textures = []
        for o in self.env.objects:
            t = o.type.name
            if t == "TextAsset":
                self.by_name.setdefault(o.read().m_Name, []).append(o)
            elif t == "Font":
                self.fonts.append(o)
            elif t == "Texture2D":
                self.textures.append(o)

    def entry_off(self, o):
        """offset (no arquivo) da entrada da tabela de objetos: pathID(q) byteStart(q) byteSize(I)."""
        rel = o.byte_start - self.data_offset
        pat = struct.pack("<qqI", o.path_id, rel, o.byte_size)
        i = self.raw.find(pat, 0, self.data_offset)
        if i < 0 or self.raw.find(pat, i + 1, 0 + self.data_offset) >= 0:
            raise RuntimeError("entrada da tabela de objetos nao encontrada de forma unica "
                               "(versao do Unity diferente da esperada?)")
        return i

    def script_of(self, o):
        raw = o.get_raw_data()
        n = struct.unpack_from("<I", raw, 0)[0]
        p = 4 + n + pad4(n)
        l = struct.unpack_from("<I", raw, p)[0]
        return raw[p + 4:p + 4 + l]

class Patch:
    """Acumula edicoes in-place + dados anexados ao fim do arquivo (reversivel)."""
    def __init__(self, res):
        self.res = res
        self.edits = []      # (offset, old_bytes, new_bytes)
        self.blob = bytearray()
        self.orig_size = res.size
        pad = (8 - self.orig_size % 8) % 8
        self.blob += b"\0" * pad

    def add_edit(self, offset, new, note=""):
        old = self.res.raw[offset:offset + len(new)]
        self.edits.append((offset, bytes(old), bytes(new), note))

    def replace_object(self, o, new_data, note=""):
        """aponta a entrada do objeto para dados novos anexados ao fim."""
        start = self.orig_size + len(self.blob)
        self.blob += new_data
        while (self.orig_size + len(self.blob)) % 8:
            self.blob += b"\0"
        i = self.res.entry_off(o)
        newv = struct.pack("<qI", start - self.res.data_offset, len(new_data))
        self.add_edit(i + 8, newv, note)

    def finalize(self):
        new_size = self.orig_size + len(self.blob)
        self.add_edit(24, struct.pack(">Q", new_size), "tamanho do arquivo no cabecalho")
        return new_size

    def apply_to(self, path):
        with open(path, "r+b") as f:
            for off, old, new, _ in self.edits:
                f.seek(off); f.write(new)
            f.seek(0, 2)
            if f.tell() != self.orig_size:
                f.truncate(self.orig_size)
            f.write(bytes(self.blob))

def undo(path, undo_info):
    """desfaz usando as informacoes gravadas em apply."""
    with open(path, "r+b") as f:
        for off, old_hex in undo_info["edits"]:
            f.seek(off); f.write(bytes.fromhex(old_hex))
        f.truncate(undo_info["orig_size"])
