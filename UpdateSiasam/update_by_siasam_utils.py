import datetime
import pandas as pd

siasam_name_columns = {
    'Code':0,
    'Name':1,
    'Unit':2,
    'Tech':3,
    'SiasamName':5,
}

siasam_columns = {
    'SiasamName':0,
    'EquipType':1,
    'SiasamCode':10,
    'StartDate':2,
    'EndDate':3,
    'Duration':4,
}

solicitudes_minimas_columns = {
    'SolicitationName':0,
    'PlantCode':1,
    'PlantTech':2,
    'PlantName':3,
    'UnitCode':4,
    'MinDateDay':5,
    'MinDateMonth':6,
    'MinDateYear':7,
    'MaxDateDay':8,
    'MaxDateMonth':9,
    'MaxDateYear':10,
    'Duration':11,
    'Priority':12,
    'PrefDateDay':13,
    'PrefDateMonth':14,
    'PrefDateYear':15,
}

siasam_fijas_columns = {
    'Area':0,
    'SolicitationName':3,
    'UnitName':4,
    'StartDate':8,
    'Duration':9,
}

sddp_tech_codes = {
    'Termica':0,
    'Hidro mayor':1,
    'Hidro menor':6,
}

def calculate_intersection_days(start1, end1, start2, end2):
    intersection_start = max(start1, start2)
    intersection_end = min(end1, end2)
    delta = (intersection_end - intersection_start).days + 1
    return max(0, delta)

def round_hour_to_date(date_string):
    return datetime.datetime.strptime(date_string, "%d/%m/%Y  %H:%M").date()

def str_to_date(date_string):
    return datetime.datetime.strptime(date_string, "%d/%m/%Y").date()

def loadGeneratorUnits(siasam_name_file, system_code):
    generator_units = []
    df_siasam_name = pd.read_csv(siasam_name_file)
    for index, row in df_siasam_name.iterrows():
        unit_plant_name = row.iloc[siasam_name_columns['Name']]
        unit_plant_code = row.iloc[siasam_name_columns['Code']]
        unit_plant_type = row.iloc[siasam_name_columns['Tech']]
        unit_siasam_name = row.iloc[siasam_name_columns['SiasamName']]
        unit_num = row.iloc[siasam_name_columns['Unit']]
        unit_is_defined = False
        for unit_i in generator_units:
            if (
                unit_i.plant_type == sddp_tech_codes[unit_plant_type]
                and unit_i.plant_code == unit_plant_code
                and unit_i.unit == unit_num
            ):
                unit = unit_i
                unit_is_defined = True
                break
        if not unit_is_defined:
            unit = GeneratorUnit(system_code, unit_plant_name, unit_plant_code, sddp_tech_codes[unit_plant_type], unit_num)
            generator_units.append(unit)
        unit.addSiasamName(unit_siasam_name)
    return generator_units

