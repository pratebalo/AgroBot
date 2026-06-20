import os.path
import random

import pandas as pd
from decouple import config
from bot_base.logger_config import logger
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import utils.database as db

DICT = {
    'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.google-apps.form': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.google-apps.jam': ''}
FOLDER_BASE = '0AHBcqK_64EhOUk9PVA'

SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/contacts',
          'https://www.googleapis.com/auth/spreadsheets']

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
creds = None
if os.path.exists(ROOT_DIR + '/token.json'):
    creds = Credentials.from_authorized_user_file(ROOT_DIR + '/token.json',
                                                  SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(ROOT_DIR + '/credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open(ROOT_DIR + '/token.json', 'w') as token:
        token.write(creds.to_json())

sheets_service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
spreadsheets = sheets_service.spreadsheets()
drive = build('drive', 'v3', credentials=creds, cache_discovery=False)

SHEET_ID = config('SHEET_ID')
WORKSHEET_FUEL = config('WORKSHEET_FUEL')
WORKSHEET_EXPENSES = config('WORKSHEET_EXPENSES')
WORKSHEET_TRIPS = config('WORKSHEET_TRIPS')


def create_sheet(sheet_name, folder_id):
    try:
        file_metadata = {
            'name': sheet_name,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.spreadsheet',
        }
        response = drive.files().create(body=file_metadata).execute()

        sheet = get_sheet(response['id'])

        return sheet

    except Exception as e:
        logger.error(e)


def create_worksheet(gsheet_id: str, worksheet_name: str):
    try:
        # Check if the worksheet exists
        response = spreadsheets.get(spreadsheetId=gsheet_id).execute()
        sheet_titles = [s['properties']['title'] for s in response['sheets']]
        # If the worksheet doesn't exist, create it
        if worksheet_name not in sheet_titles:
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': worksheet_name
                        }
                    }
                }]
            }
            spreadsheets.batchUpdate(
                spreadsheetId=gsheet_id,
                body=request_body
            ).execute()
            logger.info(f"Worksheet '{worksheet_name}' created successfully.")

    except Exception as e:
        logger.error(e)


def append_data(gsheet_id: str, worksheet_name: str, cell_range_insert: str, values: list):
    create_worksheet(gsheet_id, worksheet_name)
    try:
        value_range_body = {
            'majorDimension': 'ROWS',
            'values': values
        }

        response = spreadsheets.values().append(
            spreadsheetId=gsheet_id,
            valueInputOption='USER_ENTERED',
            range=f'{worksheet_name}!{cell_range_insert}',
            body=value_range_body
        ).execute()

        return response

    except Exception as e:
        logger.error(e)


def add_sheets(gsheet_id: str, sheet_name: str):
    try:
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 5000,
                            'columnCount': 100
                        },
                        "tabColor": {
                            "red": random.uniform(0, 1),
                            "green": random.uniform(0, 1),
                            "blue": random.uniform(0, 1)
                        }
                    }
                }
            }]
        }

        response = spreadsheets.batchUpdate(
            spreadsheetId=gsheet_id,
            body=request_body
        ).execute()

        return response

    except Exception as e:
        logger.error(e)


