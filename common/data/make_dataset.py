"""
Preprocessing of raw data to train/test splits
"""

from collections import defaultdict
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer


def process_data(
    years: list[int] = [2021, 2022, 2023, 2024],
    exclusive_test_year: int | None = None,
    raw_data_dir: str = "./data/raw",
    processed_data_dir: str = "./data/processed",
    normalize: bool = True,
    test_size: float = 0.3,
    random_state: int = 42
    ) -> None:
    """Create from raw data of specified years the train and test data"""
    
    # For now: Processing stopped if train/test files already exist (avoiding data leakage)
    if check_processed_data_dir(processed_data_dir):
        print("Processed data directory is not empty. Skipping processing step...")
        return
    
    # Get all raw data paths
    raw_paths = collect_raw_data_paths(raw_data_dir=raw_data_dir)

    # Preprocess data
    df_years = {}
    for year in years:
        df_years[year] = process_yearly_data(
            raw_path_collection=raw_paths,
            year=year)
        
    # Split data      
    X_train, X_test, y_train, y_test = split_data(
        df_collection=df_years,
        exclusive_test_year=exclusive_test_year,
        test_size=test_size,
        random_state=random_state)
    
    # Process features (NaN row handling + Normalization)
    X_train, X_test = process_features(
        X_train=X_train,
        X_test=X_test,
        normalize=normalize
    )
    
    # Save datasets to prcoessed path
    save_datasets(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        processed_data_dir=processed_data_dir
    )


def check_processed_data_dir(
        processed_data_dir: str | Path
        ) -> bool:
    """Check if train/test files already exist."""
    processed_data_dir = Path(processed_data_dir)
    processed_files = ["X_train.csv", "X_test.csv", "y_train.csv", "y_test.csv"]
    for file in processed_files:
        if (processed_data_dir / file).exists():
            return True
    return False


def collect_raw_data_paths(
        raw_data_dir: str = "./data/raw"
        ) -> defaultdict:
    """Collect file paths ordered by file type + year."""
    raw_data_dir = Path(raw_data_dir)
    files = defaultdict(dict)
    for file_path in raw_data_dir.glob("*.csv"):
        table = file_path.stem[:3].lower()
        year = int(file_path.stem[-4:])
        files[table][year] = file_path
    
    return files


def process_yearly_data(
        raw_path_collection: defaultdict,
        year: int
        ) -> pd.DataFrame:
    """Process the 4 datasets of a given year and return a single DataFrame."""
    # Importing dataset
    df_users = pd.read_csv(raw_path_collection["usa"][year], sep=";")
    df_veh = pd.read_csv(raw_path_collection["veh"][year], sep=";")
    df_caract = pd.read_csv(raw_path_collection["car"][year], sep=";")
    df_places = pd.read_csv(raw_path_collection["lie"][year], sep=";")

    # Process individual datasets
    df_users = process_users(df_users)
    df_veh = process_vehicles(df_veh)
    df_caract = process_characteristics(df_caract)
    df_places = process_places(df_places)

    # Merge datasets
    df = merge_datasets(
        df_users=df_users, 
        df_veh=df_veh,
        df_caract=df_caract,
        df_places=df_places)

    # Apply processing to merged dataset
    df = process_merged_dataset(df)

    return df
    
    
def correct_id_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """Correct 2022 Accident_Id anomaly."""
    if df.get("Accident_Id", None) is not None:
        df["Num_Acc"] = df.Accident_Id
        df = df.drop(columns=["Accident_Id"])
    
    return df


