import PySimpleGUI as sg
import threading
import cv2
import glob
import os
import time
import numpy as np
import json
import copy


class App():
                
    def __init__(self):

        self.drawing_flag = False
        self.ix, self.iy = -1, -1
        self.label_img = []
        self.label_data = []
        self.pts = []
        self.class_color_dict = {}
        self.draw_mode = ''

        self.cur_class = ''
        self.cur_img = []
        self.class_color = 'red'
        self.make_class = 5
        self.stroke_width = 10
        self.trans = 50

        self.img_loop_trg = True
        self.label_loop_trg = True
        self.img_scale = 0
        self.img_window = [1280, 960]

        ###0413追加
        self.shift = 1
        self.delta_sx, self.delta_sy = -1, -1
        self.org_sx, self.org_sy = -1, -1
        self.cur_sx, self.cur_sy = -1, -1
        self.moving_flag = False
        self.dst_img = []

        self.label_dict = {"name":"TEST","time":"2020-03-25T09:37:28.746Z","version":"1.1.3",
                           "data":[]}
 
        sg.theme('SystemDefault')

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


        ##GUIレイアウト
        class_layout = [
            [sg.Radio('', 'class', pad=(0,0), key='class{}'.format(str(i)), default = False),
             sg.In('class{}'.format(str(i)),size=(15,5),pad=(0,0), key='class_name{}'.format(str(i))),
             sg.ColorChooserButton('', size=(5, 1),
                                   key='class{}_color'.format(str(i)),
                                   button_color=(self.class_color,self.class_color))] for i in range(self.make_class)]

        layout = [
            [sg.Text('StrokeWidth', size=(15, 1), font='Helvetica 14', key='StrokeWidth')],
            [sg.Slider(range=(0,300), default_value=30, resolution=1, size=(20, 20), orientation='horizontal', key='strokewidth')],

            [sg.Button('PolyLine', size=(20, 1), font='Helvetica 14', key='PolyLine')],
            [sg.Button('Ellipse', size=(20, 1), font='Helvetica 14', key='Ellipse')],
            [sg.Button('Rectangle', size=(20, 1), font='Helvetica 14', key='Rectangle')],
            [sg.Button('Polygon', size=(20, 1), font='Helvetica 14', key='Polygon')],
            [sg.Text('Class Index', size=(15, 1), font='Helvetica 14')],
            [sg.Column(class_layout)], 

            [sg.Text('Transparency', size=(15, 1), font='Helvetica 14')],
            [sg.Slider(range=(0, 100), default_value=50, resolution=1,size=(20, 20), orientation='horizontal', key='Trans')],

            [sg.Text('ImageList', size=(15, 1), font='Helvetica 14')],
            [sg.Listbox(values=img_list, size=(20, 20), key='imagelist')],


            [sg.Button('SaveLabel', size=(20, 1), font='Helvetica 14', pad=(4,(0,0)))],            
            [sg.Button('Exit', size=(20, 1), font='Helvetica 14')],
            ]
 

        window = sg.Window('Labelling Tool',layout, size=(200,1000), location=(1200,50))
 
        threading.Thread(target=self.img_cap, args=[img_list]).start()
 
        while True:
 
            event, values = window.read(timeout=100)

            if event == sg.TIMEOUT_KEY:
                self.stroke_width = int(values['strokewidth'])
                self.trans = int(values['Trans'])

                for i in range(self.make_class):
                    
                    _color = 'class{}_color'.format(str(i))

                    try:
                        window.FindElement(_color).Update(_color, button_color=(values[_color],values[_color]))
                    except:
                        None

                    if values[_color]:
                        self.class_color_dict['class{}'.format(str(i))] = values[_color]

                    else:
                        self.class_color_dict['class{}'.format(str(i))] = '#FFFFFF'

                    if values['class{}'.format(str(i))]:
                        self.cur_class = 'class{}'.format(str(i))

            if event == 'PolyLine':
                self.draw_mode = 'PolyLine'
 
            elif event == 'Ellipse':
                self.draw_mode = 'Ellipse'
 
            elif event == 'Rectangle':
                self.draw_mode = 'Rectangle'
 
            elif event == 'Polygon':
                self.draw_mode = 'Polygon'
 
            elif event == 'SaveLabel':
                save_label_dict = copy.deepcopy(self.label_dict) ##辞書はミュータブルなのでコピー時注意

                for i in range(len(save_label_dict['data'])):
                    for n in range(len(save_label_dict['data'][i]['regionLabel'])):
                        _nv = save_label_dict['data'][i]['regionLabel'][n]
                        if _nv['type'] == 'Rect':
                            _nv['width'] = _nv['width'] - _nv['x'] 
                            _nv['height'] = _nv['height'] - _nv['y'] 
                
                try:
                    save_file = sg.popup_get_file('ラベル保存',
                                                 file_types=(('JSONファイル', '*.json'),), 
                                                 save_as = True)+'{}'.format('.json')

                    with open(save_file, 'w') as f:
                        json.dump(save_label_dict, f, ensure_ascii=False)
 
                except:
                    print('保存先が指定されていません。')
                    
                    
            if event == 'Exit':
                self.img_loop_trg = False
                break
            
        window.close()            


