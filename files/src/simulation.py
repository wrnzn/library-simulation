import simpy
import pandas as pd
import numpy as np

class LibraryEnvironment:
    def __init__(self, env):
        self.env = env
        # Core Spatial Resources
        self.desks = simpy.Resource(env, capacity=56)
        self.tables = simpy.Resource(env, capacity=34)
        self.couches = simpy.Resource(env, capacity=7)
        
        # Logging structures
        self.logs = []
        self.balk_count = 0
        self.total_students = 0
        
        # Spatial grid state (abstract representation for UI)
        # Will track which entities are occupying which resource indices
        self.active_occupants = []

    def log_state(self):
        """Callback hook that records the system state at every tick (minute)."""
        while True:
            self.logs.append({
                'time_min': self.env.now,
                'desks_used': self.desks.count,
                'desks_queue': len(self.desks.queue),
                'tables_used': self.tables.count,
                'tables_queue': len(self.tables.queue),
                'couches_used': self.couches.count,
                'couches_queue': len(self.couches.queue),
                'cumulative_balks': self.balk_count,
                'total_arrivals': self.total_students,
                'occupants': list(self.active_occupants) # snapshot of current occupants
            })
            yield self.env.timeout(1)

    def student_process(self, name, intent, dwell_time, patience=5):
        """Active entity logic with conditional routing and balking."""
        self.total_students += 1
        
        # Routing logic based on latent intent
        primary_resource = self.desks if intent == "Study" else self.couches
        primary_name = "desks" if intent == "Study" else "couches"
        fallback_resource = self.tables
        fallback_name = "tables"
        
        # Phase 1: Try Primary Resource
        with primary_resource.request() as req:
            # Wait up to 'patience' minutes for a seat
            result = yield req | self.env.timeout(patience)
            
            if req in result:
                # Successfully acquired primary seat
                occupant_data = {'name': name, 'intent': intent, 'location': primary_name}
                self.active_occupants.append(occupant_data)
                
                yield self.env.timeout(dwell_time) # Dwell
                
                self.active_occupants.remove(occupant_data)
                return
                
        # Phase 2: If primary failed (balked due to patience timeout), try Fallback
        with fallback_resource.request() as req:
            result = yield req | self.env.timeout(patience)
            
            if req in result:
                # Successfully acquired fallback seat
                occupant_data = {'name': name, 'intent': intent, 'location': fallback_name}
                self.active_occupants.append(occupant_data)
                
                yield self.env.timeout(dwell_time) # Dwell
                
                self.active_occupants.remove(occupant_data)
                return
            else:
                # Phase 3: Balk entirely from library
                self.balk_count += 1

def run_simulation(arrivals, dwell_intents, dwell_times, max_time=720):
    """Orchestrates the SimPy environment execution."""
    env = simpy.Environment()
    library = LibraryEnvironment(env)
    
    # Start the background logger process
    env.process(library.log_state())
    
    def arrival_generator(env, library, arrivals, dwell_intents, dwell_times):
        student_id = 0
        for arrival_time, intent, dwell_time in zip(arrivals, dwell_intents, dwell_times):
            # Advance simulation clock to the next arrival time
            if arrival_time > env.now:
                yield env.timeout(arrival_time - env.now)
                
            env.process(library.student_process(
                name=f"S_{student_id}", 
                intent=intent, 
                dwell_time=dwell_time,
                patience=3 # Students will only wait 3 minutes before routing/balking
            ))
            student_id += 1
            
    env.process(arrival_generator(env, library, arrivals, dwell_intents, dwell_times))
    
    # Execute simulation
    env.run(until=max_time)
    
    # Extract logs to DataFrame (drop the complex occupants list for the CSV, keep raw data)
    logs_df = pd.DataFrame(library.logs)
    
    return logs_df, library.logs

if __name__ == "__main__":
    # Test script: Run simulation for Day 1
    print("Loading proxy datasets...")
    df_arr = pd.read_csv("data/arrivals_data.csv")
    df_dwell = pd.read_csv("data/dwell_times.csv")
    
    # Filter for first operational day (0 to 719 minutes)
    day1_arr = df_arr[df_arr['arrival_time_min'] < 720]
    n_day1 = len(day1_arr)
    day1_dwell = df_dwell.iloc[:n_day1]
    
    print(f"Executing DES for Day 1 ({n_day1} arrivals)...")
    logs_df, raw_logs = run_simulation(
        day1_arr['arrival_time_min'].values, 
        day1_dwell['intent'].values, 
        day1_dwell['dwell_time_min'].values
    )
    
    # Save the standard logs (drop occupants list for CSV compatibility)
    logs_df.drop(columns=['occupants']).to_csv("data/simulation_logs.csv", index=False)
    
    print("Simulation complete! Logs saved to data/simulation_logs.csv")
    
    # Print high-level metrics
    final_state = logs_df.iloc[-1]
    print("\n--- Final State (End of Day) ---")
    print(f"Total Arrivals Processed: {final_state['total_arrivals']}")
    print(f"Total Balks (Lost students): {final_state['cumulative_balks']}")
    print(f"Max Desk Queue Observed: {logs_df['desks_queue'].max()}")
    print(f"Max Table Queue Observed: {logs_df['tables_queue'].max()}")
