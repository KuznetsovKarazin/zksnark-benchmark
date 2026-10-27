#!/usr/bin/env python3
"""Account for measured access policies without treating model workloads as data.

User transaction costs, app deployment and operator publication budgets remain
separate. The model follows one unaffected legitimate user's cache state. A
separate boundary experiment describes revoked-credential exposure; denied
access is never counted as a cheap successful deposit.
"""
from __future__ import annotations

import argparse
import bisect
import csv
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

DAY = 86400
D = Decimal
VARIANTS = ('unchecked', 'signed_direct', 'signed_cache', 'zk_direct', 'zk_cache')
CACHE_HITS = ('cache_hit', 'cache_hit_grace')
EXPERIMENT = Path(__file__).resolve().parents[1]
REPOSITORY = EXPERIMENT.parents[1]


def decimal(value: Any) -> Decimal:
    if isinstance(value, Fraction):
        return D(value.numerator) / D(value.denominator)
    return D(str(value))


def cell(value: Any) -> Any:
    if value is None:
        return ''
    if isinstance(value, (Decimal, Fraction)):
        return format(decimal(value), 'f')
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_hits(counts):
    return sum(counts[event] for event in CACHE_HITS)


def load_fx(path, assumption=None):
    if assumption is not None:
        value = decimal(assumption)
        metadata = {'value': str(value), 'base': 'ETH', 'quote': 'EUR',
                    'status': 'explicit_cli_assumption_not_market_quote'}
    else:
        metadata = json.loads(path.read_text())
        if (metadata.get('base'), metadata.get('quote'), metadata.get('status')) != ('ETH', 'EUR', 'observed_web_quote'):
            raise ValueError('FX quote must be an observed EUR-per-ETH web quote')
        if not metadata.get('retrieved_at_utc') or not metadata.get('source_url'):
            raise ValueError('FX quote requires retrieval time and source URL')
        value = decimal(metadata['value'])
        metadata = {**metadata, 'file_sha256': sha(path)}
    if not value.is_finite() or value <= 0:
        raise ValueError('Positive finite EUR-per-ETH value required')
    return value, metadata


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows({k: cell(v) for k, v in row.items()} for row in rows)


def quantile(values: list[Decimal], p: Decimal) -> Decimal:
    values = sorted(values)
    q = p * (len(values) - 1)
    i = int(q)
    return values[i] if i == len(values) - 1 else values[i] + (q-i) * (values[i+1]-values[i])


@dataclass(frozen=True)
class Policy:
    id: str
    mode: int
    delta_seconds: int
    root_grace_seconds: int

    def validate(self):
        if self.mode not in (0, 1, 2) or self.delta_seconds < 0 or self.root_grace_seconds < 0:
            raise ValueError('Invalid policy')
        if self.mode != 2 and self.delta_seconds:
            raise ValueError('Only bounded-delay policy can have nonzero revocation delay')


@dataclass(frozen=True)
class Context:
    apps: int
    validity_days: int
    security_schedule: str
    renewal_batching: str = 'batched'
    accesses: int = 100
    population: int = 1000
    horizon_days: int = 90
    auth_ttl_days: int = 30
    issuers: int = 4
    tree_depth: int = 10

    @property
    def id(self):
        return f'n{self.accesses}-K{self.apps}-N{self.population}-I{self.issuers}-L{self.validity_days}-{self.security_schedule}-{self.renewal_batching}'

    def validate(self):
        if min(self.apps, self.validity_days, self.accesses, self.population,
               self.horizon_days, self.auth_ttl_days, self.issuers, self.tree_depth) <= 0:
            raise ValueError('Positive workload parameters required')
        if self.security_schedule not in ('none', 'monthly', 'weekly'):
            raise ValueError('Invalid security schedule')
        if self.renewal_batching not in ('batched', 'unbatched'):
            raise ValueError('Invalid renewal batching')
        if self.issuers > self.population:
            raise ValueError('Each model issuer must have a nonempty cohort')
        # Cohort renewal replaces slots; background additions rotate issuers.
        # Do not extrapolate a population that cannot fit the measured tree.
        peak_slots = math.ceil(self.population/self.issuers) + math.ceil((self.horizon_days-1)/self.issuers)
        if peak_slots > 2**self.tree_depth:
            raise ValueError('Scenario exceeds per-issuer Merkle-tree capacity')


