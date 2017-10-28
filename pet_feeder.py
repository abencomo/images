# Pet Feeder - By: abencomo - Sun Oct 8 2017

import sensor, image, network, usocket, sys, utime
from pyb import LED

green_led = LED(2)

SSID ='AAGG-W24'     # Network SSID
KEY  =''  # Network key
SERVER_ADDRESS = (HOST, PORT) = '', 8088
LOG_FILE = 'log.txt'

# Set sensor settings
sensor.reset()
#sensor.set_framesize(sensor.QQVGA) # 160x120
sensor.set_framesize(sensor.QVGA)   # 320x240
sensor.set_pixformat(sensor.RGB565)
#sensor.set_pixformat(sensor.GRAYSCALE)
sensor.skip_frames(time = 900)     # skip frames for x milliseconds


# Init wlan module and connect to network
wlan = network.WINC()
wlan.connect(SSID, key=KEY, security=wlan.WPA_PSK)

# We should have a valid IP now via DHCP
print(wlan.ifconfig())

# Create server socket
server = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)

# Bind and listen
try:
    server.bind([HOST, PORT])
    server.listen(4)
except OSError:
    machine.reset()

# Set server socket to non-blocking
server.settimeout(0)

html = """<!DOCTYPE html>
<html><head>
    <link rel="stylesheet" href="http://abencomo.github.io/images/style.css">
    </head>
    <body>
        <img id="openmv" style="display:block;margin-left:auto;margin-right:auto;" height="220" width="250"src="http://23.127.160.111:8088/cam.mjpg"/>
        <input type="button" id="feed" value="Feed Me!" onclick="feed(this);">
        %s
        <script>
            const EPOCH_2000 = 946684800;
            var image = document.getElementById('openmv');

            (function pullImage() {
                var date = new Date();
                var timezone_offset = date.getTimezoneOffset() * 60;
                image.src = 'http://23.127.160.111:8088/cam.mjpg' + '?' + ((parseInt(date.getTime()/1000) - EPOCH_2000) - timezone_offset);
                setTimeout(pullImage, 700);
            })();

            function feed(obj) {
                var date = new Date();
                var timezone_offset = date.getTimezoneOffset() * 60;
                var feed = 'feed?' + ((parseInt(date.getTime()/1000) - EPOCH_2000) - timezone_offset);
                var xmlhttp = new XMLHttpRequest();
                xmlhttp.onreadystatechange = function() {};
                xmlhttp.open("GET", feed, true);
                xmlhttp.send();
                obj.disabled = true;
                setTimeout(function() {
                    obj.disabled = false;
                    document.getElementById('lastfeed').innerHTML = 'Last Feed: ' + date.toDateString() + ' @ ' + date.toLocaleTimeString();
                }, 3000);
            }
        </script>
</body></html>
"""

get_path_info = lambda x: x.split()[1]

def start_webserver(server):
    while True:
        try:
           green_led.on()
           client, addr = server.accept()
           green_led.off()
           client.settimeout(9.0)
           request = client.recv(1024)
           path_info = get_path_info(request.decode('utf-8').splitlines()[0])
           print(path_info)

           if path_info.endswith('/'):
               client.send("HTTP/1.1 200 OK\r\n" \
                           "Server: OpenMV\r\n" \
                           "Content-Type: text/html\r\n" \
                           "Cache-Control: max-age=0,must-revalidate\r\n" \
                           "Pragma: no-cache\r\n\r\n")
               ptag = '<p id="lastfeed">%s</p>' % 'Z'
               response = html % ptag
               client.send(response)
               #client.send('\n')
           elif path_info.endswith('/feed'):
               client.send("HTTP/1.1 200 OK\r\n\r\n")
           else:
               parameter = path_info.split("?")
               if len(parameter) > 1:
                   print(utime.localtime(int(parameter[1])))

               # Send multipart header
               client.send("HTTP/1.1 200 OK\r\n" \
                           "Server: OpenMV\r\n" \
                           "Content-Type: multipart/x-mixed-replace;boundary=openmv\r\n" \
                           "Cache-Control: no-cache\r\n" \
                           "Pragma: no-cache\r\n\r\n")

               frame = sensor.snapshot()
               cframe = frame.compressed(quality=50)
               client.send("\r\n--openmv\r\n" \
                        "Content-Type: image/jpeg\r\n"\
                        "Content-Length:"+str(cframe.size())+"\r\n\r\n")
               client.send(cframe)

           client.close()

        except OSError as err:
           print("OS error: {0}".format(err))
        except:
           raise

def get_last_feed():
    try:
        with open(LOG_FILE) as f:
            v = int(f.read())
    except OSError:
        v = 0
        try:
            with open(LOG_FILE, "w") as f:
               f.write(str(v))
        except OSError:
            print("Can't create file %s" % LOG_FILE)

    except ValueError:
        print("invalid data in file %s" % LOG_FILE)
        v = 0

    return v

def set_last_feed(value):
    try:
        with open(LOG_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        print("Can't write to file %s" % LOG_FILE)

while (True):
    try:
        start_webserver(server)
    except OSError as e:
        client.close()
        server.close()
        sys.print_exception(e)
