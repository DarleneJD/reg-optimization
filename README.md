# Darlene OLTC LV Optimization

This repository contains the OpenDSS models and Python scripts developed for the project on reducing OLTC tap operations through coordinated adjustment of photovoltaic (PV) inverter parameters (mainly power factor settings).  
The study is based on the IEEE 13-Bus Test Feeder adapted with residential/commercial “laterals” from the publicly available [dataset](https://brunel.figshare.com/articles/dataset/Open_access_data_for_the_IEEE_13_bus_system_implementation_in_OpenDSS_associated_with_the_IEEE_Access_paper_Reactive_Power_Control_of_PV_Inverters_in_Active_Distribution_Grids_with_High_PV_Penetration_/23742222) used in [Reactive Power Control of PV Inverters in Active Distribution Grids with High PV Penetration](https://ieeexplore.ieee.org/document/10196378).



## Repository Structure

/dss/
- `IEEE13_v1.dss`
- `Transformers.dss`
- `Regulator.dss`
- `LineCodes.dss`
- `Lines.dss`
- `LateralsXFMR.dss`
- `LateralsLines.dss`
- `LateralsLoads.dss`
- `LateralsPVs2_fp.dss`


/txt/
- `demand_bloque_A_Torre_I.txt` 
- `demand_bloque_A_Torre_II.txt`
- `demand_bloque_A_Torre_III.txt` 
- `demand_bloque_CT_Infra.txt`
- `demand_bloque_B_K.txt` 
- `demand_bloque_C_D.txt` 
- `demand_bloque_E_F.txt` 
- `demand_bloque_L_1.txt` 
- `demand_bloque_L_2.txt` 
- `demand_bloque_L_3.txt` 
- `demand_bloque_Data_Center.txt` 
- `demand_bloque_Ar_Condicionado.txt` 
- `irradiancia_2880.txt`
- `temperatura_2880.txt`


/python/
- `FPA-13bus-MV-LV.py`



### Key Files

#### IEEE13_v1.dss
Main file that assembles the full distribution feeder: line geometry, transformers, laterals, PV units, loadshapes, and monitors.

#### LateralsLoads.dss
The original dataset provided in the referenced repository did not include a loads file.  
This file was created to define the missing loads and assign **distinct loadshapes** to represent realistic consumption diversity across households along the laterals.

#### LateralsPVs2_fp.dss
This modified version is used in the present project:  
- includes **irradiance and temperature curves with 2880 samples**  
- irradiance and temperature vary with time  
- PVs include **explicit power-factor declaration (pf)** to enable optimization and online adjustment during the simulations.

This file replaces `LateralsPVs2.dss` when running scenarios where inverter PF is adjusted.

The LateralsPVs2.dss (not included in this git) directly follows the configuration used in the mentioned paper:  
- volt/var curves included  
- irradiance = 1 pu  
- temperature = 25°C  
- PV generation is therefore constant and not time-varying.


---

## Objective of the Project

This project investigates how photovoltaic inverter power-factor adjustments can reduce the total number of OLTC (On-Load Tap Changer) operations in LV distribution networks with high PV penetration.
Using OpenDSS and Python automation, the methodology evaluates different PF settings applied to each PV system and measures their impact on tap activity over a full 24-hour daily simulation.

The workflow integrates:
1. OpenDSS for static and daily (2880-step) time-series power flow.
2. py-dss-interface for automating model compilation, PF assignment, simulation, and data export.
3. A custom optimization procedure that includes:
4. applying PF values to all PV systems
5. validating PF limits through a sanitization function 
6. running the full 24-hour simulation
7. exporting and reading the EventLog
8. counting OLTC tap operations
9. evaluating whether a candidate PF vector improves or worsens tap performance 
10. optimization through a meta-heuristic (Flower Pollination Algorithm — FPA) 
11. (future) OLTC mechanical life impact estimation
12. (future) PV inverter life impact estimation
13. (future) automatic plotting and reporting
---

## Python Script (`FPA-13bus-MV-LV.py`)

the script implements a complete optimization loop to minimize OLTC tap operations.
The main features are:

### Core functionality
    -Loads and compiles the IEEE13 model.

    -Configures voltage bases and static control mode.

    -Runs a 2880-step daily simulation (mode=daily number=2880).

    -Identifies the number of PV units in the system.

    -Evaluates tap operations by:

        -exporting the EventLog

        -scanning the file for TAP events

        -filtering by regulator name

        -returning the total number of tap changes


### Objective function
The optimization target evaluates a candidate PF vector by:

1. Running a reference case (PF=1.0 for all PVs) to obtain baseline tap count.

2. Running the proposed PF vector after sanitization.

3. Comparing both cases:

    if the candidate PF increases the number of taps → return a large penalty

    otherwise → return the actual number of tap operations



### Optimization via Flower Pollination Algorithm (FPA)

The algorithm includes:
    Levy flight for global exploration

    Local and global pollination steps

    Boundary control for PF values

    Real-time best-solution updates

### PF post-processing and outputs
After convergence, the script:

    Re-runs the 24-hour simulation using the best PF vector

    Exports an EventLog for the optimized case

    Saves a CSV file with:

        PV names

        raw PF values found by FPA

        sanitized PF values actually used in the model


Planned enhancements already scaffolded in the code include:


    OLTC mechanical lifetime estimation

    generation of before/after voltage and tap plots

    automatic report creation summarizing optimization results

## Row to run

Follow the steps below to execute the optimization and reproduce the results generated by FPA-13bus-MV-LV.py.

1. Install Python Dependencies
    Make sure you have Python installed.
    Then install the required packages:

        pip install py-dss-interface numpy pandas matplotlib scipy

2. Prepare the OpenDSS Model
Ensure that the main feeder file (IEEE13_v1.dss) and all dependent .dss files (loads, PVs, loadshapes, etc.) are located in the directory expected by the script.
In the script, update the following line to point to your local path:
    dss_file = r"YOUR_PATH/IEEE13_v1.dss"
All results will be exported automatically to the same directory.

3. Run the Script
4. Optional: Adjust Algorithm Parameters: 
In the script, modify these lines to change the behavior of the FPA:
- flowers     = 100      # population size
- iterations  = 100      # number of optimization iterations
- gama        = 0.1      # step size for global pollination
- lamb        = 1.5      # Levy flight exponent
- p           = 0.75     # probability of global vs local pollination


## Roadmap

The following improvements and extensions are planned for future versions of this project:

- [ ] **Voltage-violation penalty integration**  
  Add penalty terms to the objective function to simultaneously minimize TAP operations and maintain voltage compliance.

- [ ] **OLTC mechanical lifetime estimation**  
  Estimate accumulated mechanical stress based on tap-change frequency and derive lifetime reduction metrics.

- [ ] **PV inverter lifetime impact analysis**  
  Evaluate how sustained PF adjustments affect inverter thermal stress and operational aging.

- [ ] **Automated before/after plots**  
  Generate time-series charts comparing:  
  - tap operations,  
  - nodal voltages,  
  - PV output profiles,  
  - PF behavior across the fleet.

- [ ] **Automated reporting engine**  
  Export a PDF/HTML report summarizing optimization results, graphs, PF values, and system metrics.

- [ ] **Support for alternative optimization algorithms**  
  Add options such as Genetic Algorithms (GA), Particle Swarm Optimization (PSO), Differential Evolution (DE), and Simulated Annealing.

- [ ] **Parallelized simulations for speed-up**  
  Use multiprocessing or batched scenarios to accelerate FPA evaluations.

- [ ] **Flexible feeder integration**  
  Extend the code to support additional feeders beyond IEEE 13-bus (e.g., IEEE 34-bus, 123-bus, European LV test feeders).


- [ ] **Model validation and test suite**  
  Include regression tests, simplified examples, and reference outputs.


## Authors and Acknowledgment

**Author**  
- **Darlene Josiane Dullius** – Research, modeling, OpenDSS integration, and development of the PF-based optimization workflow.

**Acknowledgments**  
- **Brunel University / Figshare Repository**  
  For providing the open-access IEEE 13-Bus dataset used as the base model for this study.

- **“Reactive Power Control of PV Inverters in Active Distribution Grids with High PV Penetration” (IEEE Access)**  
  For the methodological reference and PV-lateral modeling approach upon which this repository builds.

- **py-dss-interface Development Team**  
  For maintaining the Python–OpenDSS bridge that enables automated simulation workflows.


You can increase iterations and flowers for better optimization accuracy at the cost of longer execution time.


## Project status
Ongoing