def workloads():
    return [Context(k, lifetime, security, batching)
            for k, lifetime, security, batching in itertools.product(
                (1, 5), (30, 90), ('none', 'monthly', 'weekly'), ('batched', 'unbatched'))]


def scenario(context: Context):
    context.validate()
    horizon = context.horizon_days * DAY
    times = [Fraction(horizon * i, context.accesses) for i in range(context.accesses)]
    expiry = context.validity_days * DAY
    renewals, expiries = [], []
    for time in times:
        if time >= expiry:
            renewals.append(time)
            expiry = time + context.validity_days * DAY
        expiries.append(expiry)
    additions = [Fraction(t) for t in range(DAY, horizon, DAY)]
    period = {'none': None, 'monthly': 30 * DAY, 'weekly': 7 * DAY}[context.security_schedule]
    security = [Fraction(t) for t in range(period, horizon, period)] if period else []
    publications = Counter(additions)
    publications.update(security)
    for time in renewals:
        count = context.issuers if context.renewal_batching == 'batched' else context.population
        publications[time] += count
        # Replacing expired leaves still removes leaves. Follow the contract's
        # conservative trusted-issuer rule: every removal advances security.
        security.extend([time] * count)
    return times, expiries, renewals, additions, sorted(security), publications


def access_trace(times, expiries, *, apps, ttl_seconds, policy: Policy,
                 variant, security_times, publications):
    """All supplied accesses are by one still-eligible user.

    Security events concern other credentials. A selective signed cache does
    not reset because another ID is revoked. ZK caches use the first security
    event after their authorization as their non-renewable delay origin.
    Root-update grace concerns proof presentation, not cached access.
    """
    policy.validate()
    if variant not in VARIANTS or len(times) != len(expiries):
        raise ValueError('Invalid variant or mismatched times/expiries')
    security_times = sorted(security_times)
    pub_times = sorted(publications)
    pub_cumulative = [0]
    for time in pub_times:
        pub_cumulative.append(pub_cumulative[-1] + publications[time])
    seen, caches, counts, trace = set(), {}, Counter(), []
    for i, time in enumerate(times):
        app = i % apps
        publication = pub_cumulative[bisect.bisect_right(pub_times, time)]
        security_epoch = bisect.bisect_right(security_times, time)
        first = app not in seen
        if first:
            counts['approve'] += 1
        reason, deadline = '', None
        if variant == 'unchecked' or variant.endswith('_direct'):
            event = 'access_first' if first else 'access_repeat'
        else:
            prior = caches.get(app)
            if prior is None:
                event = 'cache_register_first'
                reason = 'first'
            else:
                expired = time >= prior['until']
                stale = False
                if policy.mode == 0:
                    stale = publication != prior['publication']
                    reason = 'publication' if stale else ''
                elif variant.startswith('zk_'):
                    old_epoch = prior['security_epoch']
                    if security_epoch != old_epoch:
                        # Epoch is an event count. Its first invalidation is
                        # the next security event, not the latest event.
                        deadline = security_times[old_epoch] + policy.delta_seconds
                        stale = time >= deadline
                        reason = 'security_deadline' if stale else ''
                if expired:
                    reason = reason + '+expiry' if reason else 'expiry'
                event = 'cache_reauthorize' if expired or stale else ('cache_hit_grace' if deadline is not None else 'cache_hit')
                if event == 'cache_hit_grace':
                    reason = 'old_security_epoch_within_original_grace'
            if event not in CACHE_HITS:
                caches[app] = {'until': min(time + ttl_seconds, expiries[i]),
                               'publication': publication, 'security_epoch': security_epoch}
        seen.add(app)
        counts[event] += 1
        trace.append({'access_index': i, 'time_seconds': time, 'app_index': app,
            'variant': variant, 'policy': policy.id, 'event': event, 'reason': reason,
            'publication_epoch': publication, 'security_epoch': security_epoch,
            'old_security_deadline_seconds': deadline,
            'cache_until_seconds': caches.get(app, {}).get('until'),
            'eligible_user': True})
    if sum(counts[e] for e in ('access_first', 'access_repeat', 'cache_register_first',
                              'cache_reauthorize', *CACHE_HITS)) != len(times):
        raise AssertionError('Successful action counts do not reconcile')
    return counts, trace


