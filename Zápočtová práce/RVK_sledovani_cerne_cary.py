import numpy as np
import pygame
import cv2
import tkinter as tk
from PIL import ImageTk, Image

# Initialize constants and variables
frekvence = 420
duration = 1 / frekvence
sample_rate = 40000
mL0 = 200
mR0 = 100
dmL = 0
dmR = 0
signalLR = np.int16(np.zeros((int(sample_rate * duration) * 2)))
i_suma = 0
err_old = 0
maximum = 0
nejmensi = 99999999
m1_last = 0
m2_last = 0

# Initialize pygame mixer
pygame.mixer.pre_init(frequency=sample_rate, channels=2, allowedchanges=1)
pygame.init()

# Create a sound object
sound = pygame.mixer.Sound(signalLR.tobytes())
sound.play(-1)

def motory(mL, mR):
    global signalLR, mL0, mR0, dmL, dmR, sound
    mL, mR = int((mL + dmL) / 1), int((mR + dmR) / 1)
    mL = max(min(mL, 95), 5)
    mR = max(min(mR, 95), 5)
    if (mL != mL0) or (mR != mR0):
        dutyL = int(mL)
        dutyR = int(mR)
        signalLR[0:(2 * dutyL):2] = -32767
        signalLR[(2 * dutyL)::2] = 32767
        signalLR[1:(2 * dutyR + 1):2] = -32767
        signalLR[(2 * dutyR + 1)::2] = 32767

        sound.stop()
        sound = pygame.mixer.Sound(signalLR.tobytes())
        sound.play(-1)

        mL0, mR0 = mL, mR

def pid(error, p=17, i=0, d=0, default_speed=50, max_speed=55):
    if error < 0:
        m1 = 50
        m2 = 5
    else:
        m1 = 5
        m2 = 50
    return m2, m1

root = tk.Tk()
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)
lmain = tk.Label(root)
lmain.grid()

sPole = np.zeros((8))
vahy = np.zeros((8))

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    lmain.config(
        text="Unable to open camera: please grant appropriate permission in Pydroid permissions plugin and relaunch.\nIf this doesn't work, ensure that your device supports Camera NDK API: it is required that your device supports non-legacy Camera2 API.",
        wraplength=lmain.winfo_screenwidth(),
    )
    root.mainloop()
else:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1280)
    cap.set(cv2.CAP_PROP_ANDROID_FLASH_MODE, 1)


def refresh():
    global imgtk
    global m1_last
    global m2_last
    global maximum
    global nejmensi
    ret, frame = cap.read()
    if not ret:
        lmain.after(0, refresh)
        return

    grayFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    (thresh, binaryFrame) = cv2.threshold(grayFrame, 127, 255, cv2.THRESH_BINARY)

    cv2image = binaryFrame

    w = lmain.winfo_screenwidth()
    h = lmain.winfo_screenheight()
    cw = cv2image.shape[0]
    ch = cv2image.shape[1]
    cw, ch = ch, cw
    if (w > h) != (cw > ch):
        cw, ch = ch, cw
        cv2image = cv2.rotate(cv2image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    w = min(cw * h / ch, w)
    h = min(ch * w / cw, h)
    w, h = int(w), int(h)
    cv2image = cv2.resize(cv2image, (w, h), interpolation=cv2.INTER_LINEAR)
    obrPole = np.array(cv2image)
    sirka = w // 8
    vyska = h // 2
    vs = vyska - sirka // 2 + 200
    vh = vyska + sirka // 2 + 220
    vsum = 0
    nejvetsi = 255 * (vh - vs) * sirka
    shift = 500
    for i in range(8):
        cv2.rectangle(
            obrPole, (i, vs - shift), ((i + 1) * sirka, vh - shift), (0, 0, 0), 1
        )

    for i in range(8):
        sPole[i] = nejvetsi - np.sum(
            obrPole[vs - shift : vh - shift, i * sirka : (i + 1) * sirka]
        )
        text = cv2.putText(
            obrPole,
            str(sPole),
            (0, 270),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            2,
        )

    vahy = np.array([-10, -6, -2, -1, 1, 2, 6, 10])

    for i in range(8):
        vsum = vsum + (sPole[i] * vahy[i])

    error = vsum / np.sum(sPole)
    text = cv2.putText(
        obrPole,
        f"{error:.2f}",
        (30, 30),
        cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
        0.7,
        (0, 0, 0),
        2,
    )

    center_x = w // 2
    rectangle_top_left = (center_x - 80, 10)
    rectangle_bottom_right = (center_x + 80, 70)
    cv2.rectangle(obrPole, rectangle_top_left, rectangle_bottom_right, (0, 0, 0), -1)
    
    center_x = w // 2
    text = cv2.putText(
        obrPole,
        "Henry II",
        (center_x - 50, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2,
    ) 

    maximum = 0
    nejmensi = 99999999
    for i in range(0, 6):
        if maximum < sPole[i]:
            maximum = sPole[i]
        if nejmensi > sPole[i]:
            nejmensi = sPole[i]
    if maximum - nejmensi < 600000:
        if m1_last > m2_last:
            motory(50, 5)
        else:
            motory(5, 50)
    else:
        m1, m2 = pid(error, p=1, i=0, d=0, default_speed=50, max_speed=55)
        text = cv2.putText(
            obrPole,
            f"{m1}, {m2}",
            (30, 52),
            cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
            0.7,
            (0, 0, 0),
            2,
        )
        motory(m1, m2)
        m1_last = m1
        m2_last = m2
        text = cv2.putText(
            obrPole,
            f"{m1_last}, {m2_last}",
            (30, 74),
            cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
            0.7,
            (255, 0, 0),
            2,
        )

    img = Image.fromarray(obrPole)
    imgtk = ImageTk.PhotoImage(image=img)
    lmain.configure(image=imgtk)
    lmain.update()

    lmain.after(0, refresh)

refresh()
root.mainloop()
