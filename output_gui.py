""" output_gui

display muscle lengths and platform orientation
"""

import Tkinter as tk
from PIL import Image
from PIL import ImageTk
import copy
from math import degrees


class OutputGui(object):

    def init_gui(self, master, MIN_ACTUATOR_LEN, MAX_ACTUATOR_LEN):
        self.master = master
        self.MIN_ACTUATOR_LEN = MIN_ACTUATOR_LEN
        self.MAX_ACTUATOR_LEN = MAX_ACTUATOR_LEN

        info_frame = tk.Frame(master, relief=tk.SUNKEN, borderwidth=1)
        info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.request_fields_lbl = tk.Label(info_frame, text="request fields", anchor=tk.W, font="consolas")

        self.request_fields_lbl.pack(side=tk.LEFT, fill=tk.X)
        output_frame = tk.Frame(master)
        output_frame.pack(side=tk.LEFT)
        self.muscle_canvas_height = 250
        self.muscle_canvas = tk.Canvas(output_frame, width=100, height=self.muscle_canvas_height)
        self.muscle_canvas.pack()

        margin = int(self.muscle_canvas_height / 10)
        self.max_rectlen = self.muscle_canvas_height - 2.5 * margin
        width = 5
        background = self.muscle_canvas["background"]
        self.muscle_rect = []
        for idx in range(6):
            x0 = 16 + idx * 16
            y1 = self.max_rectlen
            r = self.muscle_canvas.create_rectangle(x0, margin,
                x0+width, y1, fill="black")
            self.muscle_rect.append(r)

        muscle_info_frame = tk.Frame(master)
        muscle_info_frame.pack(side=tk.LEFT)
        self.muscle_labels = []
        for i in range(6):
            lbl = tk.Label(muscle_info_frame, text="Actuator" + str(i), anchor=tk.W, relief=tk.SUNKEN)
            #              font="-weight bold", anchor=tk.W)
            lbl.pack(side=tk.TOP, fill=tk.X, padx=(20, 0), pady=(6, 6))
            self.muscle_labels.append(lbl)

        self.chair_img_canvas = tk.Canvas(master, width=260)
        self.chair_img_canvas.pack(side=tk.RIGHT)
        self.chair_front = Image.open("images/ChairFrontViewSmaller.png")

        self.chair_front_img = ImageTk.PhotoImage(self.chair_front.rotate(0))
        self.front_canvas_obj = self.chair_img_canvas.create_image(
                195, 40 + self.muscle_canvas_height/2, image=self.chair_front_img)

        self.chair_side = Image.open("images/ChairSideViewSmaller.png")
        self.chair_side_img = ImageTk.PhotoImage(self.chair_side.rotate(0))
        self.side_canvas_obj = self.chair_img_canvas.create_image(
                65, 40 + self.muscle_canvas_height/2, image=self.chair_side_img)

        self.chair_top = Image.open("images/ChairTopViewSmaller.png")
        self.chair_top_img = ImageTk.PhotoImage(self.chair_top.rotate(0))
        self.top_canvas_obj = self.chair_img_canvas.create_image(
                130, 50, image=self.chair_top_img)

    def show_muscles(self, position_request, muscles):
        for idx, m in enumerate(muscles):
            n = copy.copy(self.normalize(m))                       
            new_y1 = self.max_rectlen +((n+1) * self.max_rectlen * 0.125)
            _percent = int((n+1) * 50)
            #print m,n, _percent, new_y1
            x0, y0, x1, y1 = self.muscle_canvas.coords(self.muscle_rect[idx])           
            self.muscle_canvas.coords(self.muscle_rect[idx], x0, y0, x1, new_y1)
            info = "length %d is %-3d (%d)%  %" % (idx, int(m-200), _percent)
            if _percent < -100 or _percent > 100:
                color = "red"
            else:
                color = "black"
            self.muscle_labels[idx].config(text=info, fg=color)

        pos = copy.copy(position_request)
        x = pos[0] / 10
        y = pos[1] / 10
        z = 50 - pos[2] / 10
        r = degrees(pos[3])
        p = degrees(pos[4])
        y = degrees(pos[5])
        #  print pos

        self.chair_img_canvas.delete(self.front_canvas_obj)
        self.chair_front_img = ImageTk.PhotoImage(self.chair_front.rotate(r))
        self.front_canvas_obj = self.chair_img_canvas.create_image(
            65 + y, z + self.muscle_canvas_height/2, image=self.chair_front_img)

        self.chair_img_canvas.delete(self.side_canvas_obj)
        self.chair_side_img = ImageTk.PhotoImage(self.chair_side.rotate(p))
        self.side_canvas_obj = self.chair_img_canvas.create_image(
            195 + x, z + self.muscle_canvas_height/2, image=self.chair_side_img)

        self.chair_img_canvas.delete(self.chair_top_img)
        self.chair_top_img = ImageTk.PhotoImage(self.chair_top.rotate(y))
        self.top_canvas_obj = self.chair_img_canvas.create_image(
            130 + x, 50 + y, image=self.chair_top_img)

        info = "Orientation: X=%-4d Y=%-4d Z=%-4d  Roll=%-3d Pitch=%-3d Yaw=%-3d" % (pos[0], pos[1], pos[2], r, p, y)
        self.request_fields_lbl.config(text=info)
        
        self.master.update_idletasks()
        self.master.update()

    def normalize(self, item):
        i = 2 * (item - self.MIN_ACTUATOR_LEN) / (self.MAX_ACTUATOR_LEN - self.MIN_ACTUATOR_LEN)
        return i-1
