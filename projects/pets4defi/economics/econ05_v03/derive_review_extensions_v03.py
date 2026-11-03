#!/usr/bin/env python3
"""Regenerate ECON-05 per-case symbolic thresholds and the ONE matched revocation-phase sensitivity.

Uses supplied 30-row TECH-01 phase_sensitivity.csv; no ZKP, contract, web, or new simulation.
Original accepted ECON-04 economics implementation remains unchanged.
"""
from pathlib import Path
from decimal import Decimal as D, getcontext
import csv, hashlib, json
getcontext().prec=35
P=Path(__file__).resolve().parent
R=P/'results'

def read(path):
    with path.open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))

def write(path,fields,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

core=read(R/'econ05_sweep_30rows.csv')
assert len(core)==30
T=['deposits_per_user_90d','archived_fee_scenario','user_share_alpha','selected_signed_variant','selected_zk_variant','signed_pool_eur_user','zk_pool_eur_user','service_reimbursement_eur_user','required_other_net_service_revenue_inequality','required_incremental_service_margin_vs_B0_inequality','required_additional_user_benefit_inequality','gas_only_user_difference_eur','gas_only_minimum_nonnegative_benefit_eur','allocation_identity_error_eur','source_classification']
thresholds=[]
for x in core:
    r=D(x['service_subsidy_eur_user']);delta=D(x['user_pool_difference_vs_B0_eur_user']);n=x['population_n']
    thresholds.append(dict(deposits_per_user_90d=x['activity_deposits_per_user_90d'],archived_fee_scenario=x['fee_scenario'],user_share_alpha=x['user_share_alpha'],selected_signed_variant=x['baseline_signed_variant'],selected_zk_variant=x['selected_zk_variant'],signed_pool_eur_user=x['signed_access_pool_eur_user'],zk_pool_eur_user=x['zk_access_pool_eur_user'],service_reimbursement_eur_user=str(r),required_other_net_service_revenue_inequality=f'm_ZK >= s_other,ZK + {r:.6f} EUR - f + F_ZK/{n}',required_incremental_service_margin_vs_B0_inequality=f'm_ZK-m_B0 >= delta(s_other) + {r:.6f} EUR + delta(F)/{n} [same f]',required_additional_user_benefit_inequality=f'B_required >= {delta:.6f} EUR + delta(u_other) + v*(t_ZK-t_B0)',gas_only_user_difference_eur=str(delta),gas_only_minimum_nonnegative_benefit_eur=str(max(D(0),delta)),allocation_identity_error_eur=x['gas_cost_conservation_error_eur_user'],source_classification='measured event gas × modeled workload; unpriced costs and revenues symbolic'))
write(R/'thresholds_30rows.csv',T,thresholds)
source=P/'inputs'/'phase_sensitivity.csv'
phase=read(source);assert len(phase)==30
assert {x['measurement_source_sha'] for x in phase}=={'8e71e52fbfef382b96b75266a7c78d816c7e1751'}
q={'p50':D('.130658648'),'p90':D('.716536567')}; fx=D('2164.73'); alpha=D('.5');N=1000
matched={}
for name,days in [('15/45','15;45'),('30/60','30;60'),('37/67','37;67')]:
    entries=[x for x in phase if x['security_event_days']==days and x['apps']=='1']
    assert len(entries)==5 and {x['variant'] for x in entries}=={'unchecked','signed_direct','signed_cache','zk_direct','zk_cache'}
    assert all(x['accesses']=='100' and x['population']=='1000' and x['horizon_days']=='90' and x['validity_days']=='90' and x['auth_ttl_days']=='30' and x['unrelated_revocation_publications']=='2' and x['policy']=='security' and x['issuers']=='4' and x['root_grace_seconds']=='300' for x in entries)
    e={x['variant']:x for x in entries}
    sm=min(('signed_direct','signed_cache'),key=lambda z:D(e[z]['user_transaction_gas_per_user']))
    zm=min(('zk_direct','zk_cache'),key=lambda z:D(e[z]['user_transaction_gas_per_user']))
    assert sm=='signed_cache' and zm=='zk_cache'
    matched[name]=dict(e=e,sm=sm,zm=zm,G0=D(e['unchecked']['user_transaction_gas_per_user']),Gs=D(e[sm]['user_transaction_gas_per_user']),Gz=D(e[zm]['user_transaction_gas_per_user']))
assert [int(matched[k]['e']['zk_cache']['full_authorizations_per_user']) for k in ('15/45','30/60','37/67')]==[4,3,4]
assert [matched[k]['Gz'] for k in ('15/45','30/60','37/67')]==[D('8068448.4'),D('7780318.6'),D('8068448.4')]
reference=matched['30/60']
fields=['selected_extension','phase_days','event_days','policy','n_deposits_per_user_90d','services_K','population_N','credential_lifetime_days','authorization_TTL_days','weekly_vs_phase_scope','revocations_count','matched_signed_method','matched_ZK_method','unchecked_gas_per_user','signed_gas_per_user','ZK_gas_per_user','signed_auth_count','signed_cache_hits','ZK_auth_count','ZK_cache_hits','ZK_minus_signed_full_gas','ZK_gas_delta_vs_aligned','archived_fee_scenario','fee_gwei_per_gas','EUR_per_ETH','common_unchecked_cost_EUR','signed_access_pool_EUR','ZK_access_pool_EUR','ZK_minus_signed_network_EUR','user_share_alpha','service_cash_reimbursement_EUR','user_conditional_network_difference_vs_B0_EUR','service_reimbursement_delta_vs_aligned_EUR','original_network_bill_EUR','allocation_conservation_error_EUR','required_service_margin_inequality','required_user_benefit_inequality','source_sha256','source_file','evidence_status']
outputs=[];sh=hashlib.sha256(source.read_bytes()).hexdigest()
for name,days in [('15/45','15;45'),('30/60','30;60'),('37/67','37;67')]:
    z=matched[name]
    for fee,p in q.items():
        factor=p*fx/D(10)**9
        c0=z['G0']*factor; As=(z['Gs']-z['G0'])*factor;Az=(z['Gz']-z['G0'])*factor
        refund=(1-alpha)*Az; delta_user=alpha*Az-As
        aligned_refund=(1-alpha)*(reference['Gz']-reference['G0'])*factor
        resid=c0+alpha*Az+refund-z['Gz']*factor
        assert abs(resid)<D('1e-22')
        e=z['e']
        outputs.append(dict(selected_extension='fixed-count revocation phase ONLY',phase_days=name,event_days=days,policy='security',n_deposits_per_user_90d=100,services_K=1,population_N=N,credential_lifetime_days=90,authorization_TTL_days=30,weekly_vs_phase_scope='TWO REVOCATIONS; not 12-weekly core',revocations_count=2,matched_signed_method=z['sm'],matched_ZK_method=z['zm'],unchecked_gas_per_user=str(z['G0']),signed_gas_per_user=str(z['Gs']),ZK_gas_per_user=str(z['Gz']),signed_auth_count=e[z['sm']]['full_authorizations_per_user'],signed_cache_hits=e[z['sm']]['cache_hits_per_user'],ZK_auth_count=e[z['zm']]['full_authorizations_per_user'],ZK_cache_hits=e[z['zm']]['cache_hits_per_user'],ZK_minus_signed_full_gas=str(z['Gz']-z['Gs']),ZK_gas_delta_vs_aligned=str(z['Gz']-reference['Gz']),archived_fee_scenario=fee,fee_gwei_per_gas=str(p),EUR_per_ETH=str(fx),common_unchecked_cost_EUR=str(c0),signed_access_pool_EUR=str(As),ZK_access_pool_EUR=str(Az),ZK_minus_signed_network_EUR=str((z['Gz']-z['Gs'])*factor),user_share_alpha=str(alpha),service_cash_reimbursement_EUR=str(refund),user_conditional_network_difference_vs_B0_EUR=str(delta_user),service_reimbursement_delta_vs_aligned_EUR=str(refund-aligned_refund),original_network_bill_EUR=str(z['Gz']*factor),allocation_conservation_error_EUR=str(resid),required_service_margin_inequality=f'm_ZK >= s_other,ZK + {refund:.6f} EUR - f + F_ZK/{N}',required_user_benefit_inequality=f'B_required >= {delta_user:.6f} EUR + delta(u_other) + v*delta(t)',source_sha256=sh,source_file='inputs/phase_sensitivity.csv',evidence_status='Source-verified synthetic matched technical phase trace, conditional network-only economics; not measured demand/profitability'))
write(R/'phase_selected_source_verified_6rows.csv',fields,outputs)
# Supplement run metadata without replacing accepted numerical input history.
meta_path=R/'run_metadata.json'
meta=json.loads(meta_path.read_text());cfg=P/'econ05_config.json'
meta.update({'stage':'ECON-05 reproducible core sweep v0.3 with ONE source-verified technical phase extension','selected_extension':json.loads(cfg.read_text())['selected_single_technical_extension'],'phase_extension_rows':len(outputs),'phase_source_sha256':sh,'config_sha256':hashlib.sha256(cfg.read_bytes()).hexdigest(),'scope':'15×2 core weekly sensitivity plus 3×2 separately controlled two-revocation phase; no Cartesian product'})
for fn in ['phase_sensitivity.csv','ECONOMIC_PROTOCOL.md','PETs4DeFi_source_README.md','event_costs.csv','event_ledger.csv']:
    meta['input_file_sha256'][fn]=hashlib.sha256((P/'inputs'/fn).read_bytes()).hexdigest()
meta_path.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+'\n')
print('Reproduced 30 explicit thresholds, 6 source-verified phase-price rows; SHA-256:',sh)
