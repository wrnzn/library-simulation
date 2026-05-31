import sys
import os

sys.path.append(os.getcwd())
from app import run_simulation_logic

scenarios = [
    {"name": "Scenario 1: Baseline (Normal Day)", "arrival": 1.0, "loiter": 0.65, "seed": 42},
    {"name": "Scenario 2: Midterm/Finals Week (High Volume, Low Loitering)", "arrival": 1.5, "loiter": 0.20, "seed": 42},
    {"name": "Scenario 3: Policy Enforcement (Normal Volume, Low Loitering)", "arrival": 1.0, "loiter": 0.10, "seed": 42}
]

for s in scenarios:
    raw_logs, kpis = run_simulation_logic(s['arrival'], s['loiter'], seed=s['seed'])
    peak_occupants = max([len(l['occupants']) for l in raw_logs]) if raw_logs else 0
    total_balks = raw_logs[-1]['balks'] if raw_logs else 0
    
    print(f"=== {s['name']} ===")
    print(f"Arrival: {s['arrival']} | Loiter: {s['loiter']*100}% | Seed: {s['seed']}")
    print(f"Wait Time:  {kpis['avg_wait']:.2f} mins")
    print(f"Cycle Time: {kpis['avg_cycle']:.2f} mins")
    print(f"Throughput: {kpis['throughput']:.2f} / hr")
    print(f"Peak Cap:   {peak_occupants} students")
    print(f"Balks:      {total_balks}")
    print("="*40)
