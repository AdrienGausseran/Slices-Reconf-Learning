import collections
import csv


#Create a csv File to plot
def writeCSV(fileName, listName, listData):
    with open(fileName, 'w') as csvfile:
        fieldnames = listName
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        #If we want to plot list of data
        if isinstance(listData[0],(list)): 
            for i in range(len(listData[0])):
                dictToWrite = collections.OrderedDict()
                for d in range(len(listData)):
                    dictToWrite[listName[d]] = listData[d][i]
                writer.writerow(dictToWrite)
        #If we want to plot values
        else:
            dictToWrite = collections.OrderedDict()
            for d in range(len(listData)):
                dictToWrite[listName[d]] = listData[d]
            writer.writerow(dictToWrite)
            
    csvfile.close()

#Read a csv file
def readCSV(file):
    result = {}
    with open(file, 'r') as csvFile:
        reader = csv.reader(csvFile)
        listName = next(reader)
        for key in listName:
            result[key] = []
        for row in reader:
            for i in range(len(row)):
                result[listName[i]].append(float(row[i]))
    csvFile.close()
    return result
