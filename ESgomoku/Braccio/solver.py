import numpy as np

from math import cos, sin, pi
import os
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
"""
    input [A, B, C, X, Y]
    output [theta, omega, phi]/180
    X <- A cos(theta) + B cos(theta + omega -90) + C cos(theta + omega + phi - 180)
    Y <- A sin(theta) + B sin(theta + omega -90) + C sin(theta + omega + phi - 180)
"""

class solver():
    
    def func(self, theta, omega, phi, A=125.0, B=125.0, C=195.0):
        x = y = 0
        ang = theta
        angr = ang / 180 * pi
        x += A * cos(angr)
        y += A * sin(angr)
        ang += omega -90
        angr = ang / 180 * pi
        x += B * cos(angr)
        y += B * sin(angr)
        ang += phi -90
        angr = ang / 180 * pi
        x += C * cos(angr)
        y += C * sin(angr)
        return x, y
    
      
    def GenData(self):
        print('GenData')
        im = Image.new("RGBA", (1000, 1000), (0,0,0,0)) # x , y range
        draw = ImageDraw.Draw( im ) # painter color
        
        loss = Image.new("RGBA", (1000, 1000), (0,0,0,0)) # x , y range
        drawloss = ImageDraw.Draw( loss ) # painter color
        
        def DrawColor(x, y, R, G, B):
            x, y, R, G, B = int(x), int(y), int(R), int(G), int(B)
            
            def vert_loss(theta, omega, phi):
                return abs(theta + omega + phi - 540 + (180 - 60))
            
            def desicion(axis = list, angle = list, cover = False):
                a,b,c,_ = im.getpixel((axis[0],axis[1]))
                vl = vert_loss(angle[0], angle[1], angle[2])
                if cover and vl < vert_loss(a,b,c):
                    draw.point([axis[0],axis[1]],fill=(angle[0], angle[1], angle[2], 255))
                    drawloss.point([axis[0],axis[1]],fill=(vl, vl, vl, 255))
                elif _ == 0 or ( _ ==250 ):
                    draw.point([axis[0],axis[1]],fill=(angle[0], angle[1], angle[2], 250))
                    drawloss.point([axis[0],axis[1]],fill=(vl, vl, vl, 255))
                        
            desicion([x,y],angle=([R,G,B]), cover = True)
            desicion([x+1,y],angle=([R,G,B]))
            desicion([x-1,y],angle=([R,G,B]))
            desicion([x,y+1],angle=([R,G,B]))
            desicion([x,y-1],angle=([R,G,B]))
            desicion([x+1,y+1],angle=([R,G,B]))
            desicion([x+1,y-1],angle=([R,G,B]))
            desicion([x-1,y+1],angle=([R,G,B]))
            desicion([x-1,y-1],angle=([R,G,B]))
        
        for theta in range(15,165):
            for omega in range(90,180):
                for phi in range(90,180):
                    x, y = self.func(theta, omega, phi)
                    x = int(x+500)
                    y = int(y+500)
                    DrawColor(x, y, theta, omega, phi)
        DrawColor(500, 500, 0, 0, 0)
        DrawColor(505, 500, 255, 0, 0)
        DrawColor(500, 505, 0, 255, 0)
        
        im.save( os.path.dirname(os.path.abspath(__file__)) + "/fileout60.png")
        loss.save( os.path.dirname(os.path.abspath(__file__)) + "/loss60.png")
        
                
    def Calc(self,x_in,y_in,show = True):
        im = Image.open(os.path.dirname(os.path.abspath(__file__)) + "/fileout.png")
        x = x_in + 500
        y = y_in + 500
        
        t, o, p, _ = im.getpixel((x,y))
        
        if _ == 0:
            print('[solver] No Solution')
            return 0,0,0
        x, y = self.func(t,o,p)
        
        if show:
            print(f'[solver]\n    target x = {x_in}, target y = {y_in},\n    solver x = {x}, solver y = {y}\n    solution = {t},{o},{p},  error = {pow((x-x_in),2) + pow((y-y_in),2) }')
        return t, o, p

if __name__ == "__main__":
    s = solver()
    select = input('input mode:')
    if select == '0':
        s.GenData()
    else:
        select = select.split(' ')