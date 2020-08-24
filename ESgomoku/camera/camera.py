import cv2
import numpy as np
import time
import threading

class camera(threading.Thread):
    def __init__(self, url='http://127.0.0.1:4747/mjpegfeed', angle = 0, debug = False, daemon=True):
        super().__init__()
        
        self.debug = debug
        
        self.pict_size = 480
        self.w = 480
        self.h = 640
        
        if not self.debug:
            # 開啟網路攝影機
            self.cam = cv2.VideoCapture(url)
        
        self.angle = angle

        self.kernel_size = 5
        
        self.border = 0  # resize border px
        self.BoardArea = 0 # founded board area (overrided) 

        self.point = []
        for i in range(3, 12):
            for j in range(3, 12):
                self.point.append((i*self.border, j*self.border))
        self.M = None
        
        self.pict = []
        
        self.isboardcorrect = False
        self.lock = False # 開始一秒後鎖定棋盤大小
        self.corner_count = 1 # 開始一秒後鎖定邊角數
        
        

    # 定义旋转rotate函数
    def rotate(self, img, angle, center=None, scale=1.0, flip = True):
        # 获取图像尺寸
        (h, w) = img.shape[:2]

        # 若未指定旋转中心,则将图像中心设为旋转中心
        if center is None:
            center = (w / 2, h / 2)

        # 执行旋转
        M = cv2.getRotationMatrix2D(center, angle, scale)
        rotated = cv2.warpAffine(img, M, (w, h))

        """if flip:
            cv2.flip(rotated, 1)"""

        # 返回旋转后的图像
        return rotated

    def close(self):
        """ 關閉視窗"""
        self.cam.release()
        cv2.destroyAllWindows()

    def getImg(self):
        """ 從攝影機取得圖片"""
        if self.debug:
            import os
            img = cv2.imread(os.path.split(os.path.realpath(__file__))[0] +  '\debug.png')
            if __name__ == '__main':
                cv2.imshow('debug ON', img)
            return img
        
        ret, img = self.cam.read()
        while not ret:
            pass
        img = self.rotate(img, self.angle)
        #! camera 區域
        s = 100
        img = img[s:-s, 60+s:-60-s]
        img = cv2.resize(img, (self.pict_size, self.pict_size))
        return img

    def detect_border(self, blur_gray):
        """ 給定圖片,回傳邊緣偵測後的版本"""
        low_threshold = 50
        high_threshold = 150
        edges = cv2.Canny(blur_gray, low_threshold, high_threshold)
        #return edges
    
        rho = 1
        theta = np.pi/180
        threshold = 1
        min_line_length = 1
        max_line_gap = 50
        
        line_image = np.copy(edges)*0 #creating a blank to draw lines on
        
        lines = cv2.HoughLinesP(edges,rho,theta,threshold,np.array([]),min_line_length,max_line_gap)
        
        for line in lines:
            for x1,y1,x2,y2 in line:
                cv2.line(line_image,(x1,y1),(x2,y2),(255,0,0),1)
                
        
        rho = 1
        theta = np.pi/180
        threshold = 1
        min_line_length = 5
        max_line_gap = 3
        
        line_image = cv2.GaussianBlur(
            line_image, (self.kernel_size, self.kernel_size), 0)
        
        lines = cv2.HoughLinesP(line_image,rho,theta,threshold,np.array([]),min_line_length,max_line_gap)
        for line in lines:
            for x1,y1,x2,y2 in line:
                cv2.line(line_image,(x1,y1),(x2,y2),(255,0,0),3)
        
        if __name__ == '__main__':
            #cv2.imshow('edges', edges)
            cv2.imshow('line_image', line_image)
            
        return line_image

    def recatch_board(self):
        self.start_time = time.time()

    def resize(self, img):
        # 將圖片轉為灰階
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_gray = cv2.GaussianBlur(
            gray, (self.kernel_size, self.kernel_size), 0)
        
        # 對比度
        blur_gray = np.uint8(np.clip((2 * blur_gray + 0), 10, 245))
        
        if __name__ == "__main__":
            cv2.imshow('cam_gray_blur', blur_gray)
            
        try:
            edges = self.detect_border(blur_gray)
        except:
            pass


        contours, hierarchy = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        if len(contours) != 0:
            try:
                # draw in blue the contours that were founded
                #cv2.drawContours(img, contours, -1, 255, 3)

                # find the biggest countour (c) by the area
                self.board_area = max(contours, key=cv2.contourArea)
                corner = cv2.approxPolyDP(
                    self.board_area, 0.1*cv2.arcLength(self.board_area, True), True)

                corner = np.float32(corner.tolist())
                to = np.float32([[self.border, self.border], [self.border, self.pict_size-self.border], [
                                self.pict_size-self.border, self.pict_size-self.border], [self.pict_size-self.border, self.border]])

                lock =  (time.time() - self.start_time) > 3
                error = (cv2.contourArea(corner) - self.BoardArea)/(self.BoardArea+1e-6)
                c_error = abs((self.corner_count - len(self.board_area))/self.corner_count) 
                if  (not lock and error > -0.1)\
                    or\
                    (lock and abs(error) < 0.01 and\
                    abs(c_error) < 0.01):
                    # 取得變形公式
                    self.M = cv2.getPerspectiveTransform(corner, to)
                    if not lock:
                        self.BoardArea = cv2.contourArea(corner)
                        self.corner_count = len(self.board_area)
                    self.board_corner = self.board_area
                    self.isboardcorrect = True
                else:
                    self.isboardcorrect = False
                    if __name__ == '__main__':
                        print(f'{abs(error)}/{abs(c_error)}')
                        pass
            except Exception as e:
                print(e)
                pass


    def run(self):
        self.start_time = time.time()
        
        while True:
            try:
                img = self.getImg()

                #cv2.imshow('result', img)
                
                self.resize(img)
            
                while self.M is None:
                    img = self.getImg()

                    #cv2.imshow('finding M', img)
                    self.resize(img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # 透視變形
                dst = cv2.warpPerspective(
                    img, self.M, (self.pict_size, self.pict_size))
                
                #cv2.drawContours(img, self.board_area, -1, (255, 0, 0), 3)
                if __name__ == '__main__':
                    try:
                        if self.isboardcorrect:
                            cv2.drawContours(img, self.board_corner, -1, (0, 255, 0), 3)
                        else:
                            cv2.drawContours(img, self.board_corner, -1, (0, 0, 255), 3)
                    except:
                        pass
                
                if __name__ == "__main__":
                    cv2.imshow('cam', img)
                    cv2.imshow('cam_resize', dst)
                
                self.pict = [img, dst]

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
            except Exception as e:
                print(e)  

    def getDst(self):
        while self.pict == []:
            if not self.isAlive():
                self.start()
            pass
        return self.pict[0], self.pict[1]
        

if __name__ == "__main__":
    cam = camera(url = 'http://192.168.43.40:4747/mjpegfeed', angle = 0, debug = False)
    cam.start()
