import os
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt

np.random.seed(42) # For reproducibility

# Ensure directories exist
os.makedirs("data", exist_ok=True)
os.makedirs("plots", exist_ok=True)

# 1. NHPP Arrivals for 1 week (5 working days, 12 hours/day = 720 minutes)
# Base rate + morning spike (9 AM = 120m) + noon spike (12 PM = 300m) + afternoon (3 PM = 480m)
def arrival_rate(t_min):
    t_day = t_min % 720
    base = 0.8  # Base arrival rate (e.g. steady flow)
    # Spikes around class dismissals and noon lunch
    morning = 2.5 * np.exp(-0.5 * ((t_day - 120) / 25)**2)
    noon = 4.0 * np.exp(-0.5 * ((t_day - 300) / 40)**2)
    afternoon = 2.5 * np.exp(-0.5 * ((t_day - 480) / 30)**2)
    return base + morning + noon + afternoon

# Generate exact arrivals per minute across 5 days
num_days = 5
total_minutes = num_days * 720
arrivals = []
for t in range(total_minutes):
    rate = arrival_rate(t)
    count = np.random.poisson(rate)
    for _ in range(count):
        arrivals.append(t)

df_arrivals = pd.DataFrame({"arrival_time_min": arrivals})
df_arrivals.to_csv("data/arrivals_data.csv", index=False)

# Plot Arrival Rate Function
t_arr = np.arange(720)
rates = [arrival_rate(t) for t in t_arr]
plt.figure(figsize=(10, 5))
plt.plot(t_arr, rates, label="Expected $\lambda(t)$ Rate", color='#f97316', linewidth=2)
plt.fill_between(t_arr, rates, color='#f97316', alpha=0.2)
plt.title("Expected Arrival Rate over 12-hour Operational Day (7AM - 7PM)", pad=15)
plt.xlabel("Minute of Day")
plt.ylabel("Expected Arrivals / Minute")
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig("plots/arrival_rate.png", dpi=150)
plt.close()

# 2. Dwell Times (Mixture Distribution)
n_samples = len(arrivals)
# Ratios: 65% Loiter/Eat, 35% Study based on observed hidden bottlenecks
intent = np.random.choice(["Loiter/Eat", "Study"], size=n_samples, p=[0.65, 0.35])

# Using Lognormal distributions for realistic right-skewed service times
sigma_loiter = 0.5
scale_loiter = 25 # median 25 mins

sigma_study = 0.4
scale_study = 110 # median 110 mins

dwell_times = []
for i in intent:
    if i == "Loiter/Eat":
        dt = stats.lognorm.rvs(s=sigma_loiter, scale=scale_loiter)
    else:
        dt = stats.lognorm.rvs(s=sigma_study, scale=scale_study)
    dwell_times.append(max(5, dt)) # cap minimum stay at 5 minutes

df_dwell = pd.DataFrame({"intent": intent, "dwell_time_min": dwell_times})
df_dwell.to_csv("data/dwell_times.csv", index=False)

# Plot Dwell Times
plt.figure(figsize=(10, 5))
plt.hist(df_dwell[df_dwell['intent'] == 'Loiter/Eat']['dwell_time_min'], bins=40, alpha=0.7, label='Loiter/Eat (Lognormal)', color='#64748b')
plt.hist(df_dwell[df_dwell['intent'] == 'Study']['dwell_time_min'], bins=40, alpha=0.7, label='Study (Lognormal)', color='#f97316')
plt.title("Dwell Time Mixture Distribution by Intent", pad=15)
plt.xlabel("Dwell Time (minutes)")
plt.ylabel("Frequency")
plt.xlim(0, 300)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("plots/dwell_times.png", dpi=150)
plt.close()

print(f"Synthesis Complete. Total simulated arrivals: {n_samples}")
print("\nDwell Time Statistics:")
print(df_dwell.groupby('intent')['dwell_time_min'].describe().round(2))
