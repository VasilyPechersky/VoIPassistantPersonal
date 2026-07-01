import sys
import os
import csv
import base64
import subprocess
import urllib.request
import urllib.error
import threading

# Import Flask components
from flask import Flask, request

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QDialog,
    QFormLayout, QMessageBox, QMenu, QLabel, QStyle, QSystemTrayIcon, QAction
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QIntValidator
from PyQt5.QtWidgets import QTabWidget

# 1. Global Variables Startup Initialization
phone_IP = ""
userext = ""
auth_header = ""  # Ready-to-use Base64 encoded "user:password"
auth_token = ""   # Phone Authentication Token payload parameter
programmable_buttons = [{"name": "", "path": ""} for _ in range(4)]

# 2. Path Setup Utility Functions
def get_base_dir():
    """Locates or constructs the dedicated nested ~/.config/VoIPassistant/ directory profile location."""
    home_dir = os.path.expanduser("~")
    base_dir = os.path.join(home_dir, ".config", "VoIPassistant")
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
    return base_dir

def get_config_path():
    return os.path.join(get_base_dir(), "config.txt")

def get_phonebook_path():
    return os.path.join(get_base_dir(), "VoIPassistantPB.txt")


# 3. Data Persistence Methods for config.txt

def load_global_settings():
    """Reads saved system parameters and populates global runtime variables."""
    global phone_IP, userext, auth_header, auth_token, programmable_buttons
    config_file = get_config_path()
    programmable_buttons = [{"name": "", "path": ""} for _ in range(4)] # Reset
    
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 1: phone_IP = lines[0]
                if len(lines) >= 2: userext = lines[1]
                if len(lines) >= 3: auth_header = lines[2]
                if len(lines) >= 4: auth_token = lines[3]
                
                # Load the 4 programmable buttons (lines 5 to 12)
                for i in range(4):
                    name_idx = 4 + (i * 2)
                    path_idx = 5 + (i * 2)
                    if name_idx < len(lines): programmable_buttons[i]["name"] = lines[name_idx]
                    if path_idx < len(lines): programmable_buttons[i]["path"] = lines[path_idx]
        except Exception as e:
            print(f"Error loading system profile parameters: {e}")
    else:
        raw_bytes = "admin:admin".encode('utf-8')
        auth_header = base64.b64encode(raw_bytes).decode('utf-8')
        auth_token = ""

def save_global_settings():
    """Writes global runtime modifications cleanly into the localized config file structure."""
    global phone_IP, userext, auth_header, auth_token, programmable_buttons
    try:
        with open(get_config_path(), "w", encoding="utf-8") as f:
            f.write(f"{phone_IP}\n")
            f.write(f"{userext}\n")
            f.write(f"{auth_header}\n")
            f.write(f"{auth_token}\n")
            # Save the 4 programmable buttons
            for btn in programmable_buttons:
                f.write(f"{btn['name']}\n")
                f.write(f"{btn['path']}\n")
    except Exception as e:
        print(f"Error saving system parameters locally: {e}")


def get_shared_phone_icon(style_context):
    phone_icon = QIcon.fromTheme("call-start", QIcon.fromTheme("phone"))
    if phone_icon.isNull():
        phone_icon = style_context.standardIcon(QStyle.SP_MessageBoxInformation)
    return phone_icon
# 4. Core Handlers and Operational Components
def send_ccall_end():
    global phone_IP
    global auth_header
    phoneip = str(phone_IP)
    print(f"Executing send_ccall_end command drop line for target phone IP: {phoneip}")
    url_string = "http://" + phoneip + "/cgi-bin/ConfigManApp.com?key=RELEASE"
    print(url_string)
    
    req = urllib.request.Request(url_string)
    req.add_header("Authorization", f"Basic {auth_header}")
    try:
        with urllib.request.urlopen(req) as response:
            response.read()
    except urllib.error.URLError as e:
        QMessageBox.information(None, "Error", "Error connecting phone.")


