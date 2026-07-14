import joblib
import pandas as pd
import sys
import json


X_train = pd.read_csv("data/preprocessed/X_train.csv")
feature_names = X_train.columns.tolist()

# Load your saved model
loaded_model = joblib.load("./src/models/trained_model.joblib")

def predict_model(features):
    
    input_df = pd.DataFrame([features])
    

    input_df = input_df[feature_names]
    
    print("\n--- Formatted Input Data for Model ---")
    print(input_df)
    
    prediction = loaded_model.predict(input_df)
    return prediction

def get_feature_values_manually(feature_names):
    features = {}
    for feature_name in feature_names:
        feature_value = float(input(f"Enter value for {feature_name}: "))
        features[feature_name] = feature_value
    return features

if __name__ == "__main__":

    if len(sys.argv) == 2:
        json_file = sys.argv[1] 
        with open(json_file, 'r') as file:
            features = json.load(file)
    else:
    
        features = get_feature_values_manually(feature_names)

    result = predict_model(features)
    print(f"\n🔮 Prediction Result (0 = Light/No Injury, 1 = Severe Injury): {result[0]}")