from collections import OrderedDict

integerPath = True

numberOfSlices = {}
numberOfSlices["pdh"] = {"D1" : 10, "D2" : 22,  "D3" : 35, "D4" : 52, "D5" : 60, "Init" : 67}
numberOfSlices["ta1"] = {"D1" : 10, "D2" : 22,  "D3" : 35, "D4" : 52, "D5" : 60, "Init" : 67}



timePeriodeDynamic = {}
startDynamic = 0

#The first periode is fake, it's the initialization one, it last "startDynamic" minutes
timePeriodeDynamicNew = OrderedDict([(0,"D0"), (150,"D3"), (260,"D2"), (320,"D1"), (570,"D2"), (640,"D3"), (720,"D4"), (840,"D5"), (1260,"D4"), (1540,"D3")])
startDynamicNew = 150

timePeriodeDynamicOld = OrderedDict([(250,"D3"), (360,"D2"), (420,"D1"), (670,"D2"), (740,"D3"), (820,"D4"), (940,"D5"), (1360,"D4"), (1640,"D3")])
startDynamicOld = 250



scale_factors = {"D0":3 ,"D1":1,"D2":2.25,"D3":3.5,"D4":5.25,"D5":6}

"""
x = nombre de slices par minute en moyenne
y = nombre de slices par minute en moyenne en periode D1
(250*y) + (2.25*130*y)+(3.5*240*y)+(5.25*400*y)+(6*420*y) = 1440*x
6002.5y = 1440x
y = 0.24x"""
numberOfSlicesPerMinute = 0.24    #This number correspond to the number of slice per minute in period D1 if the AVG for the day is 1 slice per minute
#avgLifeTime = 30    #Average lifetime of a slice before dying (in minutes)
avgLifeTime = 45    #Average lifetime of a slice before dying (in minutes)
nbStepsReconf = 3



nbThreadSub = 8

doReconfGC = True
doReconfILP = False

doAllocWOReconf = True

stableStopGC = True
stableCycle = 15
nbIterationMaxFoCG = 150

verbose = False
checkSolution = False
#IntegralFlow = True


congestionLow = False
congestionMedium = True
congestionHigh = False

timeLimiteILP = 1000
timeLimitReconf = 3

log = None
