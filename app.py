import gradio as gr
import numpy as np
import scipy.stats as stats
import simpy
import random
import json
import warnings
warnings.filterwarnings('ignore')

# --- SIMULATION LOGIC ---
class LibraryEnvironment:
    def __init__(self, env):
        self.env = env
        self.pcs = simpy.Resource(env, capacity=4)
        self.desks = simpy.Resource(env, capacity=56)
        self.tables = simpy.Resource(env, capacity=272) # 34 tables * 8 seats (oversitted)
        self.couches = simpy.Resource(env, capacity=42) # 7 couches * 6 seats (oversitted) # Base 7, but oversitted up to 12 due to squeezing
        self.balks = 0
        self.occupants = []
        self.waiting_times = []
        self.cycle_times = []
        self.completed_customers = 0

def student_process(env, student_id, intent, dwell, lib):
    arrival_time = env.now
    
    def log_success(seat_loc):
        start_service = env.now
        lib.waiting_times.append(start_service - arrival_time)
        lib.occupants.append({"id": student_id, "location": seat_loc, "type": intent})
        
    def log_finish():
        end_time = env.now
        lib.cycle_times.append(end_time - arrival_time)
        lib.completed_customers += 1
        lib.occupants = [o for o in lib.occupants if o["id"] != student_id]

    if intent == "Study":
        with lib.pcs.request() as req:
            res = yield req | env.timeout(0)
            if req in res:
                log_success("pcs")
                yield env.timeout(dwell)
                log_finish()
                return
        with lib.desks.request() as req:
            res = yield req | env.timeout(0)
            if req in res:
                log_success("desks")
                yield env.timeout(dwell)
                log_finish()
                return
        with lib.tables.request() as req:
            res = yield req | env.timeout(3)
            if req in res:
                log_success("tables")
                yield env.timeout(dwell)
                log_finish()
                return
        lib.balks += 1
    else:
        with lib.couches.request() as req:
            res = yield req | env.timeout(0)
            if req in res:
                log_success("couches")
                yield env.timeout(dwell)
                log_finish()
                return
        with lib.tables.request() as req:
            res = yield req | env.timeout(3)
            if req in res:
                log_success("tables")
                yield env.timeout(dwell)
                log_finish()
                return
        lib.balks += 1

def run_simulation_logic(arrival_multiplier, loiter_ratio, seed=42):
    np.random.seed(int(seed))
    random.seed(int(seed))
    # Base rate
    def arrival_rate(t):
        # Increased mathematically to reflect a real crowded university library (approx 800-1200 daily arrivals)
        base = 5.0
        peak1 = 30.0 * np.exp(-((t - 120)**2) / (2 * 45**2))
        peak2 = 50.0 * np.exp(-((t - 300)**2) / (2 * 30**2))
        peak3 = 35.0 * np.exp(-((t - 480)**2) / (2 * 45**2))
        return (base + peak1 + peak2 + peak3) / 2.0

    arrivals = []
    for t in range(720):
        rate = arrival_rate(t) * arrival_multiplier
        count = np.random.poisson(rate)
        for _ in range(count):
            arrivals.append(t)

    n_samples = len(arrivals)
    intent_p = [loiter_ratio, 1.0 - loiter_ratio]
    if n_samples > 0:
        intent = np.random.choice(["Loitering", "Study"], size=n_samples, p=intent_p)
    else:
        intent = []

    dwell_times = []
    for i in intent:
        if i == "Loitering":
            dt = stats.lognorm.rvs(s=0.5, scale=25)
        else:
            dt = stats.lognorm.rvs(s=0.4, scale=110)
        dwell_times.append(max(5, int(dt)))

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
    env.run(until=720)
    
    avg_wait = sum(lib.waiting_times)/len(lib.waiting_times) if lib.waiting_times else 0
    avg_cycle = sum(lib.cycle_times)/len(lib.cycle_times) if lib.cycle_times else 0
    throughput = lib.completed_customers / 12.0 # students per hour over 12 hrs
    
    kpis = {
        "avg_wait": avg_wait,
        "avg_cycle": avg_cycle,
        "throughput": throughput
    }
    return raw_logs, kpis

