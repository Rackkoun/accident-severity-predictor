# -*- coding: utf-8 -*-
import os
import logging
from pathlib import Path
import click
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from check_structure import check_existing_file, check_existing_folder

@click.command()
@click.argument('input_filepath', type=click.Path(exists=False), required=0)
@click.argument('output_filepath', type=click.Path(exists=False), required=0)
def main(input_filepath, output_filepath):
    """ Runs data processing scripts to turn raw data from (../raw) into
        cleaned data ready to be analyzed (saved in ../preprocessed).
    """
    logger = logging.getLogger(__name__)
    logger.info('making final data set from raw data')

    # Interaktive Abfragen für Flexibilität bei den Jahrgängen
    input_filepath = click.prompt('Enter the file path for the input data', type=click.Path(exists=True))
    year = click.prompt('Enter the year of the data (e.g., 2021, 2022, 2023, 2024)', type=int)
    
    # Alle Dateinamen im Rohdaten-Ordner einlesen
    all_files = os.listdir(input_filepath)
    
  
    def find_file_dynamic(keyword, year, files):
        for f in files:
            if keyword.lower() in f.lower() and str(year) in f:
                return os.path.join(input_filepath, f)
        raise FileNotFoundError(f"🚨 Datei mit '{keyword}' und Jahr {year} nicht gefunden!")

    # Pfade vollautomatisch und tippfehler-sicher zuordnen
    input_filepath_users = find_file_dynamic("usag", year, all_files)
    input_filepath_caract = find_file_dynamic("car", year, all_files) # "car" fängt "carcteristiques" ab!
    input_filepath_places = find_file_dynamic("lieux", year, all_files)
    input_filepath_veh = find_file_dynamic("vehic", year, all_files)
    
    print(f"\n🎯 Dynamische Dateizuordnung für {year} erfolgreich:")
    print(f" -> Users:  {os.path.basename(input_filepath_users)}")
    print(f" -> Caract: {os.path.basename(input_filepath_caract)}")
    
    output_folderpath = click.prompt('Enter the folder path for the output preprocessed data (e.g., data/preprocessed)', type=click.Path())
    
    # Datenverarbeitung starten
    process_data(input_filepath_users, input_filepath_caract, input_filepath_places, input_filepath_veh, output_folderpath)

