    
import param



class ObjectifChooser(object):
    def __init__(self, listBeta):

        self.listBeta = listBeta
        self.lastTimeSinceChanging = 0
    
    def getObjectif(self, timeStep):
        self.lastTimeSinceChanging += 1
        if self.lastTimeSinceChanging == 1:
            self.lastTimeSinceChanging = 0
            return self.listBeta[0]
        
        
class ObjectifChooserTest(ObjectifChooser):
    def __init__(self, listBeta):

        self.listBeta = listBeta
        self.lastTimeSinceChanging = 0
    
    def getObjectif(self, timeStep):
        pass
          
        
class ObjectifChooserLearning(ObjectifChooser):
    def __init__(self, listBeta):

        self.listBeta = listBeta
        self.lastTimeSinceChanging = 0
    
    def getObjectif(self, timeStep):
        
        timePeriodeDynamic = param.timePeriodeDynamic
        startDynamic = param.startDynamic
        periode = "D3"
        for timePeriode in timePeriodeDynamic:
            if timeStep < timePeriode:
                periode = timePeriodeDynamic[timePeriode]
                
        if periode == "D1" or periode == "D2":
            return self.listBeta[0]
        elif periode == "D3":
            return self.listBeta[1]
        else:
            return self.listBeta[2]
                
        
        