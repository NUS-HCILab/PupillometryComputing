import Config
import ReadRawPupilData

if __name__ == '__main__':
    threadPupilDataReader = ReadRawPupilData.DataReadThread(setting='-' + Config.MIDDLELUX + '-' + Config.ONEBACK + '-13')
    threadPupilDataReader.start()