# --- HTML TEMPLATE ---
html_template = """
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

<div style="font-family: sans-serif; width: 100%; max-width: 1400px; box-sizing: border-box; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 0 auto; overflow-x: hidden;">
  <h2>SimPy Real-Time Operations Dashboard</h2>
  <div style="display: flex; gap: 20px; margin-bottom: 15px; font-size: 1rem; flex-wrap: wrap; background: #e0f2fe; padding: 10px; border-radius: 8px; border: 1px solid #bae6fd; justify-content: space-between;">
      <div>⏱️ <b>Avg Wait Time:</b> <span style="color:#0369a1;">__AVG_WAIT__ mins</span></div>
      <div>🔄 <b>Avg Cycle Time:</b> <span style="color:#0369a1;">__AVG_CYCLE__ mins</span></div>
      <div>🚀 <b>Throughput Rate:</b> <span style="color:#0369a1;">__THROUGHPUT__ students/hour</span></div>
  </div>

  <div style="display: flex; gap: 20px; align-items: center; margin-bottom: 20px;">
      <label><b>Time Scrubber</b></label>
      <button id="playBtn" style="padding: 4px 12px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">▶ Play</button>
      <input type="range" id="timeSlider" min="0" max="719" value="0" style="width: 400px;">
      <span id="timeLabel" style="font-size: 1.2rem; font-weight: bold; background: #eee; padding: 4px 8px; border-radius: 4px;">07:00</span>
  </div>
  
  <div style="display: flex; gap: 15px; margin-bottom: 20px; font-size: 0.9rem; flex-wrap: wrap; align-items: center;">
      <div style="background:#e2e8f0; padding:4px 8px; border-radius:4px;"><b>Realtime Students:</b> <span id="totalStudents" style="color: blue; font-weight: bold; font-size: 1.1em;">0</span></div>
      <div style="background:#fef3c7; padding:4px 8px; border-radius:4px;"><b>Peak Capacity Today:</b> <span id="peakCapLabel" style="color: #d97706; font-weight: bold;">0</span></div>
      <div><b>Balks:</b> <span id="balkCount" style="color: red; font-weight: bold;">0</span></div>
      <div><b>PCs:</b> <span id="pcCount">0</span>/4</div>
      <div><b>Desks:</b> <span id="deskCount">0</span>/56</div>
      <div><b>Tables:</b> <span id="tableCount">0</span>/272 (Max 204 Base)</div>
      <div><b>Couches:</b> <span id="couchCount">0</span>/42 (Max 28 Base)</div>
  </div>

  <div style="display: flex; gap: 20px; align-items: stretch; flex-wrap: wrap;">
      <div class="library-container" id="libContainer">
        <!-- Static Zones -->
        <div class="red-zone-left"></div>
        <div class="red-zone-bottom"></div>
        <div class="entrance">Ent</div>
        <div class="exit">Exit</div>
      </div>
      
      <div style="flex: 1; display: flex; flex-direction: column; justify-content: space-between; min-width: 0; gap: 10px;">
          <div style="flex: 1; min-height: 140px; position: relative;"><canvas id="totalChart"></canvas></div>
          <div style="flex: 1; min-height: 140px; position: relative;"><canvas id="utilChart"></canvas></div>
          <div style="flex: 1; min-height: 140px; position: relative;"><canvas id="balkChart"></canvas></div>
      </div>
  </div>
</div>

<script>
  // A small wrapper to initialize only when the element exists (Gradio reloads)
  function initDashboard() {
      const simLogs = __LOG_DATA__;
      
      const container = document.getElementById('libContainer');
      if(!container) return; // Wait for DOM
      if(container.hasAttribute('data-init')) return; // already initialized
      container.setAttribute('data-init', 'true');
      
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
      // Try to register, but ignore if already registered
      try { Chart.register(cursorPlugin); } catch(e){}

      const labels = simLogs.map(s => {
         let hr = Math.floor(s.time / 60) + 7;
         let mn = s.time % 60;
         return `${hr.toString().padStart(2,'0')}:${mn.toString().padStart(2,'0')}`;
      });
      
      const tsData = { pcs: [], desks: [], tables: [], couches: [] };
      const balkData = [];
      const totalData = [];
      let maxStudents = 0;
      let peakTime = 0;
      
      simLogs.forEach(state => {
          let c = { pcs:0, desks:0, tables:0, couches:0 };
          let totalCount = state.occupants.length;
          
          if(totalCount > maxStudents) {
              maxStudents = totalCount;
              peakTime = state.time;
          }
          
          totalData.push(totalCount);
          
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
      
      let peakHr = Math.floor(peakTime / 60) + 7;
      let peakMn = peakTime % 60;
      document.getElementById('peakCapLabel').innerText = `${maxStudents} students @ ${peakHr.toString().padStart(2,'0')}:${peakMn.toString().padStart(2,'0')}`;


      // Destroy old charts if they exist (Gradio re-renders)
      if(window.totalChartInstance) window.totalChartInstance.destroy();
      if(window.utilChartInstance) window.utilChartInstance.destroy();
      if(window.balkChartInstance) window.balkChartInstance.destroy();

      const ctxTotal = document.getElementById('totalChart').getContext('2d');
      window.totalChartInstance = new Chart(ctxTotal, {
          type: 'line',
          data: {
              labels: labels,
              datasets: [{ label: 'Total Students', data: totalData, borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.2)', fill: true, pointRadius: 0, borderWidth: 2 }]
          },
          options: { 
              responsive: true, maintainAspectRatio: false,
              animation: false,
              plugins: { legend: { display: false }, title: { display: true, text: 'Total Students inside Library' } },
              scales: { x: { ticks: { maxTicksLimit: 12 } }, y: { beginAtZero: true } },
              cursorIndex: 0
          }
      });

      const ctxUtil = document.getElementById('utilChart').getContext('2d');
      window.utilChartInstance = new Chart(ctxUtil, {
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
              scales: { x: { ticks: { maxTicksLimit: 12 } }, y: { beginAtZero: true, max: 210 } },
              cursorIndex: 0
          }
      });
      
      const ctxBalk = document.getElementById('balkChart').getContext('2d');
      window.balkChartInstance = new Chart(ctxBalk, {
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
        
        let hr = Math.floor(t / 60) + 7;
        let mn = t % 60;
        timeLabel.innerText = `${hr.toString().padStart(2,'0')}:${mn.toString().padStart(2,'0')}`;
        
        window.totalChartInstance.options.cursorIndex = t;
        window.utilChartInstance.options.cursorIndex = t;
        window.balkChartInstance.options.cursorIndex = t;
        window.totalChartInstance.update();
        window.utilChartInstance.update();
        window.balkChartInstance.update();
        
        document.getElementById('totalStudents').innerText = state.occupants.length;
        document.getElementById('balkCount').innerText = state.balks;
        
        elements.pcs.forEach(e => e.classList.remove('occupied'));
        elements.couches.forEach(e => {
            e.classList.remove('occupied');
            e.style.boxShadow = '';
            e.style.backgroundColor = ''; // Reset custom colors
        });
        elements.tables.forEach(e => {
            e.classList.remove('occupied');
            e.style.backgroundColor = '';
        });
        elements.deskSeats.forEach(e => e.classList.remove('occupied'));
        
        let counts = { pcs:0, desks:0, tables:0, couches:0 };
        
        state.occupants.forEach(occ => {
           if(occ.location === 'pcs') {
               if(counts.pcs < 4) elements.pcs[counts.pcs].classList.add('occupied');
               counts.pcs++;
           } else if(occ.location === 'couches') {
               let couchIdx = counts.couches % 7; // Distribute evenly across 7 couches
               elements.couches[couchIdx].classList.add('occupied');
               let peopleAtThisCouch = Math.floor(counts.couches / 7) + 1;
               if(peopleAtThisCouch > 4) { // Oversitting (5 or 6)
                   elements.couches[couchIdx].style.boxShadow = '0 0 10px rgba(255,165,0,0.9)';
                   elements.couches[couchIdx].style.backgroundColor = '#ff8c00'; // Orange
               }
               counts.couches++;
           } else if(occ.location === 'tables') {
               let tableIdx = counts.tables % 34; // Distribute evenly across 34 tables
               elements.tables[tableIdx].classList.add('occupied');
               let peopleAtThisTable = Math.floor(counts.tables / 34) + 1;
               if(peopleAtThisTable > 6) { // Oversitting (7 or 8)
                   elements.tables[tableIdx].style.backgroundColor = '#ffa500'; // Orange
               }
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
      
      // Autoplay Logic
      let playInterval = null;
      const playBtn = document.getElementById('playBtn');
      playBtn.addEventListener('click', () => {
          if (playInterval) {
              clearInterval(playInterval);
              playInterval = null;
              playBtn.innerText = '▶ Play';
              playBtn.style.background = '#3b82f6';
          } else {
              playBtn.innerText = '⏸ Pause';
              playBtn.style.background = '#ef4444';
              playInterval = setInterval(() => {
                  let currentVal = parseInt(slider.value);
                  if (currentVal >= parseInt(slider.max)) {
                      clearInterval(playInterval);
                      playInterval = null;
                      playBtn.innerText = '▶ Play';
                      playBtn.style.background = '#3b82f6';
                  } else {
                      slider.value = currentVal + 2; // Move 2 minutes per tick to make it brisk
                      updateUI();
                  }
              }, 50); // 50ms = 20 ticks per second (40 sim minutes per second)
          }
      });
      
      updateUI(); // init
  }
  
  // Call init soon to allow DOM to render
  setTimeout(initDashboard, 100);
</script>
"""