class IrregularityManager:
    def __init__(self, tol_starting_date = 2, tol_duration = 2):
        self.tol_starting_date = tol_starting_date
        self.tol_duration = tol_duration
        self.irregularities_overlap = []
        self.irregularities_duplicates = []
        self.irregularities_duplicates_fixed = []
        self.irregularities_overlap_fixed = []

    def addIrregularityOverlap(self, solicitation1, solicitation2):
        self.irregularities_overlap.append([solicitation1, solicitation2])

    def addIrregularityDuplicate(self, solicitation1, solicitation2):
        self.irregularities_duplicates.append([solicitation1, solicitation2])

    def addIrregularityDuplicateFixed(self, solicitation1, solicitation2):
        self.irregularities_duplicates_fixed.append([solicitation1, solicitation2])

    def addIrregularityOverlapFixed(self, solicitation1, solicitation2):
        self.irregularities_overlap_fixed.append([solicitation1, solicitation2])

    def saveReport(self, output_file_path, duplicates=False, fixed=False):
        if duplicates and not fixed:
            irregularities = self.irregularities_duplicates
        elif duplicates and fixed:
            irregularities = self.irregularities_duplicates_fixed
        elif not duplicates and not fixed:
            irregularities = self.irregularities_overlap
        elif not duplicates and fixed:
            irregularities = self.irregularities_overlap_fixed

        with open(output_file_path + '.txt', 'w') as f:
            f.write("  =====================  INFORME DE COMPATIBILIDAD DE SOLICITUDES SIASAM  =====================\n\n")
            f.write(" Parametros para identificar solicitudes duplicadas:\n")
            f.write(f"   Tolerancia de similaridad de fecha de inicio: {self.tol_starting_date} [dias]\n")
            f.write(f"   Tolerancia de similaridad de duracion: {self.tol_duration} [dias]\n\n")
            if len(irregularities) > 0:
                f.write(f" Las siguientes solicitudes se consideraron extensiones el uno del otro (total {len(irregularities)}):\n\n")
                for i in range(len(irregularities)):
                    f.write(f"  * Planta {irregularities[i][0].plant_name}, unidad {irregularities[i][1].plant_unit}:\n")
                    f.write(f"     - Solicitud {irregularities[i][0].solicitation_name}\n")
                    f.write(f"         Fecha de inicio: {irregularities[i][0].preference_date.strftime('%d/%m/%Y')}\n")
                    f.write(f"         Duracion: {irregularities[i][0].duration}\n")
                    f.write(f"     - Solicitud {irregularities[i][1].solicitation_name}\n")
                    f.write(f"         Fecha de inicio: {irregularities[i][1].preference_date.strftime('%d/%m/%Y')}\n")
                    f.write(f"         Duracion: {irregularities[i][1].duration}\n\n")
            else:
                f.write(" No se encontraron solicitudes extendidas.")
        data = []
        for i in range(len(irregularities)):
            data.append([
            i+1,
            irregularities[i][0].plant_name,
            irregularities[i][0].plant_unit,
            irregularities[i][0].solicitation_name,
            irregularities[i][0].preference_date.strftime('%d/%m/%Y'),
            irregularities[i][0].duration,
            ])
            data.append([
            i+1,
            irregularities[i][1].plant_name,
            irregularities[i][1].plant_unit,
            irregularities[i][1].solicitation_name,
            irregularities[i][1].preference_date.strftime('%d/%m/%Y'),
            irregularities[i][1].duration,
            ])
        df = pd.DataFrame(data, columns=['Duplicate','Plant Name', 'Unit', 'Solicitation', 'Start Date', 'Duration'])
        df.to_csv(output_file_path + '.csv', index=False)

