import datetime
import pandas as pd
from tqdm import tqdm

def round_hour_to_date(date_string):
    return datetime.datetime.strptime(date_string, "%m/%d/%Y  %H:%M").date()

def ajust_date_lower(date):
    year = date.year
    month = date.month
    if month <= 3:
        semester_start_month = 1
        semester_start_year  = year
    elif month <= 9:
        semester_start_month = 7
        semester_start_year  = year
    else:
        semester_start_month = 1
        semester_start_year  = year + 1
    return datetime.datetime(year=semester_start_year, month=semester_start_month, day=1)

def ajust_date_upper(date):
    year = date.year
    month = date.month
    if month >= 10:
        semester_end_month = 12
        semester_start_year = year
    elif month >= 4:
        semester_end_month = 6
        semester_start_year = year
    else:
        semester_end_month = 12
        semester_start_year = year - 1
    return datetime.datetime(year=semester_start_year, month=semester_end_month, day=30 if semester_end_month == 6 else 31)

def loadSiasamSolicitations(filename):
    solicitation = MaintenanceSolicitations()
    df_solicitations = pd.read_csv(filename)
    for index, row in df_solicitations.iterrows():
        solicitation.newSolicitation(
            row['Sname'],
            row['code'],
            row['type'],
            row['system'],
            row['Pname'],
            row['Unit'],
            datetime.datetime(row['min_date'], row['min_date'], row['min_date']),
            row['Duration'],
            row['max_date']
        )
    return solicitation

class Plant:
    def __init__(self, plant_name, plant_code, plant_type, units):
        self.plant_name = plant_name
        self.plant_code = plant_code
        self.plant_type = plant_type
        self.plant_aliases = []
        self.units = units
        self.plant_unit_aliases = {unit:[] for unit in units}
        self.siasam_solicitations = {unit:[] for unit in units}
        self.original_solicitations = {unit:[] for unit in units}

    def addAlias(self, alias):
        self.plant_aliases.append(alias)

    def hasAlias(self, alias):
        return alias in self.plant_aliases

    def addUnitAlias(self, alias, unit):
        if unit not in self.plant_unit_aliases:
            raise ValueError(f"Unit {unit} not found in plant {self.plant_name}")     
        self.plant_unit_aliases[unit].append(alias)

    def hasUnitAlias(self, alias):
        return any(alias in self.plant_unit_aliases[unit] for unit in self.plant_unit_aliases)
    
    def getUnitFromAlias(self, alias):
        for unit in self.plant_unit_aliases:
            if alias in self.plant_unit_aliases[unit]:
                return unit
        return None

    def addSiasamSolicitation(self, solicitation):
        if solicitation.plant_unit not in self.siasam_solicitations:
            raise ValueError(f"Unit {solicitation.unit} not found in plant {self.plant_name}")
        self.siasam_solicitations[solicitation.plant_unit].append(solicitation)

    def addOriginalSolicitation(self, solicitation):
        if solicitation.plant_unit not in self.original_solicitations:
            raise ValueError(f"Unit {solicitation.plant_unit} not found in plant {self.plant_name}")
        self.original_solicitations[solicitation.plant_unit].append(solicitation)

    def __str__(self):
        out = "Plant: " + self.plant_name + "\n"
        out += "    Units: " + str(self.units) + "\n"
        out += "    Aliases: " + str(self.plant_aliases) + "\n"
        out += "    Unit Aliases: " + str(self.plant_unit_aliases) + "\n"
        out += "    Original Solicitations: \n"
        for unit in self.original_solicitations:
            if len(self.original_solicitations[unit]) == 0:
                continue
            out += "       Unit " + str(unit) + ":\n"
            for origSol in self.original_solicitations[unit]:
                out += "          " + str(origSol.solicitation_name) + "\n"
        out += "    SIASAM Solicitations: \n"
        for unit in self.siasam_solicitations:
            if len(self.siasam_solicitations[unit]) == 0:
                continue
            out += "       Unit " + str(unit) + ":\n"
            for siasamSol in self.siasam_solicitations[unit]:
                out += "          " + str(siasamSol.solicitation_name) + "\n"
        return out

