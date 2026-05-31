import gradio as gr
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import scipy.stats as stats
import warnings
warnings.filterwarnings('ignore')

from src.simulation import run_simulation
from src.data_synthesis import arrival_rate

def generate_and_simulate(arrival_multiplier, loiter_ratio):
    # 1. Arrivals
    arrivals = []
    for t in range(720):
        rate = arrival_rate(t) * arrival_multiplier
        count = np.random.poisson(rate)
        for _ in range(count):
            arrivals.append(t)
    
    n_samples = len(arrivals)
    intent_p = [loiter_ratio, 1.0 - loiter_ratio]
    intent = np.random.choice(["Loiter/Eat", "Study"], size=n_samples, p=intent_p)
    
    # 2. Dwell times
    dwell_times = []
    for i in intent:
        if i == "Loiter/Eat":
            dt = stats.lognorm.rvs(s=0.5, scale=25)
        else:
            dt = stats.lognorm.rvs(s=0.4, scale=110)
        dwell_times.append(max(5, dt))
        
    # 3. Run simulation
    logs_df, raw_logs = run_simulation(arrivals, intent, dwell_times, max_time=720)
    return logs_df, raw_logs

css = """
body, .gradio-container {
    background-color: #0f172a !important; /* slate-900 */
    color: #f8fafc !important;
}
.glass-card {
    background: rgba(30, 41, 59, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    padding: 24px !important;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1) !important;
}
.gr-button-primary {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    border: none !important;
    box-shadow: 0 4px 14px 0 rgba(59, 130, 246, 0.39) !important;
    transition: all 0.2s ease !important;
}
.gr-button-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px 0 rgba(59, 130, 246, 0.5) !important;
}
"""

def create_spatial_plot(raw_logs, t_minute):
    grid = np.zeros((22, 110))
    grid[0:2, :] = 4
    grid[2:6, 0:3] = 4
    
    if t_minute >= len(raw_logs):
        t_minute = len(raw_logs) - 1
    state = raw_logs[int(t_minute)]
    occupants = state.get('occupants', [])
    
    desk_idx, table_idx, couch_idx = 0, 0, 0
    
    for occ in occupants:
        loc = occ['location']
        if loc == 'desks' and desk_idx < 56:
            row = 3 + (desk_idx // 8)
            col = 90 + (desk_idx % 8)
            if row < 22 and col < 110: grid[row, col] = 1
            desk_idx += 1
        elif loc == 'tables' and table_idx < 34:
            row = 8 + (table_idx // 10)
            col = 45 + (table_idx % 10)
            if row < 22 and col < 110: grid[row, col] = 2
            table_idx += 1
        elif loc == 'couches' and couch_idx < 7:
            row = 15 + (couch_idx // 4) * 2
            col = 15 + (couch_idx % 4) * 4
            if row < 22 and col < 110: grid[row, col] = 3
            couch_idx += 1
            
    colorscale = [
        [0.0, '#1e293b'],   # 0: Empty (Slate 800)
        [0.25, '#f97316'],  # 1: Desks (Orange)
        [0.50, '#38bdf8'],  # 2: Tables (Sky Blue)
        [0.75, '#c084fc'],  # 3: Couches (Purple)
        [1.0, '#475569']    # 4: Staff Zone (Slate 600)
    ]
    
    fig = go.Figure(data=go.Heatmap(z=grid, colorscale=colorscale, showscale=False, xgap=1, ygap=1))
    
    # Add Text Annotations for zones to provide context
    fig.add_annotation(x=93, y=10, text="STUDY DESKS", showarrow=False, font=dict(color="rgba(255,255,255,0.7)", size=12))
    fig.add_annotation(x=50, y=13, text="WHITE TABLES", showarrow=False, font=dict(color="rgba(255,255,255,0.7)", size=12))
    fig.add_annotation(x=20, y=19, text="LOUNGE COUCHES", showarrow=False, font=dict(color="rgba(255,255,255,0.7)", size=12))
    fig.add_annotation(x=55, y=0.5, text="RESTRICTED STAFF AREA", showarrow=False, font=dict(color="rgba(255,255,255,0.7)", size=10))

    # Add invisible scatter traces for the interactive legend
    legend_items = [
        ("Study Desks (Orange)", '#f97316'),
        ("White Tables (Blue)", '#38bdf8'),
        ("Couches (Purple)", '#c084fc'),
        ("Empty Space (Dark)", '#1e293b'),
        ("Staff Area (Gray)", '#475569')
    ]
    for name, color in legend_items:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(size=12, color=color, symbol='square'),
            name=name
        ))
    
    time_str = f"{7 + t_minute//60:02d}:{t_minute%60:02d}"
    
    fig.update_layout(
        title=dict(text=f"Live Library Floorplan | Time: {time_str}", font=dict(size=18, color='#f8fafc')),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, autorange='reversed', scaleanchor="x", scaleratio=1),
        margin=dict(l=10, r=10, t=50, b=10),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(color='#e2e8f0'))
    )
    return fig

