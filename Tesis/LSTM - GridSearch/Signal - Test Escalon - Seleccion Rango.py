from __future__ import print_function
import pandas as pd
import numpy
import matplotlib.pyplot as plt
from keras import Sequential
from keras.models import load_model, Model
from keras.layers import Dense, Activation, Dropout, Input, LSTM, Reshape, Lambda, RepeatVector
from keras.initializers import glorot_uniform
from keras.utils import to_categorical
from keras.optimizers import Adam
from keras import backend as K
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from pandas import DataFrame
from pandas.plotting import table
from math import sqrt, log, exp
from joblib import Parallel, delayed
import tensorflow as tf
import gc
from statistics import mean,stdev
from functools import reduce
from scipy import stats
import plotly.plotly as py
import plotly.graph_objs as go
import plotly
from numpy.random import seed
from tensorflow import set_random_seed
import os


def create_dataset(nombre_sujeto, nombre_postura):
    PATH_sujetos = ("C:/Users/Luis.O.A/Documents/USACH/Tesis/Dataset/Sujetos/Muestreo 0.4/%s/%s-%s-VE.csv"%(nombre_sujeto, nombre_sujeto, nombre_postura))
    PATH_escalon = ("C:/Users/Luis.O.A/Documents/USACH/Tesis/Dataset/esc_04.csv")
    X = pd.read_csv(PATH_sujetos, sep="	")
    data_escalon = pd.read_csv(PATH_escalon)
    
    # normalize the dataset
    scaler_VFSCd = MinMaxScaler(feature_range=(-1, 1))
    scaler_VFSCi = MinMaxScaler(feature_range=(-1, 1))
    scaler_PAMn = MinMaxScaler(feature_range=(-1, 1))
    scaler_escalon = MinMaxScaler(feature_range=(-1, 1))
    
    VFSCd = scaler_VFSCd.fit_transform(X.VFSCd.values.reshape((len(X.VFSCd.values), 1)))
    VFSCi = scaler_VFSCi.fit_transform(X.VFSCi.values.reshape((len(X.VFSCi.values), 1)))
    PAMn = scaler_PAMn.fit_transform(X.PAMn.values.reshape((len(X.PAMn.values), 1)))
    Escalon = scaler_escalon.fit_transform(data_escalon.ESCALON.values.reshape((len(data_escalon.ESCALON.values), 1)))
    
    #Dar formato float a las señales
    PAMn, VFSCd, VFSCi, Escalon = PAMn.astype('float32'), VFSCd.astype('float32'), VFSCi.astype('float32'), Escalon.astype('float32')
    PAMn, VFSCd, VFSCi, Escalon = numpy.array(PAMn), numpy.array(VFSCd), numpy.array(VFSCi), numpy.array(Escalon)
    
    # Validacion Valanceada
    train_size = int(len(PAMn) * 0.5)
    train_PAM, train_VFSCd, train_VFSCi = PAMn[0:train_size], VFSCd[0:train_size], VFSCi[0:train_size]
    test_PAM, test_VFSCd, test_VFSCi = PAMn[train_size:len(PAMn)], VFSCd[train_size:len(VFSCd)], VFSCi[train_size:len(VFSCi)]
    
    # Reshape segun el formato que acepta Keras
    # reshape input to be [samples, time steps, features]
    train_PAM = numpy.reshape(train_PAM, (train_PAM.shape[0], 1, train_PAM.shape[1]))
    test_PAM = numpy.reshape(test_PAM, (test_PAM.shape[0], 1, test_PAM.shape[1]))
    Escalon = numpy.reshape(Escalon, (Escalon.shape[0], 1, Escalon.shape[1]))
    
    return train_PAM, train_VFSCd, train_VFSCi, test_PAM, test_VFSCd, test_VFSCi, Escalon, scaler_VFSCd, scaler_VFSCi, scaler_escalon


# fit an LSTM network to training data
def fit_lstm(trainX, trainY, batch_size, epochs, optimization, activation, hidden_layers, neurons, dropout):
    
    ret_seq = False
    if hidden_layers > 1:
        ret_seq = True

    model = Sequential()
    model.add(LSTM(neurons, batch_input_shape=(batch_size, trainX.shape[1], trainX.shape[2]), return_sequences=ret_seq, stateful=True, dropout=dropout))
    for i in range (hidden_layers-1):
        if i == (hidden_layers-2):
            ret_seq = False
        model.add(LSTM(neurons, return_sequences=ret_seq, stateful = True, dropout=dropout))
    model.add(Dense(trainY.shape[1], activation=activation))

    model.compile(loss='mean_squared_error', optimizer=optimization)
    
    model.fit(trainX, trainY, epochs=epochs, batch_size=batch_size, verbose=0, shuffle=False)
    
    return model

#Evaluate the Model
def evaluate(model, X, Y, batch_size):

    output = model.predict(X, batch_size=batch_size)
    
    # invert data transforms on forecast
    # report performance
    rmse = stats.pearsonr(Y[:,0], output[:,0])
    
    return rmse[0], output

    #Evaluate the Model
