#
# File Name: Advanced_iot_weather_station.py  
# Authors: Pouria Abtahi  
# Date: November 15, 2024  
# Course: TPJ655  
## Program Description:
# This Python program is for an Advanced IoT Weather Station that leverages a Raspberry Pi 3 Model A+ as its
# central processing unit. The program integrates various environmental sensors, a GSM module, and a Wi-Fi 
# connection to monitor and alert users about real-time weather data. Data collected from the sensors is 
# displayed on a 16x2 LCD and transmitted to the Blynk IoT platform for remote monitoring. In case of severe 
# weather conditions (such as heavy rainfall or high wind speeds), the system activates a local buzzer and 
# LED alert and sends SMS notifications to pre-registered phone numbers using a SIM7670C GSM module. The 
# program includes functions for sensor reading, data processing, LCD display, Wi-Fi communication, and SMS alerting.
#
## Note:
# Private credentials such as Blynk tokens, Wi-Fi passwords,
# and phone numbers have been removed for security.


import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd
import socket
import time
import spidev
import adafruit_dht
import requests
import serial
import re
import RPi.GPIO as GPIO
import sys
import os
from enum import Enum

class WeatherCondition(Enum):
    NONE = 0
    HEAVY_RAIN_ALERT = 1
    HIGH_WIND_ALERT = 2
    HIGH_TEMP_ALERT = 3
    LOW_TEMP_ALERT = 4

# Blynk Auth Token
BLYNK_AUTH_TOKEN = 'YOUR_BLYNK_TOKEN'

# URL for batch update
BLYNK_URL = f"https://ny3.blynk.cloud/external/api/batch/update?token={BLYNK_AUTH_TOKEN}"

# Constants for weather thresholds
HEAVY_RAIN_THRESHOLD = 30  # mm
HIGH_WIND_THRESHOLD = 25   # mph
HIGH_TEMP_THRESHOLD = 35   # °C
LOW_TEMP_THRESHOLD = 5     # °C 

# GPIO button setup for reset
RESET_BUTTON_PIN = 3
BUZZER = 24
GPIO.setmode(GPIO.BCM)
GPIO.setup(RESET_BUTTON_PIN, GPIO.IN)
GPIO.setup(BUZZER, GPIO.OUT)

GPIO.output(BUZZER, False)

# Use physical pin numbering (BOARD mode)
lcd_rs = digitalio.DigitalInOut(board.D21) # GPIO21
lcd_en = digitalio.DigitalInOut(board.D20) # GPIO20
lcd_d4 = digitalio.DigitalInOut(board.D16) # GPIO16
lcd_d5 = digitalio.DigitalInOut(board.D12) # GPIO12
lcd_d6 = digitalio.DigitalInOut(board.D26) # GPIO26
lcd_d7 = digitalio.DigitalInOut(board.D19) # GPIO19

# Define the LCD size
lcd_columns = 16
lcd_rows = 2

# Initialize the LCD class
lcd = characterlcd.Character_LCD_Mono(
    lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows
)

# Define custom character for the degree symbol (°)
degree_symbol = [0b00110,  # Custom degree character
                 0b01001,
                 0b01001,
                 0b00110,
                 0b00000,
                 0b00000,
                 0b00000,
                 0b00000]

# Create the custom character
lcd.create_char(0, degree_symbol)

# Define the sensor type and the GPIO pin it is connected to
dht_device = adafruit_dht.DHT11(board.D18)  # GPIO 18 (D18 in CircuitPython)

# Initialize SPI
spi = spidev.SpiDev()
spi.open(0, 0)              # Open bus 0, device 0 (CE0)
spi.max_speed_hz = 1350000  # Set SPI speed

# MCP3208 has 8 channels (0-7)
rain_sensor_channel = 0  # Rain sensor is connected to CH0
wind_sensor_channel = 1  # Wind sensor is connected to CH0

# Signal strength and network status
network_status = 0
signal_strength = 0

latest_weather_alert = WeatherCondition.NONE
previous_weather_alert = WeatherCondition.NONE

temperature = 0
humidity = 0

# Initialize serial connection with the GSM module
try:
    # Define serial port parameters (adjust /dev/serial0 or the appropriate port)
    ser = serial.Serial(
        port='/dev/ttyS0',     # Use the correct port for your module
        baudrate=115200,       # Baudrate for the GSM module
        timeout=1,             # 1 second timeout
        rtscts=False,
        dsrdtr=False
    )
    print("Serial connection established successfully.")
except Exception as e:
    print(f"Error establishing serial connection: {e}")

