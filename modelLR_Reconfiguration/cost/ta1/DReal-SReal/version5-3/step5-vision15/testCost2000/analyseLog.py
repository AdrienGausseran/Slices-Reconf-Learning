import matplotlib.pyplot as plt
import numpy as np

f = open("log", "r")
listReward = []
listLoss = []
listLossPerReconf = []
listNbReconf = []
bestReward = (-100000000000000,-1)
bestLoss = (100000000000000,-1)
x = []
number = -1
number2 = 0
loss = 0
reward = -1000
nbReconf = 0
for line in f:
    if line[:3]  == "Ite":
        if number < 0:
            tmp = line.replace("\n","")
            tmp = tmp.split("-")[2]
            tmp.replace(" ","")
            number = int(float(tmp))
            number2 += 1
            x.append(number2)
    elif line[:12] == "        step":
        tmp = line.replace("\n","")
        tmp = tmp.split("= ")
        loss += float(tmp[2])
    elif line[:6] == "Number":
        tmp = line.replace("\n","")
        tmp = tmp.split("ne ")
        nbReconf = float(tmp[1])
    elif line[:6] == "Reward":
        tmp = line.replace("\n","")
        tmp = tmp.split(": ")
        reward = float(tmp[1])
    elif line[:11] == "    Episode":
        tmp = 0
        if nbReconf > 0 :
            tmp = loss/max(1,nbReconf)
        if reward>bestReward[0]:
            bestReward=(reward, number)
        if loss<bestLoss[0]:
            bestLoss=(loss, number)
        print("Instance {} reward {} nbReconf {} loss {} loss/reconf {}".format(number, reward, nbReconf, round(loss,3), round(tmp,3)))
        listReward.append(reward)
        listLoss.append(loss)
        listLossPerReconf.append(tmp)
        listNbReconf.append(nbReconf)
        number = -1
        loss = 0
        reward = -1000
        nbReconf = 0
    elif line[:3] == "Ins":
        tmp = line.replace("\n","")
        tmp = tmp.split(" ")
        number = tmp[1].split("-")
        number = int(float(number[-1]))
        number2 += 1
        x.append(number2)
        nbReconf = float(tmp[7])
        loss = float(tmp[9])
        reward = float(tmp[5])
        if nbReconf > 0 :
            tmp = loss/max(1,nbReconf)
        else:
            tmp = 0
        if reward>bestReward[0]:
            bestReward=(reward, number)
        if loss<bestLoss[0]:
            bestLoss=(loss, number)
        print("Instance {} reward {} nbReconf {} loss {} loss/reconf {}".format(number, reward, nbReconf, round(loss,3), round(tmp,3)))
        listReward.append(reward)
        listLoss.append(loss)
        listLossPerReconf.append(tmp)
        listNbReconf.append(nbReconf)
        number = -1
        loss = 0
        reward = -1000
        nbReconf = 0
        
f.close()

print("Best Reward : Instance {}    {}".format(bestReward[0], bestReward[1]))
print("Best Loss   : Instance {}    {}".format(bestLoss[0], bestLoss[1]))

        
        
fig, axs = plt.subplots(2, 2)
axs[0, 0].plot(x, listReward, 'tab:red')
axs[0, 0].set_title('Reward')
axs[0, 1].plot(x, listNbReconf, 'tab:blue')
axs[0, 1].set_title('NbReconf')
axs[1, 0].plot(x, listLoss, 'tab:orange')
axs[1, 0].set_title('Loss')
plt.show()


