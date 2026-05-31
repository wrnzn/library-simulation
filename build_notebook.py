import json
import os

notebook = {
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

def add_md(text):
    notebook["cells"].append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.split("\n")]
    })

def add_code(text):
    notebook["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in text.split("\n")]
    })

add_md("# 🏛️ UM Tagum Mabini Library: Discrete-Event Simulation\nThis notebook models library congestion using **SimPy** and provides a custom high-fidelity SVG floorplan visualization, backed by rigorous Data Science EDA.")

code_cell_1 = """import numpy as np
import pandas as pd
import scipy.stats as stats
import simpy
import json
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display, HTML
import warnings
warnings.filterwarnings('ignore')

# 1. Data Synthesis: Non-Homogeneous Poisson Process (Arrivals)
def arrival_rate(t):
    # Base rate
    base = 1.0
    # Three Gaussian peaks: 9:00 AM (120), 12:00 PM (300), 3:00 PM (480)
    peak1 = 8.0 * np.exp(-((t - 120)**2) / (2 * 45**2))
    peak2 = 12.0 * np.exp(-((t - 300)**2) / (2 * 30**2))
    peak3 = 9.0 * np.exp(-((t - 480)**2) / (2 * 45**2))
    return (base + peak1 + peak2 + peak3) / 10.0

arrival_multiplier = 1.0
loiter_ratio = 0.65

arrivals = []
for t in range(720):
    rate = arrival_rate(t) * arrival_multiplier
    count = np.random.poisson(rate)
    for _ in range(count):
        arrivals.append(t)

n_samples = len(arrivals)
intent_p = [loiter_ratio, 1.0 - loiter_ratio]
intent = np.random.choice(["Loitering", "Study"], size=n_samples, p=intent_p)

# 2. Dwell Times (Mixture Model)
dwell_times = []
for i in intent:
    if i == "Loitering":
        dt = stats.lognorm.rvs(s=0.5, scale=25)
    else:
        dt = stats.lognorm.rvs(s=0.4, scale=110)
    dwell_times.append(max(5, int(dt)))

print(f"Synthesized {n_samples} arrivals.")"""
add_code(code_cell_1)

add_md("## Input Data EDA\nLet's visualize the synthetic distributions (Arrivals and Dwell Times) to ensure mathematical validity before running the simulation.")

code_eda_1 = """fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# 1. Arrival Distribution over the 12-hour day
sns.histplot(arrivals, bins=72, kde=True, ax=axes[0], color='blue')
axes[0].set_title("Simulated Arrivals over 12 Hours (NHPP)")
axes[0].set_xlabel("Time (Minutes from 7:00 AM)")
axes[0].set_ylabel("Student Arrivals")
axes[0].set_xticks([0, 120, 240, 360, 480, 600, 720])
axes[0].set_xticklabels(['7AM', '9AM', '11AM', '1PM', '3PM', '5PM', '7PM'])

# 2. Dwell Time Distribution (Bimodal)
study_dwells = [dwell_times[i] for i in range(len(intent)) if intent[i] == 'Study']
loiter_dwells = [dwell_times[i] for i in range(len(intent)) if intent[i] == 'Loitering']

sns.kdeplot(study_dwells, fill=True, ax=axes[1], color='orange', label='Study')
sns.kdeplot(loiter_dwells, fill=True, ax=axes[1], color='purple', label='Loitering')
axes[1].set_title("Dwell Time Distribution by Intent")
axes[1].set_xlabel("Minutes Spent in Library")
axes[1].set_ylabel("Density")
axes[1].legend()

plt.tight_layout()
plt.show()"""
add_code(code_eda_1)


add_md("## SimPy Engine\nThis cell handles the Discrete-Event Simulation using SimPy, tracking the exact state minute-by-minute.")

