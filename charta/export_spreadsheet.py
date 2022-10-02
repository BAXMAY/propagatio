#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Copyright 2022, Baramee Thunyapoo
@Author: Baramee Thunyapoo <baramee1407@gmail.com>
@Date: 2022-May-09
@License: MIT
@Version: 0.1.0
'''

#################################################
#
#   IMPORT LIBRARY
#
#################################################

# Std Library
import datetime
import string
import sys
import logging
import json

# 3rd-Party Library
import toml
import gspread
import numpy

from optparse import OptionParser

#################################################
#
#   GLOBALS
#
#################################################

REQUIRED_ARGUMENT_NUM = 0
CREDENTIAL_FILE_PATH = 'credentials.json'
CONFIG_FILE_PATH = 'config.toml'
# NOTE: Email: mamamia-spread@stat-spreadsheet.iam.gserviceaccount.com
SPREADSHEET_ID = '1AYjSij5M2tdzQleQYxvy_WwfXJbqBNOgKqX6LzJjBDI'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

log = logging.getLogger(__name__)

#################################################
#
#   HELPER FUNCTIONS
#
#################################################

# def range_char(start: str, stop: str) -> tuple[str, ...]:
#   ''' Return tuple of character from @start to @stop
#   '''

#   for number in range(ord(start), ord(stop) + 1):
#         yield(chr(number))

def col2num(col):
  ''' Convert excel column name to number
  '''
  num = 0
  for c in col:
    if c in string.ascii_letters:
      num = num * 26 + (ord(c.upper()) - ord('A')) + 1
  return num

# def getAllSundayInMonth(month: int) -> list:
def getAllSundayInMonth(month: int):
  ''' Return list of datetime object
  '''

  today = datetime.date.today()
  day = datetime.date(today.year, month, 1)
  single_day = datetime.timedelta(days=1)

  sundayList = list()
  while day.month == month:
    if day.weekday() == 6:
      sundayList.append(day)
    day += single_day

  # print( 'Sundays:', sundayList )
  return sundayList