class GeneratorUnit:
    def __init__(self, plant_system, plant_name, plant_code, plant_type, unit):
        self.plant_system = plant_system
        self.plant_name = plant_name
        self.plant_code = plant_code
        self.plant_type = plant_type
        self.unit = unit
        self.siasam_names = []
        self.siasam_solicitations = []
        self.original_solicitations = []
        self.result_soliciations = []
        self.irregularity_manager = None

    def setIrregularityManager(self, irregularity_manager):
        self.irregularity_manager = irregularity_manager

    def addSiasamName(self, siasam_name):
        self.siasam_names.append(siasam_name)

    def hasSiasamName(self, siasam_name):
        if len(siasam_name) > 7 and siasam_name[7:9] == "-U":
            unit_num = siasam_name[9:]
            if len(siasam_name[9:]) == 1:
                unit_num = "0" + siasam_name[9:]
            siasam_name = siasam_name[:7] + unit_num
        return siasam_name in self.siasam_names

    def addSiasamSolicitation(self, solicitation, isWholePlant):
        for isiasamSol in range(len(self.siasam_solicitations)):
            siasamSol = self.siasam_solicitations[isiasamSol]
            if (
                abs((siasamSol.preference_date - solicitation.preference_date).days) <= self.irregularity_manager.tol_starting_date
                and abs(siasamSol.duration - solicitation.duration) <= self.irregularity_manager.tol_duration
                and calculate_intersection_days(
                    siasamSol.preference_date,
                    siasamSol.preference_date + datetime.timedelta(days=siasamSol.duration - 1),
                    solicitation.preference_date,
                    solicitation.preference_date + datetime.timedelta(days=solicitation.duration - 1)
                    ) > 0
            ):
                if self.siasam_solicitations[isiasamSol].fixed_date == 1:
                    self.irregularity_manager.addIrregularityDuplicateFixed(siasamSol, solicitation)
                    return 1
                elif isWholePlant:
                    del self.siasam_solicitations[isiasamSol]
                    self.siasam_solicitations.append(solicitation)
                self.irregularity_manager.addIrregularityDuplicate(siasamSol, solicitation)
                return 0
            elif (
                calculate_intersection_days(
                    siasamSol.preference_date,
                    siasamSol.preference_date + datetime.timedelta(days=siasamSol.duration - 1),
                    solicitation.preference_date,
                    solicitation.preference_date + datetime.timedelta(days=solicitation.duration - 1)
                    ) > 0
            ):
                if self.siasam_solicitations[isiasamSol].fixed_date == 1:
                    self.irregularity_manager.addIrregularityOverlapFixed(siasamSol, solicitation)
                    return 1
                self.irregularity_manager.addIrregularityOverlap(siasamSol, solicitation)
        self.siasam_solicitations.append(solicitation)
        return 0

    def addOriginalSolicitation(self, solicitation):
        self.original_solicitations.append(solicitation)

    def addResultSolicitation(self, solicitation):
        self.result_soliciations.append(solicitation)

    def __str__(self):
        out = "Plant: " + self.plant_name + "\n"
        out += "    Code: " + str(self.plant_code) + "\n"
        out += "    Type: " + str(self.plant_type) + "\n"
        out += "    System: " + str(self.plant_system) + "\n"
        out += "    Unit: " + str(self.unit) + "\n"
        out += "    Siasam Names: " + str(self.siasam_names) + "\n"
        if len(self.original_solicitations) > 0:
            out += "    Original Solicitations: \n"
            for origSol in self.original_solicitations:
                out += "      " + str(origSol.solicitation_name) + " : " + str(origSol.duration) + " days " + origSol.min_date.strftime("%m/%Y") + " - " + origSol.max_date.strftime("%m/%Y") + " node " + str(origSol.node_code) + "\n"
        if len(self.siasam_solicitations) > 0:
            out += "    Siasam Solicitations: \n"
            for siasamSol in self.siasam_solicitations:
                out += "      " + str(siasamSol.solicitation_name) + " : " + str(siasamSol.duration) + " days " + siasamSol.min_date.strftime("%m/%Y") + " - " + siasamSol.max_date.strftime("%m/%Y") + " node " + str(siasamSol.node_code) + "\n"
        if len(self.result_soliciations) > 0:
            out += "    Result Solicitations: \n"
            for resultSol in self.result_soliciations:
                out += "      " + str(resultSol.solicitation_name) + " : " + str(resultSol.duration) + " days " + resultSol.min_date.strftime("%m/%Y") + " - " + resultSol.max_date.strftime("%m/%Y") + " node " + str(resultSol.node_code) + "\n"
        return out

