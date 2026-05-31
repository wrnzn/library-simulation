# Development of a Real-Time Operations Research and Spatial Simulation System for University Library Capacity Management using SimPy and Python

**A PROJECT PROPOSAL FOR CS 20/L**  
**CS PROFESSIONAL TRACK 5**  

**SUBMITTED TO:**  
MS. KATE STEFUNNY T. BRUNO  

**SUBMITTED BY:**  
[Your Name / Group Members]  

**JUNE 2026**  

---

## BACKGROUND OF THE STUDY
University libraries serve as the primary hub for academic study, research, and student collaboration. However, as student populations grow, libraries frequently face severe spatial constraints, leading to overcrowding, long queues, and high balking rates (students leaving due to lack of seats). Furthermore, the physical layout of the library and the varying intentions of the students—such as focused study versus casual loitering or socializing—drastically impact the effective capacity of the facility. 

In many Philippine educational institutions, managing library capacity relies on manual headcounts or static scheduling, which fails to account for dynamic, real-time arrival fluctuations and stochastic dwell times. When seats like PCs, individual desks, and couches are occupied by students simply loitering or waiting for their next class, the actual capacity available for academic study is severely diminished. 

Operations Research and Discrete-Event Simulation (DES) provide powerful computational tools to model these complex queueing systems. By mathematically modeling the arrival rates, seating preferences, and dwell times of students, administrators can predict bottlenecks before they occur. This study proposes the development of a Real-Time Spatial Simulator using Python's SimPy framework to model the exact physical layout of the UM Tagum Mabini library. The system will simulate stochastic student behavior, track capacity utilization across different seating zones (PCs, tables, desks, and couches), and provide real-time Exploratory Data Analysis (EDA) to assist library administrators in optimizing spatial allocation.

## OBJECTIVE OF THE STUDY
This study aims to develop a Discrete-Event Simulation (DES) and spatial operations dashboard to model, analyze, and predict student flow and capacity bottlenecks in a university library. 

Specifically, this study aims to:
1. Develop a mathematical model representing stochastic student arrivals (using Poisson distributions) and varying dwell times (using Log-Normal distributions) based on student intent (Study vs. Loitering).
2. Map the physical constraints of the UM Tagum Mabini library—including 4 PCs, 56 desks, 34 tables (capacity of 204-272 students), and 7 physical couches (capacity of 28 students with oversitting limits)—into a computational resource pool using SimPy.
3. Simulate complex routing logic where students sequentially attempt to find optimal seating and record "balks" when the library is at maximum effective capacity.
4. Conduct Exploratory Data Analysis (EDA) on the simulated logs to identify peak utilization hours, queue drop rates, and intent distributions.
5. Develop a web-based Real-Time Operations Dashboard using Chart.js to visualize the spatial capacity, total student population, and peak thresholds interactively.
6. Provide actionable data-driven recommendations to library administrators for layout restructuring or policy adjustments based on the simulation results.

## METHODOLOGY
This section presents the methods employed in conducting the study. It covers the research design, target business entity, research instruments, procedure, and data analysis techniques.

* **Research Design:** This study employs a quantitative computational modeling and systems development research design. The simulation evaluates capacity constraints using Operations Research queueing algorithms.
* **Target Business Entity:** The UM Tagum Mabini Library, serving as the physical environment upon which the spatial constraints, seat counts, and zone mapping (PCs, Couches, Desks, Tables) are based.
* **Research Instruments:** The tools used to develop and analyze the simulation include:
  * **Python:** For backend logic.
  * **SimPy:** For Discrete-Event Simulation and resource queueing logic.
  * **NumPy:** For statistical distributions (Poisson, Log-Normal).
  * **Hugging Face / Gradio (or local browser):** For deploying the interactive web-based dashboard.
  * **Chart.js:** For real-time spatial rendering and EDA charting.
