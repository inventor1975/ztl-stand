# -*- coding: utf-8 -*-
"""THE CLIMB — which design to judge next, when the designs are too many to judge one by one (2026-11-14, the curator:
"делаем, чтобы подбирал реально").

WHY. The stand judges designs cheapest first and stops at the first EARNED one: every cheaper design was then refuted,
and the answer is the optimum. Large catalogues are cut by GROUPS (prune.py): a requirement read over the hull of a
whole group. Through a structure (`assembly`) neither works. MEASURED 2026-11-14 on a roof diaphragm of about 2500
unknowns whose zones each choose a deck from a catalogue (tens of thousands of designs): one design takes most of a
second, so the whole catalogue is hours per load case; and a group has no reading to be cut by — with the zones'
stiffness a RANGE over two ADJACENT catalogue items, ZTL's proved shear flow ran from zero to about 2.7 times the true
flow. But the flows moved by less than 1 % between the weakest deck everywhere and a deck two steps up: what a zone
needs is set almost by its own demand.

WHAT. A search, trusted for nothing — the stand's judgement of each design it proposes is the ordinary one:
  UP    start with every slot at its cheapest item; a design that is not earned names the requirement it fails;
        ONE slot is raised to its next item by cost — a slot that requirement names (its bound or its quantity reads
        the slot's field), the one whose step costs least; when the requirement names NONE (a result that leans on
        every slot), every single step up is judged and the climb goes to the one that gets furthest: past the mode
        that failed (the cheapest such), else least far past the same requirement — and stops when no step is nearer;
  DOWN  from the first EARNED design, each slot is tried one step cheaper; a design that is still EARNED is taken and
        the trial starts again, until no slot can be lowered.
WHAT IS CLAIMED. The design found is EARNED like any other. Of the optimum only what was judged: "no slot can be made
one step cheaper" — NOT "no cheaper design exists"; the designs never judged are counted and said. A climb that finds
nothing is OPEN, never "every design is refuted".
"""
from __future__ import annotations

import re

from . import bricks as B

CLIMB_ABOVE = 2000      # with a structure section, design spaces larger than this are climbed unless "search": "all"


def size(b):
    """the number of designs (the product of the slots' options), without listing them"""
    n = 1
    for _s, spec in (b.get("slots") or {}).items():
        n *= sum(len(B.items(b["catalog"][c])) for c in spec["from"])
    return n


def wanted(b, worst_case=False):
    """Is this brick's design space climbed? `"search": "climb"` asks for it, `"search": "all"` forbids it; unasked,
    a brick with a structure section and more than CLIMB_ABOVE designs is (there the groups cannot be pruned)."""
    how = b.get("search")
    if how not in (None, "all", "climb"):
        raise B.BrickError('search: "climb" (raise the slot a refutation points at, then try each slot one step '
                           'cheaper) or "all" (every design, cheapest first)')
    if how == "all" or not b.get("slots") or size(b) <= 1:
        return False                    # (one design: a pinned run of a design the outer search proposed)
    auto = how is None
    if auto and not (b.get("assembly") and size(b) > CLIMB_ABOVE):
        return False
    blockers = []
    if not b.get("objective"):
        blockers.append("an objective (the climb goes by cost)")
    if worst_case:
        blockers.append("a nominal objective (not \"case\": \"worst\")")
    if b.get("where"):
        blockers.append("no `where` (version 1)")
    if b.get("report") == "all":
        blockers.append("no \"report\": \"all\" (it asks for every design)")
    if blockers:
        if auto:
            return False
        raise B.BrickError("search: \"climb\" needs " + "; ".join(blockers))
    return True