class Measurements:
    def __init__(self, payload: dict):
        self.payload = payload
        self.metadata = payload['metadata']
        self.policies = [Policy(**{k: p[k] for k in ('id', 'mode', 'delta_seconds', 'root_grace_seconds')})
                         for p in self.metadata['policies']]
        for policy in self.policies:
            policy.validate()
        self.groups = defaultdict(list)
        for event in payload['events']:
            if event.get('evidence_status') != 'measured_local':
                raise ValueError('Only measured local events can supply operation gas')
            gas = event.get('gas_used')
            if isinstance(gas, bool) or not isinstance(gas, (int, float)) or not math.isfinite(gas) or gas < 0 or int(gas) != gas:
                raise ValueError('Gas must be nonnegative integer receipt gas')
            self.groups[event['policy'], event['variant'], event['event']].append(event)

    def observations(self, policy, variant, event):
        keys = [(policy, variant, event)]
        if variant == 'unchecked':
            keys.append(('none', 'unchecked', event))
        keys += [('shared', 'shared', event), (policy, 'shared', event)]
        for key in keys:
            if key in self.groups:
                return self.groups[key]
        raise ValueError(f'Missing measured event {policy}/{variant}/{event}')

    def gas(self, policy, variant, event):
        observations = self.observations(policy, variant, event)
        return sum(D(e['gas_used']) for e in observations) / len(observations)

    def summaries(self):
        result = []
        for (policy, variant, event), observations in sorted(self.groups.items()):
            values = [D(e['gas_used']) for e in observations]
            result.append({'policy': policy, 'variant': variant, 'event': event,
                'unit': 'gas', 'mean': sum(values)/len(values),
                'median': quantile(values, D('.5')), 'q1': quantile(values, D('.25')),
                'q3': quantile(values, D('.75')), 'n': len(values),
                'status': 'single_observation' if len(values) == 1 else 'repeated_local_measurement'})
        return result