###以下モジュール#### 
    ###メイン描画プロセス###
    def img_cap(self, img_list):
        i = 0
 
        cv2.namedWindow('ImageWindow')
 
        while self.img_loop_trg:

            self.label_data = []

            img_array = np.fromfile(img_list[i], dtype=np.uint8)
            org_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)            
            img = self.scale_box(org_img, self.img_window[0], self.img_window[1])
            
            get_img_size = org_img.shape
 
            for num_data in range(len(self.label_dict['data'])):
                if self.label_dict['data'][num_data]['fileName'] == os.path.basename(img_list[i]):
                    self.label_data = self.label_dict['data'][num_data]['regionLabel']
 
            cv2.setMouseCallback('ImageWindow', self.mouse_event)
            
            blank_img = np.zeros((get_img_size[0], get_img_size[1] ,3)).astype(np.uint8)

            ###描画プロセス###
            while self.label_loop_trg: 

                sta_time = time.perf_counter()

                self.label_img = blank_img.copy()

                self.label_update(self.label_data)

                self.label_img = self.scale_box(self.label_img, self.img_window[0], self.img_window[1])

                dst_img = cv2.addWeighted(img, 1, self.label_img, self.trans / 100, 0)
                
                dst_img = self.affine_img(dst_img)
                
                end_time = time.perf_counter()

                #print(end_time-sta_time)


                cv2.imshow('ImageWindow', dst_img)
            
                k = cv2.waitKey(1) & 0xFF
 
                if k == ord('r'):
                    i += 1
                    if i > len(img_list)-1:
                        i = 0
                    
                    break
 
                elif k == ord('b'):
                    i -= 1
                    if i < -len(img_list)+1:
                        i = 0
                    break
        
        cv2.destroyAllWindows()

 
    ##画像スケール管理
    def scale_box(self, img, width, height):
        self.img_scale = max(width / img.shape[1], height / img.shape[0])
        return cv2.resize(img, dsize=None, fx=self.img_scale, fy=self.img_scale)

 
    ##ラベル更新、描画メソッド
    def label_update(self, label_data):

        for i in range(len(label_data)):

            self.num_img = i
            label = label_data[self.num_img]

            try:
                value = self.class_color_dict[label["className"]].lstrip('#')
                lv = len(value)
                color =  [int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3)]
                color.reverse()

            except:
                print('クラスが選択されていません')


            if label['type'] == "PolyLine":
                pts = np.array(label["points"], dtype=np.int32)
                cv2.polylines(self.label_img, [pts], False,  color, thickness=label["strokeWidth"])
                
            elif label['type'] == "Ellipse":
                cv2.ellipse(self.label_img, (label['x'],label['y']),
                            (label["radiusX"],label["radiusY"]),
                            angle = 0,
                            startAngle = 0,
                            endAngle = 360,
                            color = color,
                            thickness = -1)
 
            elif label['type'] == "Rect":
                cv2.rectangle(self.label_img, (label['x'],label['y']),
                             (label['width'],label['height']), color, -1)
 
            elif label['type'] == "PolyGon":
                pts = np.array(label["points"], dtype=np.int32)
                cv2.fillConvexPoly(self.label_img, pts, color)

    def affine_img(self, img):
        
        ###シフト処理###
        src = np.array([[0.0, 0.0],[0.0, 1.0],[1.0, 0.0]], np.float32)
        dest = src.copy()

        dest[:,0] += self.cur_sx + self.delta_sx
        dest[:,1] += self.cur_sy + self.delta_sy
        affine = cv2.getAffineTransform(src, dest)                
        dst_img = cv2.warpAffine(img, affine, (self.img_window[0], self.img_window[1]))

        ###ズーム処理###
        src = np.array([[0.0, 0.0],[0.0, 1.0],[1.0, 0.0]], np.float32)
        dest = src.copy()

        dest[:,0] += - (self.img_window[0] / 2)
        dest[:,1] += - (self.img_window[1] / 2)

        dest = dest * self.shift

        dest[:,0] += self.img_window[0] / 2
        dest[:,1] += self.img_window[1] / 2

        affine = cv2.getAffineTransform(src, dest)                
        dst_img = cv2.warpAffine(dst_img, affine, (self.img_window[0], self.img_window[1]))
 
        return dst_img


