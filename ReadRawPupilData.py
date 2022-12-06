import math, pywt, numpy as np
import csv
import sys
import os
import xml.etree.ElementTree

from datetime import datetime

import zmq
from msgpack import loads

import time
from threading import Thread
from queue import Queue

import keyboard
import datetime

from socket import *
import Config, Utils
import json

"""
To use this established data processing file, simply plug the pupil core onto a laptop/PC and run the "pupil capture.exe" on it.
This data read socket is for demonstrating things in real time.

The pupil data consists of 4 parts: eye index 0/1 * 2D/3D Model. The 2D/3D model are derived from 1 data (because their timestamp is identical).
While the eye index 0/1 are not derived concurrently, but the time gap is quite small (say 0.0004s), which could be approximated as collected concurrently.
The official file said the eye tracker's sampling frequency could be 200Hz. However, data sampling could not reach to the maximum value soon. It takes time.
So when dealing with data, eliminate data in the first few seconds, the sampling rate is not right in that periods. 
"""


host = '255.255.255.255'
port = 50000    # Randomly choose a portal.

confidenceThreshold = .2
windowLengthSeconds = 5
maxSamplingRate = 120    # Changed to 60Hz due to our hardware limitations.
minSamplesPerWindow = maxSamplingRate * windowLengthSeconds
# wavelet = 'sym8'
wavelet = 'sym16'

MODE_2D = '2d c++'
MODE_3D = 'pye3d 0.3.0 real-time'
INDEX_EYE_0 = 0
INDEX_EYE_1 = 1

global threadRunning, right2DPupilDia, left2DPupilDia, right3DPupilDia, left3DPupilDia, \
    aveSamplRateRight2D, aveSamplRateLeft2D, aveSamplRateRight3D, aveSamplRateLeft3D, \
    conditions


class ProcessingThread(Thread):
    def __init__(self, I0pupilData, I1pupilData, targetSocket):
        Thread.__init__(self)
        self.I0data = I0pupilData
        self.I1data = I1pupilData
        self.targetSocket = targetSocket

    def run(self):
        global threadRunning
        processData(self.I0data, self.I1data, self.targetSocket)
        threadRunning = False


class PupilData(float):
    def __init__(self, dia):
        self.X = dia
        self.timestamp = 0
        self.confidence = 0
        self.event = Config.EVENT_DEFAULT


def createSendSocket():
    backlog = 5
    size = 1024
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    return sock


def createPupilConnection():
    context = zmq.Context()
    # open a req port to talk to pupil
    addr = '127.0.0.1'  # remote ip or localhost
    req_port = "50020"  # same as in the pupil remote gui
    req = context.socket(zmq.REQ)
    req.connect("tcp://{}:{}".format(addr, req_port))
    # ask for the sub port
    req.send_string('SUB_PORT')
    sub_port = req.recv_string()

    # open a sub port to listen to pupil
    sub = context.socket(zmq.SUB)
    sub.connect("tcp://{}:{}".format(addr, sub_port))

    sub.setsockopt_string(zmq.SUBSCRIBE, 'pupil.')  # See Pupil Lab website, don't need to change here. "Pupil Datum Format": https://docs.pupil-labs.com/developer/core/overview/.

    return sub


def cleanup(old_data):
    stddev = np.std(old_data)
    mean = np.mean(old_data)

    filtered = []
    runner = 0.0

    for i in range(len(old_data)):
        currentData = PupilData(old_data[i].X)
        currentData.timestamp = old_data[i].timestamp
        distanceToMean = abs(currentData.X - mean)

        if distanceToMean < stddev * 2:
            filtered.append(currentData)
            runner += 1

    # print(str(stddev) + " / " + str(mean) + ' / ' + str(len(filtered)))

    return filtered