def check_reset_button():
    """Check if the reset button is pressed."""
    return GPIO.input(RESET_BUTTON_PIN) == GPIO.LOW

def reset_program():
    """Reset the program by restarting the main() function."""
    print("Reset button pressed. Restarting the program...")
    lcd.clear()
    lcd.message = "Resetting..."
    time.sleep(2)
    
    # Close any open resources
    if spi:
        spi.close()
    if ser:
        ser.close()
    
    # Restart the program
    python = sys.executable
    os.execl(python, python, *sys.argv)

# Send AT command and get response
def send_at_command(command, sleep_time=1):
    if ser is None:
        print("GSM module not connected.")
        return None
    try:
        ser.write((command + '\r').encode())
        time.sleep(sleep_time)
        response = ser.read(ser.inWaiting()).decode().strip()
        print(f"CMD > {command}\nRSP > {response}")
        return response
    except serial.SerialTimeoutException:
        print("Serial timeout occurred while sending AT command.")
        return None
    except Exception as e:
        print(f"Error sending AT command: {e}")
        return None

def check_gsm_response(cmd, rsp):
    response = send_at_command(cmd)
    if response is None:
        return False
    if (cmd == 'AT+CSQ'):
        extract_signal_strength(response)
    elif (cmd == 'AT+CREG?'):
        extract_network_status(response)
    elif (cmd == 'AT+CNMI=1,2,0,0,0'):
        extract_phone_numbers(response)
    return rsp in response  # Check if rsp is in the response

def extract_signal_strength(response_csq):
    global signal_strength
    # Extract signal strength from CSQ response
    match_csq = re.search(r"\+CSQ: (\d+),(\d+)", response_csq)
    if match_csq:
        signal_strength = int(match_csq.group(2))  # Extract signal strength (RSSI)
        return signal_strength

def extract_network_status(response_creg):
    global network_status
    # Extract network status from CREG response
    match_creg = re.search(r"\+CREG: \d,(\d)", response_creg)
    if match_creg:
        network_status = int(match_creg.group(1))  # Extract network registration status
    return network_status

def connect_gsm():
    # List of commands and expected responses in order
    commands = [
        ('ATE0', 'OK'),
        ('AT+CLIP=1', 'OK'),
        ('AT+CVHU=0', 'OK'),
        ('AT+CTZU=1', 'OK'),
        ('AT+CMGF=1', 'OK'),
        ('AT+CNMI=0,0,0,0', 'OK'),
        ('AT+CSQ', 'OK'),
        ('AT+CREG?', 'OK'),
        ('AT+CMGD=1,4', 'OK')
    ]
    
    # Loop through each command and check the response
    for cmd, expected_rsp in commands:
        if not check_gsm_response(cmd, expected_rsp):
            return False  # Exit if any command fails
    
    return True  # Return True only if all commands succeed

def extract_phone_numbers(response):
    # Split the response by the delimiters: "*", "#", and ","
    parts = response.split('*')  # Split by '*'
    
    phone_numbers = []
    for part in parts:
        sub_parts = part.split('#')  # Split further by '#'
        for sub_part in sub_parts:
            # Check for phone numbers that start with '+' and contain digits
            if '+' in sub_part:
                numbers = sub_part.split(',')
                for number in numbers:
                    if number.strip().startswith('+') and number.strip()[1:].isdigit():
                        phone_numbers.append(number.strip())
    
    return phone_numbers

def wait_for_phone_number():
    numbers = []
    
    # Continuously loop until valid phone numbers are extracted
    while not numbers:
        # Execute the AT command and get the response
        response = send_at_command('AT+CNMI=1,2,0,0,0')
        
        # Try to extract phone numbers from the response
        numbers = extract_phone_numbers(response)
        
        if not numbers:
            print("No phone numbers found, retrying...")
            time.sleep(1)  # Sleep for a second before retrying (adjust as needed)
    
    # Once we get valid numbers, return them
    return numbers

def send_sms(phone_number, message):
    """
    Function to send an SMS to a given phone number.
    Args:
        phone_number (str): The recipient's phone number.
        message (str): The message to send.
    """
    # AT command to set SMS mode to text
    if check_gsm_response('AT+CMGF=1', 'OK'):
        # AT command to set the recipient phone number
        command = f'AT+CMGS="{phone_number}"\r'
        if check_gsm_response(command, '>'):
            # Send the message, followed by Ctrl+Z (ASCII code 26)
            ser.write(message.encode())
            ser.write(bytes([26]))  # Send Ctrl+Z to end the message
            response = ser.read(ser.inWaiting()).decode()
            print(f"Sent SMS to {phone_number}: {response}")
        else:
            print(f"Failed to send SMS to {phone_number}")
    else:
        print("Failed to set SMS mode to text")

