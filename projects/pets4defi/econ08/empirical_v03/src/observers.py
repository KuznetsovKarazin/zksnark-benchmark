"""Observers consume public observations, never holder assignments.

The HMM is exact for the declared DAILY Bernoulli-access model. It marginalizes
unseen successful accesses, including unseen cache resets. It is not presented
as an exact likelihood for continuous-time DeFi bursts.
"""
import numpy as np


def trigger_probabilities(publications, policy, rho=0.0, period=7):
    u = np.asarray(publications, dtype=int)
    if u.ndim != 2 or np.any(u < 0) or not 0 <= rho <= 1:
        raise ValueError("Invalid publication matrix / cover probability")
    total = u.sum(axis=0, keepdims=True)
    if policy == "selective":
        return (u > 0).astype(float)
    if policy == "common":
        return np.broadcast_to((total > 0).astype(float), u.shape).copy()
    if policy == "cover":
        return np.where(u > 0, 1.0, 1.0 - (1.0 - rho) ** (total - u))
    if policy == "batch":
        if period < 1:
            raise ValueError("Invalid cadence")
        return np.broadcast_to((np.arange(u.shape[1]) % period == 0).astype(float), u.shape).copy()
    raise ValueError(policy)


def hmm(observations, publications, access_probability, *, prior=None, ttl=30,
        policy="selective", rho=0.0, period=7, label_error=0.0, missing=0.0,
        chunk_size=128):
    """Return N x T x B posteriors. Observation -1 means no observed access.

    State = issuer, age since last full authorization (capped at TTL), pending
    selected publication. Daily order: age, publication, access, observation.
    A missing call is not a hit and does not erase an actual hidden cache reset.
    `access_probability` is an explicit attacker assumption, not inferred truth.
    """
    obs = np.asarray(observations, dtype=int)
    u = np.asarray(publications)
    if obs.ndim != 2 or u.ndim != 2 or obs.shape[1] != u.shape[1]:
        raise ValueError("Shape mismatch")
    if not np.all(np.isin(obs, [-1, 0, 1])) or not 0 <= label_error <= 0.5 or not 0 <= missing < 1 or ttl < 1:
        raise ValueError("Invalid observation model")
    n, days = obs.shape
    b = u.shape[0]
    prior = np.full(b, 1/b) if prior is None else np.asarray(prior, dtype=float)
    if prior.shape != (b,) or np.any(prior < 0) or not np.isclose(prior.sum(), 1):
        raise ValueError("Invalid prior")
    activity = np.broadcast_to(np.asarray(access_probability, dtype=float), (n,))
    if np.any(activity <= 0) or np.any(activity > 1):
        raise ValueError("Activity must be in (0,1]")
    triggers = trigger_probabilities(u, policy, rho, period)
    result = np.empty((n, days, b), dtype=float)
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        a = activity[start:end, None]
        count = end - start
        q0 = np.zeros((count, b, ttl + 1))  # no pending invalidation
        q1 = np.zeros_like(q0)             # pending invalidation
        q0[:, :, ttl] = prior
        for day in range(days):
            if day:
                for q in (q0, q1):
                    terminal = q[:, :, -1].copy()
                    q[:, :, 1:] = q[:, :, :-1]
                    q[:, :, -1] += terminal
                    q[:, :, 0] = 0
            p = triggers[None, :, day, None]
            q1 += q0 * p
            q0 *= 1 - p
            full_mass = q1.sum(axis=2) + q0[:, :, ttl]
            y = obs[start:end, day, None]
            absent = y == -1
            # No-access transitions preserve pending status and age. Unobserved
            # actual full accesses still reset age/pending in the hidden state.
            stay = np.where(absent, 1 - a, 0)
            full_weight = np.where(absent, a * missing,
                                   a * (1-missing) * np.where(y == 1, 1-label_error, label_error))
            hit_weight = np.where(absent, a * missing,
                                  a * (1-missing) * np.where(y == 0, 1-label_error, label_error))
            new0 = q0 * stay[:, :, None]
            new0[:, :, :ttl] += q0[:, :, :ttl] * hit_weight[:, :, None]
            new0[:, :, 0] += full_mass * full_weight
            q1 *= stay[:, :, None]
            q0 = new0
            weights = q0.sum(axis=2) + q1.sum(axis=2)
            normalizer = weights.sum(axis=1)
            if np.any(normalizer <= 0) or not np.all(np.isfinite(normalizer)):
                raise ValueError(f"Impossible observation under stated model at day {day}; no silent smoothing")
            q0 /= normalizer[:, None, None]
            q1 /= normalizer[:, None, None]
            result[start:end, day, :] = weights / normalizer[:, None]
    return result


def spectral(observations, issuers, seed=0, neighbors=20):
    """Sparse kNN affinity; no dense holder-by-holder distance matrix.

    Presence and full/hit are separate public features. Clustering predicts
    unlabeled groups, not issuer names. Unobserved days are not cached hits.
    """
    from sklearn.cluster import SpectralClustering
    from sklearn.preprocessing import normalize
    obs = np.asarray(observations)
    features = np.concatenate([(obs == 1), (obs == 0)], axis=1).astype(float)
    features = normalize(features)
    n = len(obs)
    if issuers >= n:
        raise ValueError("Need more holders than clusters")
    return SpectralClustering(n_clusters=issuers, affinity="nearest_neighbors",
                              n_neighbors=min(neighbors, n-1), assign_labels="cluster_qr",
                              eigen_solver="arpack", random_state=seed, n_jobs=1).fit_predict(features)


def anchored_predictions(clusters, anchors):
    """`anchors` maps ONLY disclosed holder indices to issuer labels.

    An unanchored cluster yields -1 (abstention); evaluation must exclude anchors.
    """
    c = np.asarray(clusters)
    predictions = np.full(len(c), -1, dtype=int)
    for cluster in np.unique(c):
        labels = [label for index, label in anchors.items() if c[index] == cluster]
        if labels:
            values, counts = np.unique(labels, return_counts=True)
            predictions[c == cluster] = values[np.argmax(counts)]
    return predictions
