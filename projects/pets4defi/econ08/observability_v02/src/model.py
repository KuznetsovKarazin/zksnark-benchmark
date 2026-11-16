"""Observable transcript models. Python standard library; no EVM or cryptography.

The attacker accepts only public timing, method classes and publication labels.
The generator alone receives the true issuer. See MODEL.md for scope.
"""
import bisect
import itertools
import math
import random

DAY = 86400


def entropy(p):
    return -sum(x * math.log2(x) for x in p if x > 0)


def update_lists(updates, issuers):
    return [sorted(u['at'] for u in updates if u['issuer'] == j) for j in range(issuers)]


def needs_refresh(t, last, ttl, delta, times):
    if last is None or t >= last + ttl:
        return True
    k = bisect.bisect_right(times, last)
    return k < len(times) and times[k] <= t and t >= times[k] + delta


def event_prob(t, last, ttl, delta, lists, issuer, policy, rho=0.0):
    if policy == 'every':
        return 1.0
    common_times = sorted(itertools.chain.from_iterable(lists))
    times = common_times if policy == 'common' else lists[issuer]
    if needs_refresh(t, last, ttl, delta, times):
        return 1.0
    if policy == 'event_cover' and not needs_refresh(t, last, ttl, delta, common_times):
        return 0.0
    return rho


def generate(accesses, updates, issuer, issuers=4, ttl=30*DAY, delta=0,
             policy='selective', rho=0.0, seed=0):
    """Selective is an idealized private invalidation oracle, not a contract."""
    if not 0 <= rho <= 1:
        raise ValueError('rho outside [0,1]')
    if policy == 'one_coin':
        return generate_one_coin(accesses, updates, issuer, ttl, delta, rho, seed)
    rng = random.Random(seed)
    lists = update_lists(updates, issuers)
    last = None
    rows = []
    for t in accesses:
        p = event_prob(t, last, ttl, delta, lists, issuer, policy, rho)
        refresh = rng.random() < p
        rows.append({'at': t, 'refresh': refresh})
        if refresh:
            last = t
    return rows


def infer(rows, updates, issuers=4, ttl=30*DAY, delta=0,
          policy='selective', rho=0.0, prior=None):
    """Exact Bayes filter conditional on public attempts; no true issuer arg."""
    prior = list(prior) if prior is not None else [1/issuers]*issuers
    if len(prior) != issuers or any(x < 0 for x in prior) or abs(sum(prior)-1) > 1e-12:
        raise ValueError('invalid prior')
    if any(set(r) != {'at', 'refresh'} for r in rows):
        raise ValueError('attacker input must contain only at and refresh')
    if policy == 'one_coin':
        return infer_one_coin(rows, updates, issuers, ttl, delta, rho, prior)
    lists = update_lists(updates, issuers)
    last, p, result = None, prior, []
    for row in rows:
        t, y = row['at'], row['refresh']
        likelihood = [event_prob(t, last, ttl, delta, lists, j, policy, rho) for j in range(issuers)]
        weights = [v*(l if y else 1-l) for v,l in zip(p,likelihood)]
        z = sum(weights)
        if z == 0:
            raise ValueError('impossible transcript under stated model')
        p = [v/z for v in weights]
        result.append({'at': t, 'posterior': p[:], 'entropy': entropy(p),
                       'support': sum(x>0 for x in p), 'pmax': max(p)})
        if y:
            last = t
    return result


def generate_one_coin(accesses, updates, issuer, ttl, delta, rho, seed):
    """One independent coin per foreign publication, never retried.

    A full authorization absorbs all earlier publications, including ones whose
    grace has not expired. A skipped foreign event stays skipped until absorbed.
    Own publications are always selected. This is an oracle policy, not EVM code.
    """
    rng = random.Random(seed)
    selected = sorted(u['at'] for u in updates
                      if u['issuer'] == issuer or rng.random() < rho)
    last, result = None, []
    for t in accesses:
        refresh = needs_refresh(t, last, ttl, delta, selected)
        result.append({'at': t, 'refresh': refresh})
        if refresh:
            last = t
    return result


def one_coin_probabilities(t, last, last_hit, ttl, delta, lists, common, issuer, rho):
    """Exact conditional (full, hit) probabilities after public history.

    A hit reveals that all due coins since the last full were zero. Only newly
    due coins remain random. Keeping the hit probability separately avoids
    catastrophic cancellation when 1 - tiny rounds to 1.
    """
    if needs_refresh(t, last, ttl, delta, lists[issuer]):
        return 1.0, 0.0
    lower = max(last, last_hit-delta) if last_hit is not None else last
    upper = t-delta
    if upper <= lower:
        return 0.0, 1.0
    own = lists[issuer]
    count = (bisect.bisect_right(common, upper)-bisect.bisect_right(common, lower)
             -bisect.bisect_right(own, upper)+bisect.bisect_right(own, lower))
    assert count >= 0
    hit = (1-rho)**count
    return 1-hit, hit


