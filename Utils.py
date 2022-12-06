import csv
import datetime
import os

import Config


def collectData(right2D, left2D, right3D, left3D, right2DSP, left2DSP, right3DSP, left3DSP, conditions):
    now = datetime.datetime.now()
    conditionString = now.strftime("%d-%m-%H-%M") + conditions
    folderPath = Config.RAW_DATA_PATH + conditionString + '/'
    folderPathPreproData = Config.PREPROCESSED_DATA_PATH + conditionString + '/'

    # Check the existence of the folder. If not, create one.
    if os.path.exists(folderPath) is False:
        os.makedirs(folderPath)
    if os.path.exists(folderPathPreproData) is False:
        os.makedirs(folderPathPreproData)

    write2csv(pupilDataList=right2D, filePath=folderPath + 'right2D_' + str(right2DSP) + 'Hz.csv')
    write2csv(pupilDataList=left2D, filePath=folderPath + 'left2D_' + str(left2DSP) + 'Hz.csv')
    write2csv(pupilDataList=right3D, filePath=folderPath + 'right3D_' + str(right3DSP) + 'Hz.csv')
    write2csv(pupilDataList=left3D, filePath=folderPath + 'left3D_' + str(left3DSP) + 'Hz.csv')


def write2csv(pupilDataList, filePath):
    """
    This function writes 4 kinds of pupil diameter data into a csv file. Then being processed.
    :return:
    """

    # open the file in the write mode
    with open(filePath, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(Config.RAW_DATA_CSV_HEADER)

        for pupilData in pupilDataList:
            # write the data
            data = [pupilData.timestamp, pupilData.confidence, pupilData.X, pupilData.event]
            writer.writerow(data)