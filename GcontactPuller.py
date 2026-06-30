import os
import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class OrderedVCardParser(QThread):
    """Parses vCards into exact layout order: First, Last, Company, Phone."""

    status_signal = pyqtSignal(str)
    contacts_signal = pyqtSignal(list)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        if not os.path.exists(self.file_path):
            self.status_signal.emit("Error: File path does not exist.")
            self.contacts_signal.emit([])
            return

        self.status_signal.emit("Parsing vCard file structure...")
        processed_contacts = []

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            first_name = ""
            last_name = ""
            company = ""
            job_title = ""
            phone_numbers = []

            for line in lines:
                line = line.strip()

                # 1. Parse Structured Name component
                if line.startswith("N:"):
                    name_parts = line[2:].split(";")
                    last = name_parts[0].strip() if len(name_parts) > 0 else ""
                    first = name_parts[1].strip() if len(name_parts) > 1 else ""
                    first_name = first
                    last_name = last

                # 2. Fallback if First/Last mapping fields are completely empty
                elif line.startswith("FN:") and not first_name:
                    full_name = line[3:].strip()
                    name_parts = full_name.split(" ", 1)
                    first_name = name_parts[0]
                    last_name = name_parts[1] if len(name_parts) > 1 else ""

                # 3. Parse Organization Name
                elif line.startswith("ORG:"):
                    org_parts = line[4:].split(";")
                    company = org_parts[0].strip() if org_parts else ""

                # 4. Parse Job Title
                elif line.startswith("TITLE:"):
                    job_title = line[6:].strip()

                # 5. Parse Phone Numbers and their respective Types
                elif line.startswith("TEL"):
                    phone_type = "Other"
                    if "TYPE=" in line:
                        try:
                            type_part = line.split(":", 1)[0]
                            if "TYPE=" in type_part:
                                phone_type = (
                                    type_part.split("TYPE=")[1]
                                    .split(";")[0]
                                    .replace('"', "")
                                )
                        except Exception:
                            phone_type = "Other"

                    if ":" in line:
                        raw_num = line.split(":", 1)[1].strip()
                        clean_num = (
                            raw_num.replace(" ", "")
                            .replace("-", "")
                            .replace("(", "")
                            .replace(")", "")
                        )
                        phone_numbers.append(
                            {"number": clean_num, "type": phone_type.title()}
                        )

                # 6. End of single Contact Card Block
                elif line.startswith("END:VCARD"):
                    final_company = company
                    if job_title:
                        final_company = (
                            f"{job_title} at {company}"
                            if company
                            else job_title
                        )

                    if phone_numbers:
                        for index, phone_obj in enumerate(phone_numbers):
                            # Rule: if it is an additional number, append type to last name field
                            if index == 0:
                                current_last_name = last_name
                            else:
                                current_last_name = (
                                    f"{last_name} ({phone_obj['type']})"
                                    if last_name
                                    else f"({phone_obj['type']})"
                                )

                            # Append tracking dictionary explicitly matching requirements
                            processed_contacts.append(
                                {
                                    "first": first_name,
                                    "last": current_last_name,
                                    "company": final_company,
                                    "phone": phone_obj["number"],
                                }
                            )

                    # Clear variables for next iteration block loop
                    first_name = ""
                    last_name = ""
                    company = ""
                    job_title = ""
                    phone_numbers = []

            # Save data array out natively
            self.write_out_phonebook(processed_contacts)
            self.contacts_signal.emit(processed_contacts)

        except Exception as e:
            self.status_signal.emit(f"Parsing Error: {str(e)}")
            self.contacts_signal.emit([])

    def write_out_phonebook(self, contacts):
        config_dir = os.path.expanduser(
            os.path.join("~", ".config", "VoIPassistant")
        )
        os.makedirs(config_dir, exist_ok=True)
        file_path = os.path.join(config_dir, "VoIPassistantPB.txt")

        existing_entries = set()
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    existing_entries.add(line.strip())

        new_entries = 0
        with open(file_path, "a", encoding="utf-8") as f:
            for c in contacts:
                # ORDER CORRECTION CRITICAL LINE: first_name, last_name, company, phone
                csv_line = (
                    f"{c['first']},{c['last']},{c['company']},{c['phone']}"
                )
                if csv_line not in existing_entries:
                    f.write(f"{csv_line}\n")
                    new_entries += 1

        self.status_signal.emit(
            f"Successfully updated VoIPassistantPB.txt with {new_entries} records."
        )


class MainOrderedApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoIP Assistant - Exact Order vCard Importer")
        self.resize(750, 550)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.import_button = QPushButton("Load Google Contacts vCard (.vcf)")
        self.import_button.clicked.connect(self.select_file)
        layout.addWidget(self.import_button)

        self.status_label = QLabel(
            "Select an exported Google vCard file to map contacts."
        )
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        # Visual columns match exact file tracking layout sequence rules
        self.table.setHorizontalHeaderLabels(
            ["First Name", "Last Name", "Company", "Phone Number"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Google vCard File", "", "vCard Files (*.vcf)"
        )
        if not file_path:
            return

        self.import_button.setEnabled(False)
        self.table.setRowCount(0)

        self.worker = OrderedVCardParser(file_path)
        self.worker.status_signal.connect(self.status_label.setText)
        self.worker.contacts_signal.connect(self.display_data)
        self.worker.start()

    def display_data(self, contacts):
        self.import_button.setEnabled(True)
        self.table.setRowCount(len(contacts))
        for row, c in enumerate(contacts):
            self.table.setItem(row, 0, QTableWidgetItem(c["first"]))
            self.table.setItem(row, 1, QTableWidgetItem(c["last"]))
            self.table.setItem(row, 2, QTableWidgetItem(c["company"]))
            self.table.setItem(row, 3, QTableWidgetItem(c["phone"]))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainOrderedApp()
    window.show()
    sys.exit(app.exec_())