##マウスイベント管理
    def mouse_event(self, event, x, y, flags, param):
        x = int((1 / self.img_scale) * x)
        y = int((1 / self.img_scale) * y)

        if not flags & cv2.EVENT_FLAG_SHIFTKEY:
            x = int((1/self.shift) * x - self.cur_sx + (self.img_window[0]-(self.img_window[0]/self.shift)) / 2)
            y = int((1/self.shift) * y - self.cur_sy + (self.img_window[1]-(self.img_window[1]/self.shift)) / 2)

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
        
        else:
            if event == cv2.EVENT_MOUSEWHEEL:
                if flags > 0:
                    self.shift += 0.1

                else:
                    self.shift -= 0.1
                    if self.shift <= 0:
                        self.shift = 0
                
            elif event == cv2.EVENT_LBUTTONDOWN:
                self.moving_flag = True
                self.org_sx, self.org_sy = x, y

            elif event == cv2.EVENT_MOUSEMOVE:
                if self.moving_flag:
                    self.delta_sx = x - self.org_sx
                    self.delta_sy = y - self.org_sy
                    
            elif event == cv2.EVENT_LBUTTONUP:
                self.moving_flag = False
                self.cur_sx  += self.delta_sx
                self.cur_sy += self.delta_sy
            
                self.delta_sx, self.delta_sy = 0, 0



##個別描画処理
    ##Polylineマウスイベント
    def draw_polyline(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
 
            self.drawing_flag = True
            self.pts = []
            self.pts.append([x, y])
            self.label_data.append({"className":self.cur_class,
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
            self.label_data.append({"className":self.cur_class,
                                    "type":"Ellipse",
                                    "x":self.ix,
                                    "y":self.iy,
                                    "radiusX":0,
                                    "radiusY":0})
             
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing_flag == True:
                self.label_data[-1]["radiusX"] = abs(self.ix - x)
                self.label_data[-1]["radiusY"] = abs(self.iy - y)

    ##Rectangleマウスイベント                 
    def draw_rectangle(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing_flag = True
            self.ix, self.iy = x, y
            self.label_data.append({"className":self.cur_class,
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
            self.label_data.append({"className":self.cur_class,
                                    "type":"PolyGon",
                                    "points":[self.pts]})
 
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing_flag == True:
                self.pts.append([x, y])
                self.label_data[-1]["points"] = self.pts
  

App()
 