def blamed(b, req):
    """The slots a failed requirement NAMES: its bound or its quantity reads a field of the slot — directly, or through
    the laws that define what it reads. An empty list: it names none (a result that leans on every slot)."""
    if not isinstance(req, dict):
        return []
    slots = list(b.get("slots") or {})
    text = " ".join(str(req.get(k, "")) for k in ("quantity", "value"))
    seen, todo = set(), set(re.findall(r"[A-Za-z_]\w*", text))
    laws = [l["zfl"] if isinstance(l, dict) else str(l) for l in b.get("laws") or []]
    defs = {}
    for law in laws:
        if law.count("==") == 1:
            lhs = law.split("==")[0].strip()
            if lhs.isidentifier():
                defs[lhs] = law.split("==", 1)[1]
    defs.update({k: str(v) for k, v in (b.get("define") or {}).items()})
    defs.update({k: str(v) for k, v in (b.get("computed") or {}).items()} if isinstance(b.get("computed"), dict) else {})
    hit = [s for s in slots if re.search(rf"\b{re.escape(s)}(\.|__)", text)]
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        if n in defs:
            hit += [s for s in slots if s not in hit and re.search(rf"\b{re.escape(s)}(\.|__)", defs[n])]
            todo |= set(re.findall(r"[A-Za-z_]\w*", defs[n])) - seen
    return [s for s in slots if s in hit]


