from update_by_siasam_utils import *
import pandas as pd
import networkx as nx
import copy
import os

# Leer archivo que va a correlacionar los nombres de las plantas en el SIASAM con el SDDP
print('Cargando correspondencia de centrales...')
generator_units = loadGeneratorUnits('01-04Feb-CorrespondenciaCentrales_SDDP_SIASAM.csv')

# Carga las solicitudes de mantenimiento originales
print('Cargando solicitudes de mantenimiento originales...')
originalSolicitations = MaintenanceSolicitations('solicitudes_minimas.csv')

irregularity_manager = IrregularityManager(     # Solicitudes SIASAM muy similares pueden recibir un trato especial, aqui se configura los critérios de identificación de esas solicitudes
    tol_starting_date = 2, # Tolerancia en días para la proximidad de la fecha de inicio
    tol_duration = 2,      # Tolerancia en días para la proximidad de la duración
)                          # Si la fecha de inicio y la duración de dos solicitudes están abajo de la tolerancia, se consideran la misma y no se duplican

# Adiciona las solicitudes de mantenimiento originales a las unidades
for unit in generator_units:
    unit.setIrregularityManager(irregularity_manager)
    solicitations = originalSolicitations.getUnitSolicitations(unit)
    for solicitation in solicitations:
        unit.addOriginalSolicitation(solicitation)

# Carga las solicitudes de mantenimiento del SIASAM
print('Cargando solicitudes de mantenimiento del SIASAM...')
association_constraints = AssociationConstraints()
df_siasam = pd.read_csv('Solicitudes SIASAM 2025-2027_17-01-2025.csv')
# Limpia char160
str_cols = df_siasam.select_dtypes(include=['object']).columns
df_siasam[str_cols] = df_siasam[str_cols].apply(lambda col: col.str.replace("\xa0", " ", regex=False))
for index, row in df_siasam.iterrows():
    siasam_name = row[siasam_columns['SiasamName']]
    siasam_code = row[siasam_columns['SiasamCode']]
    minDate = round_hour_to_date(row[siasam_columns['StartDate']])
    maxDate = round_hour_to_date(row[siasam_columns['EndDate']])
    duration = row[siasam_columns['Duration']]
    equipType = row[siasam_columns['EquipType']]
    area = siasam_code.split('-')[0]
    siasam_name = area + "-" + siasam_name
    isWholePlant = False
    if equipType == 'CG':
        isWholePlant = True
        association_constraint = AssociationConstraint("assoc-" + siasam_code)
    siasamCounter = 0
    for unit in generator_units:
        if unit.hasSiasamName(siasam_name):
            siasamCounter+=1
            siasamFinalCode = siasam_code
            if siasamCounter > 1:
                siasamFinalCode = siasamFinalCode + "-" + str(siasamCounter)
            solicitation = SolicitationInstance(
                solicitation_name = siasamFinalCode,
                plant_code = unit.plant_code,
                plant_type = unit.plant_type,
                system_code = unit.plant_system,
                plant_name = unit.plant_name,
                plant_unit = unit.unit,
                duration = duration,
                min_date = datetime.datetime(minDate.year, 1, 1),
                max_date = datetime.datetime(maxDate.year, 12, 31),
                priority = 0,
                preference_date = minDate,
                fixed_date = 0
                )
            unit.addSiasamSolicitation(solicitation)
            if isWholePlant:
                association_constraint.addSolicitation(solicitation)
    if isWholePlant:
        association_constraints.addConstraint(association_constraint)
association_constraints.save('siasam_association_constraints.csv')
irregularity_manager.saveReport('siasam_matching_report')
irregularity_manager.saveReport('siasam_irregularities_duplicates', duplicates=True)

# ALGOTITMO DE ALOCACIÓN DE SOLICITUDES
print('Optimizando alocación de solicitudes...')
source = 1
node_code_counter = 2
for unit in generator_units:
    for solicitation in unit.siasam_solicitations:
        solicitation.setNodeCode(node_code_counter)
        node_code_counter += 1
    for solicitation in unit.original_solicitations:
        solicitation.setNodeCode(node_code_counter)
        node_code_counter += 1