class MaintenanceSolicitations:
    def __init__(self, load_from_file=None, fixed=False):
        self.solicitations_name_count = {}
        self.solicitations = {}
        self.header = """$version=2,,,,,,,,,,,,,,,,,
!Sname,code   ,type      ,system,Pname       ,Unit,min_date,min_date,min_date,max_date,max_date,max_date,Duration, Priority, Preference Date,Preference Date,Preference Date,Fixed Date
!       ,       ,0=thermal ,          ,            ,,dd,mm      ,yy      ,dd,mm      ,yy      ,days,,dd,mm      ,yy,
!       ,       ,1=hidro   ,          ,  ,,,        ,        ,,        ,        ,,,,,,"""
        if load_from_file is not None:
            self.loadSolicitations(load_from_file, fixed=fixed)

    def saveSolicitations(self, output_file_path):
        with open(output_file_path, 'w') as f:
            f.write(self.header)
            for key in self.solicitations:
                solicitation = self.solicitations[key]
                text_line = f"\n{solicitation.solicitation_name},"
                text_line += f"{solicitation.plant_code},"
                text_line += f"{solicitation.plant_type},"
                text_line += f"{solicitation.system_code},"
                text_line += f"{solicitation.plant_name},"
                text_line += f"{solicitation.plant_unit},"
                text_line += f"{solicitation.min_date.day},"
                text_line += f"{solicitation.min_date.month},"
                text_line += f"{solicitation.min_date.year},"
                text_line += f"{solicitation.max_date.day},"
                text_line += f"{solicitation.max_date.month},"
                text_line += f"{solicitation.max_date.year},"
                text_line += f"{solicitation.duration},"
                text_line += f"{solicitation.priority},"
                text_line += f"{solicitation.preference_date.day}," if solicitation.preference_date is not None else "0,"
                text_line += f"{solicitation.preference_date.month}," if solicitation.preference_date is not None else "0,"
                text_line += f"{solicitation.preference_date.year}," if solicitation.preference_date is not None else "0,"
                text_line += f"{solicitation.fixed_date}"
                f.write(text_line)

    def loadSolicitations(self, input_file_path, fixed=False):
        # Read the CSV file, skipping the first two header lines
        df = pd.read_csv(input_file_path)

        # Iterate through the rows and recreate SolicitationInstance objects
        for _, row in df.iterrows():
            # Parse dates using datetime
            min_date = datetime.date(
                year=int(row.iloc[solicitudes_minimas_columns["MinDateYear"]]),
                month=int(row.iloc[solicitudes_minimas_columns["MinDateMonth"]]),
                day=int(row.iloc[solicitudes_minimas_columns["MinDateDay"]])
            )
            max_date = datetime.date(
                year=int(row.iloc[solicitudes_minimas_columns["MaxDateYear"]]),
                month=int(row.iloc[solicitudes_minimas_columns["MaxDateMonth"]]),
                day=int(row.iloc[solicitudes_minimas_columns["MaxDateDay"]])
            )
            if not fixed:
                sol = SolicitationInstance(
                    solicitation_name=row.iloc[solicitudes_minimas_columns["SolicitationName"]],
                    plant_code=row.iloc[solicitudes_minimas_columns["PlantCode"]],
                    plant_type=int(row.iloc[solicitudes_minimas_columns["PlantTech"]]),
                    system_code=1,
                    plant_name=row.iloc[solicitudes_minimas_columns["PlantName"]],
                    plant_unit=row.iloc[solicitudes_minimas_columns["UnitCode"]],
                    min_date=min_date,
                    max_date=max_date,
                    duration=int(row.iloc[solicitudes_minimas_columns["Duration"]]),     
                    priority=0,
                    preference_date=None,
                    fixed_date=0
                )
            else:
                pref_date = datetime.datetime(
                    year=int(row.iloc[solicitudes_minimas_columns["PrefDateYear"]]),
                    month=int(row.iloc[solicitudes_minimas_columns["PrefDateMonth"]]),
                    day=int(row.iloc[solicitudes_minimas_columns["PrefDateDay"]])
                )
                sol = SolicitationInstance(
                    solicitation_name=row.iloc[solicitudes_minimas_columns["SolicitationName"]],
                    plant_code=row.iloc[solicitudes_minimas_columns["PlantCode"]],
                    plant_type=int(row.iloc[solicitudes_minimas_columns["PlantTech"]]),
                    system_code=1,
                    plant_name=row.iloc[solicitudes_minimas_columns["PlantName"]],
                    plant_unit=row.iloc[solicitudes_minimas_columns["UnitCode"]],
                    min_date=min_date,
                    max_date=max_date,
                    duration=int(row.iloc[solicitudes_minimas_columns["Duration"]]),     
                    priority=int(row.iloc[solicitudes_minimas_columns["Priority"]]),
                    preference_date=pref_date,
                    fixed_date=1,
                )

            self.addSolicitation(sol)

    def addSolicitation(self, solicitation):
        if solicitation.solicitation_name in self.solicitations_name_count:
            self.solicitations_name_count[solicitation.solicitation_name] += 1
            solicitation.solicitation_name += f"_{self.solicitations_name_count[solicitation.solicitation_name]}"
        self.solicitations[solicitation.solicitation_name] = solicitation

    def addSolicitations(self, solicitations):
        for solicitation in solicitations:
            self.addSolicitation(solicitation)

    def getUnitSolicitations(self, unit):
        unit_solicitations = []
        for key in self.solicitations:
            if (
                self.solicitations[key].plant_type == unit.plant_type
                and self.solicitations[key].plant_code == unit.plant_code
                and self.solicitations[key].system_code == unit.plant_system
                and self.solicitations[key].plant_unit == unit.unit
            ):
                unit_solicitations.append(self.solicitations[key])
        return unit_solicitations
    