def delete_sheet(gsheet_id: str, sheet_id: str):
    try:
        request_body = {
            'requests': [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
        }

        response = spreadsheets.batchUpdate(
            spreadsheetId=gsheet_id,
            body=request_body
        ).execute()

        return response

    except Exception as e:
        logger.error(e)


def clear_sheet(gsheet_id: str, sheet_name: str, ranged='A1:ZZ'):
    create_worksheet(gsheet_id, sheet_name)
    try:
        response = spreadsheets.values().clear(
            spreadsheetId=gsheet_id,
            body={},
            range=f'{sheet_name}!{ranged}'
        ).execute()

        return response

    except Exception as e:
        logger.error(e)


def get_sheet(gsheet_id: str):
    sheet = sheets_service.spreadsheets().get(spreadsheetId=gsheet_id).execute()

    return sheet


def rename_file(file_id: str, new_name: str) -> None:
    try:
        body = {'name': new_name}
        return drive.files().update(fileId=file_id, body=body).execute()

    except Exception as e:
        logger.error(e)


def generate_sheet_fuel() -> None:
    """Consulta la tabla fuel y la escribe en la pestaña Gasofa del sheet"""
    try:
        fuel_df = db.select('fuel')
        fuel_df["date"] = pd.to_datetime(fuel_df["date"]).dt.strftime("%d/%m/%Y")
        clear_sheet(SHEET_ID, WORKSHEET_FUEL)
        data = [["Id", "Fecha", "Precio/L", "Persona"]]
        data.extend(fuel_df.values.tolist())
        append_data(SHEET_ID, WORKSHEET_FUEL, 'B2', data)
        logger.info("Datos de fuel actualizados en la pestaña Gasofa")
    except Exception as e:
        logger.error(f"Error al actualizar fuel en Gasofa: {e}")

#
#
#
# def generate_sheet_sections() -> None:
#     list_sections = gillweb.get_listed_sections()
#     new_name = f'Listados-{datetime.now().strftime("%d/%m/%y %H:%M")}'
#     rename_file(ID_SHEET_LISTADOS, new_name)
#     for section, df in list_sections:
#         clear_sheet(ID_SHEET_LISTADOS, section)
#         data = [df.columns.values.tolist()]
#         data.extend(df.values.tolist())
#         append_data(ID_SHEET_LISTADOS, section, 'B2', data)
#         x = df.groupby(['Generación']).size().reset_index(name='Total')
#         x.loc[len(x.index)] = ['Total', sum(x.Total)]
#         data = [x.columns.values.tolist()]
#         data.extend(x.values.tolist())
#         append_data(ID_SHEET_LISTADOS, section, 'H3', data)
#
#
# def generate_sheet_assistance(section: int) -> None:
#     sheet_id = sheet_sections[section]
#     assistance = db.select_where("assistance", ['section', 'season'], [section, db.get_current_season()]).sort_values('date')
#     data_gillweb = gillweb.get_data_gillweb(section=section)[['id', 'name', 'surname']]
#     result_df = data_gillweb.copy()
#     seen = {}
#     new_columns = []
#     for item in assistance.meeting_name:
#         if item in seen:
#             seen[item] += 1
#             new_columns.append(f"{item} ({seen[item]})")
#         else:
#             seen[item] = 1
#             new_columns.append(item)
#     assistance.meeting_name = new_columns
#     current_year = db.get_current_season().split("-")[1]
#     trims = ['01-10', '03-25', '09-16']
#     date_trims = [datetime.strptime(f"{current_year}-{trim}", '%Y-%m-%d').date() for trim in trims]
#     pos = 0
#     total = 0
#
#     for index, row in assistance.iterrows():
#         if row["date"] > date_trims[pos]:
#             if total != 0:
#                 result_df[f"Trimestre {pos + 1}"] = result_df[result_df.columns[-total:]].sum(axis=1)
#             pos += 1
#             total = 0
#         attendees = row['people_id']
#         result_df[row['meeting_name']] = result_df['id'].apply(lambda x: 1 if x in attendees else 0)
#         total += 1
#
#     if "Trimestre" not in result_df.columns[-1] and len(result_df.columns) > 3:
#         result_df[f"Trimestre {pos + 1}"] = result_df[result_df.columns[-total:]].sum(axis=1)
#
#     quarters_col = [index for index, column_name in enumerate(result_df.columns) if 'Trimestre' in column_name]
#
#     result_df[f"Total"] = result_df.iloc[:, quarters_col].sum(axis=1)
#     result_df[assistance.meeting_name] = result_df[assistance.meeting_name].replace({1: 'SI', 0: 'NO'})
#     result_df.sort_values('Total', inplace=True, ascending=False)
#     result_df.drop("id", inplace=True, axis=1)
#     result_df = result_df.rename(columns={"name": "Nombre", "surname": "Apellidos"})
#     clear_sheet(sheet_id, 'Asistencia')
#     data = [result_df.columns.tolist()]
#     data.extend(result_df.values.tolist())
#     append_data(sheet_id, 'Asistencia', 'B2', data)
