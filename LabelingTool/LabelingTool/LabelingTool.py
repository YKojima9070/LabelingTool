import PySimpleGUI as sg
import threading
import cv2
import io
import glob
import os
import time
import datetime
import numpy as np
import json

##test##

class App():
                
    def __init__(self):
        self.drawing_flag = False
        self.ix, self.iy = -1, -1
        self.img = []
        self.label_img = []
        self.label_data = []
        self.pts = []
        self.dst = []
        self.draw_mode = ''
        self.class_num = ''
        self.stroke_width = 10
        self.img_loop_trg = True
        self.img_scale = 0
        self.img_window = [640, 480]
 
        self.label_dict = {"name":"TEST","time":"2020-03-25T09:37:28.746Z","version":"1.1.3",
                           "data":[]}
 
        sg.theme('SystemDefault')
 
        ##以下メインプロセス
        layout = [
            [sg.Text('Label Tool', size=(15, 1), font='Helvetica 15')],
            [sg.Button('PolyLine', size=(20, 1), font='Helvetica 14', key='PolyLine')],
            [sg.Button('Ellipse', size=(20, 1), font='Helvetica 14', key='Ellipse')],
            [sg.Button('Rectangle', size=(20, 1), font='Helvetica 14', key='Rectangle')],
            [sg.Button('Polygon', size=(20, 1), font='Helvetica 14', key='Polygon')],
            [sg.Text('StrokeWidth', size=(15, 1), font='Helvetica 10', key='StrokeWidth')],
            [sg.In(self.stroke_width, size=(15,1), font='Helvetica 10', key='strokewidth')],
 
            [sg.Button('SaveLabel', size=(20, 1), font='Helvetica 15')],            
            [sg.Button('Exit', size=(20, 1), font='Helvetica 15')]
            ]
 
#                  [sg.Slider(range=(0, num_frames),
#                             size=(60, 10), orientation='h', key='-slider-')],
 
        ##参照フォルダ指定
        img_format = [".png", ".jpg", ".jpeg", ".bmp"]
        tar_dir = os.path.dirname(os.path.abspath(sg.popup_get_file('画像読込')))

        if tar_dir is None:
            return
        img_list = [p for p in glob.glob("{0}\\**".format(tar_dir),
                                        recursive=True) if os.path.splitext(p)[1] in img_format]
         
        [self.label_dict['data'].append({"fileName":os.path.basename(img_list[i]),
                                         "set":"",
                                         "classLabel":"",
                                         "regionLabel":[]}) 
         for i in range(len(img_list))]
 
        window = sg.Window('Demo Application - Labelling Tool',layout, size=(200, 700), location=(1200,50))
                    #        no_titlebar = False,
                    #        loation=(0,0))
 
        #slider_elem = window['-slider-']
 
        threading.Thread(target=self.img_cap, args=[img_list]).start()
 
        while True:
 
            event, values = window.read(timeout=100)
            if event == sg.TIMEOUT_KEY:
                self.stroke_width = int(values['strokewidth'])
               
            if event == 'PolyLine':
                self.draw_mode = 'PolyLine'
 
            elif event == 'Ellipse':
                self.draw_mode = 'Ellipse'
 
            elif event == 'Rectangle':
                self.draw_mode = 'Rectangle'
 
            elif event == 'Polygon':
                self.draw_mode = 'Polygon'
 
            elif event == 'SaveLabel':
                dt = datetime.datetime.now()
                save_file = '{0}\\{1:%Y%m%d-%H%M%S}.json'.format(os.getcwd(), dt) 
                with open(save_file, 'w') as f:
                    json.dump(self.label_dict, f, ensure_ascii=False)
 
            if event == 'Exit':
                self.img_loop_trg = False
                break
            
        window.close()            
 
    def img_cap(self, img_list):
        i = 0
 
        cv2.namedWindow(winname='ImageWindow')
 
        while self.img_loop_trg:
            self.label_data = []
            img = cv2.imread(img_list[i])
            self.img = self.scale_box(img, self.img_window[0], self.img_window[1])
            get_img_size = img.shape
 
            for num_data in range(len(self.label_dict['data'])):
                if self.label_dict['data'][num_data]['fileName'] == os.path.basename(img_list[i]):
                    self.label_data = self.label_dict['data'][num_data]['regionLabel']
 
            cv2.setMouseCallback('ImageWindow', self.draw_label)
 
            while self.img_loop_trg:
 
                ##描画プロセス
                self.label_img = np.zeros((get_img_size[0], get_img_size[1] ,3)).astype(np.uint8)

                self.label_update(self.label_data)
                self.label_img = self.scale_box(self.label_img, self.img_window[0], self.img_window[1])

                self.dst = cv2.addWeighted(self.img, 1, self.label_img, 0.3, 0)
 
                cv2.imshow('ImageWindow', self.dst)
            
                k = cv2.waitKey(1) & 0xFF
 
                if k == ord('r'):
                    if i == len(img_list):
                        i = 0
                    else:
                        i += 1
                    break
 
                elif k == ord('b'):
                    if i == -len(img_list):
                        i = 0
                    else:
                        i -= 1                   
                    break
            break
 
