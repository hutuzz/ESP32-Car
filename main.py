import network
import socket
import select
import time
import machine
import gc
import ssd1306
from machine import Pin, PWM, I2C, time_pulse_us

gc.enable()

# ================= CẤU HÌNH PHẦN CỨNG =================
in1 = Pin(27, Pin.OUT)
in2 = Pin(26, Pin.OUT)
in3 = Pin(25, Pin.OUT)
in4 = Pin(33, Pin.OUT)
ena = PWM(Pin(13), freq=1000)
enb = PWM(Pin(32), freq=1000)

trig = Pin(5, Pin.OUT)
echo = Pin(18, Pin.IN)
servo = PWM(Pin(4), freq=50)

try:
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
except TypeError:
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# ================= BIẾN TOÀN CỤC =================
is_auto = False
current_speed = 110
current_action = "DUNG IM"
current_dist = 999
oled_page = 0
oled_lines = ["Khoi dong...", "", "", "", ""]
last_cmd_time = time.ticks_ms()
last_oled_time = time.ticks_ms()
last_wifi_activity = time.ticks_ms()

# ================= HÀM ĐIỀU KHIỂN & CẢM BIẾN =================
def set_servo_angle(angle):
    duty = int(40 + (angle / 180.0) * 75)
    servo.duty(duty)

def get_distance():
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    
    duration = time_pulse_us(echo, 1, 30000) 
    
    if duration < 0:
        return 999
    return int((duration * 0.034) / 2)

def drive(left_dir, right_dir, spd):
    in1.value(1 if left_dir > 0 else 0)
    in2.value(1 if left_dir < 0 else 0)
    in3.value(1 if right_dir > 0 else 0)
    in4.value(1 if right_dir < 0 else 0)
    
    ena.duty(1023 if left_dir == 0 else int(spd * 4.01))
    enb.duty(1023 if right_dir == 0 else int(spd * 4.01))

def stop_car():
    drive(0, 0, 0)

# ================= NON-BLOCKING DELAY =================
def wait_ms(ms):
    """Delay non-blocking, lập tức trả về False nếu bị hủy Auto hoặc mất kết nối"""
    t = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t) < ms:
        check_web()
        if not is_auto:
            return False 
        if time.ticks_diff(time.ticks_ms(), last_cmd_time) > 1500:
            return False
        time.sleep_ms(5)
    return True

def look_forward():
    set_servo_angle(90)
    return wait_ms(250)

def scan_left():
    set_servo_angle(170)
    if not wait_ms(350): return 999
    return get_distance()

def scan_right():
    set_servo_angle(10)
    if not wait_ms(350): return 999
    return get_distance()

# ================= MẠNG & WEB TỐI ƯU =================
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="Xe_ESP32", password="12345678", authmode=network.AUTH_WPA_WPA2_PSK)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)
s.setblocking(False)

poller = select.poll()
poller.register(s, select.POLLIN)