class HistoricalMaintenances:
    def __init__(self, historical_file_path):
        self.historical = {}
        df_historical = pd.read_csv(historical_file_path)
        for index, row in tqdm(df_historical.iterrows(), total=len(df_historical), desc="Processing"):
            plant_name = row['Nome SIASAM'].split('-')[0]
            plant_unit = int(row['Nome SIASAM'].split('U')[-1])
            start_date = datetime.datetime.strptime(row['Saida'], '%m/%d/%Y')
            duration = int(row['Duracao'])
            self.saveMaintenance(plant_name, plant_unit, start_date, duration)

    def saveMaintenance(self, plant_name, plant_unit, start_date, duration):
        maintenance = HistoricalMaintenance()
        maintenance.plant_name = plant_name
        maintenance.plant_unit = plant_unit
        maintenance.start_date = start_date
        maintenance.duration = duration
        maintenance.plant_id = plant_name + "-" + str(plant_unit)
        self.historical[maintenance.plant_id] = maintenance

    def getLatestMaintenance(self, plant_name, plant_unit, duration):
        latestDate = datetime.datetime(1990, 1, 1)
        latestIndex = None
        plant_id = plant_name + "-" + str(plant_unit)
        for key in self.historical:
            if key == plant_id and self.historical[key].start_date > latestDate and self.historical[key].duration >= duration*0.75 and self.historical[key].duration <= duration*1.25:
                latestDate = self.historical[key].start_date
                latestIndex = key
        if latestIndex is not None:
            return self.historical[latestIndex]
        else:
            return None

class HistoricalMaintenance:
    def __init__(self):
        self.plant_id = None
        self.plant_name = None
        self.plant_unit = None
        self.start_date = None
        self.duration = None

class PlantTechs:
    def __init__(self, catalogue_file_path):
        self.siasam = {}
        df_catalogue = pd.read_csv(catalogue_file_path)
        for index, row in df_catalogue.iterrows():
            name = row['Nombre']
            self.siasam[name] = row['Tecnologia']
    def getTechType(self, plant_name):
        if plant_name in self.siasam:
            return self.siasam[plant_name]
        else:
            code = ''.join(filter(str.isalpha, plant_name))[:3]
            for key in self.siasam:
                if code in key:
                    return self.siasam[key]
            return None

class MaintenanceSolicitations:
    def __init__(self, load_from_file=None):
        self.solicitations = {}
        self.header = "Nombre referencia ,Codigo de la planta en el SDDP,Tipo de la central (0=Termica/1=Hidro Mayor/6=Hidro Menor),Nombre de la planta en el SDDP,Codigo de la unidad en el OptMain,Dia de la fecha minima,Mes de la fecha minima,Ano de la fecha minima,Dia de la fecha maxima,Mes de la fecha maxima,Ano de la fecha maxima,Duracion del mantenimiento"
        if load_from_file is not None:
            self.load_solicitations(load_from_file)
    def newSolicitation(self, solicitation_name, plant_code, plant_type, system_code, plant_name, plant_unit, min_date, max_date, duration, priority=0, preference_date=None, fixed_date=0):
        solicitation = MaintenanceSolicitation(
            solicitation_name = solicitation_name,
            plant_code = plant_code,
            plant_type = plant_type, 
            system_code = system_code,
            plant_name = plant_name,
            plant_unit = plant_unit, 
            min_date = min_date,
            max_date = max_date, 
            duration = duration,
            priority = priority,
            preference_date = preference_date,
            fixed_date = fixed_date
            )
        self.solicitations[solicitation_name] = solicitation

    def saveSolicitations(self, output_file_path):
        with open(output_file_path, 'w') as f:
            f.write(self.header)
            for key in self.solicitations:
                solicitation = self.solicitations[key]
                text_line = f"\n{solicitation.solicitation_name},"
                text_line += f"{solicitation.plant_code},"
                text_line += f"{solicitation.plant_type},"
                text_line += f"{solicitation.plant_name},"
                text_line += f"{solicitation.plant_unit},"
                text_line += f"{solicitation.min_date.day},"
                text_line += f"{solicitation.min_date.month},"
                text_line += f"{solicitation.min_date.year},"
                text_line += f"{solicitation.max_date.day},"
                text_line += f"{solicitation.max_date.month},"
                text_line += f"{solicitation.max_date.year},"
                text_line += f"{solicitation.duration},"
                f.write(text_line)

    def addSolicitation(self, solicitation):
        self.solicitations[solicitation.solicitation_name] = solicitation

    def addSolicitations(self, solicitations):
        for solicitation in solicitations:
            self.solicitations[solicitation.solicitation_name] = solicitation

    def getPlantSolicitations(self, plant):
        plant_solicitations = []
        for key in self.solicitations:
            if self.solicitations[key].plant_name == plant.plant_name:
                plant_solicitations.append(self.solicitations[key])
        return plant_solicitations
            
    def deleteSolicitation(self, solicitation_name):
        del self.solicitations[solicitation_name]