##画像スケール管理
    def scale_box(self, img, width, height):
        self.img_scale = max(width / img.shape[1], height / img.shape[0])
        return cv2.resize(img, dsize=None, fx=self.img_scale, fy=self.img_scale)
 
##ラベル更新、描画メソッド
    def label_update(self, label_data):
 
        for i in range(len(label_data)):
            self.num_img = i
 
            label = label_data[self.num_img]

            if label['type'] == "PolyLine":
                pts = np.array(label["points"], dtype=np.int32)
                cv2.polylines(self.label_img, [pts], False,  (255, 255, 255), thickness=label["strokeWidth"])
                
            elif label['type'] == "Ellipse":
                cv2.ellipse(self.label_img, (label['x'],label['y']),
                            (label["radiusX"],label["radiusY"]),
                            angle = 0,
                            startAngle = 0,
                            endAngle = 360,
                            color = (255,255,255),
                            thickness = -1)
 
            elif label['type'] == "Rect":
                cv2.rectangle(self.label_img, (label['x'],label['y']),
                             (label['width'],label['height']), (255, 255, 255), -1)
 
            elif label['type'] == "PolyGon":
                pts = np.array(label["points"], dtype=np.int32)
                cv2.fillConvexPoly(self.label_img, pts,(255, 255, 255))
 

##描画モード管理
    def draw_label(self, event, x, y, flags, param):
        x = int((1 / self.img_scale) * x)
        y = int((1 / self.img_scale) * y)
 
        if self.draw_mode == "PolyLine":
            self.draw_polyline(event, x, y, flags, param)

        elif self.draw_mode == "Ellipse":
            self.draw_ellipse(event, x, y, flags, param)

        elif self.draw_mode == "Rectangle":
            self.draw_rectangle(event, x, y, flags, param)
 
        elif self.draw_mode == "Polygon":
            self.draw_polygon(event, x, y, flags, param)

        if event == cv2.EVENT_RBUTTONDOWN:
            if self.drawing_flag == False:
                del self.label_data[-1]

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing_flag = False
         
 
##個別描画処理
    ##Polylineマウスイベント
    def draw_polyline(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
 
            self.drawing_flag = True
            self.pts = []
            self.pts.append([x, y])
            self.label_data.append({"className":"class0",
                                    "type":"PolyLine",
                                    "strokeWidth":self.stroke_width,
                                    "points":[self.pts]})
 
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing_flag == True:
                self.pts.append([x, y])
                self.label_data[-1]["points"] = self.pts
 
    ##Ellipseマウスイベント 
    def draw_ellipse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing_flag = True
            self.ix, self.iy = x, y
            self.label_data.append({"className":"class0",
                                    "type":"Ellipse",
                                    "x":self.ix,
                                    "y":self.iy,
                                    "radiusX":0,
                                    "radiusY":0})
             
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing_flag == True:
                self.label_data[-1]["radiusX"] = abs(x - self.ix)
                self.label_data[-1]["radiusY"] = abs(y - self.iy)

    ##Rectangleマウスイベント                 
    def draw_rectangle(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing_flag = True
            self.ix, self.iy = x, y
            self.label_data.append({"className":"class0",
                                    "type":"Rect",
                                    "x":self.ix,
                                    "y":self.iy,
                                    "width":x,
                                    "height":y})
 
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing_flag == True:
                self.label_data[-1]["width"] = x
                self.label_data[-1]["height"] = y            
 
    ##Polygonマウスイベント                  
    def draw_polygon(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
 
            self.drawing_flag = True
            self.pts = []
            self.pts.append([x, y])
            self.label_data.append({"className":"class0",
                                    "type":"PolyGon",
                                    "points":[self.pts]})
 
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing_flag == True:
                self.pts.append([x, y])
                self.label_data[-1]["points"] = self.pts
  
 
App()
 

