import requests
import pandas as pd
from io import StringIO
from decouple import config
from bot_base.logger_config import logger

desired_width = 320

pd.set_option('display.width', desired_width)

pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 200)

user = config("USER_GILLWEB")
password = config("PASS_GILLWEB")


def post_transform_data(data: pd.DataFrame) -> pd.DataFrame:
    data.scouter_section = data.scouter_section.astype("category")
    data.scouter_section = data.scouter_section.astype("category")
    data.id = data.id.astype(int)
    pd.to_datetime(data['birth_date'])
    return data


def pre_transform_data(data: pd.DataFrame) -> pd.DataFrame:
    data["scout_section"] = data["scout_subsection"].replace("Scouter", "Scouter  ").str.replace("Scout ", "Tropa ").str.replace("Esculta", "Escultas")
    data["scout_section"] = data["scout_section"].str.replace("Lobato", "Lobatos").str.replace("Castor", "Castores").str[:-2]
    data["scout_subsection"] = data["scout_subsection"].replace("Scouter", "").str[-1:]
    data['scouter_section'] = data['scouter_section'].str.replace("Educador ", "").replace("Sección Scout", "Tropa").replace("de Apoyo", "Apoyo")
    data["complete_name"] = data.nombre_dni + " " + data.surname

    return data


def download_data_gillweb():
    excepcion = set()
    columns = [
        'id', 'dni', 'name', 'nombre_dni', 'surname', 'gender', 'address', 'zip', 'locality', 'province', 'birth_date', 'mobile', 'email',
        'health_problems', 'food_problems', 'other_problems', 'father_name', 'father_surname', 'father_phone', 'father_email', 'mother_name',
        'mother_surname', 'mother_phone', 'mother_email', 'scout_subsection', 'scouter_section', 'coordinate_section']

    url_login = "https://www.gillweb.es/core/api.php?controller=user&action=login"
    url = f"https://www.gillweb.es/core/api.php?controller=user&action=exportCSV" \
          f"&filter%5B0%5D%5B%5D=active&filter%5B0%5D%5B%5D=%3D&filter%5B0%5D%5B%5D=1"

    for col in columns:
        url += f"&fields%5B%5D={col}"
    for i in range(0, 10):
        try:
            token = requests.post(url_login, data={"login": user, "password": password}, timeout=1).json()["data"]

            csv = requests.get(url + f"&token={token}").text

            data = pd.read_csv(StringIO(csv), sep=";", encoding="utf-8", na_filter=False, dtype=str)
            break
        except Exception as e:
            excepcion.add(e)
            continue
    else:
        logger.error(f"Fallo en la descarga de datos de gillweb -> {excepcion}")
        raise Exception(f"Fallo en la descarga de datos de gillweb")
    data = pre_transform_data(data)
    data.to_csv("data_gillweb.csv", sep=";", index=False)
    return data

download_data_gillweb()

def filter_not_scouter(data):
    data = data[["complete_name", "scout_section", "scout_subsection",
                 "father_name", "father_surname", "father_phone", "father_email",
                 "mother_name", "mother_surname", "mother_phone", "mother_email"]]
    data = data[data.scout_section != "Scouter"].reset_index(drop=True)
    data = data.sort_values("complete_name").reset_index(drop=True)
    return data


