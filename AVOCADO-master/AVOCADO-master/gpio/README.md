Jetson:

pinout diagram: https://www.jetsonhacks.com/nvidia-jetson-tx2-j21-header-pinout/
![pinout diagram](https://github.com/CalPolyCPE/AVOCADO/blob/master/gpio/table.PNG)

odd numbers on the outside of the board

2: 5V to servo 

3: SDA to arduino SDA

5: SCL to arduino SCL

31: motor enable

35: motor control

36: either car gnd

39: gnd to arduino gnd

x: reverse/brake control. I dont know what pin this is, either check the jetson or ask Jacob

Arduino:

3: motor control

4: speed feedback

5: steering control

20: SDA to jetson SDA

21: SCL to jetson SCL

gnd to arduino gnd



make sure car, jetson, and arduino all have same gnd

5V for servo can come from arduino or jetson