class Climb:
    """The order of judging. `cost(design)` is the stand's nominal cost; a design is {slot: (catalog, item)}."""

    def __init__(self, b, cost):
        self.b, self.cost = b, cost
        self.slots = list(b["slots"])
        opts = {s: [(c, it) for c in b["slots"][s]["from"] for it in B.items(b["catalog"][c])] for s in self.slots}
        if not all(opts.values()):
            raise B.BrickError("search: a slot has no item to choose from")
        base = {s: o[0] for s, o in opts.items()}
        # each slot's items by the cost of the design that holds it (the other slots at their first item); stable
        self.opts = {s: [opts[s][i] for i in sorted(range(len(opts[s])),
                                                    key=lambda i, s=s: cost(dict(base, **{s: opts[s][i]})))]
                     for s in self.slots}
        self.total = 1
        for s in self.slots:
            self.total *= len(self.opts[s])
        self.made = {}                      # position -> the design object (one object per position: the loop keys by id)
        self.where = {}                     # id(design) -> position
        self.verdict = {}                   # position -> "EARNED" | "REFUTED" | "OPEN"
        self.pos = tuple(0 for _ in self.slots)
        self.best = None                    # the position of the cheapest EARNED design taken
        self.stopped = None                 # why the climb ended without an earned design
        self.steps_up = self.steps_down = 0
        self.probe, self.probes = None, 0   # the single steps being tried for a requirement that names no slot

    def at(self, pos):
        if pos not in self.made:
            d = {s: self.opts[s][k] for s, k in zip(self.slots, pos)}
            self.made[pos] = d
            self.where[id(d)] = pos
        return self.made[pos]

    def first(self):
        return self.at(self.pos)

    def best_design(self):
        return None if self.best is None else self.made[self.best]

    def _raise(self, pos, names):
        """one slot a step up: among the named slots that can rise (else among all), the cheapest step"""
        here = self.cost(self.at(pos))
        for pool in ([s for s in self.slots if s in names], self.slots):
            steps = []
            for i, s in enumerate(self.slots):
                if s in pool and pos[i] + 1 < len(self.opts[s]):
                    nxt = pos[:i] + (pos[i] + 1,) + pos[i + 1:]
                    if nxt not in self.verdict:
                        steps.append((self.cost(self.at(nxt)) - here, i, nxt))
            if steps:
                return min(steps)[2]
        return None

    def _lower(self):
        """a neighbour of the best design, one slot one step cheaper, not judged yet"""
        for i, _s in enumerate(self.slots):
            if self.best[i] > 0:
                nxt = self.best[:i] + (self.best[i] - 1,) + self.best[i + 1:]
                if nxt not in self.verdict:
                    return nxt
        return None

    def after(self, design, verdict, names=(), over=None, mode=None, passed=()):
        """The design judged and how it came out -> the next design to judge, or None when the climb is over.
        `names`: the slots the failed requirement names. For a requirement that names NO slot (a result that leans on
        every slot - a deflection, a force in a member) the step is found by TRYING: `over` is how far the design is
        past that requirement, `mode` the mode it failed in, `passed` the modes it was judged in and earned."""
        pos = self.where[id(design)]
        self.verdict[pos] = verdict
        if self.best is None:
            if verdict == "EARNED":
                self.best, self.probe = pos, None
            else:
                names = list(names)
                if self.probe is not None and pos in self.probe["cands"]:
                    # one of the single steps being tried came back
                    self.probe["got"][pos] = (over, mode, set(passed), names)
                    left = [c for c in self.probe["cands"] if c not in self.verdict]
                    if left:
                        return self.at(left[0])
                    pick = self._pick()
                    self.probe = None
                    if pick is None:
                        self.stopped = "no single step brings the failed requirement nearer (it names no slot; every step was tried)"
                        return None
                    self.steps_up += 1
                    self.pos = pos = pick[0]
                    over, mode, _passed, names = pick[1]
                if names or over is None:
                    nxt = self._raise(pos, names)
                    if nxt is None:
                        self.stopped = ("every slot the failed requirements point at is at its last item"
                                        if any(pos[i] + 1 < len(self.opts[s]) for i, s in enumerate(self.slots))
                                        else "every slot is at its last item")
                        return None
                    self.steps_up += 1
                    self.pos = nxt
                    return self.at(nxt)
                # THE FAILED REQUIREMENT NAMES NO SLOT: every single step up from here is judged, and the climb goes to
                # the one that gets furthest (MEASURED 2026-11-14: a member force that the layout of stiffness along
                # a line moves by a tenth could only be met by the right two slots; "the cheapest step of any slot"
                # raised the wrong ones until every slot was at its last item)
                cands = [pos[:i] + (pos[i] + 1,) + pos[i + 1:] for i, s in enumerate(self.slots) if pos[i] + 1 < len(self.opts[s])]
                cands = [c for c in cands if c not in self.verdict]
                if not cands:
                    self.stopped = "every single step from here was judged already"
                    return None
                self.probe = {"base": pos, "over": over, "mode": mode, "cands": cands, "got": {}}
                self.probes += 1
                return self.at(cands[0])
        elif verdict == "EARNED":
            self.best = pos
        nxt = self._lower()
        if nxt is None:
            return None
        self.steps_down += 1
        return self.at(nxt)

    def _pick(self):
        """of the single steps tried: one that EARNED is taken before this is called; else the cheapest that got past
        the mode the base failed in; else the one that is least far past the same requirement, if nearer than the base"""
        pr = self.probe
        here = self.cost(self.at(pr["base"]))
        beyond = [(self.cost(self.at(c)) - here, c) for c, g in pr["got"].items() if pr["mode"] is not None and pr["mode"] in g[1 + 1]]
        if beyond:
            c = min(beyond)[1]
            return c, pr["got"][c]
        same = [(g[0], self.cost(self.at(c)) - here, c) for c, g in pr["got"].items()
                if g[0] is not None and g[1] == pr["mode"] and g[0] < pr["over"]]
        if same:
            c = min(same)[2]
            return c, pr["got"][c]
        return None

    def report(self, label):
        """What the search did and what it shows — for the stand's answer."""
        judged = len(self.verdict)
        out = {"mode": "climb", "designs_in_the_catalogue": self.total, "judged": judged,
               "not_judged": self.total - judged, "steps_up": self.steps_up, "steps_down": self.steps_down,
               **({"steps_found_by_trying": self.probes} if self.probes else {}),
               "why": ("the designs are too many to judge one by one and no group of them can be read at once; the "
                       "search raised the slot each refutation pointed at, then tried every slot one step cheaper. "
                       "Each design it proposed was judged by the stand as usual")}
        if self.best is None:
            out["found"] = f"no earned design ({self.stopped or 'stopped'})"
            return out
        near = []
        for i, s in enumerate(self.slots):
            if self.best[i] == 0:
                near.append({"slot": s, "one_step_cheaper": "none: it holds its cheapest item"})
            else:
                nxt = self.best[:i] + (self.best[i] - 1,) + self.best[i + 1:]
                near.append({"slot": s, "one_step_cheaper": label(self.at(nxt)), "verdict": self.verdict.get(nxt, "not judged")})
        out["one_step_cheaper"] = near
        out["shown"] = ("no single slot can be made one step cheaper: each such design was judged and is not earned. "
                        f"NOT shown: that no cheaper design exists — {self.total - judged} design(s) were never judged "
                        "(\"search\": \"all\" judges every design, cheapest first)")
        return out
