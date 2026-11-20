"""Minimal MS-NRBF (.NET BinaryFormatter) reader/writer for L-Connect 3 .template files.

Reads a stream into a generic object tree (Obj / Arr / primitives / str / bytes)
and writes such a tree back out. Enough of the spec to round-trip L-Connect
templates (classes, strings, primitive arrays, object arrays, nulls, refs).
"""
import struct, io

# PrimitiveTypeEnumeration
PT = {1: 'Boolean', 2: 'Byte', 3: 'Char', 5: 'Decimal', 6: 'Double', 7: 'Int16', 8: 'Int32',
      9: 'Int64', 10: 'SByte', 11: 'Single', 12: 'TimeSpan', 13: 'DateTime', 14: 'UInt16',
      15: 'UInt32', 16: 'UInt64', 17: 'Null', 18: 'String'}
PFMT = {1: '<?', 2: '<B', 7: '<h', 8: '<i', 9: '<q', 10: '<b', 11: '<f', 6: '<d', 12: '<q',
        13: '<q', 14: '<H', 15: '<I', 16: '<Q'}


class Obj:
    """A class instance. members: list of (name, value). cls: (lib_name or None, class_name)."""
    def __init__(self, cls, members, mtypes):
        self.cls = cls            # (library or None for system, class name)
        self.members = members    # ordered list [name, value]
        self.mtypes = mtypes      # list of (binarytype, extra) per member
    def get(self, name):
        for m in self.members:
            if m[0] == name:
                return m[1]
        raise KeyError(name)
    def set(self, name, value):
        for m in self.members:
            if m[0] == name:
                m[1] = value
                return
        raise KeyError(name)
    def has(self, name):
        return any(m[0] == name for m in self.members)
    def __repr__(self):
        return f'<Obj {self.cls[1]}>'


class Prim:
    """A boxed primitive (MemberPrimitiveTyped) or typed primitive value."""
    def __init__(self, ptype, value):
        self.ptype, self.value = ptype, value
    def __repr__(self):
        return f'Prim({PT[self.ptype]}, {self.value!r})'


class Arr:
    """Array. kind: 'prim' (ptype), 'obj', 'str', or 'binary' (BinaryArray with type info)."""
    def __init__(self, kind, items, ptype=None, binfo=None):
        self.kind, self.items, self.ptype, self.binfo = kind, items, ptype, binfo
    def __repr__(self):
        return f'<Arr {self.kind} n={len(self.items)}>'


class Ref:
    def __init__(self, id):
        self.id = id