def evaluate(context: Context, policy: Policy, variant: str, m: Measurements, security_days=None):
    times, expiries, renewals, additions, security, publications = scenario(context)
    if security_days is not None:
        if renewals:
            raise ValueError('Phase sensitivity requires a lifetime covering the horizon')
        security = [Fraction(day * DAY) for day in security_days]
        publications = Counter(additions) + Counter(security)
    counts, trace = access_trace(times, expiries, apps=context.apps,
        ttl_seconds=context.auth_ttl_days * DAY, policy=policy, variant=variant,
        security_times=security, publications=publications)
    action = sum(count * m.gas(policy.id, variant, event) for event, count in counts.items() if count)
    gate = context.apps * m.gas(policy.id, variant, 'deploy_gate') / context.population
    renewal_publications = len(renewals) * (context.issuers if context.renewal_batching == 'batched' else context.population)
    unrelated_revocations = len(security) - renewal_publications
    # Different measured events price an eight-leaf batch replacement and a
    # single replacement. Their fixed-size on-chain roots are extrapolated;
    # neither measurement executes the model population of 1,000 users.
    renewal_unit = 'batch_security_update' if context.renewal_batching == 'batched' else 'issuer_security_update'
    addition_gas = len(additions) * m.gas('shared', 'shared', 'issuer_addition')
    renewal_gas = renewal_publications * m.gas('shared', 'shared', renewal_unit)
    security_gas = unrelated_revocations * m.gas('shared', 'shared', 'issuer_security_update')
    id_gas = unrelated_revocations * m.gas('shared', 'shared', 'public_id_revoke')
    initial_root_gas = context.issuers * m.gas('shared', 'shared', 'issuer_root_initial')
    row = {'context_id': context.id, 'policy': policy.id, 'variant': variant,
        **asdict(context), 'delta_seconds': policy.delta_seconds,
        'root_grace_seconds': policy.root_grace_seconds,
        'full_authorizations_per_user': 0 if variant == 'unchecked' else context.accesses-cache_hits(counts),
        'cache_hits_per_user': cache_hits(counts),
        'old_epoch_grace_hits_per_user': counts['cache_hit_grace'],
        'reauthorizations_per_user': counts['cache_reauthorize'],
        'credential_renewals_per_user': len(renewals), 'approvals_per_user': counts['approve'],
        'user_transaction_gas_per_user': action,
        'gate_deployment_gas_per_user': gate,
        'zk_initial_roots_gas_per_population': initial_root_gas,
        'zk_ongoing_publication_budget_gas_per_population': addition_gas + renewal_gas + security_gas,
        'signed_public_id_publication_budget_gas_per_population': id_gas,
        'operator_budget_allocation_population': context.population,
        'background_addition_publications': len(additions),
        'renewal_replacement_publications': renewal_publications,
        'unrelated_revocation_publications': unrelated_revocations,
        'root_publications': len(additions) + len(security),
        'publication_scope': 'one_batch_per_issuer_per_renewal;daily_addition_rotates_issuers;all_removals_advance_security',
        'budget_note': 'operator_budgets_separate_not_added_to_user_transaction_gas',
        'security_timing_note': 'fixed_two_events_day30_day60_aligned_control' if context.security_schedule == 'monthly' else 'synthetic_schedule_not_observed_frequency',
        'delay_resolution': 'coarse_access_grid_not_evidence_for_minute_scale_delay',
        'status': 'synthetic_workload_projection_from_measured_mean_gas'}
    if security_days is not None:
        row.update(context_id=f'{context.id}-phase{security_days[0]}',
                   security_event_days=';'.join(map(str, security_days)),
                   security_timing_note='two_events_fixed_count_shifted_phase_control')
    for t in trace:
        t['context_id'] = row['context_id']
    return row, trace


def exposure_rows(policies):
    """A revoked credential's authorization existed before authoritative revoke.

    TTL/credential expiry are assumed later than the boundary. This is an
    acceptance-window calculation, not measured misconduct or expected loss.
    """
    rows = []
    for p in policies:
        offsets = sorted({-1, 0, 1, max(0, p.delta_seconds-1), p.delta_seconds, p.delta_seconds+1})
        for offset in offsets:
            accepted = offset < 0 or (p.mode == 2 and offset < p.delta_seconds)
            rows.append({'policy': p.id, 'delta_seconds': p.delta_seconds,
                'authorization_type': 'preexisting_signed_or_zk_cache',
                'offset_from_authoritative_revoke_seconds': offset,
                'old_authorization_accepted': accepted,
                'emergency_accepted_at_or_after_revoke': False,
                'maximum_acceptance_delay_seconds': p.delta_seconds,
                'old_root_zk_direct_presentation_max_seconds': min(p.delta_seconds, p.root_grace_seconds),
                'origin': 'first_authoritative_revocation_not_last_proof_refresh',
                'status': 'policy_boundary_projection_not_measured_incident_frequency'})
    return rows