def clean_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Get rid of non-breaking spaces."""
    obj_cols = df.select_dtypes(include=["object", "str"]).columns
    df[obj_cols] = (
        df[obj_cols]
        .apply(lambda s: s.str.replace("\xa0", "", regex=False).str.strip())
    )

    return df


def process_users(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw users csv."""
    # Make sure "Num_Acc" exists
    df = correct_id_anomaly(df)

    # Remove non-breaking spaces from object cols
    df = clean_object_columns(df)

    # Modify target variable
    # From 1: Unharmed, 2: Killed, 3: Injured (hospitalized), 4: Lightly injured
    # To   0: Unharmed, Lightly injured, 1: Injured (hospitalized), Killed
    df["grav"] = df["grav"].replace([1,2,3,4], [0,1,1,0])

    # Create accident year column
    df["year_acc"] = df["Num_Acc"].astype(str).apply(lambda x : x[:4]).astype(int)

    # Create victim age column
    df["victim_age"] = df["year_acc"]-df["an_nais"]
    for age in df["victim_age"] :
        if (age>120)|(age<0):
            df["victim_age"].replace(age,np.nan)

    # Drop victim birth column
    df = df.drop(['an_nais'], axis=1)

    # Create victim count column
    nb_victim = df.groupby(df.Num_Acc).size().rename("nb_victim")
    df = df.merge(nb_victim, on="Num_Acc", how="inner")

    return df