class Reader:
    def __init__(self, data):
        self.f = io.BytesIO(data)
        self.libs = {}
        self.classes = {}   # objectId -> (cls, names, mtypes)
        self.objects = {}
        self.pending = []   # (container, key) for refs
        self.root_id = None

    def u8(self): return self.f.read(1)[0]
    def i32(self): return struct.unpack('<i', self.f.read(4))[0]
    def s(self):
        n, shift = 0, 0
        while True:
            b = self.u8(); n |= (b & 0x7f) << shift; shift += 7
            if not b & 0x80: break
        return self.f.read(n).decode('utf-8')

    def prim(self, pt):
        if pt == 18: return self.s()
        if pt == 3:  # char (utf8)
            b = self.f.read(1)
            n = 1 if b[0] < 0x80 else 2 if b[0] < 0xe0 else 3 if b[0] < 0xf0 else 4
            return (b + self.f.read(n - 1)).decode('utf-8')
        if pt == 5: return self.s()
        fmt = PFMT[pt]
        return struct.unpack(fmt, self.f.read(struct.calcsize(fmt)))[0]

    def class_info(self):
        oid = self.i32(); name = self.s(); n = self.i32()
        names = [self.s() for _ in range(n)]
        return oid, name, names

    def member_type_info(self, n):
        bts = [self.u8() for _ in range(n)]
        out = []
        for bt in bts:
            if bt in (0, 7): out.append((bt, self.u8()))
            elif bt == 3: out.append((bt, self.s()))
            elif bt == 4: out.append((bt, (self.s(), self.i32())))
            else: out.append((bt, None))
        return out

    def read_value_for(self, bt, extra):
        if bt == 0:
            return Prim(extra, self.prim(extra))
        return self.record()

    def read_members(self, mtypes):
        vals = []
        i = 0
        while i < len(mtypes):
            bt, extra = mtypes[i]
            if bt == 0:
                vals.append(Prim(extra, self.prim(extra))); i += 1
            else:
                v = self.record()
                if isinstance(v, tuple) and v[0] == 'nulls':
                    vals.extend([None] * v[1]); i += v[1]
                else:
                    vals.append(v); i += 1
        return vals

    def reg(self, oid, o):
        self.objects[oid] = o
        o._id = oid
        return o

    def record(self):
        rt = self.u8()
        if rt == 0:
            self.root_id = self.i32(); self.i32(); self.i32(); self.i32(); return 'header'
        if rt == 12:
            lid = self.i32(); self.libs[lid] = self.s(); return self.record()
        if rt in (5, 4, 3, 2):
            oid, name, names = self.class_info()
            if rt in (5, 4):
                mtypes = self.member_type_info(len(names))
            else:
                mtypes = [(None, None)] * len(names)
            lib = self.libs[self.i32()] if rt in (5, 3) else None
            cls = (lib, name)
            self.classes[oid] = (cls, names, mtypes)
            o = self.reg(oid, Obj(cls, [], mtypes))
            vals = self.read_members(mtypes)
            o.members = [[n, v] for n, v in zip(names, vals)]
            return o
        if rt == 1:
            oid = self.i32(); mid = self.i32()
            cls, names, mtypes = self.classes[mid]
            self.classes[oid] = (cls, names, mtypes)
            o = self.reg(oid, Obj(cls, [], mtypes))
            vals = self.read_members(mtypes)
            o.members = [[n, v] for n, v in zip(names, vals)]
            return o
        if rt == 6:
            oid = self.i32(); v = self.s()
            st = Str(v); return self.reg(oid, st)
        if rt == 8:
            pt = self.u8(); return Prim(pt, self.prim(pt))
        if rt == 9:
            return Ref(self.i32())
        if rt == 10:
            return None
        if rt == 13:
            return ('nulls', self.u8())
        if rt == 14:
            return ('nulls', self.i32())
        if rt == 15:
            oid = self.i32(); n = self.i32(); pt = self.u8()
            if pt == 2:
                items = self.f.read(n)
            else:
                items = [self.prim(pt) for _ in range(n)]
            return self.reg(oid, Arr('prim', items, ptype=pt))
        if rt in (16, 17):
            oid = self.i32(); n = self.i32()
            a = self.reg(oid, Arr('obj' if rt == 16 else 'str', []))
            items = []
            while len(items) < n:
                v = self.record()
                if isinstance(v, tuple): items.extend([None] * v[1])
                else: items.append(v)
            a.items = items
            return a
        if rt == 7:
            oid = self.i32(); atype = self.u8(); rank = self.i32()
            lengths = [self.i32() for _ in range(rank)]
            lbounds = [self.i32() for _ in range(rank)] if atype in (3, 4, 5) else None
            bt = self.u8()
            extra = None
            if bt in (0, 7): extra = self.u8()
            elif bt == 3: extra = self.s()
            elif bt == 4: extra = (self.s(), self.i32())
            total = 1
            for L in lengths: total *= L
            a = self.reg(oid, Arr('binary', [], binfo=(atype, rank, lengths, lbounds, bt, extra)))
            items = []
            while len(items) < total:
                if bt == 0:
                    items.append(self.prim(extra))
                else:
                    v = self.record()
                    if isinstance(v, tuple): items.extend([None] * v[1])
                    else: items.append(v)
            a.items = items
            return a
        if rt == 11:
            return 'end'
        raise ValueError(f'unknown record {rt} at {self.f.tell()-1}')

    def read(self):
        recs = []
        while True:
            r = self.record()
            if r == 'end': break
            if r != 'header': recs.append(r)
        # resolve references
        seen = set()
        def fix(v):
            if isinstance(v, Ref): return self.objects[v.id]
            return v
        for o in list(self.objects.values()):
            if isinstance(o, Obj):
                for m in o.members: m[1] = fix(m[1])
            elif isinstance(o, Arr) and o.kind != 'prim':
                o.items = [fix(x) for x in o.items]
        return self.objects[self.root_id]


class Str(str):
    pass


def load(path):
    with open(path, 'rb') as fh:
        return Reader(fh.read()).read()