def infer_one_coin(rows, updates, issuers, ttl, delta, rho, prior):
    lists = update_lists(updates, issuers)
    common = sorted(u['at'] for u in updates)
    last = last_hit = None
    p, result = list(prior), []
    for row in rows:
        t, full = row['at'], row['refresh']
        prob = [one_coin_probabilities(t, last, last_hit, ttl, delta,
                                      lists, common, j, rho)[0 if full else 1]
                for j in range(issuers)]
        weights = [v*q for v,q in zip(p,prob)]
        z = sum(weights)
        if not z:
            raise ValueError('impossible transcript under one-coin policy')
        p = [v/z for v in weights]
        result.append({'at':t,'posterior':p[:],'entropy':entropy(p),
                       'support':sum(x>0 for x in p),'pmax':max(p)})
        if full:
            last, last_hit = t, None
        else:
            last_hit = t
    return result


def coin_likelihood_enumeration(rows, updates, issuer, ttl, delta, rho):
    """Independent small-instance oracle: enumerate hidden coins explicitly."""
    foreign = [j for j,u in enumerate(updates) if u['issuer'] != issuer]
    own = {j for j,u in enumerate(updates) if u['issuer'] == issuer}
    total = 0.0
    for bits in itertools.product([0,1], repeat=len(foreign)):
        probability = rho**sum(bits)*(1-rho)**(len(bits)-sum(bits))
        if not probability:
            continue
        selected = own | {j for j,b in zip(foreign,bits) if b}
        last, valid = None, True
        for row in rows:
            t = row['at']
            needed = (last is None or t-last >= ttl or any(
                last < updates[j]['at'] <= t and updates[j]['at']+delta <= t
                for j in selected))
            if needed != row['refresh']:
                valid = False
                break
            if needed:
                last = t
        if valid:
            total += probability
    return total


def likelihood_reference(rows, updates, issuer, ttl, delta, policy, rho):
    """Slow history-scan likelihood, deliberately separate from online filter."""
    value, authorizations = 1.0, []
    for r in rows:
        t = r['at']
        forced = policy == 'every' or not authorizations or t-authorizations[-1] >= ttl
        if not forced:
            last = authorizations[-1]
            qualifying = [u for u in updates if last < u['at'] <= t and
                          (policy == 'common' or u['issuer'] == issuer)]
            forced = bool(qualifying) and t >= min(u['at'] for u in qualifying) + delta
        pr = 1.0 if forced else rho
        if policy == 'event_cover' and not forced:
            last = authorizations[-1]
            all_changes = [u['at'] for u in updates if last < u['at'] <= t]
            if not all_changes or t < min(all_changes) + delta:
                pr = 0.0
        value *= pr if r['refresh'] else 1-pr
        if r['refresh']:
            authorizations.append(t)
    return value


def anonymous_label_posterior(rows, updates, issuers, ttl, delta, rho=0.0):
    """Unknown global permutation of issuer labels; exchangeable uniform prior.

    A symmetry control, NOT a full Ethereum Foundation threat model.
    """
    weights = [0.0]*issuers
    for perm in itertools.permutations(range(issuers)):
        u = [{'at': x['at'], 'issuer': perm[x['issuer']]} for x in updates]
        for j in range(issuers):
            weights[j] += likelihood_reference(rows, u, j, ttl, delta, 'selective', rho)
    z = sum(weights)
    if z == 0:
        raise ValueError('impossible transcript')
    return [x/z for x in weights]


def admissible_accept_set(candidates, fresh, k, policy):
    """Public deterministic policy; all attempts and accept/deny are observable."""
    c, s = set(candidates), set(fresh)
    if policy == 'common':
        return c if c <= s else set()
    if policy == 'fresh_k':
        return c & s if len(s) >= k else set()
    if policy != 'guard_k':
        raise ValueError(policy)
    f = c & s
    if f == c:
        return c
    if len(c) < 2*k or len(f) < k:
        return set()
    # Largest safe accepting branch; ties resolved by a fixed public ordering.
    # Remaining fresh issuers may be denied to protect the rejecting branch.
    return set(sorted(f)[:min(len(f), len(c)-k)])


def availability_trace(masks, issuer, issuers=4, k=3, policy='fresh_k'):
    c = set(range(issuers))
    positive = c.copy()
    rows = []
    for index, s in enumerate(masks):
        s = set(s)
        a = admissible_accept_set(c, s, k, policy)
        ok = issuer in a
        c = c & a if ok else c-a
        if ok:
            positive &= s
        assert issuer in c
        if policy == 'guard_k':
            assert len(c) >= k
        rows.append({'step':index, 'accepted':ok, 'fresh':sorted(s),
                     'accepting':sorted(a), 'candidates':sorted(c),
                     'support':len(c), 'entropy':math.log2(len(c)),
                     'positive_support':len(positive)})
    return rows


def heartbeat_masks(issuers, days, fail_probability, recovery_probability,
                    freshness_days, seed):
    """Synthetic independent outages. Daily publication while online; lag zero.

    Access is at noon. Last publication is source-dated at start of day.
    Initial day online; subsequent daily transitions before publication.
    """
    rng = random.Random(seed)
    online = [True]*issuers
    last = [0]*issuers
    masks, publications = [], 0
    for day in range(days):
        for j in range(issuers):
            if day:
                if online[j]:
                    online[j] = rng.random() >= fail_probability
                else:
                    online[j] = rng.random() < recovery_probability
            if online[j]:
                last[j] = day
                publications += 1
        masks.append([j for j in range(issuers) if day+0.5 < last[j]+freshness_days])
    return masks, publications