def snd_call_answer():
    global phone_IP
    global auth_header
    phoneip = str(phone_IP)
    #contact_name = ""
    print(f"Executing snd_call_answer command for target phone IP: {phoneip}")
    url_string = "http://" + phoneip + "/cgi-bin/ConfigManApp.com?key=ENTER"#key=ENTER 
    print(url_string)
    
    req = urllib.request.Request(url_string)
    req.add_header("Authorization", f"Basic {auth_header}")
    try:
        with urllib.request.urlopen(req) as response:
            response.read()
        #call_popup = ActiveCallDialog(contact_name, phone_number, parent_window)
        #call_popup.exec_()
    except urllib.error.URLError as e:
        QMessageBox.information(None, "Error", "Error connecting phone.")


class ActiveCallDialog(QDialog):
    """Modal tracking window showcasing operational macros and inline contact creation."""
    def __init__(self, contact_name: str, phone_number: str, parent=None):
        super(ActiveCallDialog, self).__init__(parent)
        global programmable_buttons
        self.phone_number = phone_number
        self.contact_name = contact_name
        self.is_known_contact = False

        # Check if this contact already exists in the parent phonebook database
        main_win = parent if parent else self.parentWidget()
        if main_win and hasattr(main_win, 'contacts'):
            for contact in main_win.contacts:
                if contact.get('phone', '').strip() == phone_number.strip():
                    self.is_known_contact = True
                    break

        self.setWindowTitle("Active Session")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(340, 240)
        self.setModal(True)

        layout = QVBoxLayout(self)
        
        # Display Name String
        self.status_label = QLabel(f"Calling <b>{self.contact_name}</b>...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.status_label)

        # Inline Number Row: Number on Left, Quick-Add Button on Right
        number_row_layout = QHBoxLayout()
        
        num_label = QLabel(f"Number: {self.phone_number}", self)
        num_label.setFont(QFont("Arial", 10))
        num_label.setStyleSheet("color: gray;")
        number_row_layout.addWidget(num_label, 1)

        # Render quick-add button only if number is missing from the local CSV phonebook
        if not self.is_known_contact:
            self.add_contact_btn = QPushButton(self)
            self.add_contact_btn.setFixedSize(28, 28)
            self.add_contact_btn.setToolTip("Add to Contacts")
            icon = QIcon.fromTheme("contact-new-symbolic", self.style().standardIcon(QStyle.SP_DialogHelpButton))
            self.add_contact_btn.setIcon(icon)
            self.add_contact_btn.clicked.connect(self.trigger_quick_add_contact)
            number_row_layout.addWidget(self.add_contact_btn)

        layout.addLayout(number_row_layout)

        # Core Call Control Hooks (End / Dismiss)
        btn_layout = QHBoxLayout()
        self.end_btn = QPushButton("End", self)
        self.end_btn.setStyleSheet("background-color: #ff9999; font-weight: bold;")
        self.end_btn.clicked.connect(self.handle_end_call)

        self.dismiss_btn = QPushButton("Dismiss", self)
        self.dismiss_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.end_btn)
        btn_layout.addWidget(self.dismiss_btn)
        layout.addLayout(btn_layout)

        # --- Split 4 Programmable Buttons into 2 Rows (2 in Upper, 2 in Lower) ---
        from PyQt5.QtWidgets import QGridLayout
        macro_grid = QGridLayout()
        macro_grid.setSpacing(6)
        
        for idx, btn_data in enumerate(programmable_buttons):
            macro_btn = QPushButton(self)
            display_text = btn_data["name"] if btn_data["name"] else ""
            macro_btn.setText(display_text)
            macro_btn.setMinimumHeight(35)
            
            target_path = btn_data["path"]
            if target_path:
                macro_btn.clicked.connect(lambda checked, p=target_path: self.execute_macro_path(p))
            else:
                macro_btn.setEnabled(False) 
                
            row = idx // 2
            col = idx % 2
            macro_grid.addWidget(macro_btn, row, col)
            
        layout.addLayout(macro_grid)

    def trigger_quick_add_contact(self):
        """Launches ContactDialog from active call state with matching Z-index layer depth."""
        main_win = self.parentWidget()
        if main_win:
            prefilled_data = {'first_name': '', 'last_name': '', 'company': '', 'phone': self.phone_number}
            dialog = ContactDialog(main_win, prefilled_data)
            
            # FIX: Force the contact dialog to inherit the "always on top" priority
            # This ensures it layers properly above or next to the active call screen
            dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)
            
            if dialog.exec_() == QDialog.Accepted:
                main_win.contacts.append(dialog.get_data())
                main_win.save_to_csv()
                main_win.populate_list()
                
                # Instantly update active interface variables to hide macro button 
                if hasattr(self, 'add_contact_btn'):
                    self.add_contact_btn.hide()


    def execute_macro_path(self, raw_path_string):
        """Replaces $N with active string values and launches system processes."""
        parsed_command = raw_path_string.replace("$N", self.phone_number)
        print(f"Executing system macro string pipeline hook: {parsed_command}")
        try:
            subprocess.Popen(parsed_command, shell=True)
        except Exception as e:
            print(f"Failed handling execution command string loop call: {e}")

    def handle_end_call(self):
        send_ccall_end()
        self.close()


