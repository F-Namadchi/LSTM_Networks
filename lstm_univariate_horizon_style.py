# -*- coding: utf-8 -*-
"""LSTM_Univariate_Horizon_Style.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ByLTBNB0vzKvi-l4JJP2YnfTL7WcpbQS
"""

#Import libraries
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn import preprocessing
import matplotlib.pyplot as plt
tf.random.set_seed(123)
np.random.seed(123)

#Import dataset
df = pd.read_csv('Metro_Interstate_Traffic_Volume.csv')
df.head()

df.describe()

df.shape

df['date_time'].nunique()

#Drop duplicate for same hours
df.drop_duplicates(subset=['date_time'], keep=False,inplace=True)

df.shape

"""We hold back ten hours of data (i.e., ten
records), which we can use to validate the data after training on the past
data.
"""

validate = df['traffic_volume'].tail(10)   #Return the last 10 rows
df.drop(df['traffic_volume'].tail(10).index, inplace=True)
uni_data = df['traffic_volume']
uni_data.index = df['date_time']
uni_data.head()

uni_data.shape

"""We rescale the data because neural networks are known to converge
sooner with better accuracy when features are on the same scale
"""

#Data rescaling
uni_data = uni_data.values
scaler_x = preprocessing.MinMaxScaler()
x_rescaled = scaler_x.fit_transform(uni_data.reshape(-1, 1))

"""Define a function to prepare univariate data that is suitable for a time
series.
"""

def custom_ts_univariate_data_prep(dataset, start, end, window, horizon):
    X = []
    y = []
    start = start + window
    if end is None:
       end = len(dataset) - horizon
    for i in range(start, end):
        indicesx = range(i-window, i)
        X.append(np.reshape(dataset[indicesx], (window, 1)))
        indicesy = range(i, i+horizon)
        y.append(dataset[indicesy])
    return np.array(X), np.array(y)

b = range(-48, 0)

univar_hist_window = 48
horizon = 1
TRAIN_SPLIT = 30000
x_train_uni, y_train_uni = custom_ts_univariate_data_prep(x_rescaled, 0, TRAIN_SPLIT,univar_hist_window, horizon)
x_val_uni, y_val_uni = custom_ts_univariate_data_prep(x_rescaled, TRAIN_SPLIT, None,univar_hist_window,horizon)
print ('Single window of past history')
print (x_train_uni[0])
print ('\n Target horizon')
print (y_train_uni[0])

#Prepare the training and validation time-series data using the tf.data
#function, which is a much faster and more efficient way of feeding data to the model.
BATCH_SIZE = 256
BUFFER_SIZE = 150
train_univariate = tf.data.Dataset.from_tensor_slices((x_train_uni, y_train_uni))
train_univariate = train_univariate.cache().shuffle(BUFFER_SIZE).batch(BATCH_SIZE).repeat()
val_univariate = tf.data.Dataset.from_tensor_slices((x_val_uni,y_val_uni))
val_univariate = val_univariate.batch(BATCH_SIZE).repeat()

#The best weights are stored at model_path
model_path = r'\Chapter 6\LSTM_Univarient_1.h5'

#Define the LSTM model
lstm_model = tf.keras.models.Sequential([tf.keras.layers.LSTM(100, 
             input_shape=x_train_uni.shape[-2:],return_sequences=True),
             tf.keras.layers.Dropout(0.2),
             tf.keras.layers.LSTM(units=50,return_sequences=False),
             tf.keras.layers.Dropout(0.2),
             tf.keras.layers.Dense(units=horizon),
             ])
lstm_model.compile(optimizer='adam', loss='mse')

#Configure the model and start training with early stopping and checkpointing.
#Early stopping stops the training when the monitored loss starts to increase above the patience.
#Checkpointing saves the model weights as it reaches the minimum loss.
EVALUATION_INTERVAL = 100
EPOCHS = 150
history = lstm_model.fit(train_univariate, epochs=EPOCHS,steps_per_epoch=EVALUATION_INTERVAL,
                         validation_data=val_univariate,validation_steps=50,verbose =1,
callbacks =[tf.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0, patience=10, verbose=1, mode='min'),
tf.keras.callbacks.ModelCheckpoint(model_path,monitor='val_loss', save_best_only=True, mode='min', verbose=0)])

#Load the best weight into the model
Trained_model = tf.keras.models.load_model(model_path)

#Check the summary
Trained_model.summary()

#Plot the loss and loss_val against the epochs
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train loss', 'validation loss'], loc='upper left')
plt.rcParams["figure.figsize"] = [16,9]
plt.show()

#Forecast the next 10 hours of values
uni = df['traffic_volume']
validatehori = uni.tail(48)
validatehist = validatehori.values
scaler_val = preprocessing.MinMaxScaler()
val_rescaled = scaler_x.fit_transform(validatehist.reshape(-1, 1))
val_rescaled = val_rescaled.reshape((1, val_rescaled.shape[0], 1))
Predicted_results = Trained_model.predict(val_rescaled)
Predicted_results

#Rescale the predicted values back to the original scale
Predicted_inver_res = scaler_x.inverse_transform(Predicted_results)
Predicted_inver_res

#Define the time series evaluation function
from sklearn import metrics
def timeseries_evaluation_metrics_func(y_true, y_pred):
  def mean_absolute_percentage_error(y_true, y_pred):
      y_true, y_pred = np.array(y_true), np.array(y_pred)
      return np.mean(np.abs((y_true - y_pred) / y_true)) * 100
  print('Evaluation metric results:-')
  print(f'MSE is : {metrics.mean_squared_error(y_true,y_pred)}')
  print(f'MAE is : {metrics.mean_absolute_error(y_true,y_pred)}')
  print(f'RMSE is : {np.sqrt(metrics.mean_squared_error(y_true, y_pred))}')
  print(f'MAPE is : {mean_absolute_percentage_error(y_true,y_pred)}')
  print(f'R2 is : {metrics.r2_score(y_true, y_pred)}',end='\n\n')

timeseries_evaluation_metrics_func(validate,Predicted_inver_res[0])

#Plot the actual versus predicted values
plt.plot( list(validate))
plt.plot( list(Predicted_inver_res[0]))
plt.title("Actual vs Predicted")
plt.ylabel("Traffic volume")
plt.legend(('Actual','predicted'))
plt.show()

"""# Bidirectional LSTM"""

Bi_lstm_model = tf.keras.models.Sequential([
tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(100, return_sequences=True), input_shape=x_train_uni.shape[-2:]),
tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(50)),
tf.keras.layers.Dense(20, activation='softmax'),
tf.keras.layers.Dropout(0.2),
tf.keras.layers.Dense(units=1),
])
Bi_lstm_model.compile(optimizer='adam', loss='mse')

#The best weights are stored at model_path
model_path2 = r'\Chapter 6\Bi_directional_LSTM_Univarient_2.h5'

EVALUATION_INTERVAL = 100
EPOCHS = 150
history = Bi_lstm_model.fit(train_univariate, epochs=EPOCHS,steps_per_epoch=EVALUATION_INTERVAL,
                            validation_data=val_univariate, validation_steps=50,verbose =1,
callbacks =[tf.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0, patience=10, verbose=1, mode='min'),
            tf.keras.callbacks.ModelCheckpoint(model_path2, monitor='val_loss', save_best_only=True, mode='min',verbose=0)])

#Load the best weights into the model
Trained_model2 = tf.keras.models.load_model(model_path2)

#Check the model summary
Trained_model.summary()

#Plot the train loss Vs validation loss
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train loss', 'validation loss'], loc='upper left')
plt.rcParams["figure.figsize"] = [16,9]
plt.show()