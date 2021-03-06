from flask import Flask , jsonify, request, send_file, render_template, send_from_directory
from flask_cors import CORS
from predictor import *
from imgUtil import *
import random
import json
import pandas as pd
import numpy as np
import csv
from tensorflow.keras import models
import time
import datetime
import cv2
import sys, getopt
import os

global model, sess, graph
model, sess, graph = init()

testJson = json.dumps({"drawing":{"0":"[[[17, 174, 252, 255, 250, 250, 248, 244, 176, 136, 40, 15, 6, 3, 0, 5, 11], [4, 24, 25, 30, 48, 78, 92, 95, 92, 86, 86, 82, 79, 74, 15, 2, 0]], [[243, 243, 238, 219, 203, 17, 11, 3, 0, 0, 6, 10], [96, 157, 164, 154, 152, 156, 147, 143, 132, 94, 75, 75]], [[242, 229, 227, 215, 198, 179, 89, 42, 2, 0, 9, 12, 19], [165, 210, 214, 221, 220, 213, 213, 206, 204, 196, 177, 141, 136]], [[126, 120, 120, 132, 132, 123], [185, 192, 198, 197, 183, 183]]]"}})

print("if there is a dresser printed below, means the model works")
with graph.as_default():
    print(categories[perpareJSONDataAndPredict(model, testJson)[0]])

end = dt.datetime.now()
print('{}, server initialized in .\nTotal time {}s'.format(end, (end - start).seconds))

app = Flask(__name__)
CORS(app)
https = False;
devMode = False;
# SSLify(app)

def parseArgs(argv):
    global https, devMode
    try:
        opts, args = getopt.getopt(argv,"sdh",["https", "dev", "help"])
    except getopt.GetoptError:
        print('no arguments, https = False')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print("-s --https run on https and port 1337, otherwise run on http and port 5800")
            print("-d --dev   debuger on")
            sys.exit()
        elif opt in ("-s", "--https"):
            https = True
            print('enable https')
        elif opt in ("-d", "--dev"):
            devMode = True
            print('enable debuger')

pathToCert = "/etc/letsencrypt/live/point99.xyz/cert.pem"
pathToKey = "/etc/letsencrypt/live/point99.xyz/privkey.pem"
pathToItemData = "./data/ItemsAndTags.csv"
pathToSprites = "./doodleSprites/"
pathToPuzzleData = "./data/PuzzleAndSolvers_"
@app.route("/api/getItemData", methods=["GET"])
def getItemDataAPI():
    r = {"items": []}
    with open(pathToItemData) as csvData:
        reader = csv.DictReader(csvData)
        for row in reader:
            r["items"].append(row)
            r["items"].sort(key = lambda e: int(e["Id"]) )
    return jsonify(r)

@app.route("/api/getPuzzleData", methods=["GET"])
def getPuzzleDataAPI():
    id = request.values['id']
    path = pathToPuzzleData + str(id) +".csv"
    r = {"Id": id, "Solvers":[]}
    with open(path) as csvData:
        reader = csv.DictReader(csvData)
        for row in reader:
            if row["Result"] is not "":
                r["Solvers"].append(row)
                r["Solvers"].sort(key = lambda e: int(e["Id"]) )
    return jsonify(r)

@app.route("/api/doodlePredict", methods=["POST"])
def predictAPI():
    global model, graph
    # print("get a is the request: ", request.form.to_dict())
    print("get a predicting request: ")
    image_raw = request.form.to_dict()["data"]
    image_raw = stringToRGB(image_raw)
    image = prepareImage(image_raw)
    response = {'prediction':{
    'numbers':[],
    'names':[]
    }}
    with sess.as_default():
        with graph.as_default():
            response['prediction']['numbers'] = prepareImageAndPredict(model, image).tolist()
    for i in range(len(response['prediction']['numbers'])):
        response['prediction']['names'].append(categories[response['prediction']['numbers'][i]])
    print("this is the response: ", response['prediction']['names'])
    cv2.imwrite("./doodleHistory/"+ ', '.join(response['prediction']['names']) +", "+datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y") +".jpg", image_raw)
    return jsonify(response)

@app.route("/api/askForSprite", methods=["POST"])
def processSprite():
    start = dt.datetime.now()
    global model, graph
    image_raw = stringToRGB(request.form.to_dict()["data"])
    image = prepareImage(image_raw)
    res = {'fileName':''}
    prediction = {'prediction':{
    'numbers':[],
    'names':[]
    }}
    with sess.as_default():
        with graph.as_default():
            prediction['prediction']['numbers'] = prepareImageAndPredict(model, image).tolist()
    for i in range(len(prediction['prediction']['numbers'])):
        prediction['prediction']['names'].append(categories[prediction['prediction']['numbers'][i]])
    rgba = getRGBAimg(image_raw)
    fileName = ', '.join(prediction['prediction']['names']) +", "+datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y") +".png"
    print("this is the fileName: ", fileName)
    cv2.imwrite(pathToSprites+ fileName, rgba)
    res['fileName'] = fileName
    end = dt.datetime.now()
    print('prepareda sprite\nTotal time {}s'.format((end - start).microseconds/1000000))
    return jsonify(res)

@app.route("/api/downloadSprite", methods=["GET"])
def returnSprite():
    print(request.values['fileName'])
    filePath = pathToSprites + request.values['fileName']
    return send_file(filePath, mimetype='image/png')


@app.route("/api/test", methods=["GET"])
def testServer():
    return "working"


@app.route("/doodles", methods=["GET"])
def sendGallery():
    doodlePath = "./doodleHistory"
    if request.args.get('startAt') is None:
        i = 0
    else: i = request.values['startAt']
    image_names = [f for f in os.listdir(doodlePath) if not f.startswith('.')]
    os.chdir(doodlePath)
    image_names.sort(key=os.path.getmtime, reverse = True)
    os.chdir("..")
    image_names = image_names[i: i+40]
    return render_template("doodles.html", image_names = image_names)

@app.route('/upload/<filename>')
def send_image(filename):
    return send_from_directory("./doodleHistory", filename)
    # return filename

if __name__ == "__main__":

    parseArgs(sys.argv[1:])

    if https:
        app.run(host = "0.0.0.0",port = 1337, ssl_context=(pathToCert,pathToKey), debug = devMode, threaded=True)
    else :
        print("devmode =", devMode)
        app.run(host = "0.0.0.0", port = 5800, debug = devMode, threaded=True)
