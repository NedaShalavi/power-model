import os
import time
import sys
import threading as th
import time
import numpy as np
import csv
import sys
import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


#num = int(sys.argv[1])
ginput_size = int(sys.argv[1])
goutput_size = int(sys.argv[2])
batch_size = int(sys.argv[3])
EPOCH = 4 #int(sys.argv[5])
iterations = 30 #int(sys.argv[6])


mutex = th.Lock()
count = 0
board_power = 0
min_power = 1000000
peak_power = 0

class PowerSampler(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = th.Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

def sampler(name):
    global count, board_power, mutex, min_power, peak_power
    mutex.acquire()
    count += 1


    with open("/sys/bus/i2c/drivers/ina3221/7-0040/hwmon/hwmon4/in4_input", 'r') as f:
        tmp = float(f.read())
        board_power += tmp
        min_power = min(min_power, tmp)
        peak_power = max(peak_power, tmp)

    mutex.release()


def reset():
    global count, board_power, min_power, peak_power, mutex
    count = board_power = peak_power =0
    min_power = 1000000











class Net(nn.Module):
    def __init__(self, input_size, output_size):
        super().__init__()
        
        self.fc1 = nn.Linear(input_size, output_size)

    def forward(self, x):
        
        x = F.relu(self.fc1(x))
        
        return x

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

model = Net(input_size=ginput_size, output_size=goutput_size)

model = model.to(device)



criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)






reset()
rt = PowerSampler(0.0001, sampler, "World")





for e in range(EPOCH):
    time1 = []
    time2 = []
    avgp1 = []
    avgp2 = []
    energy1 = []
    energy2 = []
    count1 = []
    count2 = []
    maxp1 = 0
    maxp2 = 0
    minp1 = 1000000
    minp2 = 1000000
    avgpower2 = avgpower1 = 0

    for i in range(30):
        x = np.random.random(size=(batch_size,ginput_size))
        y = np.zeros((batch_size, goutput_size))
        a = np.random.randint(0,goutput_size, size=(batch_size))
        y[ np.arange(batch_size), a] = 1
                
        x = torch.Tensor(x) 
        y = torch.Tensor(y)
        try:
            now1 = time.time()
            rt.start()
            x = x.to(device)
            y = y.to(device)
            rt.stop()
            delay1 = time.time() - now1
            mutex.acquire()
            if count>0:
            	avgpower1 = int(board_power/count)
            #else:
            	#avgpower1 = avgpower2

            count1.append(count)
            maxp1 = max(peak_power, maxp1) 
            minp1 = min(min_power, minp1)
            time1.append(delay1)
            energy1.append(avgpower1 * delay1)
            avgp1.append(avgpower1)
            reset()
            mutex.release()
        except e:
            reset()
            mutex.release()
            print("Exception occured")
        #if count1>0:
        #    avgpower1 = avgpower1 / count1
        #    print("iter: {} -- delau: {} -- avg: {} -- min: {} -- max: {} -- count: {}".format(i, delay1, avgpower1, minP1, maxP1, count1))    


        try:
            now2 = time.time()
            rt.start()

            y_hat = model(x)
            optimizer.zero_grad()
            
            loss = criterion(y_hat, y)        
            
            loss.backward()
            optimizer.step()
            
            rt.stop()
            delay2 = time.time()-now2
            mutex.acquire()
            if count>0:
                avgpower2 = int(board_power/count)
            #else:
                #avgpower2 = avgpower1
            
            count2.append(count)
            time2.append(delay2)
            energy2.append(avgpower2 * delay2)
            avgp2.append(avgpower2)
            
            maxp2 = max(peak_power, maxp2) 
            minp2 = min(min_power, minp2)
            
            reset()
            
            mutex.release()
        except e:
            reset()
            mutex.release()
            print("Exception occured")
    with open(f"num_{num}_input_{ginput_size}_output_{goutput_size}_epoch_{e+1}.txt", "w") as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerows(zip(avgp1,time1,energy1,count1,avgp2,time2,energy2,count2))