def dial_number(contact_name: str, phone_number: str, parent_window=None):
    print(f"Initiating connection handshake out to: {phone_number}")
    global phone_IP
    global auth_header
    phoneip = str(phone_IP)
    url_string = "http://" + phoneip + "/cgi-bin/ConfigManApp.com?key=" + phone_number +";ENTER;"
    print(url_string)
    
    req = urllib.request.Request(url_string)
    req.add_header("Authorization", f"Basic {auth_header}")   
    try:
        with urllib.request.urlopen(req) as response:
            response.read()
    except urllib.error.URLError as e:
        QMessageBox.information(None, "Error", "Error connecting phone.")
        
    call_popup = ActiveCallDialog(contact_name, phone_number, parent_window)
    call_popup.exec_()


class DirectDialDialog(QDialog):
    """Interceptive popup enabling instant runtime outbound dialing loops."""
    def __init__(self, parent=None):
        super(DirectDialDialog, self).__init__(parent)
        self.setWindowTitle("Direct Dial")
        self.setModal(True)
        self.resize(300, 110)
        
        layout = QVBoxLayout(self)
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Enter phone number...")
        
        validator = QIntValidator(self)
        self.input_field.setValidator(validator)
        layout.addWidget(self.input_field)
        
        btn_layout = QHBoxLayout()
        self.dial_btn = QPushButton("Dial", self)
        self.dial_btn.setIcon(get_shared_phone_icon(self.style()))
        self.dial_btn.setStyleSheet("background-color: #98fb98; font-weight: bold;")
        self.dial_btn.clicked.connect(self.validate_and_dial)
        
        self.close_btn = QPushButton("Close", self)
        self.close_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.dial_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
    def validate_and_dial(self):
        number = self.input_field.text().strip()
        if len(number) < 2:
            QMessageBox.warning(self, "Invalid Entry", "Target phone number must contain at least 2 characters!")
            self.input_field.setFocus()
            return
        
        self.close()
        dial_number(number, number, self.parentWidget())