def focused_burst(policies, m):
    # Ordinary user remains eligible. Five OTHER credentials are revoked in
    # four minutes; this is explicitly a stress workload, not a field estimate.
    security = [Fraction(t) for t in (3600, 3660, 3720, 3780, 3840)]
    times = [Fraction(t) for t in (0, 3599, 3600, 3660, 3720, 3780, 3840, 3899, 3900, 3901, 7199, 7200, 7201)]
    expiries = [Fraction(90 * DAY)] * len(times)
    rows, details = [], []
    for p in policies:
        for variant in ('signed_cache', 'zk_cache'):
            counts, trace = access_trace(times, expiries, apps=1, ttl_seconds=30 * DAY,
                policy=p, variant=variant, security_times=security, publications=Counter(security))
            gas = sum(count*m.gas(p.id, variant, event) for event, count in counts.items() if count)
            rows.append({'policy': p.id, 'variant': variant, 'delta_seconds': p.delta_seconds,
                'eligible_user_accesses': len(times), 'other_credential_revocations': len(security),
                'cache_hits': cache_hits(counts), 'old_epoch_grace_hits': counts['cache_hit_grace'],
                'reauthorizations': counts['cache_reauthorize'],
                'user_transaction_gas': gas, 'revoked_credential_max_acceptance_seconds': p.delta_seconds,
                'event_schedule_seconds': ';'.join(map(str, security)),
                'access_schedule_seconds': ';'.join(map(str, times)),
                'status': 'synthetic_burst_projection;cost_for_unaffected_user;exposure_for_distinct_revoked_credential',
                'risk_money': ''})
            details.extend(trace)
    return rows, details


def freshness(signed, zk):
    if zk['variant'] == 'zk_direct' and signed['delta_seconds'] > zk['root_grace_seconds']:
        return 'signed_grace_exceeds_old_root_zk_presentation_bound'
    return 'matched_maximum_revocation_delay;different_status_check_architectures'


def comparisons(rows, fee, fx):
    index = {(r['context_id'], r['policy'], r['variant']): r for r in rows}
    result = []
    for context, policy in sorted({(r['context_id'], r['policy']) for r in rows}):
        unchecked = index[context, policy, 'unchecked']['user_transaction_gas_per_user']
        for mode in ('direct', 'cache'):
            signed = index[context, policy, 'signed_' + mode]
            zk = index[context, policy, 'zk_' + mode]
            compliance = signed['user_transaction_gas_per_user'] - unchecked
            privacy = zk['user_transaction_gas_per_user'] - signed['user_transaction_gas_per_user']
            result.append({'context_id': context, 'policy': policy, 'access_method': mode,
                'signed_minus_unchecked_user_gas': compliance,
                'zk_minus_signed_user_gas': privacy,
                'zk_minus_signed_gate_setup_gas_per_user': zk['gate_deployment_gas_per_user']-signed['gate_deployment_gas_per_user'],
                'eur_per_eth': fx,
                'privacy_user_eur_fee_p50': privacy*D(fee['p50_wei'])/D(10**18)*fx,
                'privacy_user_eur_fee_p90': privacy*D(fee['p90_wei'])/D(10**18)*fx,
                'compliance_user_eur_fee_p50': compliance*D(fee['p50_wei'])/D(10**18)*fx,
                'fee_p50_wei_per_gas': fee['p50_wei'], 'fee_p90_wei_per_gas': fee['p90_wei'],
                'period_days': signed['horizon_days'],
                'revocation_freshness': freshness(signed, zk),
                'boundary': 'user_transactions_only;operator_and_setup_separate;offchain_cost_unknown',
                'status': 'fee_scenarios_not_quarterly_cost_quantiles'})
    return result


