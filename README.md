\# Advanced IoT Weather Station



\## Overview

This project is a Raspberry Pi-based IoT weather station designed to monitor environmental conditions in real time. The system collects temperature, humidity, rainfall, and wind speed data using sensors and displays the readings locally on a 16x2 LCD screen.



The system also supports remote monitoring through the Blynk IoT platform and sends SMS alerts during severe weather conditions using a GSM module.



\## Why I Built This Project

I built this project as part of my Computer Engineering Technology program at Seneca Polytechnic. The goal was to combine hardware, software, sensors, communication modules, and IoT technology into one working system.



This project helped me apply both my computer engineering technology background and my mechanical engineering knowledge in a practical hardware/software project.



\## Main Features

\- Real-time temperature and humidity monitoring

\- Rainfall detection

\- Wind speed monitoring

\- Local display using a 16x2 LCD

\- Remote monitoring using the Blynk IoT platform

\- SMS alerts using a GSM module

\- Buzzer and LED alerts for severe weather

\- Customizable thresholds for weather alerts

\- PCB design using Proteus



\## Hardware Used

\- Raspberry Pi 3 Model A+

\- DHT11 temperature and humidity sensor

\- Raindrop detection sensor

\- Anemometer wind speed sensor

\- SIM7670C GSM module

\- 16x2 LCD display

\- MCP3208 analog-to-digital converter

\- MAX232 serial communication IC

\- LM2576 voltage regulator

\- Buzzer and LED

\- Custom PCB design



\## Software Used

\- Python

\- Raspberry Pi OS / Linux

\- RPi.GPIO

\- spidev

\- adafruit\_dht

\- adafruit\_character\_lcd

\- serial communication

\- requests library

\- Blynk IoT platform



\## System Operation

The Raspberry Pi collects sensor data from the DHT11 sensor, raindrop sensor, and wind speed sensor. The data is processed in Python and displayed on the LCD screen. The same data is also sent to the Blynk IoT dashboard for remote monitoring.



If the system detects severe weather conditions, such as heavy rain, high wind speed, high temperature, or low temperature, it activates a local buzzer and LED alert. It can also send SMS alerts to registered phone numbers using the GSM module.



\## Severe Weather Alert Thresholds

\- Heavy rainfall: above 30 mm

\- High wind speed: above 25 mph

\- High temperature: above 35°C

\- Low temperature: below 5°C



\## Skills Demonstrated

\- Raspberry Pi setup and configuration

\- Python programming

\- Linux basics

\- Sensor integration

\- GPIO control

\- SPI communication

\- Serial communication

\- IoT dashboard integration

\- GSM/SMS communication

\- Hardware troubleshooting

\- PCB design

\- System testing and documentation



\## Project Images



\### System Block Diagram

!\[System Block Diagram](images/block-diagram.png)



\### LCD Display

!\[LCD Display](images/lcd-display.png)



\### Blynk Dashboard

!\[Blynk Dashboard](images/blynk-dashboard.png)



\### PCB Layout

!\[PCB Layout](images/pcb-layout.png)



\## Challenges

During this project, I worked on troubleshooting sensor readings, wiring connections, GSM communication, and software configuration. I solved these issues step by step by checking hardware connections, reviewing the code, and testing each component separately.



\## Future Improvements

\- Add solar power support

\- Add more sensors such as air quality, UV index, and snow detection

\- Build a mobile app

\- Add cloud data storage

\- Add historical data visualization

\- Improve weatherproofing for outdoor use



\## Author

Pouria Abtahi  

Computer Engineering Technology  

Seneca Polytechnic

DEC 2024