# --- New Incoming Call Alert Window ---
class IncomingCallDialog(QDialog):
    """Popup window triggered by Flask backend when state=ring with contact matching."""
    def __init__(self, raw_number: str, parent=None):
        super(IncomingCallDialog, self).__init__(parent)
        self.phone_number = raw_number
        self.contact_name = "Unknown Caller"
        self.is_known_contact = False
        
        if parent and hasattr(parent, 'contacts'):
            for contact in parent.contacts:
                if contact.get('phone', '').strip() == raw_number.strip():
                    full_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                    self.contact_name = full_name if full_name else f"Contact: {raw_number}"
                    self.is_known_contact = True
                    break

        self.setWindowTitle("Incoming Call Alert")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(340, 150)
        self.setModal(False)

        layout = QVBoxLayout(self)
        
        status_label = QLabel(f"Incoming Call From:<br><b>{self.contact_name}</b>", self)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setFont(QFont("Arial", 12))
        layout.addWidget(status_label)
        
        # Lower String Layout: Number on Left, Quick-Add Button on Right
        number_row_layout = QHBoxLayout()
        
        num_label = QLabel(f"Number: {self.phone_number}", self)
        num_label.setFont(QFont("Arial", 10))
        num_label.setStyleSheet("color: gray;")
        number_row_layout.addWidget(num_label, 1)
        
        if not self.is_known_contact:
            self.add_contact_btn = QPushButton(self)
            self.add_contact_btn.setFixedSize(28, 28)
            self.add_contact_btn.setToolTip("Add to Contacts")
            icon = QIcon.fromTheme("contact-new-symbolic", self.style().standardIcon(QStyle.SP_DialogHelpButton))
            self.add_contact_btn.setIcon(icon)
            self.add_contact_btn.clicked.connect(self.trigger_quick_add_contact)
            number_row_layout.addWidget(self.add_contact_btn)
            
        layout.addLayout(number_row_layout)

        # Operational Call Controls
        btn_layout = QHBoxLayout()
        
        self.answer_btn = QPushButton(self)
        self.answer_btn.setFixedSize(100, 40)
        self.answer_btn.setIcon(QIcon.fromTheme("call-start", self.style().standardIcon(QStyle.SP_DialogApplyButton)))
        self.answer_btn.setIconSize(QSize(24, 24))
        self.answer_btn.setStyleSheet("background-color: #98fb98;")
        self.answer_btn.clicked.connect(self.handle_answer)

        self.end_btn = QPushButton(self)
        self.end_btn.setFixedSize(100, 40)
        self.end_btn.setIcon(QIcon.fromTheme("call-stop", self.style().standardIcon(QStyle.SP_DialogCancelButton)))
        self.end_btn.setIconSize(QSize(24, 24))
        self.end_btn.setStyleSheet("background-color: #ff9999;")
        self.end_btn.clicked.connect(self.handle_end)

        btn_layout.addWidget(self.answer_btn)
        btn_layout.addWidget(self.end_btn)
        layout.addLayout(btn_layout)

    def trigger_quick_add_contact(self):
        """Launches ContactDialog with the incoming number pre-filled."""
        main_win = self.parentWidget()
        if main_win:
            prefilled_data = {'first_name': '', 'last_name': '', 'company': '', 'phone': self.phone_number}
            dialog = ContactDialog(main_win, prefilled_data)
            
            if dialog.exec_() == QDialog.Accepted:
                main_win.contacts.append(dialog.get_data())
                main_win.save_to_csv()
                main_win.populate_list()
                
                if hasattr(self, 'add_contact_btn'):
                    self.add_contact_btn.hide()

    def handle_answer(self):
        """Answers call and spawns macro-enabled ActiveCallDialog window directly."""
        snd_call_answer()
        self.close()
        
        call_popup = ActiveCallDialog(self.contact_name, self.phone_number, self.parentWidget())
        call_popup.exec_()

    def handle_end(self):
        send_ccall_end()
        self.close()