def decisions(rows, fee, fx):
    """Choose within each family using user action/approval gas only.

    Deployment, operator and unknown off-chain costs do not enter selection.
    Equal action costs choose direct deterministically; no full-system optimum
    or privacy demand is inferred from this conditional cost comparison.
    """
    index = {(r['context_id'], r['policy'], r['variant']): r for r in rows}
    result = []
    for context, policy in sorted({(r['context_id'], r['policy']) for r in rows}):
        signed = min((index[context, policy, 'signed_'+mode] for mode in ('direct', 'cache')),
                     key=lambda r: r['user_transaction_gas_per_user'])
        zk = min((index[context, policy, 'zk_'+mode] for mode in ('direct', 'cache')),
                 key=lambda r: r['user_transaction_gas_per_user'])
        unchecked = index[context, policy, 'unchecked']['user_transaction_gas_per_user']
        compliance = signed['user_transaction_gas_per_user'] - unchecked
        privacy = zk['user_transaction_gas_per_user'] - signed['user_transaction_gas_per_user']
        result.append({'context_id': context, 'policy': policy,
            'selected_signed_variant': signed['variant'], 'selected_zk_variant': zk['variant'],
            'selection_objective': 'minimum_user_action_and_approval_gas_only',
            'signed_user_transaction_gas_per_user': signed['user_transaction_gas_per_user'],
            'zk_user_transaction_gas_per_user': zk['user_transaction_gas_per_user'],
            'signed_minus_unchecked_user_gas': compliance, 'zk_minus_signed_user_gas': privacy,
            'selected_signed_gate_deployment_gas_per_user': signed['gate_deployment_gas_per_user'],
            'selected_zk_gate_deployment_gas_per_user': zk['gate_deployment_gas_per_user'],
            'eur_per_eth': fx,
            'privacy_user_eur_fee_p50': privacy*D(fee['p50_wei'])/D(10**18)*fx,
            'privacy_user_eur_fee_p90': privacy*D(fee['p90_wei'])/D(10**18)*fx,
            'compliance_user_eur_fee_p50': compliance*D(fee['p50_wei'])/D(10**18)*fx,
            'fee_p50_wei_per_gas': fee['p50_wei'], 'fee_p90_wei_per_gas': fee['p90_wei'],
            'revocation_freshness': freshness(signed, zk),
            'boundary': 'user_transactions_only;operator_and_setup_separate;offchain_cost_unknown;not_full_system_minimum',
            'status': 'conditional_cost_difference_not_privacy_demand_or_quarterly_cost_quantile'})
    return result


