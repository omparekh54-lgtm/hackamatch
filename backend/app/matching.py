"""Seeded multistart allocation with cached candidate triples and global swap search."""

import itertools, random, statistics, time

WEIGHTS = {
    "skills": 35,
    "roles": 20,
    "goals": 15,
    "experience": 10,
    "schedule": 10,
    "style": 5,
    "interests": 5,
}
VERSION = "hm-1.0"


def avg(v):
    return sum(v) / len(v) if v else None


def overlap(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a and b else None


def score_team(team, weights=None, pool_experience=1):
    weights = weights or WEIGHTS
    # Skill component measures marginal diversity. Role component separately measures
    # whether distinct people can cover build, design and communicate responsibilities.
    known = [
        set(p.get("skills", [])) - {"other"}
        for p in team
        if set(p.get("skills", [])) - {"other"}
    ]
    skills = None
    if len(known) >= 2:
        union = set.union(*known)
        diversity = avg(
            [
                1 - len(a & b) / len(a | b)
                for a, b in itertools.combinations(known, 2)
                if a | b
            ]
        )
        skills = 0.6 * min(1, len(union) / 4) + 0.4 * (diversity or 0)
    role_sets = []
    for p in team:
        sk = set(p.get("skills", []))
        r = {}
        if sk & {"frontend", "backend", "ai", "data", "mobile", "hardware"}:
            r["build"] = 1
        elif "fullstack" in sk:
            r["build"] = 0.8
        if "design" in sk:
            r["design"] = 1
        elif sk & {"frontend", "fullstack"}:
            r["design"] = 0.35
        if sk & {"presentation", "product", "research"}:
            r["communicate"] = 1
        role_sets.append(r)
    roles = (
        max(
            (
                sum(role_sets[i].get(role, 0) for i, role in enumerate(perm)) / 3
                for perm in itertools.permutations(["build", "design", "communicate"])
            ),
            default=0,
        )
        if all(set(p.get("skills", [])) - {"other"} for p in team)
        else None
    )

    def pair_feature(key):
        return avg(
            [
                v
                for a, b in itertools.combinations(team, 2)
                if (v := overlap(a.get(key, []), b.get(key, []))) is not None
            ]
        )

    exp = [p["experience"] for p in team if p.get("experience") is not None]
    experience = (
        1 - min(1, abs(statistics.mean(exp) - pool_experience) / 2)
        if len(exp) >= 2
        else None
    )
    lead = [p["leadership"] for p in team if p.get("leadership") is not None]
    leadership = 1 - abs(statistics.mean(lead) - 1) if len(lead) >= 2 else None
    conflicts = [p["conflict"] for p in team if p.get("conflict")]
    conflict = (
        (0.6 + 0.4 * min(1, (len(set(conflicts)) - 1) / 2))
        if len(conflicts) >= 2
        else None
    )
    stretch = [
        p
        for p in team
        if p.get("stretch") == "stretch" and set(p.get("skills", [])) - {"other"}
    ]
    support_values = []
    for p in stretch:
        known_peers = [
            q for q in team if q is not p and set(q.get("skills", [])) - {"other"}
        ]
        if known_peers:
            support_values.append(
                float(
                    any(
                        (set(p["skills"]) - {"other"}) & (set(q["skills"]) - {"other"})
                        for q in known_peers
                        if q.get("stretch") != "stretch"
                    )
                )
            )
    support = avg(support_values)
    style = avg([x for x in [leadership, conflict, support] if x is not None])
    interests = avg(
        [
            v
            for k in ["hobbies", "description", "feed", "soundtrack"]
            if (v := pair_feature(k)) is not None
        ]
    )
    components = {
        "skills": skills,
        "roles": roles,
        "goals": pair_feature("goals"),
        "experience": experience,
        "schedule": pair_feature("schedule"),
        "style": style,
        "interests": interests,
    }
    available = sum(weights[k] for k, v in components.items() if v is not None)
    total = (
        sum(weights[k] * v for k, v in components.items() if v is not None) / available
        if available
        else 0.5
    )
    return {
        "total": round(total * 100, 3),
        "components": {
            k: round(v * 100, 2) if v is not None else None
            for k, v in components.items()
        },
        "signal_weight_available": available,
        "weights": weights,
        "explanation": "Complementary capabilities, workable schedules and shared goals; unknown signals are omitted. This is a matching heuristic, not a measure of people.",
    }


def allocate(pool, seed=42, weights=None, restarts=16):
    start = time.perf_counter()
    pool = sorted(pool, key=lambda p: p["id"])
    if len(set(p["id"] for p in pool)) != len(pool):
        raise ValueError("Duplicate participant")
    if len(pool) > 500:
        raise ValueError(
            "Allocation supports up to 500 verified participants per window"
        )
    rng = random.Random(seed)
    cache = {}
    ex = [p["experience"] for p in pool if p.get("experience") is not None]
    mean = statistics.mean(ex) if ex else 1

    def score(ids):
        key = tuple(sorted(ids))
        if key not in cache:
            cache[key] = score_team([pool[i] for i in key], weights, mean)
        return cache[key]["total"]

    best = None
    best_value = -1
    baseline = None
    for restart in range(restarts):
        order = list(range(len(pool)))
        rng.shuffle(order)
        teams = [order[i : i + 3] for i in range(0, len(order) - len(order) % 3, 3)]
        leftovers = order[len(teams) * 3 :]
        initial = sum(score(t) for t in teams)
        if baseline is None:
            baseline = initial
        # Global objective: all complete teams; swaps include waitlist participants.
        for _ in range(max(100, len(pool) * 30)):
            if not teams:
                break
            a = rng.randrange(len(teams))
            ai = rng.randrange(3)
            if leftovers and rng.random() < 0.2:
                bi = rng.randrange(len(leftovers))
                candidate = teams[a].copy()
                candidate[ai] = leftovers[bi]
                if score(candidate) > score(teams[a]) + 1e-8:
                    leftovers[bi], teams[a][ai] = teams[a][ai], leftovers[bi]
            elif len(teams) > 1:
                b = rng.randrange(len(teams))
                if a == b:
                    continue
                bi = rng.randrange(3)
                ta = teams[a].copy()
                tb = teams[b].copy()
                ta[ai], tb[bi] = tb[bi], ta[ai]
                if score(ta) + score(tb) > score(teams[a]) + score(teams[b]) + 1e-8:
                    teams[a], teams[b] = ta, tb
        val = sum(score(t) for t in teams)
        if val > best_value:
            best_value = val
            best = (teams, leftovers)
    groups, leftovers = best or ([], list(range(len(pool))))
    result = {
        "teams": [
            {
                "members": sorted(pool[i]["id"] for i in t),
                "score": cache[tuple(sorted(t))],
            }
            for t in groups
        ],
        "unassigned": sorted(pool[i]["id"] for i in leftovers),
        "seed": seed,
        "algorithm": VERSION,
        "objective": best_value,
        "baseline": baseline,
        "candidates_scored": len(cache),
        "runtime_ms": round((time.perf_counter() - start) * 1000, 2),
    }
    assigned = [i for t in result["teams"] for i in t["members"]]
    assert len(assigned) == len(set(assigned)) and set(
        assigned + result["unassigned"]
    ) == {p["id"] for p in pool}
    return result
