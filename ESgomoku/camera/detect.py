import cv2
import time
import numpy as np

import cv2

from numba import jit
from copy import deepcopy

class detect():
    def __init__(self, camera, points=9, outline = 0.4, debug = False, finding_color = 2):
        super().__init__()
        self.debug = debug
        
        self.finding_color = finding_color
        
        self.ds = None
        self.ds_show = None
        self.imsLock = True
        
        self.im_size = 480
        self.unit = unitW = unitH = int(self.im_size/(points+2*outline))
        
        self.point = []
        
        self.color_black = [80,80,80]
        self.color_white = [195,195,195]
        
        self.vis = np.zeros((points,points)).tolist()
        self.count = 0 # numbers of chess now
        
        self.memory = [] # board-changed that founded
        self.confidence = 0.0 # confidence of board changed
        self.conf_trigger = 10 # trigger num of confdence
        
        self.cam = camera
        #self.cam.start()
        
        self.points = points
        self.pos = []
        for x in range(0, points ):
            for y in range(0, points ):
                self.pos.append([int(unitW * (x+outline+0.5)), int(unitH *( y+outline+0.5))])

                # tuple
                self.point.append((int((x+outline+0.5)*self.unit), int((y+outline+0.5)*self.unit)))
    
    def restart(self):
        self.vis = np.zeros((9,9)).tolist()
        
              
    def create(self): # the same to getLoc, but no return / while
        self.imsLock = True
        
        im, d = self.cam.getDst()
        
        gray = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
        d = cv2.GaussianBlur(gray, (9,9),0)
        
        d = cv2.cvtColor(d, cv2.COLOR_GRAY2BGR)

        if self.cam.isboardcorrect:
            cv2.drawContours(im, self.cam.board_corner, -1, (0, 255, 0), 3)
        else:
            cv2.drawContours(im, self.cam.board_corner, -1, (0, 0, 255), 3)
                        
        self.ims = cv2.resize(im,(self.im_size,self.im_size))
        ds = cv2.resize(d,(self.im_size,self.im_size))
        
        color = None
        if self.cam.isboardcorrect:
            color, loc = self.analyze(ds)
        
        cv2.imshow('original', self.ims)
        
        self.ds = ds
        self.ds_show = deepcopy(ds) # copy for future showing
        
        return
    
    #@jit(forceobj = True, parallel = True)    
    def getLoc(self):
        while True:
            self.imsLock = True
                        
            im, d = self.cam.getDst()
            
            gray = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
            d = cv2.GaussianBlur(gray, (9,9),0)
            
            d = cv2.cvtColor(d, cv2.COLOR_GRAY2BGR)

            if self.cam.isboardcorrect:
                cv2.drawContours(im, self.cam.board_corner, -1, (0, 255, 0), 3)
            else:
                cv2.drawContours(im, self.cam.board_corner, -1, (0, 0, 255), 3)
                                
                      
            self.ims = cv2.resize(im,(self.im_size,self.im_size))
            ds = cv2.resize(d,(self.im_size,self.im_size))
            
            color = None
            if self.cam.isboardcorrect:
                color, loc = self.analyze(ds)
            
            cv2.imshow('original', self.ims)
            
            self.ds = ds
            self.ds_show = deepcopy(ds) # copy for future showing
            
                
            if not color is None:
                loc[0], loc[1] = 8-loc[0], loc[1] 
                return color, loc
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
    def analyze(self, dst):
        """取得當前棋盤所有落子位置"""
        black, white, dotList = self.getDot(dst)
        dotChange, color = self.getChange(dotList)
        if color != 0:
            self.count += 1
            disp = dotChange
            print(f'[Detect] Step {self.count}: { {1:"black",2:"white"}.get(color) } {disp}')
            return color, dotChange
        else:
            return None, [-1,-1]
    
    def isChess(self, color):
        def blackTest(i):
            if color[i] < self.color_black[i]:
                return -1
            return 0
        
        def whiteTest(i):
            if color[i] > self.color_white[i]:
                return 1
            return 0
            
        gate = 0
        for i in range(0,3):
            gate += blackTest(i)
            gate += whiteTest(i)
        
        if gate < -2:
            return 1, 0
        elif gate > 2:
            return 0, 1
        else:
            return 0, 0
            
    @jit(forceobj = True, parallel = True)
    def getDot(self, img):
        white = []
        black = []
        vis = []
        
        if not self.ds_show is None:
            for point in self.point:
                self.ds_show = cv2.circle(self.ds_show, point, 8, (0, 0, 255), thickness=-1)
                        
        for x in range(9):
            line = [[],[],[]]
            for y in range(9):
                pos = self.pos[x*9 + y]
                gap = int(self.unit/10)
                color_array = np.array([img[int(pos[0]),int(pos[1])],
                                  img[int(pos[0])+gap,int(pos[1])],
                                  img[int(pos[0]),int(pos[1])+gap],
                                  img[int(pos[0])-gap,int(pos[1])],
                                  img[int(pos[0]),int(pos[1])-gap],
                                  
                                  img[int(pos[0])+gap,int(pos[1])+gap],
                                img[int(pos[0])-gap,int(pos[1])-gap],
                                img[int(pos[0])-gap,int(pos[1])+gap],
                                    img[int(pos[0])+gap,int(pos[1])-gap]])
                color = np.mean(color_array, axis=0).tolist()
                b, w = self.isChess(color)
                line[0].append(b)
                line[1].append(w)
                line[2].append(2*w+b) #> b = 1; w = 2
                
                if not self.ds_show is None:
                    if w == 1:
                        color = [255,255,255]
                        self.ds_show = cv2.circle(self.ds_show, (int(pos[1]),int(pos[0])), 8, (200,200,200), thickness=-1)
                    elif b == 1:
                        color = [0,0,0]
                        self.ds_show = cv2.circle(self.ds_show, (int(pos[1]),int(pos[0])), 8, (30,30,30), thickness=-1)
                    self.ds_show = cv2.circle(self.ds_show, (int(pos[1]),int(pos[0])), 5, (color), thickness=-1)
                
            black.append(line[0])
            white.append(line[1])
            vis.append(line[2])
            
            self.imsLock = False
            
        if not self.ds_show is None:
            cv2.imshow('result', self.ds_show)
        return black, white, vis

    
    def getChange(self, dot = list):
        """return dotChange, changed"""
        find = [0,0]
        find_num = 0
        for x in range(self.points):
            for y in range(self.points):
                if dot[x][y] != self.vis[x][y] and self.vis[x][y] == 0:
                    if dot[x][y] == self.finding_color:
                        find[0] = x
                        find[1] = y
                        find_num += 1
                        color = dot[x][y] # color is 1 or 2
                    
        if find_num == 1:
            if self.memory == find:
                if self.confidence >= self.conf_trigger:
                    # very sure
                    #self.vis = dot
                    x, y = find[0], find[1]
                    self.vis[x][y] = color
                    if self.finding_color == 1:
                        self.finding_color = 2
                        print('debug')
                    else:
                        self.finding_color = 1
                        print('mode')
                    
                    return find, color
                else:
                    # more sure
                    self.confidence += 1
                    return find, 0
            else:
                # change my mind
                self.memory = find
                self.confidence = 0
                return find, 0
        else:
            return find, 0

    def getDst(self):
        if not self.imsLock:
            return self.ims, self.ds
        else:
            return None, None
    
if __name__ == "__main__":
    from camera import camera
    import cv2
    cam = camera(url = 'http://192.168.43.40:4747/mjpegfeed', angle = 180, debug = False)
    
    cam.start()
    det = detect(cam)
    time.sleep(1)
    while True:
        print(det.getLoc())
