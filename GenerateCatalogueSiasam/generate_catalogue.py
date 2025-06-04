from generate_catalogue_utils import *
import csv

FIRST_YEAR = 2025
NUMBER_OF_YEARS = 3
faltando_catalogo = []

historicalMaintenances = HistoricalMaintenances('historico.csv')
plantTechs = PlantTechs('tecnologias_plantas.csv')
catalogue = MaintenanceCatalogue('catalogo_general_completo.csv', plantTechs)
maintenanceSolicitations = MaintenanceSolicitations()
precedenceConstraints = PrecedenceConstraints()
unitCodes = UnitCodes('optmuntcod.csv')

# Faz solicitacoes para usinas termicas
df_plants = pd.read_csv('plantas_para_catalogo.csv')
for index, row in df_plants.iterrows():
    plant_name = row['Nome']
    plant_type = row['Tipo']
    plant_code = row['Codigo']
    system_code = 1
    number_units = int(row['Unidades'])
    catalogueRules = catalogue.getCatalogueRules(plant_name)
    if catalogueRules is None:
        print(f"Aviso: Regla de maintenimiento no fue encontrada para {plant_name}")
        faltando_catalogo.append(plant_name)
        continue
    for unit in range(1, number_units + 1):
        if unitCodes.hasUnitCodes(plant_name, plant_type, system_code):
            if unitCodes.hasValidUnitCodes(plant_name, plant_type, system_code, number_units):
                unit = unitCodes.getUnitCode(plant_name, plant_type, system_code, unit)
            else:
                print(f"Aviso: Planta {plant_name} esta en el archivo de codigos de unidades pero no lo numero de unidades no coincide")
        count_sol = 1
        for catalogueRule in catalogueRules:
            latest_maintenance = historicalMaintenances.getLatestMaintenance(plant_name, unit, catalogueRule.duration)
            if latest_maintenance == None:
                next_date_min = datetime.datetime(FIRST_YEAR, 1, 1)
            else:
                next_date_min = latest_maintenance.start_date + datetime.timedelta(days=catalogueRule.interval)
            num_maint_horizon = 1 + int((NUMBER_OF_YEARS * 365 - catalogueRule.interval) / ((next_date_min - datetime.datetime(FIRST_YEAR, 1, 1)).days + catalogueRule.interval))
            for count_prec in range(1, num_maint_horizon + 1):
                maintenanceSolicitations.newSolicitation(
                    f"CAT{count_sol}-n{count_prec}-{plant_name}-U{unit}",
                    plant_code,
                    plant_type,
                    system_code,
                    plant_name,
                    unit,
                    ajust_date_lower(next_date_min),
                    ajust_date_upper(next_date_min + datetime.timedelta(days=catalogueRule.interval) + datetime.timedelta(days=catalogueRule.duration)),
                    catalogueRule.duration
                )
                if num_maint_horizon > 1:
                    if count_prec > 1:
                        precedenceConstraints.addLine(
                            f"CAT{count_sol}-{plant_name}-U{unit}",
                            f"CAT{count_sol}-n{count_prec}-{plant_name}-U{unit}",
                            catalogueRule.interval_min,
                            catalogueRule.interval_max
                        )
                    else:
                        precedenceConstraints.addLine(
                            f"CAT{count_sol}-{plant_name}-U{unit}",
                            f"CAT{count_sol}-n{count_prec}-{plant_name}-U{unit}",
                            0,
                            0
                        )
                next_date_min = next_date_min + datetime.timedelta(days=catalogueRule.interval)
            count_sol += 1

maintenanceSolicitations.saveSolicitations('solicitudes_minimas.csv')
precedenceConstraints.saveConstraints('precedencia_solicitudes_minimas.csv')

with open('faltando_catalogo.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows([[name] for name in faltando_catalogo])