# ---------------------------------------------------------------- writer
class Writer:
    def __init__(self):
        self.f = io.BytesIO()
        self.ids = {}       # id(pyobj) -> objectId
        self.next = 1
        self.libs = {}
        self.cls_meta = {}  # (cls, names tuple) -> objectId of first instance
        self.queue = []

    def w(self, b): self.f.write(b)
    def u8(self, v): self.w(bytes([v]))
    def i32(self, v): self.w(struct.pack('<i', v))
    def s(self, v):
        b = v.encode('utf-8'); n = len(b)
        while True:
            x = n & 0x7f; n >>= 7
            if n: self.u8(x | 0x80)
            else: self.u8(x); break
        self.w(b)

    def prim(self, pt, v):
        if pt in (18, 5): return self.s(v)
        if pt == 3: return self.w(v.encode('utf-8'))
        if pt == 2 and isinstance(v, (bytes, bytearray)): return self.w(v)
        self.w(struct.pack(PFMT[pt], v))

    def oid(self, o):
        k = id(o)
        if k not in self.ids:
            self.ids[k] = self.next; self.next += 1
        return self.ids[k]

    def lib(self, name):
        if name not in self.libs:
            lid = self.next; self.next += 1
            self.libs[name] = lid
            self.u8(12); self.i32(lid); self.s(name)
        return self.libs[name]

    def ref_or_inline(self, v, inline):
        """Write member value; objects referenced (queued) unless inline is True for strings."""
        if v is None:
            self.u8(10); return
        if isinstance(v, Prim):
            self.u8(8); self.u8(v.ptype); self.prim(v.ptype, v.value); return
        if isinstance(v, str):
            if id(v) in self.ids:
                self.u8(9); self.i32(self.ids[id(v)]); return
            self.u8(6); self.i32(self.oid(v)); self.s(v); return
        # Obj or Arr -> MemberReference + queue
        k = id(v)
        first = k not in self.ids
        self.u8(9); self.i32(self.oid(v))
        if first: self.queue.append(v)

    def write_obj(self, o):
        oid = self.oid(o)
        names = tuple(m[0] for m in o.members)
        key = (o.cls, names)
        if key in self.cls_meta:
            self.u8(1); self.i32(oid); self.i32(self.cls_meta[key])
        else:
            lib = o.cls[0]
            lid = self.lib(lib) if lib else None
            self.cls_meta[key] = oid
            self.u8(5 if lib else 4); self.i32(oid); self.s(o.cls[1]); self.i32(len(names))
            for n in names: self.s(n)
            for bt, extra in o.mtypes: self.u8(bt)
            for bt, extra in o.mtypes:
                if bt in (0, 7): self.u8(extra)
                elif bt == 3: self.s(extra)
                elif bt == 4:
                    self.s(extra[0]); self.i32(self.lib(extra[0]) if False else self._libid(extra[0], extra[1]))
            if lib: self.i32(lid)
        for (n, v), (bt, extra) in zip(o.members, o.mtypes):
            if bt == 0:
                self.prim(extra, v.value if isinstance(v, Prim) else v)
            else:
                self.ref_or_inline(v, True)

    def _libid(self, clsname, old_lid):
        return self._extlib_map[old_lid]

    def write_arr(self, a):
        oid = self.oid(a)
        if a.kind == 'prim':
            self.u8(15); self.i32(oid); self.i32(len(a.items)); self.u8(a.ptype)
            if a.ptype == 2: self.w(bytes(a.items))
            else:
                for x in a.items: self.prim(a.ptype, x)
            return
        if a.kind in ('obj', 'str'):
            self.u8(16 if a.kind == 'obj' else 17); self.i32(oid); self.i32(len(a.items))
            self.write_items(a.items)
            return
        atype, rank, lengths, lbounds, bt, extra = a.binfo
        self.u8(7); self.i32(oid); self.u8(atype); self.i32(rank)
        for L in lengths: self.i32(L)
        if lbounds:
            for L in lbounds: self.i32(L)
        self.u8(bt)
        if bt in (0, 7): self.u8(extra)
        elif bt == 3: self.s(extra)
        elif bt == 4: self.s(extra[0]); self.i32(self._libid(extra[0], extra[1]))
        if bt == 0:
            for x in a.items: self.prim(extra, x)
        else:
            self.write_items(a.items)

    def write_items(self, items):
        i = 0
        while i < len(items):
            if items[i] is None:
                j = i
                while j < len(items) and items[j] is None: j += 1
                n = j - i
                if n == 1: self.u8(10)
                elif n < 256: self.u8(13); self.u8(n)
                else: self.u8(14); self.i32(n)
                i = j
            else:
                self.ref_or_inline(items[i], True); i += 1

    def dump(self, root, extlibs):
        """extlibs: {old_lib_id: lib_name} used by ClassTypeInfo (bt 4) entries."""
        self._extlib_map = {}
        self.u8(0); self.i32(1); self.i32(-1); self.i32(1); self.i32(0)
        self.oid(root)
        # pre-register libraries in a stable order so class type infos can point at them
        for old, name in sorted(extlibs.items()):
            self._extlib_map[old] = self.lib(name)
        self.queue = [root]
        while self.queue:
            o = self.queue.pop(0)
            if isinstance(o, Obj): self.write_obj(o)
            else: self.write_arr(o)
        self.u8(11)
        return self.f.getvalue()