def evaluate_stair(model, Escalon, batch_size):

    output = model.predict(Escalon, batch_size=batch_size)
    
    return output

# run a repeated experiment
def experiment(trainX, trainY, testX, testY, repeats, batch_size, epochs, optimization, activation, hidden_layers, neurons, dropout):
    # run experiment

    # fit the model
    lstm_model = fit_lstm(trainX, trainY, batch_size, epochs, optimization, activation, hidden_layers, neurons, dropout)
    # report performance
    r, output = evaluate(lstm_model, testX, testY, batch_size)

    K.clear_session()
    del lstm_model
    gc.collect()
    print('epochs=%d, dropout=%.1f, activation=%s, optimization=%s neurons=%d, batch_size=%d, hidden_layers=%d:::::::::: RESULT=%.3f' % (epochs, dropout, activation, optimization, neurons, batch_size, hidden_layers, r))
    return r

def run_experiment(trainX, trainY, testX, testY, batch_size=[1], epochs=[10], optimization=["Adam"], activation=["linear"], hidden_layers=[3], neurons=[10], dropout=[1.0]):
    
    columnas = ['epochs','dropout','activation','optimization','neurons','batch_size','hidden_layers','RESULT']
    filas = len(batch_size) * len(epochs) * len(optimization) * len(activation) * len(hidden_layers) * len(neurons) * len(dropout)
    results = numpy.chararray((filas,8), itemsize=20)
    row = 0
    repeats = 1
    
    for b in batch_size:
        for e in epochs:
            for o in optimization:
                for a in activation:
                    for h in hidden_layers:
                        for n in neurons:
                            for d in dropout:
                                result = experiment(trainX, trainY, testX, testY, repeats, b, e, o, a, h, n, d)
                                results[row][0] = e
                                results[row][1] = d
                                results[row][2] = a
                                results[row][3] = o
                                results[row][4] = n
                                results[row][5] = b
                                results[row][6] = h
                                results[row][7] = result

                                row = row + 1
    
    df = pd.DataFrame(results, columns=columnas)
    df = df.sort_values(by='RESULT', ascending=False)

    return df

def best_model(df_1, df_2, ruta_archivo):

    balance_extencion = "_1.csv"
    best_balance = 1
    max_df_1 = float(df_1.iat[0,7])
    max_df_2 = float(df_2.iat[0,7])

    df = df_1
    if(max_df_1<max_df_2):
        df = df_2
        best_balance = 2
        balance_extencion = "_2.csv"


    print('++++++++++++++++++++++++++++++++++++++ Mejor Balance: ')
    print(df)
    writer = pd.ExcelWriter(ruta_archivo+balance_extencion)
    df.to_excel(writer,'Resultados')
    writer.save()
    print('################################################################################### Archivo |||'+ruta_archivo+'||| Creado')

    return df, best_balance


def plotting(r, pam, output, scaler_VFSC, scaler_escalon):

    re_pam = numpy.reshape(pam, (pam.shape[0], 1))
    re_output = numpy.reshape(output, (output.shape[0], 1))

    plotly.tools.set_credentials_file(username='luis.orellana777', api_key='pCEXLd20Nqi47WlLGYGk')

    trace_high = go.Scatter(
                    x=list(range(1, len(re_pam))),
                    y=scaler_escalon.inverse_transform(re_pam),
                    name = "PAM",
                    line = dict(color = '#17BECF'),
                    opacity = 0.8)

    trace_low = go.Scatter(
                    x=list(range(1, len(re_output))),
                    y=scaler_VFSC.inverse_transform(output),
                    name = "VFSC Respuesta Escalon",
                    line = dict(color = '#7F7F7F'),
                    opacity = 0.8)

    data = [trace_high,trace_low]

    layout = dict(
        title = "LSTM VFSC",
        xaxis = dict(
            range = [1, len(re_output)])
    )

    fig = dict(data=data, layout=layout)
    py.plot(fig, filename = "LSTM VFSC")


def apply_stair(df, trainX, trainY, Escalon, scaler_VFSC, scaler_escalon):

    for row in range(df.shape[0]):#Cantidad de registros en el dataframe resultados
        batch_size = int(df.iat[row,6])
        epochs = int(df.iat[row,1])
        optimization = df.iat[row,4]
        activation = df.iat[row,3]
        hidden_layers = int(df.iat[row,7])
        neurons = int(df.iat[row,5])
        #dropout = float(df.iat[row,2])
        result_r = float(df.iat[row,8])

        for dropout in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            lstm_model = fit_lstm(trainX, trainY, batch_size, epochs, optimization, activation, hidden_layers, neurons, dropout)

            output = evaluate_stair(lstm_model, Escalon, batch_size)

            plotting(result_r, trainY, output, scaler_VFSC, scaler_escalon)

            K.clear_session()
            del lstm_model
            gc.collect()

            seguir = input("dropout=%.1f \nSeguir si(1) no(0):"%dropout)
            if seguir == "0":
                break

        seguir = input("Seguir si(1) no(0):")
        if seguir == "0":
            break