def cleanBlinks(data):
    blinks = []

    minNumForBlinks = 2
    numSamples = len(data)
    i = 0
    minConfidence = .25

    while i < numSamples:
        if data[i].confidence < minConfidence and i < numSamples - 1:
            runner = 1
            nextData = data[i + runner]
            while nextData.confidence < minConfidence:
                runner = runner + 1

                if i + runner >= numSamples:
                    break

                nextData = data[i + runner]

            if runner >= minNumForBlinks:
                blinks.append((i, runner))

            i = i + runner
        else:
            i = i + 1

    durationsSampleRemoveMS = 200
    numSamplesRemove = int(math.ceil(120 / (1000 / durationsSampleRemoveMS)))

    blinkMarkers = np.ones(numSamples)
    for i in range(len(blinks)):
        blinkIndex = blinks[i][0]
        blinkLength = blinks[i][1]

        for j in range(0, blinkLength):
            blinkMarkers[blinkIndex + j] = 0

        for j in range(0, numSamplesRemove):
            decrementIndex = blinkIndex - j
            incrementIndex = blinkIndex + blinkLength + j

            if decrementIndex >= 0:
                blinkMarkers[decrementIndex] = 0

            if incrementIndex < numSamples:
                blinkMarkers[incrementIndex] = 0

    newSamplesList = []

    for i in range(0, numSamples):
        if blinkMarkers[i] == 1:
            newSamplesList.append(data[i])

    return newSamplesList


def fixTimestamp(data):
    runner = 0.0
    for i in range(len(data)):
        data[i].timestamp = runner / 120.0
        runner += 1


def processData(I0data, I1data, socket):
    blinkedRemovedI0 = cleanBlinks(I0data)
    cleanedI0Data = cleanup(blinkedRemovedI0)
    fixTimestamp(cleanedI0Data)

    blinkedRemovedI1 = cleanBlinks(I1data)
    cleanedI1Data = cleanup(blinkedRemovedI1)
    fixTimestamp(cleanedI1Data)

    print('Eye 0: ' + str(datetime.datetime.now()) + ' ' + str(len(cleanedI0Data)) + ' / ' + str(
        len(I0data)) + ' samples')
    print(str(cleanedI0Data))
    print('Eye 1: ' + str(datetime.datetime.now()) + ' ' + str(len(cleanedI1Data)) + ' / ' + str(
        len(I1data)) + ' samples')
    print(str(cleanedI1Data))
    # socket.sendto(str.encode(str(round(averagedCurrentIPA, 3))), (host, port))    # TODO: resume this part later.