class MaintenanceSolicitation:
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
        return out

class MaintenanceCatalogue:
    def __init__(self, catalogue_file_path, plantTechs):
        self.plantTechs = plantTechs
        self.catalogue_specific = {}
        self.catalogue_tech = {}
        df_catalogue = pd.read_csv(catalogue_file_path)
        for index, row in df_catalogue.iterrows():
            code = row['Codigo Tecnologia']
            if '-' in code:
                if code not in self.catalogue_specific:
                    self.catalogue_specific[code] = []
                self.catalogue_specific[row['Codigo Tecnologia']].append(CatalogueRule(row['Intervalo'], row['Duracao']))
            else:
                if code not in self.catalogue_tech:
                    self.catalogue_tech[code] = []
                self.catalogue_tech[code].append(CatalogueRule(row['Intervalo'], row['Duracao']))

    def getCatalogueRules(self, plant_name):
        tech_type = self.plantTechs.getTechType(plant_name)
        if plant_name[2:] in self.catalogue_specific:
            return self.catalogue_specific[plant_name[2:]]
        elif tech_type in self.catalogue_tech:
            return self.catalogue_tech[tech_type]
        else:
            return None

class CatalogueRule:
    def __init__(self, interval, duration):
        self.interval = interval
        self.duration = duration
        self.interval_max = int(self.interval * 1.25)
        self.interval_min = int(self.interval * 0.75)

class PrecedenceConstraints:
    def __init__(self):
        self.header = "!PrecName,SolName,DelayMin,DelayMax"
        self.constraints = []

    def addLine(self, prec_name, sol_name, delay_min, delay_max):
        constraint = PrecedenceConstraint(prec_name, sol_name, delay_min, delay_max)
        self.constraints.append(constraint)

    def saveConstraints(self, output_file_path):
        with open(output_file_path, 'w') as f:
            f.write(self.header)
            for constraint in self.constraints:
                f.write(f"\n{constraint.prec_name},{constraint.sol_name},{constraint.delay_min},{constraint.delay_max}")

class PrecedenceConstraint:

    def __init__(self, prec_name, sol_name, delay_min, delay_max):
        self.prec_name = prec_name
        self.sol_name = sol_name
        self.delay_min = delay_min
        self.delay_max = delay_max

class UnitCodes:
    def __init__(self, unit_codes_file):
        self.unit_codes = {}
        with open(unit_codes_file) as f:
            for line in f:
                if line[0] == '!':
                    continue
                file_values = line.split(',')
                plant_name = file_values[0]
                plant_type = int(file_values[1])
                plant_system = int(file_values[2])
                num_units = int(file_values[3])
                unit_codes = [int(unit) for unit in file_values[4:]]
                self.unit_codes[(plant_name, plant_type, plant_system)] = {
                    'num_units': num_units,
                    'unit_codes': unit_codes
                }
    def hasUnitCodes(self, plant_name, plant_type, plant_system):
        return (plant_name, plant_type, plant_system) in self.unit_codes
    def hasValidUnitCodes(self, plant_name, plant_type, plant_system, num_units):
        return num_units == self.unit_codes[(plant_name, plant_type, plant_system)]['num_units']
    def getUnitCode(self, plant_name, plant_type, plant_system, num_unit):
        return self.unit_codes[(plant_name, plant_type, plant_system)]['unit_codes'][num_unit - 1]
        