* **Procedure:** 
  1. **Spatial Mapping:** Audit the physical library to determine exact resource capacities (4 PCs, 56 desks, 34 tables (capacity 204 base, 272 max), 7 couches (capacity 28 base, 42 max)).
  2. **Mathematical Modeling:** Define the probability density functions for arrival rates (multi-peak Poisson distribution representing morning, noon, and afternoon rushes) and dwell times (Log-Normal).
  3. **Simulation Engineering:** Write the SimPy logic to handle student routing and queueing over a 12-hour operational day (7:00 AM to 7:00 PM).
  4. **Data Aggregation:** Collect frame-by-frame state data into a JSON log structure.
  5. **Dashboard Integration:** Inject the simulation engine into a web application with real-time Chart.js synchronization for interactive EDA.

## ETHICAL, LEGAL, AND DATA PRIVACY CONSIDERATIONS
As this study involves simulating student behavior and facility utilization, no Personally Identifiable Information (PII) is collected, stored, or processed. The system relies entirely on synthetic stochastic generation driven by mathematical distributions rather than empirical tracking of real individuals. Therefore, it remains fully compliant with the Philippine Data Privacy Act of 2012 (Republic Act No. 10173).

## RESULT AND DISCUSSION
Three distinctive scenarios were evaluated using the simulation framework to identify bottlenecks and test potential library policies. 

### Scenario 1: Baseline (Normal Day)
**Parameters:** Arrival Volume = 1.0 | Loitering Ratio = 65% | Seed = 42
* **Average Wait Time:** 0.82 minutes
* **Average Cycle Time:** 47.27 minutes
* **Peak Simultaneous Capacity:** 374 students
* **Total Balks (Queue Drops):** 2,624 students
* **Analysis:** On a standard operational day, the library handles throughput effectively (376 students/hour), but high loitering (65%) forces students to rapidly cycle through available tables and couches. The high balk rate demonstrates that even on a normal day, the physical footprint of the library cannot support all incoming foot traffic during peak rushes.

### Scenario 2: Midterm/Finals Week (High Volume, Low Loitering)
**Parameters:** Arrival Volume = 1.5 | Loitering Ratio = 20% | Seed = 42
* **Average Wait Time:** 1.03 minutes
* **Average Cycle Time:** 70.59 minutes
* **Peak Simultaneous Capacity:** 374 students
* **Total Balks (Queue Drops):** 7,213 students
* **Analysis:** During exam weeks, arrival volumes spike by 50%, and students primarily come to study (80% study intent). Because studying requires significantly longer dwell times (~110 minutes on average) compared to loitering (~25 minutes), seats are locked up for extended periods. This creates a severe gridlock, skyrocketing the balks to over 7,200 students.

### Scenario 3: Policy Enforcement (Normal Volume, Low Loitering)
**Parameters:** Arrival Volume = 1.0 | Loitering Ratio = 10% | Seed = 42
* **Average Wait Time:** 0.84 minutes
* **Average Cycle Time:** 90.25 minutes
* **Peak Simultaneous Capacity:** 374 students
* **Total Balks (Queue Drops):** 4,554 students
* **Analysis:** A surprising and counter-intuitive finding emerges when evaluating a strict "No Loitering" policy. If staff heavily enforce studying (dropping loiterers to 10%), the average cycle time nearly doubles to 90.25 minutes. Because every occupant is now staying for long-duration study sessions, table turnover grinds to a halt. As a result, the balk rate *increases* to 4,554 (up from 2,624 in the baseline). This Operations Research insight proves that simply eliminating loiterers without physically expanding the library space actively worsens queue drops because studying is an intensive, long-duration activity.

## FINAL SYSTEM OUTPUTS
1. A fully functional Discrete-Event Simulation engine written in Python (SimPy).
2. A reproducible interactive Jupyter Notebook (`Library_Simulation_v2.ipynb`) combining backend logic and dynamic visualization.
3. Interactive EDA charts tracking Capacity Utilization, Cumulative Balks, and Total Student Population via Chart.js.
4. A spatial 2D map dynamically rendering occupied vs. unoccupied seats (highlighting oversitting thresholds in orange) in real-time.