# --- New Background Thread Core for Flask Application Integration ---
class FlaskServerThread(QThread):
    """Isolated server environment emitting signal triggers back into PyQt runtime thread handles."""
    ring_signal = pyqtSignal(str)

    def run(self):
        flask_app = Flask("VoIPAssistantBackend")

        @flask_app.route('/', methods=['GET'])
        def route_default():
            return "system operational", 200

        @flask_app.route('/call', methods=['GET', 'POST'])
        def route_call():
            state_val = request.values.get('state', '').strip().lower()
            # Capture the value of the 'in' parameter representing the caller phone number
            caller_num = request.values.get('in', '').strip()

            if state_val == 'ring':
                # Pass the raw caller number back to the main UI thread via signal
                self.ring_signal.emit(caller_num)
            return "OK", 200

        # Port 80 requires administrator/root authentication permissions on host machines
        try:
            flask_app.run(host='0.0.0.0', port=18025, debug=False, use_reloader=False)
        except Exception as e:
            print(f"CRITICAL: Failed starting internal Flask instance on port 80: {e}")

class SettingsDialog(QDialog):
    """Configuration prompt with standard VoIP options and a Programmable Buttons tab."""
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        global phone_IP, userext, auth_header, auth_token, programmable_buttons
        self.setWindowTitle("VoIP Settings")
        self.setModal(True)
        self.resize(400, 320)

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)

        # --- TAB 1: General Connection Settings ---
        tab1 = QWidget()
        self.layout1 = QFormLayout(tab1)
        self.server_ip_input = QLineEdit(tab1)
        self.server_ip_input.setText(phone_IP)
        self.extension_input = QLineEdit(tab1)
        self.extension_input.setText(userext)
        self.token_input = QLineEdit(tab1)
        self.token_input.setText(auth_token)

        try:
            decoded_str = base64.b64decode(auth_header.encode('utf-8')).decode('utf-8')
            parsed_user, parsed_pass = decoded_str.split(":", 1)
        except Exception:
            parsed_user, parsed_pass = "admin", "admin"

        self.user_input = QLineEdit(tab1)
        self.user_input.setText(parsed_user)
        self.pass_input = QLineEdit(tab1)
        self.pass_input.setText(parsed_pass)
        self.pass_input.setEchoMode(QLineEdit.Password)

        self.layout1.addRow("Phone IP:", self.server_ip_input)
        self.layout1.addRow("Phone User:", self.user_input)
        self.layout1.addRow("Phone Password:", self.pass_input)
        self.layout1.addRow("My Extension:", self.extension_input)
        self.layout1.addRow("Phone Auth Token:", self.token_input)
        self.tabs.addTab(tab1, "VoIP Parameters")

        # --- TAB 2: Programmable Buttons Settings ---
        tab2 = QWidget()
        self.layout2 = QFormLayout(tab2)
        self.btn_inputs = []

        for i in range(4):
            name_in = QLineEdit(tab2)
            name_in.setMaxLength(16)  # Forced 16 chars maximum length validation
            name_in.setPlaceholderText(f"Button {i+1} Text Display")
            name_in.setText(programmable_buttons[i]["name"])

            path_in = QLineEdit(tab2)
            path_in.setPlaceholderText("Script/binary execution path... ($N = number)")
            path_in.setText(programmable_buttons[i]["path"])

            self.layout2.addRow(QLabel(f"<b>Button {i+1} Configuration:</b>"))
            self.layout2.addRow("  Label Name:", name_in)
            self.layout2.addRow("  Execute Path:", path_in)
            self.btn_inputs.append((name_in, path_in))

        self.tabs.addTab(tab2, "Programmable Buttons")
        main_layout.addWidget(self.tabs)

        # Global Save Button Action Anchor
        self.save_button = QPushButton("Save All Settings", self)
        self.save_button.clicked.connect(self.save_and_close)
        main_layout.addWidget(self.save_button)

    def save_and_close(self):
        global phone_IP, userext, auth_header, auth_token, programmable_buttons
        phone_IP = self.server_ip_input.text().strip()
        userext = self.extension_input.text().strip()
        auth_token = self.token_input.text().strip()
        
        raw_user = self.user_input.text().strip()
        raw_pass = self.pass_input.text().strip()
        combined_bytes = f"{raw_user}:{raw_pass}".encode('utf-8')
        auth_header = base64.b64encode(combined_bytes).decode('utf-8')
        
        # Save macro buttons fields mapping array strings
        for i in range(4):
            programmable_buttons[i]["name"] = self.btn_inputs[i][0].text().strip()
            programmable_buttons[i]["path"] = self.btn_inputs[i][1].text().strip()

        save_global_settings()
        self.accept()