def process_vehicles(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw vehicles csv."""
    # Make sure "Num_Acc" exists
    df = correct_id_anomaly(df)

    # Remove non-breaking spaces from object cols
    df = clean_object_columns(df)

    # Summarize vehicle category
    catv_value = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,30,31,32,33,34,35,36,37,38,39,40,41,42,43,50,60,80,99]
    catv_value_new = [0,1,1,2,1,1,6,2,5,5,5,5,5,4,4,4,4,4,3,3,4,4,1,1,1,1,1,6,6,3,3,3,3,1,1,1,1,1,0,0]
    df["catv"] = df["catv"].replace(catv_value, catv_value_new)

    # Create vehicle count column (involved vehicles)
    nb_vehicles = df.groupby(df.Num_Acc).size().rename("nb_vehicles")
    df = df.merge(nb_vehicles, on="Num_Acc", how="inner")

    return df


def process_characteristics(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw characteristics csv."""
    # Make sure "Num_Acc" exists
    df = correct_id_anomaly(df)

    # Remove non-breaking spaces from object cols
    df = clean_object_columns(df)

    # Département & Municipality code replacement
    df["dep"] = df["dep"].str.replace("2A", "201")
    df["dep"] = df["dep"].str.replace("2B", "202")
    df["com"] = df["com"].str.replace("2A", "201")
    df["com"] = df["com"].str.replace("2B", "202")

    # Create hour column
    df["hour"] = df["hrmn"].astype(str).apply(lambda x : x[:-3])

    # Drop columns
    df = df.drop(['hrmn', 'an'], axis=1)

    # Converting columns types
    cols = ["dep", "com", "hour"]
    df[cols] = df[cols].apply(
        pd.to_numeric,
        errors="coerce"
    ).astype("Int64")

    # lat and lon values to float
    dico_to_float = { 'lat': float, 'long':float}
    df["lat"] = df["lat"].str.replace(',', '.')
    df["long"] = df["long"].str.replace(',', '.')
    df = df.astype(dico_to_float)

    # Group weather conditions
    dico = {1:0, 2:1, 3:1, 4:1, 5:1, 6:1,7:1, 8:0, 9:0}
    df["atm"] = df["atm"].replace(dico)
    
    return df


def process_places(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw places csv."""
    # Make sure "Num_Acc" exists
    df = correct_id_anomaly(df)

    # Remove non-breaking spaces from object cols
    df = clean_object_columns(df)
    
    return df


def merge_datasets(
        df_users: pd.DataFrame,
        df_veh: pd.DataFrame,
        df_places: pd.DataFrame,
        df_caract: pd.DataFrame
        ) -> pd.DataFrame:
    """Merge the 4 cleaned datasets to one DataFrame."""
    fusion1= df_users.merge(df_veh, on = ["Num_Acc","num_veh", "id_vehicule"], how="inner")
    fusion1 = fusion1.sort_values(by = "grav", ascending = False)
    fusion1 = fusion1.drop_duplicates(subset = ['Num_Acc'], keep="first")
    fusion2 = fusion1.merge(df_places, on = "Num_Acc", how = "left")
    df = fusion2.merge(df_caract, on = 'Num_Acc', how="left")

    return df


def process_merged_dataset(
        df: pd.DataFrame
        ) -> pd.DataFrame:
    """Processing step for merged dataset."""
    # Replacing values -1 and 0 
    col_to_replace0_na = ["trajet", "catv", "motor"]
    col_to_replace1_na = ["trajet", "secu1", "catv", "obsm", "motor", "circ", "surf", "situ", "vma", "atm", "col"]
    df[col_to_replace1_na] = df[col_to_replace1_na].replace(-1, np.nan)
    df[col_to_replace0_na] = df[col_to_replace0_na].replace(0, np.nan)

    # Dropping columns 
    list_to_drop = ['senc','larrout','actp', 'manv', 'choc', 'nbv', 'prof', 'plan', 'Num_Acc', 'id_vehicule', 
                    'num_veh', 'pr', 'pr1','voie', 'trajet',"secu2", "secu3",'adr', 'v1', 'lartpc','occutc',
                    'v2','vosp','locp','etatp', 'infra', 'obs']
    df.drop(list_to_drop, axis=1, inplace=True)

    return df


def split_data(
        df_collection: dict[int, pd.DataFrame],
        exclusive_test_year: int | None = None,
        test_size: float = 0.3,
        random_state: int = 42
        ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Create train-test splits. 
    test_size and random_state are only used if exclusive_test_year is None.
    """
    # Case 1: Test data based on specific year
    if exclusive_test_year:
        train = pd.concat(
            [df for year, df in df_collection.items()
            if year != exclusive_test_year],
            ignore_index=True,
        )

        X_train = train.drop(["grav"], axis = 1)
        y_train = train["grav"]

        test = df_collection[exclusive_test_year]

        X_test = test.drop(["grav"], axis = 1)
        y_test = test["grav"]
    
    # Case 2: Test data randomly sampled
    else:
        df = pd.concat(
            [df for year, df in df_collection.items()
            if year != exclusive_test_year],
            ignore_index=True,
        )

        target = df['grav']
        feats = df.drop(['grav'], axis = 1)

        X_train, X_test, y_train, y_test = train_test_split(
            feats, target, test_size=test_size, random_state=random_state
            )
        
    return X_train, X_test, y_train, y_test


def process_features(
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        normalize: bool = True
        ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply categorial and numeric imputation to NaN values + normalize data"""
    
    # Imputation for NaN values
    cat_cols = ['place', 'catu', 'sexe', 'secu1', 'catv', 'obsm', 'motor', 'catr', 'circ',
       'surf', 'situ', 'jour', 'mois', 'lum', 'dep', 'com', 'agg', 'int', 'atm', 'col', 
       'lat', 'long', 'hour']
    num_cols = [
        c for c in X_train.columns
        if c not in cat_cols
        ]
    
    median_imputer = SimpleImputer(strategy="median")
    mode_imputer = SimpleImputer(strategy="most_frequent")

    X_train[num_cols] = median_imputer.fit_transform(X_train[num_cols])
    X_test[num_cols] = median_imputer.transform(X_test[num_cols])

    X_train[cat_cols] = mode_imputer.fit_transform(X_train[cat_cols])
    X_test[cat_cols] = mode_imputer.transform(X_test[cat_cols])

    # Apply normalization
    if normalize:
        scaler = StandardScaler()

        X_train = pd.DataFrame(
            scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index,
        )

        X_test = pd.DataFrame(
            scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index,
        )

    return X_train, X_test
    
    
def save_datasets(
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        processed_data_dir: str | Path
        ) -> None:
    """Save the train/test datasets"""
    for file, filename in zip([X_train, X_test, y_train, y_test], ["X_train", "X_test", "y_train", "y_test"]):
        out_path = Path(processed_data_dir) / f"{filename}.csv"
        file.to_csv(out_path, index=False)


if __name__ == "__main__":
    
    # Config
    YEARS = [2021, 2022, 2023, 2024]
    EXCLUSIVE_TEST_YEAR = 2024
    RAW_DATA_DIR = "../../data/raw"
    PROCESSED_DATA_DIR = "../../data/processed"
    NORMALIZE = True

    # Run processing
    process_data(
        years=YEARS,
        exclusive_test_year=EXCLUSIVE_TEST_YEAR,
        raw_data_dir=RAW_DATA_DIR,
        processed_data_dir=PROCESSED_DATA_DIR,
        normalize=NORMALIZE
    )