def process_data(input_filepath_users, input_filepath_caract, input_filepath_places, input_filepath_veh, output_folderpath):
    logger = logging.getLogger(__name__)
 
    #--Importing dataset 
    df_users = pd.read_csv(input_filepath_users, sep=";")
    df_caract = pd.read_csv(input_filepath_caract, sep=";", header=0, low_memory=False)
    df_places = pd.read_csv(input_filepath_places, sep=";", encoding='utf-8')
    df_veh = pd.read_csv(input_filepath_veh, sep=";")

    # Jede Spalte im gesamten Projekt von den unsichtbaren \xa0 Zeichen befreien
    for df_temp in [df_users, df_caract, df_places, df_veh]:
        for col in df_temp.columns:
            if df_temp[col].dtype == object:
                df_temp[col] = df_temp[col].astype(str).str.replace(r'[\s\xa0]+', '', regex=True)

    # === MLOPS FIX: 2022 Accident_Id Anomalie abfangen ===
    if 'Accident_Id' in df_caract.columns:
        df_caract.rename(columns={'Accident_Id': 'Num_Acc'}, inplace=True)
        logger.info("Detected and fixed 2022 'Accident_Id' anomaly on the fly.")

    #-- Creating new columns
    nb_victim = pd.crosstab(df_users.Num_Acc, "count").reset_index()
    nb_vehicules = pd.crosstab(df_veh.Num_Acc, "count").reset_index()
    
    df_users["year_acc"] = df_users["Num_Acc"].astype(str).apply(lambda x : x[:4]).astype(int)
    df_users["victim_age"] = df_users["year_acc"] - df_users["an_nais"]
    
    for i in df_users["victim_age"]:
        if (i > 120) | (i < 0):
            df_users["victim_age"].replace(i, np.nan, inplace=True)
            
    # Robuster Uhrzeit-Extraktor für wechselnde Formate (z.B. mit oder ohne Doppelpunkt)
    df_caract["hour"] = df_caract["hrmn"].astype(str).apply(lambda x : x.split(':')[0] if ':' in x else (x[:-3] if len(x) > 3 else x))
    df_caract["hour"] = pd.to_numeric(df_caract["hour"], errors='coerce').fillna(12).astype(int)
    
    df_caract.drop(['hrmn', 'an'], inplace=True, errors='ignore')
    df_users.drop(['an_nais'], inplace=True, errors='ignore')

    #-- Replacing names 
    df_users.grav.replace([1, 2, 3, 4], [1, 3, 4, 2], inplace=True)
    df_caract.rename(columns={"agg" : "agg_"}, inplace=True, errors='ignore')
    
    # Korsika-Fix robust auf alle Datentypen anwenden
    df_caract["dep"] = df_caract["dep"].astype(str).str.replace("2A", "201").str.replace("2B", "202")
    df_caract["com"] = df_caract["com"].astype(str).str.replace("2A", "201").str.replace("2B", "202")

    #-- Converting columns types
    df_caract[["dep", "com", "hour"]] = df_caract[["dep", "com", "hour"]].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)

    # 
    if df_caract["lat"].dtype == object:
        df_caract["lat"] = df_caract["lat"].astype(str).str.replace(',', '.')
    if df_caract["long"].dtype == object:
        df_caract["long"] = df_caract["long"].astype(str).str.replace(',', '.')
        
    df_caract["lat"] = pd.to_numeric(df_caract["lat"], errors='coerce').fillna(0.0)
    df_caract["long"] = pd.to_numeric(df_caract["long"], errors='coerce').fillna(0.0)

    #-- Grouping modalities 
    dico = {1:0, 2:1, 3:1, 4:1, 5:1, 6:1, 7:1, 8:0, 9:0}
    df_caract["atm"] = df_caract["atm"].replace(dico)
    
    catv_value = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,30,31,32,33,34,35,36,37,38,39,40,41,42,43,50,60,80,99]
    catv_value_new = [0,1,1,2,1,1,6,2,5,5,5,5,5,4,4,4,4,4,3,3,4,4,1,1,1,1,1,6,6,3,3,3,3,1,1,1,1,1,0,0]
    df_veh['catv'].replace(catv_value, catv_value_new, inplace=True)

    #-- Merging datasets 
    fusion1 = df_users.merge(df_veh, on=["Num_Acc", "num_veh", "id_vehicule"], how="inner")
    fusion1 = fusion1.sort_values(by="grav", ascending=False)
    fusion1 = fusion1.drop_duplicates(subset=['Num_Acc'], keep="first")
    fusion2 = fusion1.merge(df_places, on="Num_Acc", how="left")
    df = fusion2.merge(df_caract, on='Num_Acc', how="left")

    #-- Adding new columns
    df = df.merge(nb_victim, on="Num_Acc", how="inner")
    df.rename(columns={"count" : "nb_victim"}, inplace=True) 
    df = df.merge(nb_vehicules, on="Num_Acc", how="inner") 
    df.rename(columns={"count" : "nb_vehicules"}, inplace=True)

    #-- Modification of the target variable: 1: prioritary // 0: non-prioritary
    df['grav'].replace([2, 3, 4], [0, 1, 1], inplace=True)

    # === MLOPS FIX: -1 Werte in der Target-Variable 'grav' abfangen ===
    col_to_replace0_na = ["trajet", "catv", "motor"]
    col_to_replace1_na = ["grav", "trajet", "secu1", "catv", "obsm", "motor", "circ", "surf", "situ", "vma", "atm", "col"]
    
    df[col_to_replace1_na] = df[col_to_replace1_na].replace(-1, np.nan)
    df[col_to_replace0_na] = df[col_to_replace0_na].replace(0, np.nan)

    #-- Dropping columns (Defensiv mit List-Comprehension gegen fehlende Spalten)
    list_to_drop = ['senc', 'larrout', 'actp', 'manv', 'choc', 'nbv', 'prof', 'plan', 'Num_Acc', 'id_vehicule', 'num_veh', 'pr', 'pr1', 'voie', 'trajet', "secu2", "secu3", 'adr', 'v1', 'lartpc', 'occutc', 'v2', 'vosp', 'locp', 'etatp', 'infra', 'obs']
    df.drop(columns=[col for col in list_to_drop if col in df.columns], inplace=True)

    #-- Dropping lines with NaN values in critical columns
    col_to_drop_lines = ['catv', 'vma', 'secu1', 'obsm', 'atm']
    df = df.dropna(subset=col_to_drop_lines, axis=0)

    target = df['grav']
    feats = df.drop(['grav'], axis=1)

    X_train, X_test, y_train, y_test = train_test_split(feats, target, test_size=0.3, random_state=42)

    #-- Filling NaN values
    col_to_fill_na = ["surf", "circ", "col", "motor"]
    if not X_train.empty:
        X_train[col_to_fill_na] = X_train[col_to_fill_na].fillna(X_train[col_to_fill_na].mode().iloc[0])
        X_test[col_to_fill_na] = X_test[col_to_fill_na].fillna(X_train[col_to_fill_na].mode().iloc[0])

    # Erstellung des preprocessed Ordners erzwingen
    os.makedirs(output_folderpath, exist_ok=True)

    #-- Saving the dataframes to their respective output file paths
    for file, filename in zip([X_train, X_test, y_train, y_test], ['X_train', 'X_test', 'y_train', 'y_test']):
        output_filepath = os.path.join(output_folderpath, f'{filename}.csv')
        file.to_csv(output_filepath, index=False)
        logger.info(f"Saved preprocessed file: {output_filepath}")

if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    main()