def send_sms_to_all(phone_numbers, message):
    """
    Send an SMS to all phone numbers in the list.
    Args:
        phone_numbers (list): A list of phone numbers.
        message (str): The message to send.
    """
    for number in phone_numbers:
        send_sms(number, message)

# Function to read ADC data from MCP3208
def read_adc(channel):
    if channel > 7 or channel < 0:
        return -1
    # SPI message to send (start bit + single/diff bit + channel selection)
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    # Combine the received bits to get the actual value (10-bit data from MCP3208)
    data = ((adc[1] & 3) << 8) + adc[2]
    return data

# Convert raw ADC value to voltage (assuming a 3.3V reference)
def convert_to_voltage(adc_value, v_ref=3.3):
    return (adc_value * v_ref) / float(1023)

# Convert voltage to rain level in mm (inverse relationship)
def convert_to_rain_mm(voltage, max_voltage=3.3, max_rain_mm=50):
    # Inverting the relationship: Higher voltage = Less rain
    return max_rain_mm * (1 - (voltage / max_voltage))

# Function to calculate wind speed
def convert_to_wind_mph(value, in_min = 11, in_max = 20, out_min = 0, out_max = 100):
    if value < in_min:
        return out_min
    elif value > in_max:
        # If the value is above the maximum, continue scaling it proportionally
        return out_max + (value - in_max) * (out_max - out_min) / (in_max - in_min)
    else:
        # If the value is within the range, map it as usual
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def read_dht11():
    global temperature, humidity
    try:
        temperature = round(float(dht_device.temperature), 1)  # Round to 1 decimal place
        humidity = round(float(dht_device.humidity), 1)        # Round to 1 decimal place
        if humidity is not None and temperature is not None:
            print(f"Temperature: {temperature:.1f}°C")
            print(f"Humidity: {humidity:.1f}%")
        else:
            print("Failed to retrieve data from DHT11 sensor")
    except RuntimeError as error:
        # Errors happen fairly often with DHT sensors, they are slow to respond.
        print(f"RuntimeError: {error.args[0]}")
    except Exception as error:
        dht_device.exit()
        raise error
    
def check_bad_weather(rain_mm, wind_level, temperature):
    """
    Check if current weather conditions are considered 'bad'.
    Returns a tuple (is_bad_weather, message) where is_bad_weather is a boolean
    and message describes the bad weather conditions.
    """
    conditions = []
    is_bad_weather = False
    global latest_weather_alert

    if rain_mm >= HEAVY_RAIN_THRESHOLD:
        conditions.append(f"Heavy rain ({rain_mm:.1f}mm)")
        is_bad_weather = True
        latest_weather_alert = WeatherCondition.HEAVY_RAIN_ALERT
    
    if wind_level >= HIGH_WIND_THRESHOLD:
        conditions.append(f"Strong winds ({wind_level:.1f}mph)")
        is_bad_weather = True
        latest_weather_alert = WeatherCondition.HIGH_WIND_ALERT
    
    if temperature >= HIGH_TEMP_THRESHOLD:
        conditions.append(f"High temperature ({temperature:.1f}C)")
        is_bad_weather = True
        latest_weather_alert = WeatherCondition.HIGH_TEMP_ALERT
    
    if temperature <= LOW_TEMP_THRESHOLD:
        conditions.append(f"Low temperature ({temperature:.1f}C)")
        is_bad_weather = True
        latest_weather_alert = WeatherCondition.LOW_TEMP_ALERT

    message = ''.join(conditions) if conditions else ""
    return is_bad_weather, message
    
# Function to update Blynk with multiple values
def update_blynk(values):
    # Construct the full URL with the values
    full_url = BLYNK_URL + ''.join([f"&V{pin}={value}" for pin, value in values.items()])
    try:
        response = requests.get(full_url)
        if response.status_code == 200:
            print(f"Successfully updated: {values}")
        else:
            print(f"Failed to update. HTTP Error: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error while updating Blynk: {str(e)}")

def display_message_on_lcd(message, duration=2):
    """
    Display a message on the LCD, splitting it into chunks if necessary.
    """
    words = message.split()
    chunks = []
    current_chunk = ""

    for word in words:
        if len(current_chunk) + len(word) + 1 <= 16:  # +1 for space
            current_chunk += " " + word if current_chunk else word
        else:
            chunks.append(current_chunk)
            current_chunk = word

    if current_chunk:
        chunks.append(current_chunk)

    for i in range(0, len(chunks), 2):
        lcd.clear()
        lcd.message = chunks[i].ljust(16)
        if i + 1 < len(chunks):
            lcd.message += "\n" + chunks[i + 1].ljust(16)
        time.sleep(duration)