def run (sujeto, postura):
    print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
    
    ruta_archivo = 'C:/Users/Luis.O.A/Documents/USACH/Tesis/Resultados_Escalon/'+sujeto+'_'+postura+'_Derecho'

    exists_1 = os.path.isfile(ruta_archivo+"_1.csv")
    exists_2 = os.path.isfile(ruta_archivo+"_2.csv")

    train_PAM, train_VFSCd, train_VFSCi, test_PAM, test_VFSCd, test_VFSCi, Escalon, scaler_VFSCd, scaler_VFSCi, scaler_escalon = create_dataset(sujeto, postura)

    
    neurons = [6,8]#[6,8,10,12,14,16,18,20,22,24,26]

    batch_size = []
    for i in range(1,train_PAM.shape[0]+1):
        if (train_PAM.shape[0]%i)==0:
            batch_size.append(i)

    best_balance = 0
    
    if exists_1 == False and exists_2 == False:
        ################################################################################### Balance 1
        print('++++++++++++++++++++++++++++++++++++++ Sujeto: ' + sujeto + ' Posicion: ' + postura + ' Balance: 1, Emisferio: Derecho')

        df_1 = run_experiment(train_PAM, train_VFSCd, test_PAM, test_VFSCd, batch_size=batch_size, neurons=neurons)

        ################################################################################### Balance 2
        print('++++++++++++++++++++++++++++++++++++++ Sujeto: ' + sujeto + ' Posicion: ' + postura + ' Balance: 2, Emisferio: Derecho')

        df_2 = run_experiment(test_PAM, test_VFSCd, train_PAM, train_VFSCd, batch_size=batch_size, neurons=neurons)

        df, best_balance = best_model(df_1, df_2, ruta_archivo)

    ########################################################################################## ENTRENAR MODELO A PARTIR DE "df" Y GRAFICAR RESPUESTA  ESCALON
    if best_balance == 1 or exists_1 == True:

        df = pd.read_csv('C:/Users/Luis.O.A/Documents/USACH/Tesis/Resultados_Escalon/AC_ACOSTADO_Derecho_1.csv')

        apply_stair(df, train_PAM, train_VFSCd, Escalon, scaler_VFSCd, scaler_escalon)

    elif best_balance == 2 or exists_2 == True:

        df = pd.read_csv('C:/Users/Luis.O.A/Documents/USACH/Tesis/Resultados_Escalon/AC_ACOSTADO_Derecho_2.csv')

        apply_stair(df, test_PAM, test_VFSCd, Escalon, scaler_VFSCd, scaler_escalon)
    ################################################################################### Balance 1
    
    ruta_archivo = 'C:/Users/Luis.O.A/Documents/USACH/Tesis/Resultados_Escalon/'+sujeto+'_'+postura+'_Izquierdo'

    exists_1 = os.path.isfile(ruta_archivo+"_1.csv")
    exists_2 = os.path.isfile(ruta_archivo+"_2.csv")
    
    print('++++++++++++++++++++++++++++++++++++++ Sujeto: ' + sujeto + ' Posicion: ' + postura + ' Balance: 1, Emisferio: Izquierdo')

    if exists_1 == False and exists_2 == False:
        df_1 = run_experiment(train_PAM, train_VFSCi, test_PAM, test_VFSCi, batch_size=batch_size, neurons=neurons)

        ################################################################################### Balance 2
        print('++++++++++++++++++++++++++++++++++++++ Sujeto: ' + sujeto + ' Posicion: ' + postura + ' Balance: 2, Emisferio: Izquierdo')

        df_2 = run_experiment(test_PAM, test_VFSCi, train_PAM, train_VFSCi, batch_size=batch_size, neurons=neurons)

        df, best_balance = best_model(df_1, df_2, ruta_archivo)

    ########################################################################################## ENTRENAR MODELO A PARTIR DE "df" Y GRAFICAR RESPUESTA  ESCALON

    if best_balance == 1 or exists_1 == True:

        df = pd.read_csv('C:/Users/Luis.O.A/Documents/USACH/Tesis/Resultados_Escalon/AC_ACOSTADO_Derecho_1.csv')

        apply_stair(df, train_PAM, train_VFSCi, Escalon, scaler_VFSCi, scaler_escalon)

    elif best_balance == 2 or exists_2 == True:

        df = pd.read_csv('C:/Users/Luis.O.A/Documents/USACH/Tesis/Resultados_Escalon/AC_ACOSTADO_Derecho_2.csv')

        apply_stair(df, test_PAM, test_VFSCi, Escalon, scaler_VFSCi, scaler_escalon)




#Repitable Experiment
seed(1)
set_random_seed(2)

run(sujeto='AC', postura='ACOSTADO')