def create_capacity_plot(raw_logs, t_minute):
    if t_minute >= len(raw_logs):
        t_minute = len(raw_logs) - 1
    state = raw_logs[int(t_minute)]
    
    used_desks = state['desks_used']
    used_tables = state['tables_used']
    used_couches = state['couches_used']
    
    categories = ['Study Desks (Max: 56)', 'White Tables (Max: 34)', 'Couches (Max: 7)']
    used_vals = [used_desks, used_tables, used_couches]
    max_vals = [56, 34, 7]
    free_vals = [m - u for m, u in zip(max_vals, used_vals)]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=categories, x=used_vals, name='Occupied', orientation='h',
        marker=dict(color=['#f97316', '#38bdf8', '#c084fc'])
    ))
    fig.add_trace(go.Bar(
        y=categories, x=free_vals, name='Available', orientation='h',
        marker=dict(color='#1e293b', line=dict(color='rgba(255,255,255,0.1)', width=1))
    ))
    
    fig.update_layout(
        barmode='stack',
        title=dict(text="Real-Time Capacity Utilization", font=dict(size=14, color='#f8fafc')),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        xaxis=dict(showgrid=True, gridcolor='#334155', title="Seats", range=[0, 60]),
        yaxis=dict(showgrid=False),
        margin=dict(l=10, r=10, t=40, b=10),
        height=200,
        showlegend=False
    )
    # Add text labels on bars
    for i in range(3):
        fig.add_annotation(
            x=used_vals[i] / 2 if used_vals[i] > 0 else 0,
            y=categories[i],
            text=f"{used_vals[i]}/{max_vals[i]}",
            showarrow=False,
            font=dict(color="white", size=12)
        )
    return fig

def update_ui(arrival_multiplier, loiter_ratio):
    logs_df, raw_logs = generate_and_simulate(arrival_multiplier, loiter_ratio)
    
    final = logs_df.iloc[-1]
    total_arr = int(final['total_arrivals'])
    total_balk = int(final['cumulative_balks'])
    max_desk_q = int(logs_df['desks_queue'].max())
    max_table_q = int(logs_df['tables_queue'].max())
    
    fig_spatial = create_spatial_plot(raw_logs, t_minute=300)
    fig_capacity = create_capacity_plot(raw_logs, t_minute=300)
    
    return total_arr, total_balk, max_desk_q, max_table_q, fig_spatial, fig_capacity, raw_logs, gr.update(value=300)

def update_time_slider(t_minute, raw_logs):
    if not raw_logs:
        return None, None
    return create_spatial_plot(raw_logs, t_minute), create_capacity_plot(raw_logs, t_minute)

with gr.Blocks(css=css, theme=gr.themes.Base()) as demo:
    raw_logs_state = gr.State([])
    
    gr.HTML("<h1 style='text-align: center; color: #f8fafc; margin-bottom: 5px;'>🏛️ UM Tagum Mabini: Library Spatial Simulator</h1>")
    gr.HTML("<p style='text-align: center; color: #94a3b8; margin-bottom: 25px;'>Analyze student congestion, spatial capacity, and seating bottlenecks dynamically.</p>")
        
    with gr.Row():
        # LEFT COLUMN: Controls & KPIs
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["glass-card"]):
                gr.Markdown("### 🎛️ Simulation Parameters")
                gr.Markdown("<small style='color:#94a3b8'>Adjust these sliders to simulate different stress tests. <b>Arrival Multiplier</b> scales the total number of students entering the library today. <b>Intent Ratio</b> determines what percentage of them just want to loiter/eat vs academically study.</small>")
                arrival_slider = gr.Slider(0.5, 2.0, value=1.0, step=0.1, label="Student Arrival Volume (1.0 = Normal Day)")
                intent_slider = gr.Slider(0.0, 1.0, value=0.65, step=0.05, label="Percentage of Students Loitering/Eating (vs Studying)")
                simulate_btn = gr.Button("⚡ Re-Run Simulation", variant="primary")
            
            with gr.Group(elem_classes=["glass-card"]):
                gr.Markdown("### 📊 End-of-Day Summary")
                with gr.Row():
                    kpi_arr = gr.Number(label="Total Students Arrived", interactive=False)
                    kpi_balk = gr.Number(label="Students Turned Away (Full)", interactive=False)
                with gr.Row():
                    kpi_dq = gr.Number(label="Longest Line for a Desk", interactive=False)
                    kpi_tq = gr.Number(label="Longest Line for a Table", interactive=False)

        # RIGHT COLUMN: Plotly Mapping & Capacity
        with gr.Column(scale=3):
            with gr.Group(elem_classes=["glass-card"]):
                gr.Markdown("### 🗺️ Live Floorplan Tracker")
                time_slider = gr.Slider(0, 719, value=300, step=1, label="Scrub Time (Minute of Day: 0 = 7AM, 719 = 7PM)")
                spatial_plot = gr.Plot()
                capacity_plot = gr.Plot()

    # Event Wiring
    simulate_btn.click(
        fn=update_ui,
        inputs=[arrival_slider, intent_slider],
        outputs=[kpi_arr, kpi_balk, kpi_dq, kpi_tq, spatial_plot, capacity_plot, raw_logs_state, time_slider]
    )
    
    time_slider.change(
        fn=update_time_slider,
        inputs=[time_slider, raw_logs_state],
        outputs=[spatial_plot, capacity_plot]
    )
    
    # Auto-initialize
    demo.load(
        fn=update_ui,
        inputs=[arrival_slider, intent_slider],
        outputs=[kpi_arr, kpi_balk, kpi_dq, kpi_tq, spatial_plot, capacity_plot, raw_logs_state, time_slider]
    )

if __name__ == "__main__":
    demo.launch(server_port=7860)
