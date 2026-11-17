import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

class Forecaster:
    def __init__(self, model_path='models/forecaster_model.pkl'):
        self.model = joblib.load(model_path)

    def forecast(self, data):
        # Ensure data is a DataFrame
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        
        # Predict the future values
        predictions = self.model.predict(data)
        
        return predictions

    def train(self, data, labels, model_save_path='models/forecaster_model.pkl'):
        # Ensure data is a DataFrame
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)
        
        # Train the model
        self.model = LinearRegression()
        self.model.fit(data, labels)
        
        # Save the model
        joblib.dump(self.model, model_save_path)