code_cell_2 = """class LibraryEnvironment:
    def __init__(self, env):
        self.env = env
        self.pcs = simpy.Resource(env, capacity=4)
        self.desks = simpy.Resource(env, capacity=56)
        self.tables = simpy.Resource(env, capacity=34)
        self.couches = simpy.Resource(env, capacity=12) # Base 7, but oversitted up to 12 due to squeezing
        self.balks = 0
        self.occupants = []

def student_process(env, student_id, intent, dwell, lib):
    arrival_time = env.now
    seat_found = None
    
    # Routing Logic
    if intent == "Study":
        # 1. Try PC
        with lib.pcs.request() as req:
            res = yield req | env.timeout(0)
            if req in res:
                seat_found = "pcs"
                lib.occupants.append({"id": student_id, "location": "pcs", "type": intent})
                yield env.timeout(dwell)
                lib.occupants = [o for o in lib.occupants if o["id"] != student_id]
                return
        # 2. Try Desk
        with lib.desks.request() as req:
            res = yield req | env.timeout(0)
            if req in res:
                seat_found = "desks"
                lib.occupants.append({"id": student_id, "location": "desks", "type": intent})
                yield env.timeout(dwell)
                lib.occupants = [o for o in lib.occupants if o["id"] != student_id]
                return
        # 3. Try Table
        with lib.tables.request() as req:
            res = yield req | env.timeout(3) # Wait 3 mins max
            if req in res:
                seat_found = "tables"
                lib.occupants.append({"id": student_id, "location": "tables", "type": intent})
                yield env.timeout(dwell)
                lib.occupants = [o for o in lib.occupants if o["id"] != student_id]
                return
        lib.balks += 1
    else:
        # Loiterer
        # 1. Try Couches
        with lib.couches.request() as req:
            res = yield req | env.timeout(0)
            if req in res:
                seat_found = "couches"
                lib.occupants.append({"id": student_id, "location": "couches", "type": intent})
                yield env.timeout(dwell)
                lib.occupants = [o for o in lib.occupants if o["id"] != student_id]
                return
        # 2. Try Table
        with lib.tables.request() as req:
            res = yield req | env.timeout(3)
            if req in res:
                seat_found = "tables"
                lib.occupants.append({"id": student_id, "location": "tables", "type": intent})
                yield env.timeout(dwell)
                lib.occupants = [o for o in lib.occupants if o["id"] != student_id]
                return
        lib.balks += 1

def run_simulation(arrivals, intent, dwell_times, max_time=720):
    env = simpy.Environment()
    lib = LibraryEnvironment(env)
    raw_logs = []
    
    def arrival_generator(env, lib):
        student_id = 0
        current_time = 0
        for arr in arrivals:
            if arr > current_time:
                yield env.timeout(arr - current_time)
                current_time = arr
            env.process(student_process(env, student_id, intent[student_id], dwell_times[student_id], lib))
            student_id += 1
            
    def monitor(env, lib):
        while True:
            current_occupants = [o.copy() for o in lib.occupants]
            raw_logs.append({
                "time": env.now,
                "balks": lib.balks,
                "occupants": current_occupants
            })
            yield env.timeout(1)
            
    env.process(arrival_generator(env, lib))
    env.process(monitor(env, lib))
    env.run(until=max_time)
    
    return raw_logs

# Run the simulation
raw_logs = run_simulation(arrivals, intent, dwell_times)
print("Simulation Complete. 720 ticks logged.")"""
add_code(code_cell_2)

add_md("## Real-Time Interactive Floorplan & EDA\nThis renders an interactive HTML/JS canvas mapped to the physical library layout, perfectly synchronized with **Chart.js** real-time EDA data pipelines.")