def receivePupilData(udp, pupilSocket):     # The "udp" is for "user datagram protocol".
    try:
        # Variable initialization:
        currentEvent = Config.EVENT_DEFAULT
        startTime = time.time()
        while True:
            topic = pupilSocket.recv_string()
            msg = pupilSocket.recv()
            # msg = loads(msg, encoding='utf-8')
            msg = loads(msg, raw=False)
            # print("\n{}: {}".format(topic, msg))

            global threadRunning
            method = msg['method']
            idEye = msg['id']

            if method == MODE_2D:   # Only using the 2D model to get the pupil diameter.
                if idEye == INDEX_EYE_0:
                    I0data = PupilData(msg['diameter'])  # Collect the 2-D pixel data.
                    I0data.timestamp = msg['timestamp']
                    I0data.confidence = msg['confidence']
                    I0data.event = currentEvent
                    right2DPupilDia.append(I0data)
                elif idEye == INDEX_EYE_1:
                    I1data = PupilData(msg['diameter'])  # Collect the 2-D pixel data.
                    I1data.timestamp = msg['timestamp']
                    I1data.confidence = msg['confidence']
                    I1data.event = currentEvent
                    left2DPupilDia.append(I1data)

            elif method == MODE_3D:   # Only using the 3D model to get the pupil diameter.
                if idEye == INDEX_EYE_0:
                    I0data = PupilData(msg['diameter_3d'])    # Calculate the 3-D mm model data.  Sometimes lacks this data.
                    I0data.timestamp = msg['timestamp']
                    I0data.confidence = msg['confidence']
                    I0data.event = currentEvent
                    right3DPupilDia.append(I0data)
                elif idEye == INDEX_EYE_1:
                    I1data = PupilData(msg['diameter_3d'])  # Calculate the 3-D mm model data.  Sometimes lacks this data.
                    I1data.timestamp = msg['timestamp']
                    I1data.confidence = msg['confidence']
                    I1data.event = currentEvent
                    left3DPupilDia.append(I1data)

            # # Calculate and send out the ipa data. TODO: we don't process data here, in the data collection section.
            # while len(currentI0PupilData) > minSamplesPerWindow:
            #     currentI0PupilData.pop(0)     # Remove the first element in the list.
            # while len(currentI1PupilData) > minSamplesPerWindow:
            #     currentI1PupilData.pop(0)  # Remove the first element in the list.
            #
            # if len(currentI0PupilData) == minSamplesPerWindow and len(currentI1PupilData) == minSamplesPerWindow and threadRunning is False:     # Wait for reaching 1-minute's windows length; enough data points.
            #     threadRunning = True
            #     processingThread = ProcessingThread(list(currentI0PupilData), list(currentI1PupilData), udp)    # Iteratively apply and start threads. TODO: make a new thread cope 2 pupils.
            #     processingThread.start()

            if keyboard.is_pressed('esc'):
                global aveSamplRateRight2D, aveSamplRateLeft2D, aveSamplRateRight3D, aveSamplRateLeft3D
                endTime = time.time()
                elapsTime = endTime - startTime     # The unit should be "second"

                aveSamplRateRight2D = int(len(right2DPupilDia) / elapsTime)
                aveSamplRateLeft2D = int(len(left2DPupilDia) / elapsTime)
                aveSamplRateRight3D = int(len(right3DPupilDia) / elapsTime)
                aveSamplRateLeft3D = int(len(left3DPupilDia) / elapsTime)
                print("\nEnd the data read procedure!\n")
                break
            elif keyboard.is_pressed(Config.KEY_SITTING):
                currentEvent = Config.EVENT_SITTING
                print('\nEvent changed to SITTING...\n')
            elif keyboard.is_pressed(Config.KEY_WALKING):
                currentEvent = Config.EVENT_WALKING
                print('\nEvent changed to WALKING...\n')
            elif keyboard.is_pressed(Config.KEY_READING_SITTING):
                currentEvent = Config.EVENT_READING_SITTING
                print('\nEvent changed to READING ANSWRGD SITTING...\n')
            elif keyboard.is_pressed(Config.KEY_READING_WALKING):
                currentEvent = Config.EVENT_READING_WALKING
                print('\nEvent changed to READING AND WALKING...\n')
    except KeyboardInterrupt:
        pass


def runPupilReader():
    global threadRunning, right2DPupilDia, left2DPupilDia, right3DPupilDia, left3DPupilDia, \
        aveSamplRateRight2D, aveSamplRateLeft2D, aveSamplRateRight3D, aveSamplRateLeft3D, \
        conditions

    threadRunning = False
    right2DPupilDia = list()      # Added to apply 2 pupil analysis.
    left2DPupilDia = list()      # Distinguish between 2D and 3D model.
    right3DPupilDia = list()
    left3DPupilDia = list()

    print(datetime.datetime.now())
    socket = createSendSocket()
    pupilSocket = createPupilConnection()  # Subscribe pupil data "Pupil Datum Format".

    receivePupilData(socket, pupilSocket)
    Utils.collectData(right2D=right2DPupilDia,
                      left2D=left2DPupilDia,
                      right3D=right3DPupilDia,
                      left3D=left3DPupilDia,
                      right2DSP=aveSamplRateRight2D,
                      left2DSP=aveSamplRateLeft2D,
                      right3DSP=aveSamplRateRight3D,
                      left3DSP=aveSamplRateLeft3D,
                      conditions=conditions)
    print('\nWrite to local csv done...... End of the raw data collection session\n')


class DataReadThread(Thread):
    def __init__(self, setting):
        Thread.__init__(self)
        global conditions
        conditions = setting

    def run(self):
        runPupilReader()