class ContactDialog(QDialog):
    def __init__(self, parent=None, contact_data=None):
        super(ContactDialog, self).__init__(parent)
        self.setWindowTitle("Contact Details")
        self.setModal(True)
        self.resize(320, 200)
        self.layout = QFormLayout(self)
        self.first_name_input = QLineEdit(self)
        self.last_name_input = QLineEdit(self)
        self.company_input = QLineEdit(self)
        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText("Required *")
        
        self.layout.addRow("First Name:", self.first_name_input)
        self.layout.addRow("Last Name:", self.last_name_input)
        self.layout.addRow("Company Name:", self.company_input)
        self.layout.addRow("Phone Number *:", self.phone_input)
        
        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.validate_and_accept)
        self.layout.addRow(self.save_button)
        
        if contact_data:
            self.first_name_input.setText(contact_data.get('first_name', ''))
            self.last_name_input.setText(contact_data.get('last_name', ''))
            self.company_input.setText(contact_data.get('company', ''))
            self.phone_input.setText(contact_data.get('phone', ''))

    def validate_and_accept(self):
        if not self.phone_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "The Phone Number field is mandatory!")
            self.phone_input.setFocus()
            return
        self.accept()

    def get_data(self):
        return {
            'first_name': self.first_name_input.text().strip(),
            'last_name': self.last_name_input.text().strip(),
            'company': self.company_input.text().strip(),
            'phone': self.phone_input.text().strip()
        }


class ContactRowWidget(QWidget):
    def __init__(self, contact_data, dial_callback, edit_callback, remove_callback, main_app, parent=None):
        super(ContactRowWidget, self).__init__(parent)
        self.contact_data = contact_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        details_layout = QVBoxLayout()

        self.full_display_name = f"{contact_data['first_name']} {contact_data['last_name']}".strip()
        if not self.full_display_name:
            self.full_display_name = f"Contact: {contact_data['phone']}"

        name_label = QLabel(f"<b>{self.full_display_name}</b>")
        name_label.setFont(QFont("Arial", 14))
        company_label = QLabel(contact_data['company'] if contact_data['company'] else "No Company")
        company_label.setStyleSheet("color: gray;")
        details_layout.addWidget(name_label)
        details_layout.addWidget(company_label)
        layout.addLayout(details_layout, 4)

        self.gear_btn = QPushButton(self)
        self.gear_btn.setFixedSize(30, 30)
        self.gear_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogListView))
        self.menu = QMenu(self)
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: edit_callback(self.contact_data))
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: remove_callback(self.contact_data))
        self.menu.addAction(edit_action)
        self.menu.addAction(remove_action)
        self.gear_btn.setMenu(self.menu)
        self.gear_btn.setStyleSheet("QPushButton::menu-indicator { image: none; }")

        self.dial_btn = QPushButton(self)
        self.dial_btn.setFixedSize(60, 30)
        self.dial_btn.setIcon(get_shared_phone_icon(self.style()))
        self.dial_btn.setIconSize(QSize(18, 18))
        self.dial_btn.setToolTip(f"Dial {contact_data['phone']}")
        self.dial_btn.clicked.connect(lambda: dial_callback(self.full_display_name, contact_data['phone'], main_app))
        self.dial_btn.setStyleSheet("""
            QPushButton { background-color: #98fb98; border: 1px solid #7bc87b; border-radius: 4px; }
            QPushButton:hover { background-color: #a2ffa2; }
            QPushButton:pressed { background-color: #83d683; }
        """)
        layout.addWidget(self.dial_btn)
        layout.addWidget(self.gear_btn)