def phase_sensitivity(m):
    policy = next(p for p in m.policies if p.id == 'security')
    rows, traces = [], []
    for apps, event_days, variant in itertools.product((1, 5), ((30, 60), (37, 67), (15, 45)), VARIANTS):
        row, trace = evaluate(Context(apps, 90, 'monthly'), policy, variant, m, security_days=event_days)
        rows.append(row)
        traces.extend(trace)
    return rows, traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements', type=Path, default=EXPERIMENT/'results/policy_measurements.json')
    parser.add_argument('--out', type=Path, default=EXPERIMENT/'results')
    parser.add_argument('--participant-out', type=Path, default=REPOSITORY/'projects/pets4defi/data')
    parser.add_argument('--fee-snapshot', type=Path, default=EXPERIMENT/'results/fee_snapshot.json')
    parser.add_argument('--fx-quote', type=Path, default=REPOSITORY/'projects/pets4defi/data/fx_quote.json')
    parser.add_argument('--assumed-eur-per-eth', type=Decimal, default=None)
    parser.add_argument('--allow-debug', action='store_true')
    args = parser.parse_args()
    payload = json.loads(args.measurements.read_text())
    m = Measurements(payload)
    if payload['metadata'].get('debug_run') and not args.allow_debug:
        raise ValueError('Debug measurements require --allow-debug and are not final evidence')
    if payload['metadata'].get('debug_run') and args.participant_out.resolve() == (REPOSITORY/'projects/pets4defi/data').resolve():
        raise ValueError('Debug export requires a separate --participant-out directory')
    register = args.participant_out/'input_register.csv'
    if not register.exists():
        raise ValueError('Provide input_register.csv; exporter does not replace sourced economic inputs')
    fx, fx_metadata = load_fx(args.fx_quote, args.assumed_eur_per_eth)
    fees = json.loads(args.fee_snapshot.read_text())
    network = next(n for n in fees['networks'] if n['network'] == 'ethereum')
    if network['status'] != 'available':
        raise ValueError('No observed Ethereum fee window available')
    archive = args.fee_snapshot.parent/fees['raw_archive']['path']
    if sha(archive) != fees['raw_archive']['sha256']:
        raise ValueError('Fee archive integrity failure')
    fee = network['summary']['within_block_effective_p50_block_weighted']
    summaries = m.summaries()
    rows, traces = [], []
    for context, policy, variant in itertools.product(workloads(), m.policies, VARIANTS):
        row, trace = evaluate(context, policy, variant, m)
        rows.append(row)
        traces.extend(trace)
    diff = comparisons(rows, fee, fx)
    decision_rows = decisions(rows, fee, fx)
    phase, phase_trace = phase_sensitivity(m)
    exposure = exposure_rows(m.policies)
    burst, burst_detail = focused_burst(m.policies, m)
    source_meta = {'measurements_sha256': sha(args.measurements), 'exporter_sha256': sha(Path(__file__)),
                   'measurement_source_sha': payload['metadata'].get('source_sha', ''),
                   'debug_run': bool(payload['metadata'].get('debug_run'))}
    for table in (summaries, rows, diff, decision_rows, phase, exposure, burst):
        for row in table:
            row.update(source_meta)
    for row in diff + decision_rows:
        row.update(fx_status=fx_metadata['status'], fx_source_url=fx_metadata.get('source_url', ''),
                   fx_retrieved_at_utc=fx_metadata.get('retrieved_at_utc', ''))
    files = {'policy_event_costs.csv': summaries, 'policy_workload_costs.csv': rows,
        'policy_comparisons.csv': diff, 'policy_trace.csv': traces,
        'policy_decisions.csv': decision_rows, 'policy_phase_sensitivity.csv': phase,
        'policy_phase_trace.csv': phase_trace,
        'policy_exposure.csv': exposure, 'policy_burst.csv': burst,
        'policy_burst_trace.csv': burst_detail, 'policy_failure_costs.csv': payload.get('failures', [])}
    args.out.mkdir(parents=True, exist_ok=True)
    for name, table in files.items():
        write_csv(args.out/name, table)
    args.participant_out.mkdir(parents=True, exist_ok=True)
    primary = [r for r in rows if r['renewal_batching'] == 'batched' and r['policy'] in ('global', 'security')]
    primary_ids = {r['context_id'] for r in primary}
    primary_diff = [r for r in decision_rows if r['context_id'] in primary_ids and r['policy'] in ('global', 'security')]
    for name, table in {'event_costs.csv': summaries, 'workload_costs.csv': primary,
                        'privacy_premium.csv': primary_diff, 'revocation_tradeoff.csv': burst,
                        'phase_sensitivity.csv': phase}.items():
        write_csv(args.participant_out/name, table)
    # Existing input register is deliberately kept editable: do not discard a
    # colleague's sourced values. Initial generation can copy the known template.
    try:
        source_file = str(args.measurements.resolve().relative_to(REPOSITORY))
    except ValueError:
        source_file = args.measurements.name
    provenance = {'dataset': 'PETs4DeFi eligibility-access policy inputs', **source_meta,
        'source_file': source_file, 'fee_snapshot_sha256': sha(args.fee_snapshot),
        'fee_archive_sha256': sha(archive), 'fee_window': network['window'],
        'fee_metric': fees['methodology']['summary_metric'],
        'fx': fx_metadata,
        'policies': [asdict(p) for p in m.policies],
        'counts': {'primary_contexts': len(primary_ids), 'primary_workload_rows': len(primary),
                   'primary_decision_rows': len(primary_diff), 'phase_sensitivity_rows': len(phase),
                   'all_workload_rows': len(rows)},
        'cost_boundary': 'user_transactions;gate_deployment_and_operator_budgets_separate;no_full_system_total',
        'population_boundary': 'synthetic_synchronized_cohort;four_issuers_250_users_each;renewal_reuses_slots;daily_additions_rotate_issuers;fixed_root_gas_extrapolation_from_8_leaf_batch_not_1000_user_execution',
        'comparison_boundary': 'same_eligible_workload;cached_revocation_bounds_matched;direct_delta3600_signed_grace_exceeds_ZK_old_root_presentation_bound300',
        'files': {p.name: sha(p) for p in sorted(args.participant_out.glob('*.csv'))},
        'unmeasured': ['operational_issuer_prices', 'population_witness_distribution',
                      'phone_performance', 'full_L2_fees', 'incident_frequency_and_loss',
                      'minimal_standalone_signed_registry_deployment']}
    (args.participant_out/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    (args.out/'policy_accounting_summary.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(json.dumps(provenance['counts']))


if __name__ == '__main__':
    main()
