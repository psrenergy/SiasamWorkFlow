# UpdateSiasam

The **UpdateSiasam** module is part of a broader project designed to assist in planning maintenance schedules for power system generators. It aims to reconcile the minimum theoretical maintenance requirements (referred to as "catalogue minimum requests") for each technology type with the latest actual maintenance requests made by power system agents and asset owners (referred to as "SIASAM requests"). This repository implements a matching methodology using a graph model, incorporating the Ford-Fulkerson and Network Simplex optimization methods. The output is a merged maintenance request list and adjusted data that complies with scheduling constraints.

### Input Data
By default, the script expects the following input files:
- `01-04Feb-CorrespondenciaCentrales_SDDP_SIASAM.csv`: Mapping between generators for the catalogue and SIASAM data.
- `Solicitudes SIASAM 2025-2027_17-01-2025.csv`: SIASAM maintenance requests.
- `solicitudes_minimas.csv`: Catalogue minimum required maintenance requests.
- `catalogo_precedencia.csv`: Precedence constraints for the minimum required maintenance requests.

### Output Data
The program generates the following output files:
- `optmcfg.csv`: **Merged** maintenance requests.
- `optmprec.csv`: **Merged** precedence constraints.
- `siasam_association_constraints.csv`: **New** association constraints to append to any existing ones.
- `siasam_matching_report.txt`: A report listing matching cases that might require special attention.

### Execution Steps
To run the model, ensure that Python is installed on your system. To install the required dependencies, open the command prompt, navigate to the root directory, and run:
```
pip install -r requirements.txt
```
Once the environment is properly set up, execute the program by running:
```
.\update_by_siasam.bat
```