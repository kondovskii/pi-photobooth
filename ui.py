import tkinter as tk
from PIL import Image, ImageTk, ImageFilter
from datetime import datetime
from picamera2 import Picamera2
from escpos.printer import Usb

root = tk.Tk()
root.attributes('-fullscreen', True)
root.config(cursor="none")

bg_image = Image.open("photobooth_assets/background.jpg")
bg_image = bg_image.resize((800, 480))
bg_photo = ImageTk.PhotoImage(bg_image)

canvas = tk.Canvas(root, width=800, height=480, highlightthickness=0)
canvas.pack(fill="both", expand=True)

result_photo_ref = None
feed_photo_ref = None
running_feed = False

# Set up the camera once at startup
picam2 = Picamera2()
cam_config = picam2.create_still_configuration(main={"size": (1640, 1232), "format": "RGB888"})
picam2.configure(cam_config)
picam2.start()

def draw_background():
    canvas.delete("all")
    canvas.create_image(0, 0, image=bg_photo, anchor="nw")

def draw_idle_screen():
    draw_background()
    canvas.create_text(400, 180, text="✧ pic me! ✧", font=("Trebuchet MS", 36, "bold"), fill="white", tags="ui")
    canvas.create_rectangle(300, 260, 500, 310, fill="white", outline="#993556", width=3, tags="ui")
    canvas.create_text(400, 285, text="☆ tap to start ☆", font=("Trebuchet MS", 16, "bold"), fill="#993556", tags="ui")
    canvas.bind("<Button-1>", lambda event: start_sequence())

def draw_ready_screen():
    draw_background()
    canvas.create_text(400, 240, text="get ready! ✨", font=("Trebuchet MS", 40, "bold"), fill="white", tags="ui")

def start_sequence():
    canvas.unbind("<Button-1>")
    draw_ready_screen()
    root.after(2000, begin_live_feed_countdown)

def begin_live_feed_countdown():
    global running_feed
    draw_background()
    running_feed = True
    update_live_feed()
    run_countdown(3)

def update_live_feed():
    global feed_photo_ref
    if not running_feed:
        return
    frame = picam2.capture_array()

    img = Image.fromarray(frame[:, :, ::-1])  # swap BGR -> RGB
    img = img.resize((520, 300))
    feed_photo_ref = ImageTk.PhotoImage(img)
    canvas.delete("feed")
    canvas.create_image(400, 220, image=feed_photo_ref, tags="feed")
    canvas.tag_raise("countdown_num")
    root.after(150, update_live_feed)

def run_countdown(number):
    if number > 0:
        canvas.delete("countdown_num")
        canvas.create_text(400, 220, text=str(number), font=("Trebuchet MS", 130, "bold"),
                            fill="white", tags="countdown_num")
        canvas.tag_raise("countdown_num")
        root.after(1000, lambda: run_countdown(number - 1))
    else:
        flash_and_capture()

def flash_and_capture():
    global running_feed
    running_feed = False
    canvas.delete("all")
    canvas.create_rectangle(0, 0, 800, 480, fill="white", outline="white")
    canvas.update()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"photo_{timestamp}.jpg"
    picam2.capture_file(raw_filename)  # captures EXACTLY at the flash

    root.after(100, lambda: after_capture(raw_filename))

def draw_loading_screen():
    draw_background()
    canvas.create_text(400, 240, text="loading... 💫", font=("Trebuchet MS", 28, "bold"), fill="white", tags="ui")

def after_capture(raw_filename):
    global result_photo_ref
    draw_loading_screen()
    canvas.update()

    dithered_filename = raw_filename.replace(".jpg", "_dithered.png")
    dither_photo(raw_filename, dithered_filename)

    # Show the ORIGINAL color photo, not the dithered one
    draw_background()
    orig_img = Image.open(raw_filename)
    display_width = 620
    aspect_ratio = orig_img.height / orig_img.width
    display_height = int(display_width * aspect_ratio)
    orig_resized = orig_img.resize((display_width, display_height))
    result_photo_ref = ImageTk.PhotoImage(orig_resized)
    canvas.create_image(400, 220, image=result_photo_ref, tags="ui")
    canvas.create_text(400, 440, text="here's your pic! 💕", font=("Trebuchet MS", 16, "bold"), fill="white", tags="ui")

    root.after(2000, lambda: start_printing(dithered_filename))

def draw_printing_screen():
    draw_background()
    # Printer body
    canvas.create_rectangle(340, 170, 460, 230, fill="white", outline="#993556", width=3, tags="ui")
    # Paper slot on top
    canvas.create_rectangle(355, 160, 445, 172, fill="#f4c0d1", outline="#993556", width=2, tags="ui")
    # Paper coming out, printed on
    canvas.create_rectangle(365, 230, 435, 280, fill="white", outline="#993556", width=2, tags="ui")
    canvas.create_line(375, 240, 425, 240, fill="#993556", width=1, tags="ui")
    canvas.create_line(375, 250, 425, 250, fill="#993556", width=1, tags="ui")
    canvas.create_line(375, 260, 405, 260, fill="#993556", width=1, tags="ui")
    # Small blinking light on the printer body
    canvas.create_oval(395, 195, 405, 205, fill="#ff6fa8", outline="#993556", tags="ui")

    canvas.create_text(400, 320, text="printing your pic!", font=("Trebuchet MS", 16, "bold"), fill="white", tags="ui")
    canvas.create_text(400, 350, text="hang tight ✨", font=("Trebuchet MS", 13, "bold"), fill="white", tags="ui")


def start_printing(dithered_filename):
    draw_printing_screen()
    canvas.update()
    print_receipt(dithered_filename)
    root.after(5000, draw_idle_screen)

def dither_photo(input_filename, output_filename):
    img = Image.open(input_filename)
    target_width = 384
    aspect_ratio = img.height / img.width
    target_height = int(target_width * aspect_ratio)
    img_resized = img.resize((target_width, target_height), Image.LANCZOS)
    img_gray = img_resized.convert('L')
    img_smoothed = img_gray.filter(ImageFilter.GaussianBlur(radius=0.8))
    img_dithered = img_smoothed.convert('1')
    img_dithered.save(output_filename)

def print_receipt(dithered_filename):
    try:
        printer = Usb(0x1d81, 0x5721, 0)
        img = Image.open(dithered_filename)
        printer.image(img)
        printer.cut()
        printer.close()
        print("Print job sent successfully!")
    except Exception as e:
        print(f"Print failed: {e}")

draw_idle_screen()
root.mainloop()