def display_project_title_on_lcd():
    lcd.clear()
    lcd.message = f"  Advanced IoT  \nWeather Station."
    time.sleep(4)

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    except Exception as e:
        ip_address = "No IP"
        print(f"Error getting IP: {e}")
    finally:
        s.close()
    return ip_address

def main():
    global temperature, humidity
    previous_weather_alert = WeatherCondition.NONE
    
    display_project_title_on_lcd()
    display_message_on_lcd('Connecting GSM...')
    
    while not ser:
        display_message_on_lcd('No GSM connection.')
        print("Exiting. No GSM connection.")
        if check_reset_button():
            reset_program()

    while not connect_gsm():
        display_message_on_lcd('GSM connection failed.')
        print("Exiting. GSM connection failed.")
        if check_reset_button():
            reset_program()

    # Interpret the network registration status
    network_status_meaning = {
        0: "Not registered, not searching",
        1: "Registered, home network",
        2: "Not registered, searching",
        3: "Registration denied",
        4: "Unknown",
        5: "Registered, roaming",
        6: "Registered for SMS only",
    }.get(network_status, "Unknown status")
    print(network_status_meaning)

    display_message_on_lcd(network_status_meaning)
    display_message_on_lcd('Waiting for registeration...')

    numbers = wait_for_phone_number()
    print(f"Phone numbers: {numbers}")
    send_sms_to_all(numbers, 'This number has been registered.')
    display_message_on_lcd('Phone numbers registered.')

    last_alert_time = 0  # To track when the last alert was sent
    alert_cooldown = 600  # 10 minutes in seconds

    while True:
        GPIO.output(BUZZER, False)
        
        # Check for reset button press
        if check_reset_button():
            reset_program()

        read_dht11()

        # Read ADC value from the rain sensor channel
        rain_value = read_adc(rain_sensor_channel)
        time.sleep(0.005)  # Add 5 milliseconds delay between channel readings
        wind_value = read_adc(wind_sensor_channel)
        
        # Convert the raw ADC value to voltage
        rain_voltage = convert_to_voltage(rain_value)
        
        # Convert the voltage to rain level in mm
        rain_mm = float(convert_to_rain_mm(rain_voltage))
        
        # Convert the ADC value to wind level in mph
        wind_level = float(convert_to_wind_mph(wind_value))
        
        print(f"Rainfall: {rain_mm:.2f} mm")
        print(f"Wind speed: {wind_level:.2f} level")

        # Update multiple virtual pins
        sensor_data = {
            0: rain_mm,     # Update V0 to rain_mm
            1: wind_level,  # Update V1 to wind_level
            2: temperature, # Update V2 to temperature
            3: humidity     # Update V3 to humidity
        }
        
        update_blynk(sensor_data)

        # Display data on LCD
        lcd.clear()
        lcd.message = f"Rain: {rain_mm:.1f}mm\nWind: {wind_level:.1f}mph"
        time.sleep(1)

        lcd.clear()
        lcd.message = f"Temp: {temperature:.1f}{chr(0)}C\nHumi: {humidity:.1f}%"
        time.sleep(1)

        # Check for bad weather conditions
        is_bad_weather, weather_message = check_bad_weather(rain_mm, wind_level, temperature)
        
        if is_bad_weather:
            GPIO.output(BUZZER, True)
        else:
            GPIO.output(BUZZER, False)
            
        # Display alert on LCD
        display_message_on_lcd(weather_message, duration=3)
        
        # Send SMS alert if bad weather is detected and cooldown period has passed
        current_time = time.time()
        if is_bad_weather and ((current_time - last_alert_time) >= alert_cooldown or latest_weather_alert != previous_weather_alert):
            # Create the SMS message with "Weather Alert:" and the condition
            weather_details = f"Weather Alert: {weather_message}\n\n" \
                            f"Rain: {rain_mm:.1f}mm\n" \
                            f"Wind: {wind_level:.1f}mph\n" \
                            f"Temp: {temperature:.1f}°C\n" \
                            f"Humidity: {humidity:.1f}%"
            send_sms_to_all(numbers, weather_details)
            last_alert_time = current_time
            previous_weather_alert = latest_weather_alert
            print(f"{weather_details}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted.")
    finally:
        print("Exiting program.")
        if spi:
            spi.close()
        if ser:
            ser.close()
