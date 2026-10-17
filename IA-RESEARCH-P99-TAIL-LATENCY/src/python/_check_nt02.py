import json

r = json.load(open('experiments/nt02_calibration_results.json'))
print("=== NT-02 stored results ===")
print(f"base_config: {r['base_config']}")
print()
for c in r['calibration_results']:
    print(f"rho={c['rho']}, alpha={c['alpha']}, p_relax={c['p_relax']}, "
          f"P99_sim={c['P99_simulated']:.0f}, P99_pred={c['P99_predicted']:.0f}, "
          f"err={c['relative_error_pct']:.1f}%, p_ctrl={c.get('p_controller', 'N/A')}")