def export_spreadsheet(num_week, month=None, spreadsheet_id=SPREADSHEET_ID, credential_file_path=CREDENTIAL_FILE_PATH, config_file_path=CONFIG_FILE_PATH):
  # Read config file
  configDict = toml.load(config_file_path)

  # Get sheet setting dict
  sheetSettingDict = configDict['common']
  outputMetricDict = configDict['metrics']
  structureDict = configDict['structure']
  month: int = month if month != None else sheetSettingDict['month']

  summarySheetName = sheetSettingDict['summarySheetName']
  # structureNameCol = sheetSettingDict['structureNameCol']
  # leaderNameCol = sheetSettingDict['leaderNameCol']
  weekRangeList = sheetSettingDict['weekRange'][:num_week]
  metricColList = sheetSettingDict['metricColList']
  followUpSheetNameList = sheetSettingDict['followUpSheetNameList'][:num_week]
  followUpDataColumnList = sheetSettingDict['followUpDataColumnList']
  leaderFollowUpDataColumn = sheetSettingDict['leaderFollowUpDataColumn']

  # get all sunday in month
  sundayList = getAllSundayInMonth(month)

  if num_week > len(sundayList):
    log.critical(f'Month {month} has only {len(sundayList)} weeks. but want {num_week} week.')
    return

  # Get credential of service account
  client = gspread.service_account(credential_file_path)
  sheet = client.open_by_key(spreadsheet_id)

  # Get summary worksheet
  summaryWorkSheet = sheet.worksheet(summarySheetName)

  summaryValueListOfList = summaryWorkSheet.get_values()

  structureTypeDict = {
    'RP': ['UN1'],
    'SDL': [],
    'UL': [],
  }
  rawDataDict = dict()

  # Get unprocess data
  for weekRange in weekRangeList:
    start, stop = weekRange.split(':')
    start = col2num(start)
    stop = col2num(stop)

    # print(f'{start}:{stop} => {weekRange}')
    for structureName, infoDict in structureDict.items():
      rowNum = infoDict['summaryRow'] - 1

      rawDataDict.setdefault(structureName, dict())

      for idx, colNum in enumerate(range(start - 1, stop)):
        
        # Too many api call
        # val = summaryWorkSheet.cell(rowNum, colNum).value

        # Use already fetched data
        val = summaryValueListOfList[rowNum][colNum]

        # If no 0 value but only blank string in cell, forcefully set it to zero
        if ( val == "" ):
          print(structureName, ': Could not identify number. change str to zerp.')
          val = 0

        # print(f'{rowNum}:{colNum} => {val}')

        rawDataDict[structureName].setdefault(metricColList[idx], list())
        # care: {S: 2, BT: 1, ATP: 1, ...}
        rawDataDict[structureName][metricColList[idx]].append(int(val))

  # print(rawDataDict)

  outputDict = dict()
  # metrics
  for structureName, infoDict in rawDataDict.items():
    outputDict.setdefault(structureName, dict())
    outputDict[structureName]['Target'] = structureDict[structureName]['target']
    outputDict[structureName]['SBAC'] = numpy.array(infoDict['S']) + numpy.array(infoDict['BT']) + numpy.array(infoDict['ATP']) + numpy.array(infoDict['C'])
    outputDict[structureName]['SBAC'] = outputDict[structureName]['SBAC'].tolist()
    outputDict[structureName]['SBAC+On'] = numpy.array(infoDict['S']) + numpy.array(infoDict['BT']) + numpy.array(infoDict['ATP']) + numpy.array(infoDict['C']) + numpy.array(infoDict['On'])
    outputDict[structureName]['SBAC+On'] = outputDict[structureName]['SBAC+On'].tolist()
    outputDict[structureName]['Care'] = numpy.array(infoDict['Care']).tolist()
    outputDict[structureName]['ผจ.'] = numpy.array(infoDict['ผจ.']).tolist()
    outputDict[structureName]['ผส.'] = numpy.array(infoDict['ผส.']).tolist()
    outputDict[structureName]['1:1'] = list()

  # print(outputDict)

  # follow-up

  # Get all sheet values required
  followUpWorkSheetList = list()
  for followUpSheetName in followUpSheetNameList:
    followUpWorkSheet = sheet.worksheet(followUpSheetName)
    followUpWorkSheet = followUpWorkSheet.get_values()
    followUpWorkSheetList.append(followUpWorkSheet)

  # Calc and save followUp of each structure in week order 
  for structureName, _ in outputDict.items():
    
    structureInfoDict = structureDict[structureName]

    if structureInfoDict['type'] in ['CL', 'RP']:

      followUpRow = structureInfoDict['followUpRow'] - 1

      for idx, followUpWorkSheet in enumerate(followUpWorkSheetList):
        # calculate followUp in a week
        val = 0
        for followUpDataColumn in followUpDataColumnList:

          followUpCol = col2num(followUpDataColumn) - 1

          val += int( followUpWorkSheet[followUpRow][followUpCol] )

        outputDict[structureName]['1:1'].append( val )

  # UL
  for structureName, _ in outputDict.items():
    
    structureInfoDict = structureDict[structureName]

    if structureInfoDict['type'] == 'UL':

      structureTypeDict['UL'].append(structureName)

      careNameList = structureInfoDict['dependencies']

      val = numpy.array(outputDict[careNameList[0]]['1:1'])

      for careName in careNameList[1:]:
        val += numpy.array(outputDict[careName]['1:1'])

      outputDict[structureName]['1:1'] = val.tolist()

  # SDL
  for structureName, _ in outputDict.items():
    
    structureInfoDict = structureDict[structureName]

    if structureInfoDict['type'] == 'SDL':

      structureTypeDict['SDL'].append(structureName)

      followUpRow = structureInfoDict['followUpRow'] - 1

      unitNameList = structureInfoDict['dependencies']

      followUpCol = col2num(leaderFollowUpDataColumn) - 1

      val = None

      for unitName in unitNameList:
        if val is None:
          val = numpy.array(outputDict[unitName]['1:1'])
        else:
          val += numpy.array(outputDict[unitName]['1:1'])

      for idx, followUpWorkSheet in enumerate(followUpWorkSheetList):
        # add leader follow up to val
        val[idx] += int( followUpWorkSheet[followUpRow][followUpCol] )

      outputDict[structureName]['1:1'] = val.tolist()

  # Convert to nivo line chart data format
  graphDataDict = dict()
  for structureName, metricDict in outputDict.items():
    graphDataDict[structureName] = list()

    for metricName, data in metricDict.items():

      dataDict = {'id': metricName}

      dataDict['data'] = list()

      if not isinstance(data, list):
        data = [data] * len(sundayList)

      for idx, sunday in enumerate(sundayList[:num_week]):

        dataDict['data'].append( {
          "x": sunday.strftime("%d-%b-%Y"),
          "y": data[idx]
        } )

      graphDataDict[structureName].append(dataDict)
      
  return json.dumps(graphDataDict)

  # Save to file
  # with open('nivo_data.json', 'w') as json_file:
  #   json.dump(graphDataDict, json_file, indent = 2)

  # with open('structure_data.json', 'w') as json_file:
  #   json.dump(structureTypeDict, json_file, indent = 2)

#################################################
#
#   CLASS DEFINITIONS
#
#################################################

#################################################
#
#   MAIN
#
#################################################

def main():
  ''' Entry Point of The Program
  '''

  parser = OptionParser()

  parser.add_option('-w', '--week',
                    dest = 'num_week',
                    help = 'number of week of the current month',
                    type = 'int',
                    default = 5)
  parser.add_option('-a', '--credentialFile', 
                    dest = 'credential_file_path',
                    help = 'path to credential file location',
                    default = CREDENTIAL_FILE_PATH,
                    metavar = 'FILE')
  parser.add_option('-c', '--configFile', 
                    dest = 'config_file_path',
                    help = 'path to config file location',
                    default = CONFIG_FILE_PATH,
                    metavar = 'FILE')
  parser.add_option('-s', '--spreadsheetId',
                    dest = 'spreadsheet_id',
                    help = 'id of google spreadsheet',
                    default = SPREADSHEET_ID)

  (options, args) = parser.parse_args()

  # Check for require number of arguments
  if len(args) != REQUIRED_ARGUMENT_NUM:
    log.critical(f'Require {REQUIRED_ARGUMENT_NUM} argument(s). But got {len(args)}.')
    sys.exit(-1)

  # Parse options
  credential_file_path = options.credential_file_path
  config_file_path     = options.config_file_path
  spreadsheet_id       = options.spreadsheet_id
  num_week             = options.num_week
  
  export_spreadsheet(num_week, spreadsheet_id, credential_file_path, config_file_path)

if __name__ == '__main__':
  main()