class SolicitationInstance:
    def __init__(
            self,
            solicitation_name=None,
            plant_code=None,
            plant_type=None,
            system_code=None,
            plant_name=None,
            plant_unit=None,
            min_date=None,
            max_date=None,
            duration=None,
            priority=0,
            preference_date=None,
            fixed_date=0
            ):
        self.solicitation_name = solicitation_name
        self.plant_code = plant_code
        self.plant_type = plant_type
        self.system_code = system_code
        self.plant_name = plant_name
        self.plant_unit = plant_unit
        self.duration = duration
        self.min_date = min_date
        self.max_date = max_date
        self.priority = priority
        self.preference_date = preference_date
        self.fixed_date = fixed_date
        self.node_code = None

    def setNodeCode(self, node_code):
        self.node_code = node_code

    def getNodeCode(self):
        return self.node_code

    def __str__(self):
        out = "Solicitation: " + self.solicitation_name + "\n"
        out += "    Plant Code: " + str(self.plant_code) + "\n"
        out += "    Plant Type: " + str(self.plant_type) + "\n"
        out += "    System Code: " + str(self.system_code) + "\n"
        out += "    Plant Name: " + self.plant_name + "\n"
        out += "    Plant Unit: " + str(self.plant_unit) + "\n"
        out += "    Duration: " + str(self.duration) + "\n"
        out += "    Min Date: " + str(self.min_date) + "\n"
        out += "    Max Date: " + str(self.max_date) + "\n"
        out += "    Priority: " + str(self.priority) + "\n"
        out += "    Preference Date: " + str(self.preference_date) + "\n"
        out += "    Fixed Date: " + str(self.fixed_date) + "\n"
        out += "    Node Code: " + str(self.node_code) + "\n"
        return out
    
class AssociationConstraint:
    def __init__(self, name):
        self.name = name
        self.solicitation = []
    def addSolicitation(self, solicitation):
        self.solicitation.append(solicitation)

class AssociationConstraints:

    def __init__(self):
        self.constraints = []
        self.header = "!SetName,SolicitationName"
    def addConstraint(self, constraint):
        self.constraints.append(constraint)
    def save(self, output_file_path):
        with open(output_file_path, 'w') as f:
            f.write(self.header)
            for constraint in self.constraints:
                if len(constraint.solicitation) > 1:
                    for solicitation in constraint.solicitation:
                        f.write(f"\n{constraint.name},{solicitation.solicitation_name}")
    def filterBySolicitations(self,generator_units):
        existing_solicitations = []
        for unit in generator_units:
            for solicitation in unit.siasam_solicitations:
                existing_solicitations.append(solicitation.solicitation_name)
            for solicitation in unit.original_solicitations:
                existing_solicitations.append(solicitation.solicitation_name)
        for i in range(len(self.constraints)-1,-1,-1):
            constraint = self.constraints[i]
            for solicitation in constraint.solicitation:
                if solicitation.solicitation_name not in existing_solicitations:
                    del self.constraints[i]

class PrecedenceConstraint:
    def __init__(self, name):
        self.name = name
        self.solicitation_names = []
        self.min_delays = []
        self.max_delays = []
    def addSolicitation(self, solicitation_name, min_delay, max_delay):
        self.solicitation_names.append(solicitation_name)
        self.min_delays.append(min_delay)
        self.max_delays.append(max_delay)

class PrecedenceConstraints:
        def __init__(self):
            self.constraints = []
            self.header = "!PrecName,SolName,DelayMin,DelayMax"
        def save(self, output_file_path):
            with open(output_file_path, 'w') as f:
                f.write(self.header)
                for constraint in self.constraints:
                    if len(constraint.solicitation_names) > 1:
                        for i in range(len(constraint.solicitation_names)):
                            f.write(f"\n{constraint.name},{constraint.solicitation_names[i]},{constraint.min_delays[i]},{constraint.max_delays[i]}")
        def load(self, input_file_path):
            df = pd.read_csv(input_file_path)
            for _, row in df.iterrows():
                located = False
                for constraint in self.constraints:
                    if constraint.name == row["!PrecName"]:
                        located = True
                        constraint.addSolicitation(row["SolName"], row["DelayMin"], row["DelayMax"])
                if not located:
                    constraint = PrecedenceConstraint(row["!PrecName"])
                    constraint.addSolicitation(row["SolName"], row["DelayMin"], row["DelayMax"])
                    self.constraints.append(constraint)