code_cell_3 = '''# Generate HTML Canvas with CSS Grid
html_content = """
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  .library-container {
    background-color: #fce8d5; /* matching sketch paper color */
    width: 600px;
    height: 400px;
    position: relative;
    border: 2px solid #000;
    margin: 20px 0;
    font-family: sans-serif;
    overflow: hidden;
  }
  
  /* Walls/Zones */
  .red-zone-left { position: absolute; left: 0; top: 0; width: 60px; height: 100%; background: #ff0000; border-right: 2px solid #000; }
  .red-zone-bottom { position: absolute; left: 150px; bottom: 0; width: 150px; height: 40px; background: #ff0000; border: 2px solid #000; border-bottom: none; }
  .entrance { position: absolute; left: 100px; bottom: 0; width: 40px; height: 15px; background: #00ffff; border: 2px solid #000; border-bottom: none; font-size: 10px; text-align: center; line-height: 12px; font-weight: bold; }
  .exit { position: absolute; left: 320px; bottom: 0; width: 40px; height: 15px; background: #00ffff; border: 2px solid #000; border-bottom: none; font-size: 10px; text-align: center; line-height: 12px; font-weight: bold; }

  /* Bookshelves */
  .bookshelf {
    position: absolute;
    width: 14px; height: 36px;
    background: #ffffff; border: 1px solid #000;
    display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 2px;
  }
  .book { width: 8px; height: 4px; border-radius: 1px; }

  /* Couches */
  .circle-couch {
    position: absolute;
    width: 40px; height: 40px; border-radius: 50%;
    background: #1e3f20; border: 2px solid #000;
    transition: opacity 0.2s;
    opacity: 0.3; /* Unoccupied state */
  }
  .circle-couch.occupied { opacity: 1.0; box-shadow: 0 0 10px rgba(0,255,0,0.8); }
  
  .l-couch {
    position: absolute;
    width: 30px; height: 30px;
    background: #3b2a22; border: 2px solid #000;
    border-top-right-radius: 10px;
    clip-path: polygon(0 0, 40% 0, 40% 60%, 100% 60%, 100% 100%, 0 100%);
    transition: opacity 0.2s;
    opacity: 0.3;
  }
  .l-couch.occupied { opacity: 1.0; box-shadow: 0 0 10px rgba(0,255,0,0.8); }

  /* PCs */
  .pc-station {
    position: absolute; width: 20px; height: 16px; background: #6b8c9e; border: 1px solid #000;
    transition: background 0.2s;
  }
  .pc-station.occupied { background: #00ff00; }
  
  /* White Tables */
  .white-table {
    position: absolute; width: 14px; height: 36px; background: #ffffff; border: 1px solid #000;
    transition: background 0.2s;
  }
  .white-table.occupied { background: #00ff00; }
  
  /* Orange Partition Desks (Blocks of 4) */
  .orange-desk {
    position: absolute; width: 28px; height: 16px; background: #fca311; border: 1px solid #000;
    border-radius: 6px; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 1px; padding: 1px;
  }
  .desk-seat { background: rgba(0,0,0,0.2); transition: background 0.2s; }
  .desk-seat.occupied { background: #00ff00; }
  
</style>

<div style="font-family: sans-serif; max-width: 1200px; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
  <h2>SimPy Real-Time Operations Dashboard</h2>
  <div style="display: flex; gap: 20px; align-items: center; margin-bottom: 20px;">
      <label><b>Time Scrubber</b></label>
      <input type="range" id="timeSlider" min="0" max="719" value="0" style="width: 400px;">
      <span id="timeLabel" style="font-size: 1.2rem; font-weight: bold; background: #eee; padding: 4px 8px; border-radius: 4px;">07:00</span>
  </div>
  
  <div style="display: flex; gap: 20px; margin-bottom: 20px; font-size: 0.9rem;">
      <div><b>Balks (Turned Away):</b> <span id="balkCount" style="color: red; font-weight: bold;">0</span></div>
      <div><b>PCs:</b> <span id="pcCount">0</span>/4</div>
      <div><b>Desks:</b> <span id="deskCount">0</span>/56</div>
      <div><b>Tables:</b> <span id="tableCount">0</span>/34</div>
      <div><b>Couches:</b> <span id="couchCount">0</span>/12 (Oversitted)</div>
  </div>

  <div style="display: flex; gap: 20px; align-items: stretch;">
      <div class="library-container" id="libContainer">
        <!-- Static Zones -->
        <div class="red-zone-left"></div>
        <div class="red-zone-bottom"></div>
        <div class="entrance">Ent</div>
        <div class="exit">Exit</div>
      </div>
      
      <div style="flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
          <div style="flex: 1; min-height: 200px;"><canvas id="utilChart"></canvas></div>
          <div style="flex: 1; min-height: 200px;"><canvas id="balkChart"></canvas></div>
      </div>
  </div>
</div>

<script>
  // Insert python JSON data directly
  const simLogs = __LOG_DATA__;
  
  const container = document.getElementById('libContainer');
  const elements = { pcs: [], couches: [], tables: [], deskSeats: [] };
  
  // A. 3 Circle Couches
  const cx = [100, 150, 125];
  const cy = [40, 40, 90];
  for(let i=0; i<3; i++) {
    let el = document.createElement('div');
    el.className = 'circle-couch';
    el.style.left = cx[i] + 'px';
    el.style.top = cy[i] + 'px';
    container.appendChild(el);
    elements.couches.push(el);
  }
  
  // B. 4 L-Couches
  for(let i=0; i<4; i++) {
    let el = document.createElement('div');
    el.className = 'l-couch';
    el.style.left = '100px';
    el.style.top = (170 + i*40) + 'px';
    container.appendChild(el);
    elements.couches.push(el);
  }
  
  // C. 4 PCs
  for(let i=0; i<4; i++) {
    let el = document.createElement('div');
    el.className = 'pc-station';
    el.style.left = '160px';
    el.style.top = (185 + i*30) + 'px';
    container.appendChild(el);
    elements.pcs.push(el);
  }
  
  // D. 34 White Tables (2 rows of 17)
  for(let row=0; row<2; row++) {
    for(let col=0; col<17; col++) {
      let el = document.createElement('div');
      el.className = 'white-table';
      el.style.left = (220 + col*20) + 'px';
      el.style.top = (30 + row*45) + 'px';
      container.appendChild(el);
      elements.tables.push(el);
    }
  }
  
  // E. 14 Orange Desks (Rows of 8 and 6) = 56 seats
  let deskRows = [8, 6];
  for(let row=0; row<2; row++) {
    for(let col=0; col<deskRows[row]; col++) {
      let el = document.createElement('div');
      el.className = 'orange-desk';
      el.style.left = (240 + col*35) + 'px';
      el.style.top = (160 + row*30) + 'px';
      for(let s=0; s<4; s++){
          let seat = document.createElement('div');
          seat.className = 'desk-seat';
          el.appendChild(seat);
          elements.deskSeats.push(seat);
      }
      container.appendChild(el);
    }
  }
  
  // F. 20 Bookshelves (2 rows of 10 at bottom right)
  const bookColors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff'];
  for(let row=0; row<2; row++) {
    for(let col=0; col<10; col++) {
      let el = document.createElement('div');
      el.className = 'bookshelf';
      el.style.left = (360 + col*20) + 'px';
      el.style.top = (260 + row*45) + 'px';
      for(let b=0; b<3; b++){
          let bk = document.createElement('div');
          bk.className = 'book';
          bk.style.backgroundColor = bookColors[Math.floor(Math.random()*bookColors.length)];
          el.appendChild(bk);
      }
      container.appendChild(el);
    }
  }

  // --- Real-Time EDA (Chart.js) Integration ---
  
  // Custom cursor plugin
  const cursorPlugin = {
    id: 'cursorPlugin',
    afterDraw: chart => {
      if (chart.config.options.cursorIndex !== undefined) {
        const ctx = chart.ctx;
        const x = chart.scales.x.getPixelForTick(chart.config.options.cursorIndex);
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x, chart.chartArea.top);
        ctx.lineTo(x, chart.chartArea.bottom);
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'rgba(255, 0, 0, 0.8)';
        ctx.stroke();
        ctx.restore();
      }
    }
  };
  Chart.register(cursorPlugin);

  const labels = simLogs.map(s => {
     let hr = Math.floor(s.time / 60) + 7;
     let mn = s.time % 60;
     return `${hr.toString().padStart(2,'0')}:${mn.toString().padStart(2,'0')}`;
  });
  
  const tsData = { pcs: [], desks: [], tables: [], couches: [] };
  const balkData = [];
  
  simLogs.forEach(state => {
      let c = { pcs:0, desks:0, tables:0, couches:0 };
      state.occupants.forEach(occ => {
         if(occ.location === 'pcs') c.pcs++;
         else if(occ.location === 'desks') c.desks++;
         else if(occ.location === 'tables') c.tables++;
         else if(occ.location === 'couches') c.couches++;
      });
      tsData.pcs.push(c.pcs);
      tsData.desks.push(c.desks);
      tsData.tables.push(c.tables);
      tsData.couches.push(c.couches);
      balkData.push(state.balks);
  });

  const ctxUtil = document.getElementById('utilChart').getContext('2d');
  const utilChart = new Chart(ctxUtil, {
      type: 'line',
      data: {
          labels: labels,
          datasets: [
             { label: 'PCs', data: tsData.pcs, borderColor: '#6b8c9e', pointRadius: 0, borderWidth: 2 },
             { label: 'Desks', data: tsData.desks, borderColor: '#fca311', pointRadius: 0, borderWidth: 2 },
             { label: 'Tables', data: tsData.tables, borderColor: '#00cc00', pointRadius: 0, borderWidth: 2 },
             { label: 'Couches', data: tsData.couches, borderColor: '#1e3f20', pointRadius: 0, borderWidth: 2 }
          ]
      },
      options: { 
          responsive: true, maintainAspectRatio: false,
          animation: false,
          plugins: { legend: { display: true }, title: { display: true, text: 'Capacity Utilization' } },
          scales: { x: { ticks: { maxTicksLimit: 12 } }, y: { beginAtZero: true, max: 60 } },
          cursorIndex: 0
      }
  });
  
  const ctxBalk = document.getElementById('balkChart').getContext('2d');
  const balkChart = new Chart(ctxBalk, {
      type: 'line',
      data: {
          labels: labels,
          datasets: [{ label: 'Cumulative Balks', data: balkData, borderColor: '#ff0000', backgroundColor: 'rgba(255,0,0,0.1)', fill: true, pointRadius: 0, borderWidth: 2 }]
      },
      options: { 
          responsive: true, maintainAspectRatio: false,
          animation: false,
          plugins: { legend: { display: false }, title: { display: true, text: 'Queue Drops (Balks)' } },
          scales: { x: { ticks: { maxTicksLimit: 12 } }, y: { beginAtZero: true } },
          cursorIndex: 0
      }
  });

  // --- UI Update Sync ---
  const slider = document.getElementById('timeSlider');
  const timeLabel = document.getElementById('timeLabel');
  
  function updateUI() {
    let t = parseInt(slider.value);
    if(t >= simLogs.length) t = simLogs.length - 1;
    let state = simLogs[t];
    
    // Update Time Label
    let hr = Math.floor(t / 60) + 7;
    let mn = t % 60;
    timeLabel.innerText = `${hr.toString().padStart(2,'0')}:${mn.toString().padStart(2,'0')}`;
    
    // Sync Charts
    utilChart.options.cursorIndex = t;
    balkChart.options.cursorIndex = t;
    utilChart.update();
    balkChart.update();
    
    // Update KPI
    document.getElementById('balkCount').innerText = state.balks;
    
    // Reset all visuals
    elements.pcs.forEach(e => e.classList.remove('occupied'));
    elements.couches.forEach(e => e.classList.remove('occupied'));
    elements.tables.forEach(e => e.classList.remove('occupied'));
    elements.deskSeats.forEach(e => e.classList.remove('occupied'));
    
    let counts = { pcs:0, desks:0, tables:0, couches:0 };
    
    // Apply Active Occupants
    state.occupants.forEach(occ => {
       if(occ.location === 'pcs') {
           if(counts.pcs < 4) elements.pcs[counts.pcs].classList.add('occupied');
           counts.pcs++;
       } else if(occ.location === 'couches') {
           if(counts.couches < 7) elements.couches[counts.couches].classList.add('occupied');
           counts.couches++;
       } else if(occ.location === 'tables') {
           if(counts.tables < 34) elements.tables[counts.tables].classList.add('occupied');
           counts.tables++;
       } else if(occ.location === 'desks') {
           if(counts.desks < 56) elements.deskSeats[counts.desks].classList.add('occupied');
           counts.desks++;
       }
    });
    
    document.getElementById('pcCount').innerText = counts.pcs;
    document.getElementById('deskCount').innerText = counts.desks;
    document.getElementById('tableCount').innerText = counts.tables;
    document.getElementById('couchCount').innerText = counts.couches;
  }
  
  slider.addEventListener('input', updateUI);
  updateUI(); // init
</script>
"""

# We inject the JSON logs into the HTML
json_str = json.dumps(raw_logs)
final_html = html_content.replace("__LOG_DATA__", json_str)

display(HTML(final_html))
'''
add_code(code_cell_3)

with open(r"D:\Codes 2\simpy\Library_Simulation.ipynb", "w", encoding='utf-8') as f:
    json.dump(notebook, f, indent=1)

print("Notebook generated successfully with Real-Time Chart.js EDA.")