INDEX_HTML = b"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover"><title>Tay c\xe1\xba\xa7m xe ESP32</title>
<style>*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;}html,body{margin:0;height:100%;background:#0d0f14;overflow:hidden;font-family:"Segoe UI",Arial,sans-serif;touch-action:none;}#pad{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}@media(orientation:portrait){#pad{width:100vh;height:100vw;top:0;left:100%;inset:auto;transform:rotate(90deg);transform-origin:top left;}}.console{position:relative;width:min(96%,900px);height:min(94%,420px);background:linear-gradient(160deg,#2b2f3a 0%,#1a1d26 60%,#14161d 100%);border-radius:60px 60px 80px 80px / 50px 50px 90px 90px;box-shadow:inset 0 3px 6px rgba(255,255,255,.12),inset 0 -8px 16px rgba(0,0,0,.6),0 14px 40px rgba(0,0,0,.8);display:grid;grid-template-columns:1fr 1.2fr 1fr;align-items:center;padding:6% 4% 4%;}.shoulder{position:absolute;top:-10px;width:22%;height:46px;border:none;color:#cfd3dd;font-weight:800;font-size:16px;letter-spacing:1px;background:linear-gradient(#3a3f4d,#232632);box-shadow:0 4px 0 #0c0d12,inset 0 2px 2px rgba(255,255,255,.15);border-radius:24px 24px 10px 10px;}.shoulder.l{left:7%;}.shoulder.r{right:7%;}.shoulder.on{transform:translateY(3px);box-shadow:0 1px 0 #0c0d12;background:linear-gradient(#ffb300,#e68a00);color:#1a1d26;}.dpad{position:relative;width:190px;height:190px;justify-self:center;}.dpad button{position:absolute;width:64px;height:64px;border:none;color:#aab0bf;font-size:24px;background:linear-gradient(#3b4050,#232632);box-shadow:0 4px 0 #0c0d12,inset 0 2px 2px rgba(255,255,255,.15);}.dpad .up{left:63px;top:0;border-radius:14px 14px 4px 4px;}.dpad .down{left:63px;bottom:0;border-radius:4px 4px 14px 14px;}.dpad .left{left:0;top:63px;border-radius:14px 4px 4px 14px;}.dpad .right{right:0;top:63px;border-radius:4px 14px 14px 4px;}.dpad .hub{position:absolute;left:63px;top:63px;width:64px;height:64px;background:#232632;z-index:0;}.dpad button.on{transform:translateY(3px);box-shadow:0 1px 0 #0c0d12;background:linear-gradient(#ffb300,#e68a00);color:#1a1d26;}.center{display:flex;flex-direction:column;align-items:center;gap:16px;width:100%;}.screen{width:100%;max-width:250px;height:100px;padding:12px 14px;border-radius:12px;background:#0a1a12;color:#3dff8a;font-family:"Courier New",monospace;font-size:13px;line-height:1.4;text-shadow:0 0 4px #3dff8a;box-shadow:inset 0 0 16px #000,0 0 0 4px #0b0d12,0 0 0 6px #343947;display:flex;flex-direction:column;gap:1px;overflow:hidden;}.screen div{white-space:nowrap;}.meta{display:flex;gap:18px;}.pill{min-width:80px;padding:0 12px;height:26px;border:none;border-radius:14px;color:#8a90a0;font-size:11px;font-weight:700;letter-spacing:1px;background:linear-gradient(#3b4050,#232632);box-shadow:0 3px 0 #0c0d12;transition:0.1s;}.pill:active{transform:translateY(2px);box-shadow:0 1px 0 #0c0d12;color:#fff;}.pill.on{transform:translateY(2px);box-shadow:0 1px 0 #0c0d12;color:#1a1d26;background:linear-gradient(#3dff8a,#1b8a45);}.stopbtn{width:64px;height:64px;border-radius:50%;border:none;color:#fff;font-weight:800;font-size:13px;background:radial-gradient(circle at 35% 30%,#ff6b5e,#c62828);box-shadow:0 5px 0 #6d1212,0 8px 14px rgba(0,0,0,.6);}.stopbtn:active{transform:translateY(4px);box-shadow:0 1px 0 #6d1212;}.face{display:flex;flex-direction:row;gap:14px;justify-self:center;width:140px;justify-content:space-between;}.face button{flex:1;height:64px;border-radius:14px;border:none;color:#aab0bf;font-weight:800;font-size:26px;background:linear-gradient(#3b4050,#232632);box-shadow:0 5px 0 #0c0d12,0 8px 12px rgba(0,0,0,.5),inset 0 2px 2px rgba(255,255,255,.15);}.face button:active{transform:translateY(4px);box-shadow:0 1px 0 #0c0d12;color:#fff;background:linear-gradient(#4d5469,#2b2f3a);}@media(max-height:380px){.dpad{transform:scale(.8);}.screen{height:90px;font-size:11px;padding:8px 10px;}.console{padding-top:7%;}}</style>
</head><body><div id="pad"><div class="console">
<button class="shoulder l" data-cmd="vongtrai">LB</button><button class="shoulder r" data-cmd="vongphai">RB</button>
<div class="dpad"><div class="hub"></div><button class="up" data-cmd="tien">&#9650;</button><button class="left" data-cmd="trai">&#9664;</button><button class="right" data-cmd="phai">&#9654;</button><button class="down" data-cmd="lui">&#9660;</button></div>
<div class="center"><div class="screen"><div id="ol1">Dang ket noi...</div><div id="ol2"></div><div id="ol3"></div><div id="ol4"></div><div id="ol5"></div></div>
<div class="meta"><button id="btnSpeed" class="pill">SPEED: V\xe1\xbb\xaaA</button><button id="btnAuto" class="pill auto">T\xe1\xbb\xb0 L\xc3\x81I</button></div>
<button id="btnStop" class="stopbtn" data-cmd="dung">D\xe1\xbb\xaaNG</button></div>
<div class="face"><button id="btnPrev">&#9664;</button><button id="btnNext">&#9654;</button></div></div></div>
<script>
const speedVals=[80,110,150];const speedNames={80:'CH\xe1\xba\xacM',110:'V\xe1\xbb\xaaA',150:'NHANH'};let spdIdx=1;let speed=speedVals[spdIdx];let page=0;const held=[];let busy=false;let isAuto=false;
const $=id=>document.getElementById(id);const active=()=>{if(held.length)return held[held.length-1].cmd;if(isAuto)return 'auto';return 'dung';};
async function send(){if(busy)return;busy=true;const ctl=new AbortController();const t=setTimeout(()=>ctl.abort(),600);try{const res=await fetch(`/cmd?d=${active()}&s=${speed}&p=${page}`,{signal:ctl.signal,cache:'no-store'});const data=await res.json();
$('ol1').innerHTML=data.l1.replace(/ /g,'&nbsp;');$('ol2').innerHTML=data.l2.replace(/ /g,'&nbsp;');$('ol3').innerHTML=data.l3.replace(/ /g,'&nbsp;');$('ol4').innerHTML=data.l4.replace(/ /g,'&nbsp;');$('ol5').innerHTML=data.l5.replace(/ /g,'&nbsp;');$('ol1').style.color="#3dff8a";
}catch(e){$('ol1').textContent="\u26a0 MAT KET NOI";$('ol1').style.color="#f44336";$('ol2').textContent="";$('ol3').textContent="";$('ol4').textContent="";$('ol5').textContent="";}clearTimeout(t);busy=false;}
$('btnSpeed').addEventListener('click',(e)=>{e.preventDefault();spdIdx=(spdIdx+1)%3;speed=speedVals[spdIdx];$('btnSpeed').textContent='SPEED: '+speedNames[speed];send();});
$('btnPrev').addEventListener('click',(e)=>{e.preventDefault();page=(page-1+3)%3;send();});$('btnNext').addEventListener('click',(e)=>{e.preventDefault();page=(page+1)%3;send();});
$('btnAuto').addEventListener('click',(e)=>{e.preventDefault();isAuto=!isAuto;if(isAuto){$('btnAuto').classList.add('on');held.length=0;document.querySelectorAll('.dpad button, .shoulder').forEach(el=>el.classList.remove('on'));}else{$('btnAuto').classList.remove('on');}send();});
$('btnStop').addEventListener('click',(e)=>{e.preventDefault();if(isAuto){isAuto=false;$('btnAuto').classList.remove('on');}held.length=0;document.querySelectorAll('.dpad button, .shoulder').forEach(el=>el.classList.remove('on'));send();});
function press(el){if(isAuto){isAuto=false;$('btnAuto').classList.remove('on');}const cmd=el.dataset.cmd;held.push({el,cmd});el.classList.add('on');send();}
function release(el){el.classList.remove('on');const i=held.findIndex(h=>h.el===el);if(i>=0)held.splice(i,1);send();}
document.querySelectorAll('.dpad button, .shoulder').forEach(el=>{el.addEventListener('pointerdown',e=>{e.preventDefault();el.setPointerCapture(e.pointerId);press(el);});el.addEventListener('pointerup',()=>release(el));el.addEventListener('pointercancel',()=>release(el));el.addEventListener('lostpointercapture',()=>release(el));el.addEventListener('contextmenu',e=>e.preventDefault());});
setInterval(send,150);document.addEventListener('visibilitychange',()=>{if(document.hidden){held.length=0;isAuto=false;$('btnAuto').classList.remove('on');document.querySelectorAll('.dpad button, .shoulder').forEach(el=>el.classList.remove('on'));send();}});
</script></body></html>"""

HDR_HTML = b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n"
HDR_JSON = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"

def parse_query(req):
    params = {}
    if "? " not in req and "?" in req:
        try:
            query_str = req.split(' ')[1].split('?')[1]
            for pair in query_str.split('&'):
                if '=' in pair:
                    k, v = pair.split('=')
                    params[k] = v
        except:
            pass
    return params

def check_web():
    global is_auto, current_speed, current_action, oled_page, last_cmd_time, current_dist, last_wifi_activity
    events = poller.poll(0)
    for conn, flag in events:
        try:
            cl, addr = s.accept()
        except OSError:
            continue
            
        try:
            cl.settimeout(0.1) 
            request = cl.recv(512).decode('utf-8')
            
            if "GET / " in request:
                cl.sendall(HDR_HTML)
                cl.sendall(INDEX_HTML)
            elif "GET /cmd?" in request:
                params = parse_query(request)
                
                # Bắt lỗi parse int an toàn theo Test 10
                try:
                    d = params.get('d', 'dung')
                    s_val = params.get('s', '110')
                    current_speed = int(s_val) if s_val.isdigit() else 110
                    p_val = params.get('p', '0')
                    oled_page = int(p_val) if p_val.isdigit() else 0
                except:
                    d = 'dung'
                    current_speed = 110
                    oled_page = 0
                    
                current_speed = max(70, min(current_speed, 255))
                turn_speed = min(255, current_speed + 80)
                
                if d == "auto":
                    if not is_auto:
                        is_auto = True
                        current_action = "QUET DUONG"
                        set_servo_angle(90)
                else:
                    if is_auto:
                        is_auto = False
                        set_servo_angle(90)
                        
                    if d == "tien": 
                        if current_dist <= 20:
                            stop_car()
                            current_action = "PHANH GAP!"
                        else:
                            drive(1, 1, current_speed)
                            current_action = "TIEN"
                    elif d == "lui": drive(-1, -1, current_speed); current_action = "LUI"
                    elif d == "trai": drive(-1, 1, turn_speed); current_action = "XOAY TRAI"
                    elif d == "phai": drive(1, -1, turn_speed); current_action = "XOAY PHAI"
                    elif d == "vongtrai": drive(0, 1, turn_speed); current_action = "CUA TRAI"
                    elif d == "vongphai": drive(1, 0, turn_speed); current_action = "CUA PHAI"
                    else: stop_car(); current_action = "DUNG IM"
                
                last_cmd_time = time.ticks_ms()
                last_wifi_activity = time.ticks_ms()
                
                json_res = f'{{"l1":"{oled_lines[0]}","l2":"{oled_lines[1]}","l3":"{oled_lines[2]}","l4":"{oled_lines[3]}","l5":"{oled_lines[4]}"}}'.encode()
                cl.sendall(HDR_JSON)
                cl.sendall(json_res)
        except Exception as e:
            pass
        finally:
            cl.close()
            
    # Dọn rác khi rảnh rỗi (>50ms không có request)
    if time.ticks_diff(time.ticks_ms(), last_wifi_activity) > 50:
        gc.collect()

# ================= VÒNG LẶP CHÍNH =================
set_servo_angle(90)
time.sleep_ms(300)
stop_car()

display.fill(0)
display.text("Khoi dong Python..", 0, 20, 1)
display.show()

try:
    while True:
        check_web()
        current_dist = get_distance()
        
        # ----- CẬP NHẬT OLED -----
        if time.ticks_diff(time.ticks_ms(), last_oled_time) > 300:
            if oled_page == 0:
                oled_lines[0] = "WiFi: Xe_ESP32"
                oled_lines[1] = "IP  : 192.168.4.1"
                oled_lines[2] = "Che do: " + ("TU DONG" if is_auto else "LAI TAY")
                oled_lines[3] = "Lenh: " + current_action
                oled_lines[4] = "Vat can: " + ("Thoang" if current_dist > 150 else f"{current_dist} cm")
            elif oled_page == 1:
                oled_lines[0] = "---- RADAR ZONE ----"
                oled_lines[1] = "Khoang cach: " + ("MAX" if current_dist > 150 else f"{current_dist}") + " cm"
                oled_lines[2] = "Trang thai phanh:"
                if current_dist <= 30: oled_lines[3] = ">> PHANH GAP <<"
                elif current_dist <= 70: oled_lines[3] = ">> RA PHANH <<"
                else: oled_lines[3] = ">> AN TOAN <<"
                oled_lines[4] = ""
            elif oled_page == 2:
                rpm_bar = ""
                speed_disp = 0
                if current_action != "DUNG IM" and current_action != "MAT KET NOI!":
                    speed_disp = current_speed
                    num_bars = int(((current_speed - 70) * 7) / 185) + 3
                    rpm_bar = "=" * num_bars + "." * (10 - num_bars)
                else:
                    rpm_bar = "." * 10
                
                mode = "SPORT" if current_speed >= 150 else ("STREET" if current_speed >= 110 else "ECO")
                oled_lines[0] = "==== MOTO DASH ===="
                oled_lines[1] = f"RPM : [{rpm_bar}]"
                oled_lines[2] = f"SPEED: >> {speed_disp} <<"
                oled_lines[3] = f"MODE : {mode}"
                oled_lines[4] = "ABS: ON | TCS: ACTV"
                
            display.fill(0)
            display.text(oled_lines[0], 0, 0, 1)
            display.text(oled_lines[1], 0, 12, 1)
            display.text(oled_lines[2], 0, 24, 1)
            display.text(oled_lines[3], 0, 36, 1)
            display.text(oled_lines[4], 0, 48, 1)
            display.show()
            last_oled_time = time.ticks_ms()

        # ----- LOGIC RADAR TỰ LÁI -----
        if is_auto:
            # Watchdog 1.5s
            if time.ticks_diff(time.ticks_ms(), last_cmd_time) > 1500:
                is_auto = False
                stop_car()
                set_servo_angle(90)
                current_action = "MAT KET NOI!"
                continue

            if current_dist <= 30:
                stop_car()
                current_action = "PHANH GAP!"
                if not wait_ms(200): continue
                
                dist_left = scan_left()
                if not is_auto: continue
                
                dist_right = scan_right()
                if not is_auto: continue
                
                if not look_forward(): continue
                
                auto_turn_speed = min(255, current_speed + 80)
                if dist_left > dist_right and dist_left > 25:
                    current_action = "RE TRAI NE"
                    drive(-1, 1, auto_turn_speed)
                    if not wait_ms(400): continue
                elif dist_right >= dist_left and dist_right > 25:
                    current_action = "RE PHAI NE"
                    drive(1, -1, auto_turn_speed)
                    if not wait_ms(400): continue
                else:
                    current_action = "LUI TIM DUONG"
                    drive(-1, -1, 110)
                    if not wait_ms(500): continue
                    drive(1, -1, auto_turn_speed)
                    if not wait_ms(600): continue
                
                stop_car()
                if not wait_ms(150): continue
                current_action = "QUET DUONG"
                
            elif 30 < current_dist <= 70:
                current_action = "RA PHANH..."
                drive(1, 1, 110)
            else:
                current_action = "TIEN (AUTO)"
                drive(1, 1, current_speed)
        else:
            # ----- WATCHDOG LÁI TAY (400ms) -----
            if time.ticks_diff(time.ticks_ms(), last_cmd_time) > 400:
                stop_car()
                if current_action != "DUNG IM" and current_action != "MAT KET NOI!": 
                    current_action = "DUNG IM"
            else:
                if current_action == "TIEN" and current_dist <= 20:
                    stop_car()
                    current_action = "PHANH GAP!"

except BaseException as e:
    stop_car()
    set_servo_angle(90)
    print("Dung khan cap:", e)
    raise