"""Parallel PD certificate by slabs (2026-11-01). CORRECT (agrees with the serial one on 8 cases, sharp at lam*0.99 /
1.01) but only 1.2-1.4x on 12600 unknowns: the separator rows fill every interior column of a slab (work per column
x (1 + s/b)^2), and the separator stage is serial. Kept out of the kernel until it earns its place."""
def _eliminate(cols, order, X, one2, pos=None):
    """Interval right-looking elimination of the columns in `order` (each a dict row->interval: the entries whose
    row comes LATER in the elimination order); an update between two later unknowns lands in the column of the one
    eliminated first — by `pos` (the elimination rank), NOT by index: the first parallel version keyed it by index,
    lost the interior-separator couplings and proved a matrix that is not positive definite (caught by its own
    test, 2026-11-01). False if a pivot's lower end is not > 0."""
    rank = (lambda v: v) if pos is None else (lambda v: pos[v])
    for k in order:
        ck = cols[k]
        dk = ck.pop(k, (0, 0))
        if dk[0] <= 0:
            return False
        rk = (one2 // dk[1], -((-one2) // dk[0]))
        rest = list(ck.items())
        cols[k] = {}
        scaled = [X.mul(ai, rk) for _, ai in rest]
        for ii, (i, ai) in enumerate(rest):
            li = scaled[ii]
            for jj in range(ii + 1):
                j, aj = rest[jj]
                lo, hi = (j, i) if rank(j) <= rank(i) else (i, j)
                upd = X.mul(X.sq(ai), rk) if i == j else X.mul(li, aj)
                col = cols.setdefault(lo, {})
                col[hi] = X.sub(col.get(hi, (0, 0)), upd)
    return True


def _pd_worker(args):
    interior, local, bits = args
    X = _FX(bits)
    cols = {j: dict(c) for j, c in local.items()}
    m = len(interior)
    pos = {v: r for r, v in enumerate(interior)}
    for c in local.values():                            # separators after every interior unknown, by index
        for i in c:
            if i not in pos:
                pos[i] = m + i
    ok = _eliminate(cols, interior, X, 1 << (2 * bits), pos)
    if not ok:
        return False, None
    inner = set(interior)
    return True, {j: c for j, c in cols.items() if j not in inner and c}


def pd_certificate_par(n, entries, lam, bits=192, jobs=24):
    """pd_certificate, the elimination split over processes (2026-11-01): the matrix graph is cut into slabs by
    level sets of a breadth-first search from a far vertex; whole level sets are separators, the slabs between
    them are independent. Each slab eliminates its interior unknowns (its updates landing on its separators) in its
    own process; the separators' block, the slabs' contributions added, is eliminated last. The same interval
    elimination in another order — as sound as the serial one."""
    import multiprocessing as mp
    from collections import deque
    adj = [[] for _ in range(n)]
    for (i, j) in entries:
        if i != j:
            adj[i].append(j)
            adj[j].append(i)

    def bfs(s):
        lev = [-1] * n
        lev[s] = 0
        q = deque([s])
        while q:
            v = q.popleft()
            for w in adj[v]:
                if lev[w] < 0:
                    lev[w] = lev[v] + 1
                    q.append(w)
        return lev
    lev = bfs(0)
    if min(lev) < 0:                                     # disconnected: the serial path handles it
        return pd_certificate(n, entries, lam, bits)
    far = max(range(n), key=lambda v: lev[v])
    lev = bfs(far)
    nlev = max(lev) + 1
    by = [[] for _ in range(nlev)]
    for v in range(n):
        by[lev[v]].append(v)
    if nlev < 3 * jobs or n < 2000:
        return pd_certificate(n, entries, lam, bits)
    # separators: one level set at every ~n/jobs unknowns
    seps, acc, target = set(), 0, n / jobs
    for L in range(1, nlev - 1):
        acc += len(by[L])
        if acc >= target:
            seps.add(L)
            acc = 0
    slabs, cur = [], []
    for L in range(nlev):
        if L in seps:
            slabs.append(cur)
            cur = []
        else:
            cur.extend(by[L])
    slabs.append(cur)
    sep_nodes = set(v for L in seps for v in by[L])
    X = _FX(bits)
    full = {}
    for (i, j), v in entries.items():
        a, b = (i, j) if i >= j else (j, i)
        full[(a, b)] = full.get((a, b), Fr(0)) + _q(v)
    for d in range(n):
        full[(d, d)] = full.get((d, d), Fr(0)) - _q(lam)
    # each slab's local columns: its interior's columns (rows in interior or separators), separator rows only
    owner = {}
    for si, sl in enumerate(slabs):
        for v in sl:
            owner[v] = si
    tasks = [([], {}, bits) for _ in slabs]
    sepcols = {}
    for (a, b), v in full.items():                       # a >= b: row a, column b
        iv = X.of(v)
        if b in owner:
            tasks[owner[b]][1].setdefault(b, {})[a] = iv
        elif a in owner:
            tasks[owner[a]][1].setdefault(b, {})[a] = iv   # column b a separator, row a interior: an upper-
        else:                                               # triangle coupling in the slab's elimination order
            sepcols.setdefault(b, {})[a] = iv
    # in a slab the interior is eliminated first, so a coupling (separator column b, interior row a) belongs to
    # the interior column a with row b: move it
    for si, (interior, local, _) in enumerate(tasks):
        moved = {}
        for b in list(local):
            if b in sep_nodes:
                for a, iv in local.pop(b).items():
                    moved.setdefault(a, {})[b] = iv
        for a, rows in moved.items():
            local.setdefault(a, {}).update(rows)
        interior.extend(sorted(slabs[si]))
    # careful order inside a slab: interior unknowns by index; a column's entries must have row > column in the
    # elimination order — interior before separators holds by construction; among interior unknowns rows > col
    # (lower triangle by index) holds as given
    with mp.Pool(min(jobs, len(tasks))) as pool:
        res = pool.map(_pd_worker, tasks)
    if not all(ok for ok, _ in res):
        return False
    for ok, contrib in res:
        for j, c in contrib.items():
            col = sepcols.setdefault(j, {})
            for i, iv in c.items():
                old = col.get(i, (0, 0))
                col[i] = (old[0] + iv[0], old[1] + iv[1])
    order = sorted(sep_nodes)
    # separator columns may hold rows that are separators with a smaller index (from slab updates written as
    # (lo=min, hi=max)); re-key every entry as column = min, row = max
    S = {}
    for j, c in sepcols.items():
        for i, iv in c.items():
            lo, hi = (j, i) if j <= i else (i, j)
            old = S.setdefault(lo, {}).get(hi, (0, 0))
            S[lo][hi] = (old[0] + iv[0], old[1] + iv[1])
    return _eliminate(S, order, X, 1 << (2 * bits))