class PhoneBookApp(QMainWindow):
    def __init__(self):
        super(PhoneBookApp, self).__init__()
        self.setWindowTitle("VoIP Assistant Personal")
        self.resize(450, 600)

        self.file_path = get_phonebook_path()
        self.contacts = []

        self.load_from_csv()
        self.init_ui()
        self.init_systray()
        self.populate_list()
        
        # Start integrated background listener
        self.start_flask_server()

    def start_flask_server(self):
        self.server_thread = FlaskServerThread(self)
        # Capture the newly routed parameter from our background thread map
        self.server_thread.ring_signal.connect(self.trigger_incoming_call_popup)
        self.server_thread.start()

    def trigger_incoming_call_popup(self, incoming_number):
        """Safely invokes UI generation loops with targeted string matching."""
        self.incoming_popup = IncomingCallDialog(incoming_number, self)
        self.incoming_popup.show()
        self.incoming_popup.raise_()
        self.incoming_popup.activateWindow()


    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # --- Integrated Status Bar Layout (Placed Above Search Box) ---
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setContentsMargins(2, 2, 2, 5)
        
        # Left-aligned status indicators
        self.indicator_icon = QLabel(self)
        self.indicator_icon.setFixedSize(16, 16)
        
        self.Lab_phone_ip = QLabel(self)
        self.Lab_phone_ip.setFont(QFont("Arial", 10, QFont.Bold))
        self.update_status_bar_display()
        
        status_bar_layout.addWidget(self.indicator_icon)
        status_bar_layout.addWidget(self.Lab_phone_ip)
        status_bar_layout.addStretch()
        
        # Right-aligned quick-action control endpoints
        self.hdr_dial_btn = QPushButton(self)
        self.hdr_dial_btn.setFixedSize(30, 30)
        self.hdr_dial_btn.setIcon(QIcon.fromTheme("input-dialpad", self.style().standardIcon(QStyle.SP_FileDialogListView)))
        self.hdr_dial_btn.setToolTip("Direct Dial")
        self.hdr_dial_btn.clicked.connect(self.open_direct_dial)
        
        self.hdr_menu_btn = QPushButton(self)
        self.hdr_menu_btn.setFixedSize(30, 30)
        self.hdr_menu_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMenuButton))
        self.hdr_menu_btn.setToolTip("Application Menu")
        
        status_bar_layout.addWidget(self.hdr_dial_btn)
        status_bar_layout.addWidget(self.hdr_menu_btn)
        main_layout.addLayout(status_bar_layout)
        
        # --- Contact List Layout Profiles ---
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search contacts...")
        self.search_bar.textChanged.connect(self.populate_list)
        main_layout.addWidget(self.search_bar)
        
        self.list_widget = QListWidget(self)
        main_layout.addWidget(self.list_widget)
        
        self.add_btn = QPushButton("+ Add Record", self)
        self.add_btn.setMinimumHeight(35)
        self.add_btn.clicked.connect(self.add_contact)
        main_layout.addWidget(self.add_btn)

    def init_systray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(get_shared_phone_icon(self.style()))

        self.tray_menu = QMenu()
        show_action = QAction("Open Phone Book", self)
        show_action.triggered.connect(self.showNormal)

        direct_dial_action = QAction("Direct Dial", self)
        direct_dial_action.triggered.connect(self.open_direct_dial)

        vcf_action = QAction("Import contacts from VCF", self)
        vcf_action.triggered.connect(self.import_vcf_contacts)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)

        quit_action = QAction("Exit", self)
        # CHANGED: Connected to clean exit routine instead of generic instance quit
        quit_action.triggered.connect(self.handle_application_exit)

        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(direct_dial_action)
        self.tray_menu.addAction(vcf_action)
        self.tray_menu.addAction(settings_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()
        
        self.hdr_menu_btn.setMenu(self.tray_menu)
        self.hdr_menu_btn.setStyleSheet("QPushButton::menu-indicator { image: none; }")

    def handle_application_exit(self):
        """NEW: Safely destroys background server threads before termination."""
        self.tray_icon.hide()
        self.hide()
        
        if hasattr(self, 'server_thread') and self.server_thread.isRunning():
            self.server_thread.terminate()
            self.server_thread.wait() # Safely block until OS thread exits
            
        QApplication.instance().quit()

    def update_status_bar_display(self):
        """Refreshes status parameters based on current configuration states."""
        global phone_IP
        cleaned_ip = str(phone_IP).strip()
        if cleaned_ip:
            self.Lab_phone_ip.setText(cleaned_ip)
            self.indicator_icon.setPixmap(self.style().standardIcon(QStyle.SP_DialogApplyButton).pixmap(16, 16))
            self.Lab_phone_ip.setStyleSheet("color: green;")
        else:
            self.Lab_phone_ip.setText("No Phone IP Configured")
            self.indicator_icon.setPixmap(self.style().standardIcon(QStyle.SP_DialogCancelButton).pixmap(16, 16))
            self.Lab_phone_ip.setStyleSheet("color: red;")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_status_bar_display()

    def open_direct_dial(self):
        dialog = DirectDialDialog(self)
        dialog.exec_()

    def import_vcf_contacts(self):
        exec_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        target_script = os.path.join(exec_dir, "GcontactPuller.py")
        
        if not os.path.exists(target_script):
            QMessageBox.critical(
                self, "File Error", 
                f"Missing script dependency!\n'GcontactPuller.py' must be placed within: {exec_dir}"
            )
            return
            
        try:
            subprocess.Popen([sys.executable, target_script], cwd=exec_dir)
        except Exception as e:
            QMessageBox.critical(self, "Process Error", f"Failed to execute external data script: {e}")

    def changeEvent(self, event):
        if event.type() == event.WindowStateChange:
            if self.isMinimized():
                self.hide()
                event.accept()
        super(PhoneBookApp, self).changeEvent(event)

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def load_from_csv(self):
        if not os.path.exists(self.file_path):
            self.contacts = [
                {'first_name': 'John', 'last_name': 'Doe', 'company': 'Acme Corp', 'phone': '101'},
                {'first_name': 'Jane', 'last_name': 'Smith', 'company': 'Beta Industries', 'phone': '102'}
            ]
            self.save_to_csv()
            return
        try:
            with open(self.file_path, mode='r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                self.contacts = [row for row in reader]
        except Exception:
            self.contacts = []

    def save_to_csv(self):
        try:
            fieldnames = ['first_name', 'last_name', 'company', 'phone']
            with open(self.file_path, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.contacts)
        except Exception as e:
            QMessageBox.critical(self, "Storage Error", f"Could not write configuration modifications: {e}")

    def populate_list(self):
        self.list_widget.clear()
        search_query = self.search_bar.text().lower()
        for contact in self.contacts:
            match_string = f"{contact['first_name']} {contact['last_name']} {contact['company']} {contact['phone']}".lower()
            if search_query in match_string:
                item = QListWidgetItem(self.list_widget)
                row_widget = ContactRowWidget(contact, dial_number, self.edit_contact, self.remove_contact, self, self)
                item.setSizeHint(row_widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, row_widget)

    def add_contact(self):
        dialog = ContactDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.contacts.append(dialog.get_data())
            self.save_to_csv()
            self.populate_list()

    def edit_contact(self, contact_data):
        dialog = ContactDialog(self, contact_data)
        if dialog.exec_() == QDialog.Accepted:
            idx = self.contacts.index(contact_data)
            self.contacts[idx] = dialog.get_data()
            self.save_to_csv()
            self.populate_list()

    def remove_contact(self, contact_data):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {contact_data['first_name']} {contact_data['last_name']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.contacts.remove(contact_data)
            self.save_to_csv()
            self.populate_list()

if __name__ == "__main__":
    load_global_settings()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = PhoneBookApp()
    window.show()
    sys.exit(app.exec_())