## SCOPE AND LIMITATIONS
This study focuses strictly on the mathematical simulation of spatial capacity and queueing logic within the UM Tagum Mabini Library. It does not utilize real-time CCTV computer vision or IoT sensors to count actual students; all data is synthetically generated via stochastic models. The accuracy of the simulation is highly dependent on the initial parameters (Arrival Multiplier and Loitering Ratio) set by the user. Complex human behaviors, such as groups moving chairs between tables or students leaving bags to reserve seats, are excluded from the current routing logic to maintain computational efficiency.

## REFERENCES
*(Note: These references have been strictly verified for integrity via the OpenAlex academic database and represent actual recent publications on Discrete Event Simulation, Capacity Planning, and SimPy (2020-2024).)*

[1] Magdalena Jurczyk-Bunkowska, "Tactical manufacturing capacity planning based on discrete event simulation and throughput accounting: A case study of medium sized production enterprise," *Advances in Production Engineering & Management*, 2021. doi: https://doi.org/10.14743/apem2021.3.404
[2] Thomas Bartz–Beielstein, Frederik Rehbach, Olaf Mersmann, Eva Bartz, "Hospital Capacity Planning Using Discrete Event Simulation Under Special Consideration of the COVID-19 Pandemic," *arXiv (Cornell University)*, 2020. doi: https://doi.org/10.48550/arxiv.2012.07188
[3] Quyuan Luo, Shihong Hu, Changle Li, Guanghui Li, Weisong Shi, "Resource Scheduling in Edge Computing: A Survey," *IEEE Communications Surveys & Tutorials*, 2021. doi: https://doi.org/10.1109/comst.2021.3106401
[4] Gary E. Weissman, Andrew Crane‐Droesch, Corey Chivers, ThaiBinh Luong, Asaf Hanish, Michael Z. Levy, Jason Lubken, Michael Becker, Michael Draugelis, George L. Anesi, Patrick J. Brennan, Jason D. Christie, C. William Hanson, Mark E. Mikkelsen, Scott D. Halpern, "Locally Informed Simulation to Predict Hospital Capacity Needs During the COVID-19 Pandemic," *Annals of Internal Medicine*, 2020. doi: https://doi.org/10.7326/m20-1260
[5] Dániel Hörcher, Alejandro Tirachini, "A review of public transport economics," *Economics of Transportation*, 2021. doi: https://doi.org/10.1016/j.ecotra.2021.100196
[6] Rob Shone, K. D. Glazebrook, Konstantinos G. Zografos, "Applications of stochastic modeling in air traffic management: Methods, challenges and opportunities for solving air traffic problems under uncertainty," *European Journal of Operational Research*, 2020. doi: https://doi.org/10.1016/j.ejor.2020.10.039
[7] Yu Bai, Huijun Zhao, X. L. Zhang, Zheng Chang, Riku Jäntti, Kun Yang, "Toward Autonomous Multi-UAV Wireless Network: A Survey of Reinforcement Learning-Based Approaches," *IEEE Communications Surveys & Tutorials*, 2023. doi: https://doi.org/10.1109/comst.2023.3323344
[8] Dmitry Zinoviev, "Discrete Event Simulation: It's Easy with SimPy!," *arXiv (Cornell University)*, 2024. doi: https://doi.org/10.48550/arxiv.2405.01562
[9] Antonios Saravanos, Matthew X. Curinga, "Simulating the Software Development Lifecycle: The Waterfall Model," *Applied System Innovation*, 2023. doi: https://doi.org/10.3390/asi6060108
[10] Cemre Cubukcuoglu, Pirouz Nourian, I.S. Sariyildiz, M. Fatih Tasgetiren, "A discrete event simulation procedure for validating programs of requirements: The case of hospital space planning," *SoftwareX*, 2020. doi: https://doi.org/10.1016/j.softx.2020.100539