def get_contacts_gillweb():
    data = download_data_gillweb()

    data = filter_not_scouter(data)

    data2 = data[(data.father_name != "") & (data.father_email != "")]. \
        groupby(["father_name", "father_surname"]).agg(
        {"complete_name": lambda x: "Padre de " + ", ".join(x),
         "father_email": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "father_phone": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "scout_section": lambda x: tuple(sorted(set(list(
             x.replace('Castores', 'e042ea48c0ca0db').replace('Lobatos', '2dca868d8a090f2f')
             .replace('Tropa', 'ddb3a430c7d514f').replace('Escultas', '19bd885b8fdf19b3')
             .replace('Rover', '28bd46840ad37aa1')) + ["43b294f70ae0f4a7",
                                                       "myContacts"])))}).reset_index().rename_axis(None, axis=1)
    data3 = data[(data.mother_name != "") & (data.mother_email != "")]. \
        groupby(["mother_name", "mother_surname"]).agg(
        {"complete_name": lambda x: "Madre de " + ", ".join(x),
         "mother_email": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "mother_phone": lambda x: ", ".join(sorted(set(filter(None, x)))),
         "scout_section": lambda x: tuple(sorted(set(list(
             x.replace('Castores', 'e042ea48c0ca0db').replace('Lobatos', '2dca868d8a090f2f')
             .replace('Tropa', 'ddb3a430c7d514f').replace('Escultas', '19bd885b8fdf19b3')
             .replace('Rover', '28bd46840ad37aa1')) + ["43b294f70ae0f4a7",
                                                       "myContacts"])))}).reset_index().rename_axis(None, axis=1)
    data2.columns = ['givenName', 'familyName', 'biographies', 'emailAddresses', 'phoneNumbers', 'memberships']
    data3.columns = ['givenName', 'familyName', 'biographies', 'emailAddresses', 'phoneNumbers', 'memberships']
    data_final = pd.concat([data2, data3])
    data_final = data_final.sort_values(['givenName', 'familyName']).reset_index(drop=True)
    return data_final


def get_data_gillweb(section: int = None, scouter_section: int = None) -> pd.DataFrame:
    data = pd.read_csv("data_gillweb.csv", sep=";", encoding="utf-8", na_filter=False, dtype=str)
    data = post_transform_data(data)
    section_dict = {1: "Castores",
                    2: "Lobatos",
                    3: "Tropa",
                    4: "Escultas",
                    5: "Rover"}
    if section:
        data = data[data.scout_section == section_dict[section]].reset_index(drop=True)
    if scouter_section:
        data = data[data.scouter_section == section_dict[scouter_section]].reset_index(drop=True)
    return data


def get_listed_sections():
    download_data_gillweb()
    data = get_data_gillweb()
    data = data[["nombre_dni", "surname", "scout_section", "scout_subsection", "scouter_section", "birth_date"]]

    sections = []
    for subsection, df_subsection in data.groupby("scout_section"):
        df_subsection.sort_values("birth_date", ascending=True, inplace=True)
        df_subsection.drop(['scout_section'], axis=1, inplace=True)
        if subsection == "Scouter":
            df_subsection.drop(['scout_subsection'], axis=1, inplace=True)
            df_subsection.sort_values(['scouter_section', 'birth_date'], ascending=[True, True], inplace=True)
        else:
            df_subsection.drop(['scouter_section'], axis=1, inplace=True)

        df_subsection.columns = ['Nombre', 'Apellidos', 'Generación', 'Fecha_de_nacimiento']
        sections.append([subsection, df_subsection])
    sections = sorted(sections, key=lambda x: x[1].Fecha_de_nacimiento.iloc[0], reverse=True)

    return sections


def get_persons_gillweb(section: int) -> pd.DataFrame:
    data = pd.DataFrame()
    scouters = get_data_gillweb(scouter_section=section)
    scouters['scouter'] = True
    scouts = get_data_gillweb(section=section)
    scouts['scouter'] = False

    for data_gillweb in [scouts, scouters]:
        data_gillweb['unique_name'] = data_gillweb['name']
        duplicates = data_gillweb['name'].duplicated(keep=False)
        for index, is_duplicate in enumerate(duplicates):
            if is_duplicate:
                name = data_gillweb.at[index, 'name']
                surname = data_gillweb.at[index, 'surname']
                counter = 1
                while True:
                    new_name = f"{name} {surname[:counter]}"
                    if not data_gillweb['unique_name'].str.contains(new_name).any():
                        data_gillweb.at[index, 'unique_name'] = new_name
                        break
                    counter += 1
        if not data_gillweb.empty:
            data = pd.concat([data, data_gillweb[['id', 'unique_name', 'scouter']]], axis=0)

    data['unique_name'] = data['unique_name'].str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    data.sort_values(by=['scouter', 'unique_name'], ignore_index=True, inplace=True)
    return data
