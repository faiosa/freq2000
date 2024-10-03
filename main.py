import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, PhotoImage
import json
import serial
import serial.tools.list_ports
import time

from utils.position_window import position_window_at_centre
from utils.path import resource_path


class FrequencyTable:
    def __init__(self, master):
        self.master = master
        self.master.title("Перемикач частот-2000")

        self.default_frequencies = {
            "BAND A": [5865, 5845, 5825, 5805, 5785, 5765, 5745, 5725],
            "BAND B": [5733, 5752, 5771, 5790, 5809, 5828, 5847, 5866],
            "BAND E": [5705, 5685, 5665, 5645, 5885, 5905, 5925, 5945],
            "BAND F": [5740, 5760, 5780, 5800, 5820, 5840, 5860, 5880],
            "LOWRACE": [5362, 5399, 5436, 5473, 5510, 5547, 5584, 5621],
            "BAND X": [4990, 5020, 5050, 5080, 5110, 5140, 5170, 5200],
        }

        self.frequencies = self.default_frequencies.copy()
        self.active_cell = (0, 0)
        self.number_of_columns = 6
        self.number_of_rows = 8
        self.set_active_mode = False
        self.edit_mode = False

        self.arduino_port = None
        self.ser = None
        self.buttons = []

        self.create_table()
        self.create_control_panel()
        self.load_settings()
        self.load_arduino()

    def load_arduino(self):
        """Initializes serial connection to Arduino."""
        try:
            self.ser = serial.Serial(self.arduino_port, 9600, timeout=3)
            row, col = self.active_cell
            self.set_active_cell(0, col + 1, show_message=False)
        except serial.SerialException as e:
            if self.arduino_port:
                messagebox.showerror(
                    "Помилка підключення",
                    f"Помилка під час підключення до Ардуїно: {str(e)}",
                )

    def create_table(self):
        """Creates the table of buttons."""
        table_frame = ttk.Frame(self.master)
        table_frame.pack(padx=10, pady=10)

        headers = [" "] + list(self.frequencies.keys())
        for col, header in enumerate(headers):
            label = ttk.Label(table_frame, text=header, padding=5, relief="flat")
            label.grid(row=0, column=col, sticky="n")

        self.buttons = []
        for row in range(self.number_of_rows):
            ch_label = ttk.Label(
                table_frame, text=str(row + 1), padding=5, relief="flat"
            )
            ch_label.grid(row=row + 1, column=0, sticky="w")

            row_buttons = []
            for col, band in enumerate(self.frequencies.keys()):
                freq = self.frequencies[band][row]
                btn = tk.Button(
                    table_frame,
                    text=str(freq),
                    width=8,
                    height=2,
                    command=lambda r=row, c=col: self.cell_click(r, c),
                )
                btn.grid(row=row + 1, column=col + 1, padx=1, pady=1)
                row_buttons.append(btn)
            self.buttons.append(row_buttons)

        self.update_active_cell()

    def create_control_panel(self):
        """Creates the control panel for editing and saving the table."""
        self.control_frame = ttk.Frame(self.master)
        self.control_frame.pack(pady=10, fill=tk.X)

        self.edit_button = ttk.Button(
            self.control_frame, text="Налаштувати", command=self.toggle_edit_mode
        )
        self.edit_button.pack(side="left", padx=5)

        self.save_button = ttk.Button(
            self.control_frame, text="Зберегти", command=self.save_changes
        )
        self.set_active_button = ttk.Button(
            self.control_frame,
            text="Вибрати активну частоту",
            command=self.start_set_active_mode,
        )

        self.port_label = ttk.Label(
            self.control_frame,
            text="Порт Ардуїно: Натисніть щоб налаштувати",
            cursor="hand2",
        )
        self.port_label.pack(side="right", padx=5)
        self.port_label.bind("<Button-1>", lambda e: self.show_port_selection())

    def cell_click(self, row, col):
        if self.set_active_mode:
            self.set_active_cell(row, col)
        elif self.edit_mode:
            band = list(self.frequencies.keys())[col]
            new_freq = simpledialog.askinteger(
                "Змінити значення",
                f"Введіть нову частоту для {band} {row+1}:",
                initialvalue=self.frequencies[band][row],
            )
            if new_freq:
                self.frequencies[band][row] = new_freq
                self.buttons[row][col].config(text=str(new_freq))
                self.set_active_cell(row, col, show_message=False)
                self.save_settings()  # Save settings after changing frequency
        else:
            self.navigate_to_cell(row, col)

    def set_active_cell(self, row, col, show_message=True):
        if self.active_cell:
            self.buttons[self.active_cell[0]][self.active_cell[1]].config(
                bg="SystemButtonFace"
            )
        self.active_cell = (row, col)
        self.buttons[row][col].config(bg="lightblue")
        self.set_active_mode = False
        self.master.config(cursor="")
        if show_message:
            messagebox.showinfo(
                "Активна частота", "Нова активна частота успішно застосована!"
            )
        self.save_settings()  # Save settings after changing active cell

    def navigate_to_cell(self, target_row, target_col):
        current_row, current_col = self.active_cell

        # Calculate the number of steps needed
        if target_col != current_col:
            current_row = 0
        if target_col < current_col:
            col_diff = self.number_of_columns - current_col + target_col
        else:
            col_diff = target_col - current_col
        if target_row < current_row:
            row_diff = self.number_of_rows - current_row + target_row
        else:
            row_diff = target_row - current_row

        commands = []

        # Handle column navigation first
        if col_diff != 0:
            direction = 2 if col_diff > 0 else 1
            commands.extend([direction] * abs(col_diff))

        # Handle row navigation
        if row_diff != 0:
            direction = 2 if row_diff > 0 else 1
            commands.extend([1] * abs(row_diff))

        # Send commands to Arduino
        self.send_commands_to_arduino(commands)

        # Update active cell
        self.set_active_cell(target_row, target_col, show_message=False)

    def send_commands_to_arduino(self, commands):
        if not self.arduino_port:
            messagebox.showerror(
                "Помилка",
                "Не вибрано порт Ардуїно. Будь ласка виберіть порт ардуїно клацнувши у правому нижньому куті.",
            )
            return
        if self.ser is None:
            self.load_arduino()
        # self.ser = serial.Serial(self.arduino_port, 9600, timeout=3)
        for command in commands:
            self.ser.write(str(command).encode())
            self.ser.flush()
            response = self.ser.readline().decode().strip()
            time.sleep(0.1)
            print(f"Sent: {command}, Arduino response: {response}")

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.edit_button.config(text="Вийти")
            self.save_button.pack(side="left", padx=5)
            self.set_active_button.pack(side="left", padx=5)
        else:
            self.edit_button.config(text="Налаштувати")
            self.save_button.pack_forget()
            self.set_active_button.pack_forget()

    def start_set_active_mode(self):
        self.set_active_mode = True
        self.master.config(cursor="crosshair")
        messagebox.showinfo(
            "Нова активна частота",
            "Будь ласка натисніть на частоту, яку бажаєте використовувати як активну",
        )

    def save_changes(self):
        self.save_settings()
        messagebox.showinfo("Зберегти", "Таблиця частот була збережена успішно!")

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
                self.arduino_port = settings.get("arduino_port")
                self.active_cell = tuple(settings.get("active_cell", (0, 0)))
                self.frequencies = settings.get("frequencies", self.default_frequencies)
        except FileNotFoundError:
            self.frequencies = self.default_frequencies
        self.update_port_label()
        self.update_active_cell()
        self.update_frequency_display()

    def update_active_cell(self):
        for row in range(self.number_of_rows):
            for col in range(self.number_of_columns):
                if (row, col) == self.active_cell:
                    self.buttons[row][col].config(bg="lightblue")
                else:
                    self.buttons[row][col].config(bg="SystemButtonFace")

    def update_frequency_display(self):
        for row in range(self.number_of_rows):
            for col, band in enumerate(self.frequencies.keys()):
                self.buttons[row][col].config(text=str(self.frequencies[band][row]))

    def save_settings(self):
        settings = {
            "arduino_port": self.arduino_port,
            "active_cell": self.active_cell,
            "frequencies": self.frequencies,
        }
        with open("settings.json", "w") as f:
            json.dump(settings, f)

    def show_port_selection(self):
        port_window = tk.Toplevel(self.master)
        port_window.title("Порт Ардуїно")
        port_window.geometry(position_window_at_centre(port_window, 300, 300))

        port_listbox = tk.Listbox(port_window)
        port_listbox.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        def refresh_ports():
            port_listbox.delete(0, tk.END)
            self.ports = list(serial.tools.list_ports.comports())
            for port in self.ports:
                port_listbox.insert(tk.END, f"{port.device} - {port.description}")
            if not self.ports:
                port_listbox.insert(tk.END, "Немає портів")

        refresh_ports()

        def on_select(event=None):
            selection = port_listbox.curselection()
            if selection:
                selected_port = self.ports[selection[0]].device
                self.set_arduino_port(selected_port)
                port_window.destroy()

        port_listbox.bind("<Double-1>", on_select)  # Bind double-click event

        select_button = ttk.Button(port_window, text="Вибрати", command=on_select)
        select_button.pack(pady=5)

        refresh_button = ttk.Button(port_window, text="Оновити", command=refresh_ports)
        refresh_button.pack(pady=5)

        port_window.transient(self.master)  # Set to be on top of the main window
        port_window.grab_set()  # Make the window modal
        self.master.wait_window(port_window)  # Wait for the window to be destroyed

    def set_arduino_port(self, port):
        self.arduino_port = port
        self.save_settings()
        self.update_port_label()

    def update_port_label(self):
        if self.arduino_port:
            self.port_label.config(text=f"Arduino порт: {self.arduino_port}")
        else:
            self.port_label.config(text="Arduino Порт: Натисніть, щоб обрати")


if __name__ == "__main__":
    root = tk.Tk()
    root.iconphoto(False, PhotoImage(file=resource_path("assets/icon.png")))
    app = FrequencyTable(root)
    root.mainloop()