sink = node_code_counter
erased_solicitations = []
for unit in generator_units:
    G = nx.DiGraph()
    G.add_node(source)
    G.add_node(sink)
    for solicitation in unit.siasam_solicitations:
        G.add_node(solicitation.node_code)
        G.add_edge(source, solicitation.node_code, capacity=solicitation.duration)
    for solicitation in unit.original_solicitations:
        G.add_node(solicitation.node_code)
        G.add_edge(solicitation.node_code, sink, capacity=solicitation.duration)
    for solicitation_siasam in unit.siasam_solicitations:
        for solicitation_original in unit.original_solicitations:
            if (
                (
                    solicitation_siasam.min_date <= solicitation_original.min_date and
                    solicitation_siasam.max_date >= solicitation_original.min_date
                ) or (
                    solicitation_siasam.min_date <= solicitation_original.max_date and
                    solicitation_siasam.max_date >= solicitation_original.max_date
                ) or (
                    solicitation_siasam.min_date >= solicitation_original.min_date and
                    solicitation_siasam.max_date <= solicitation_original.max_date
                )
            ):
                cost = abs(solicitation_siasam.min_date.year - solicitation_original.min_date.year) + abs(solicitation_siasam.max_date.year - solicitation_original.max_date.year)
                G.add_edge(solicitation_siasam.node_code, solicitation_original.node_code, weight = cost)
    flow_dict = nx.max_flow_min_cost(G, source, sink)
    for siasamSolicitation in unit.siasam_solicitations:
        unit.addResultSolicitation(siasamSolicitation)
    for originalSolicitation in unit.original_solicitations:
        flow = flow_dict[originalSolicitation.node_code][sink]
        if flow < originalSolicitation.duration:
            leftover = originalSolicitation.duration - flow
            solicitation = copy.deepcopy(originalSolicitation)
            solicitation.duration = leftover
            unit.addResultSolicitation(solicitation)
        else:
            erased_solicitations.append(originalSolicitation)

print('Guardando resultados...')
resultsSoliciations = MaintenanceSolicitations()
for unit in generator_units:
    resultsSoliciations.addSolicitations(unit.result_soliciations)
resultsSoliciations.saveSolicitations('optmcfg.csv')

if os.path.exists('catalogo_precedencia.csv'):
    precedence_constraints = PrecedenceConstraints()
    precedence_constraints.load('catalogo_precedencia.csv')
    for precedence_constraint in precedence_constraints.constraints:
        for i in range(len(precedence_constraint.solicitation_names) - 1, -1, -1):
            if precedence_constraint.solicitation_names[i] in [erased_solicitation.solicitation_name for erased_solicitation in erased_solicitations]:
                if i == 0 and len(precedence_constraint.solicitation_names) > 1:
                    precedence_constraint.min_delays[i + 1] = 0
                    precedence_constraint.max_delays[i + 1] = 0
                elif i < len(precedence_constraint.solicitation_names) - 1:
                    mean_delay_1 = (precedence_constraint.min_delays[i] + precedence_constraint.max_delays[i]) / 2
                    mean_delay_2 = (precedence_constraint.min_delays[i + 1] + precedence_constraint.max_delays[i + 1]) / 2
                    new_mean_delay = mean_delay_1 + mean_delay_2
                    delta_delay = (precedence_constraint.max_delays[i] - precedence_constraint.min_delays[i]) / 2
                    precedence_constraint.min_delays[i + 1] = int(new_mean_delay - delta_delay)
                    precedence_constraint.max_delays[i + 1] = int(new_mean_delay + delta_delay)
                del precedence_constraint.solicitation_names[i]
                del precedence_constraint.min_delays[i]
                del precedence_constraint.max_delays[i]
    precedence_constraints.save('optmprec.csv')

print('Proceso finalizado.')