def generate_dashboard(arrival_multiplier, loiter_ratio, seed=42):
    raw_logs, kpis = run_simulation_logic(arrival_multiplier, loiter_ratio, seed)
    json_str = json.dumps(raw_logs)
    raw_html = html_template.replace("__LOG_DATA__", json_str)
    raw_html = raw_html.replace("__AVG_WAIT__", f"{kpis['avg_wait']:.2f}")
    raw_html = raw_html.replace("__AVG_CYCLE__", f"{kpis['avg_cycle']:.2f}")
    raw_html = raw_html.replace("__THROUGHPUT__", f"{kpis['throughput']:.2f}")
    
    import html
    safe_html = html.escape(raw_html)
    return f'<iframe srcdoc="{safe_html}" width="100%" height="850px" style="border:none; overflow:hidden; border-radius: 8px; background:white;"></iframe>'

css = """
body, .gradio-container {
    background-color: #0f172a !important; 
    color: #f8fafc !important;
}
.glass-card {
    background: rgba(30, 41, 59, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    padding: 24px !important;
}
"""

with gr.Blocks(css=css, theme=gr.themes.Base()) as demo:
    gr.HTML("<h1 style='text-align: center; color: #f8fafc; margin-bottom: 5px;'>🏛️ UM Tagum Mabini: Library Spatial Simulator</h1>")
    gr.HTML("<p style='text-align: center; color: #94a3b8; margin-bottom: 25px;'>Hugging Face Spaces Native Integration</p>")
    
    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["glass-card"]):
                gr.Markdown("### 🎛️ Simulation Parameters")
                arrival_slider = gr.Slider(0.5, 2.0, value=1.0, step=0.1, label="Arrival Volume (1.0 = Normal Day)")
                intent_slider = gr.Slider(0.0, 1.0, value=0.65, step=0.05, label="% Students Loitering/Socializing (Not Studying)")
                seed_slider = gr.Slider(0, 1000, value=42, step=1, label="Random Seed (Reproducibility)")
                simulate_btn = gr.Button("⚡ Run Simulation & Update Dashboard", variant="primary")
        
    dashboard_html = gr.HTML()

    # Initialization and event triggers
    demo.load(fn=generate_dashboard, inputs=[arrival_slider, intent_slider, seed_slider], outputs=[dashboard_html])
    simulate_btn.click(fn=generate_dashboard, inputs=[arrival_slider, intent_slider, seed_slider], outputs=[dashboard_html])

if __name__ == "__main__":
    demo.launch(server_port=7860, share=True)
