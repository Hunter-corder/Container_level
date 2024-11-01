import tkinter as tk
from PIL import Image, ImageTk
import threading
import minimalmodbus
import serial
import datetime
import time
import sqlite3
import os
import sys

global max_vessel_no
max_vessel_no = 5

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

DATABASE_PATH = resource_path(r'G:\\PythonCoding-master\\temperature_data.db')

class VesselDataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Vessel Controller")

        # Set geometry to cover about 95% of the screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{int(screen_width * 0.95)}x{int(screen_height * 0.95)}")
        self.root.configure(bg="white")

        self.slave_data = [None] * max_vessel_no
        self.slave_charts = []  # Store chart references here
        self.create_widgets()
        self.start_background_task()
        self.last_error = None
        self.bind_events()

        # Fetch latest data from the database initially
        self.get_latest_data()

    def create_widgets(self):
        # Logout button
        self.logout_button = tk.Button(
            self.root, text="Logout", command=self.logout,
            bg="white", fg="#4a90e2", font=("Arial", 12, "bold"),
            borderwidth=2, relief="solid", padx=10, pady=5
        )
        self.logout_button.place(x=20, y=20)

        # Title
        self.title = tk.Label(
            self.root, text="Vessel Data", font=("Arial", 24, "bold"),
            bg="white", fg="#4a90e2"
        )
        self.title.pack(pady=20)

        # Create a frame to hold the images and labels
        self.image_frame = tk.Frame(self.root, bg="white")
        self.image_frame.pack(pady=10)

        # Create frames for each slave
        self.slave_frames = []
        for i in range(max_vessel_no):
            image_path = resource_path(f'images/slave{i + 1}.png')
            frame = self.create_info_container(f"Slave {i + 1}", "Loading...", image_path, f"slave_{i}")
            frame.pack(side="left", padx=10)  # Pack horizontally
            self.slave_frames.append(frame)

            # Start updating the chart for each vessel
            self.update_chart(i)

        # Error display
        self.error_label = tk.Label(self.root, text="", font=("Arial", 14, "bold"), fg="red", bg="white")
        self.error_label.pack(pady=10)

    def create_info_container(self, title, value, image_path, id):
        frame = tk.Frame(self.image_frame, bg="#fff", padx=15, pady=15, bd=0, relief="flat")

        title_label = tk.Label(frame, text=title, font=("Arial", 20, "bold"), fg="#4a90e2", bg="#fff")
        title_label.pack()

        # Load and display the image
        try:
            img = Image.open(image_path)
            img = img.resize((225, 350), Image.LANCZOS)  # Adjust size here
            photo = ImageTk.PhotoImage(img)
            image_label = tk.Label(frame, image=photo, bg="#fff")
            image_label.image = photo  # Keep a reference to avoid garbage collection
            image_label.pack()
        except Exception as e:
            # print(f"Error loading image {image_path}: {e}")
            self.error_label(f"Error loading image  {image_path}: {e}")

        # Pack the value label
        value_label = tk.Label(frame, text=value, font=("Arial", 18), bg="#fff")
        value_label.pack(pady=(0, 0))

        # Create a frame to hold the thermometer
        thermometer_frame = tk.Canvas(frame, width=27.5, height=168, bg="#fff", bd=0, relief="flat")
        thermometer_frame.place(relx=0.535, rely=0.486, anchor='center')  # Adjust position here

        # Store references
        setattr(self, f"{id}_label", value_label)
        setattr(self, f"{id}_thermometer_frame", thermometer_frame)  # Store reference for the thermometer frame
        self.slave_charts.append(thermometer_frame)  # Keep a list of all thermometer frames
        return frame

    def update_chart(self, vessel_index):
        # Clear the previous drawings in the thermometer frame
        thermometer_frame = getattr(self, f'slave_{vessel_index}_thermometer_frame')
        thermometer_frame.delete("all")

        # Get the actual value from the slave data
        level = self.slave_data[vessel_index]

        # Ensure the level is within the range of 0 to 100
        if level is not None:
            level = max(0, min(100, int(level)))  # Convert to integer and limit range
        else:
            level = 0  # Default to 0 if no data is available

        # Define the height of the thermometer frame and maximum bar height
        max_bar_height = 168  # Updated height

        # Calculate the bar height based on the actual value
        bar_height = max_bar_height * (level / 100)
        bar_y = max_bar_height - bar_height  # Position the bar from the bottom

        # Draw the thermometer bar in green
        thermometer_frame.create_rectangle(5, bar_y, 25, bar_y + bar_height, fill="green", outline="")

        # Schedule the next update
        self.root.after(1000, self.update_chart, vessel_index)  # Update every second

    def update_labels(self):
        # Update GUI with the latest values for each slave
        for i in range(max_vessel_no):
            label = getattr(self, f'slave_{i}_label')
            if self.slave_data[i] is not None:
                label.config(text=f"{int(self.slave_data[i])}")  # Convert to integer for display
            else:
                label.config(text="Unknown")  # Default text if no data

    def display_error(self, message):
        # Update the error label on the GUI
        self.error_label.config(text=message)

    def clear_error(self):
        # Clear the error label on the GUI
        self.error_label.config(text="")

    def start_background_task(self):
        # Start the Modbus reading in a separate thread
        thread = threading.Thread(target=self.read_modbus_data)
        thread.daemon = True
        thread.start()

        # Start a timer to fetch latest data from the database every minute
        self.root.after(60000, self.get_latest_data)  # Fetch every 60 seconds

    def read_modbus_data(self):
        port = 'COM5'
        connected = False
        instrument = None

        # Attempt to establish a connection
        while not connected:
            try:
                instrument = minimalmodbus.Instrument(port=port, slaveaddress=1)
                instrument.serial.baudrate = 9600
                instrument.serial.bytesize = 8
                instrument.serial.parity = serial.PARITY_NONE
                instrument.serial.stopbits = 1
                connected = True
            except Exception as e:
                self.root.after(0, self.display_error, f"Could not connect to the device via {port}")
                self.last_error = f"Could not connect to the device via {port}"
                time.sleep(5)  # Wait before retrying

        # Start reading data
        while connected:
            try:
                for vessel_no in range(max_vessel_no):
                    # Set the current slave address
                    instrument.slaveaddress = vessel_no + 1  # Slave addresses start from 1
                    level = instrument.read_register(vessel_no)  # Read data for the slave
                    self.slave_data[vessel_no] = level  # Store data

                    # Save to the database
                    self.save_to_database(vessel_no + 1, level)

                # Update the GUI with new data
                self.root.after(0, self.update_labels)

                # Clear error message if previously there was an error
                if self.last_error:
                    self.root.after(0, self.clear_error)
                    self.last_error = None

            except serial.serialutil.SerialException as e:
                self.root.after(0, self.display_error, "Serial exception occurred. Reconnecting...")
                self.last_error = "Serial exception occurred. Reconnecting..."
                connected = False
                if instrument is not None:
                    try:
                        instrument.serial.close()
                    except Exception:
                        self.root.after(0, self.display_error, "Error closing port")
                break

            except Exception as e:
                self.root.after(0, self.display_error, "Unexpected error")
                # print(e)
                self.last_error = "Unexpected error"
                time.sleep(5)

            time.sleep(5)  # Sleep between reads

        if instrument is not None:
            try:
                instrument.serial.close()
            except Exception:
                self.root.after(0, self.display_error, "Error closing port")

    def get_latest_data(self):
        """Fetch the latest data from the database for each vessel."""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            for vessel_no in range(max_vessel_no):
                c.execute('''SELECT level FROM vessel_readings WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1''', (vessel_no + 1,))
                row = c.fetchone()
                if row:
                    self.slave_data[vessel_no] = row[0]
                    # print(f"Vessel {vessel_no + 1}: {row[0]}")  # Debug: Show fetched value
                else:
                    self.slave_data[vessel_no] = None  # No data available
                    # print(f"Vessel {vessel_no + 1}: No data")  # Debug: Show no datai
        except Exception as e:
            # print(f"Error fetching latest data: {e}")
            self.error_label(f"Error fetching latest data: {e}")
        finally:
            conn.close()
        
        # Update labels and charts with latest data
        self.root.after(0, self.update_labels)
        for i in range(max_vessel_no):
            self.root.after(0, self.update_chart, i)

    def save_to_database(self, device_id, level):
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()

            # Convert level to integer before saving
            level = int(level)
            # Insert a new record
            c.execute('''INSERT INTO vessel_readings (device_id, level, timestamp) VALUES (?, ?, ?)''', (device_id, level, datetime.datetime.now()))
            conn.commit()
        except Exception as e:
            self.error_label(f"Error saving to database: {e}")
        finally:
            conn.close()

    def logout(self):
        self.root.quit()

    def bind_events(self):
        self.root.bind('<Escape>', self.logout)  

if __name__ == "__main__":
    root = tk.Tk()
    app = VesselDataApp(root)
    root.mainloop()
