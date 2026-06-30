import sys
import os
import csv
import base64
import urllib.request
import urllib.error

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem, QDialog,
    QFormLayout, QMessageBox, QMenu, QLabel, QStyle, QSystemTrayIcon, QAction
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon

# 1. Global Variables Startup Initialization
phone_IP = ""
userext = ""
auth_header = ""  # Ready-to-use Base64 encoded "user:password"


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
    global phone_IP, userext, auth_header
    config_file = get_config_path()
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 1: phone_IP = lines[0]
                if len(lines) >= 2: userext = lines[1]
                if len(lines) >= 3: auth_header = lines[2]
        except Exception as e:
            print(f"Error loading system profile configuration parameters: {e}")
    else:
        # Generate factory fallback default auth string ("admin:admin") if file doesn't exist yet
        raw_bytes = "admin:admin".encode('utf-8')
        auth_header = base64.b64encode(raw_bytes).decode('utf-8')

def save_global_settings():
    """Writes global runtime modifications cleanly into the localized config file structure."""
    try:
        with open(get_config_path(), "w", encoding="utf-8") as f:
            f.write(f"{phone_IP}\n")
            f.write(f"{userext}\n")
            f.write(f"{auth_header}\n")
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

class ActiveCallDialog(QDialog):
    """Enforced synchronous modal (blocking) window tracking call processing runtime loops."""
    def __init__(self, contact_name: str, phone_number: str, parent=None):
        super(ActiveCallDialog, self).__init__(parent)
        self.phone_number = phone_number
        self.setWindowTitle("Active Session")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(300, 120)
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.status_label = QLabel(f"Calling <b>{contact_name}</b>...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.end_btn = QPushButton("End", self)
        self.end_btn.setStyleSheet("background-color: #ff9999; font-weight: bold;")
        self.end_btn.clicked.connect(self.handle_end_call)

        self.dismiss_btn = QPushButton("Dismiss", self)
        self.dismiss_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.end_btn)
        btn_layout.addWidget(self.dismiss_btn)
        layout.addLayout(btn_layout)

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


class SettingsDialog(QDialog):
    """Configuration prompt mapping parameters into operational global string indices."""
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        global phone_IP, userext, auth_header
        self.setWindowTitle("VoIP Settings")
        self.setModal(True)
        self.resize(350, 200)

        self.layout = QFormLayout(self)
        self.server_ip_input = QLineEdit(self)
        self.server_ip_input.setText(phone_IP)

        self.extension_input = QLineEdit(self)
        self.extension_input.setText(userext)

        try:
            decoded_str = base64.b64decode(auth_header.encode('utf-8')).decode('utf-8')
            parsed_user, parsed_pass = decoded_str.split(":", 1)
        except Exception:
            parsed_user, parsed_pass = "admin", "admin"

        self.user_input = QLineEdit(self)
        self.user_input.setText(parsed_user)

        self.pass_input = QLineEdit(self)
        self.pass_input.setText(parsed_pass)
        self.pass_input.setEchoMode(QLineEdit.Password)

        self.layout.addRow("Phone IP:", self.server_ip_input)
        self.layout.addRow("Phone User:", self.user_input)
        self.layout.addRow("Phone Password:", self.pass_input)
        self.layout.addRow("My Extension:", self.extension_input)

        self.save_button = QPushButton("Save Settings", self)
        self.save_button.clicked.connect(self.save_and_close)
        self.layout.addRow(self.save_button)

    def save_and_close(self):
        global phone_IP, userext, auth_header
        phone_IP = self.server_ip_input.text().strip()
        userext = self.extension_input.text().strip()
        
        raw_user = self.user_input.text().strip()
        raw_pass = self.pass_input.text().strip()
        combined_bytes = f"{raw_user}:{raw_pass}".encode('utf-8')
        auth_header = base64.b64encode(combined_bytes).decode('utf-8')
        
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

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
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

        tray_menu = QMenu()
        show_action = QAction("Open Phone Book", self)
        show_action.triggered.connect(self.showNormal)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)

        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(show_action)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

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
    # Ensure profile directories exist and load initialization parameters prior to drawing window
    load_global_settings()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = PhoneBookApp()
    window.show()
    sys.exit(app.exec_())
