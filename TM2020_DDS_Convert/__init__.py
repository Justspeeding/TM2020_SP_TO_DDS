from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Qt
from PySide2.QtGui import QKeyEvent
import substance_painter.ui
import substance_painter.event
import zipfile
import os
import configparser
import subprocess

# Configure and get path to Texconv
def config_ini(overwrite=False):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ini_file_path = os.path.join(script_dir, "TM2020-DDS-Exporter.ini")            
    TexConvPath = os.path.join(script_dir, "TexconvLocation", "texconv.exe")

    if os.path.exists(ini_file_path):
        config = configparser.ConfigParser()
        config.read(ini_file_path)
        if 'General' not in config or 'TexConvDirectory' not in config['General']:
            config['General'] = {}
            config['General']['TexConvDirectory'] = TexConvPath
            with open(ini_file_path, 'w') as configfile:
                config.write(configfile)
            print("TM2020 DDS Exporter Plugin: TexConvDirectory set in TM2020-DDS-Exporter.ini")
    else:
        config = configparser.ConfigParser()
        config['General'] = {}
        config['General']['TexConvDirectory'] = TexConvPath
        with open(ini_file_path, 'w') as configfile:
            config.write(configfile)
        print("TM2020 DDS Exporter Plugin: TM2020-DDS-Exporter.ini created with TexConvDirectory")

    return TexConvPath

# Convert PNG to DDS using texconv
def convert_png_to_dds(texconvPath, sourcePNG, outputFolder, overwrite, log_widget=None):
    texconvPath = texconvPath.replace('\\', '/')
    sourceFolder = os.path.dirname(sourcePNG).replace('\\', '/')
    outputFolder = os.path.join(sourceFolder, outputFolder)

    if not os.path.exists(outputFolder):
        os.makedirs(outputFolder)
        if log_widget:
            log_widget.append(f"Created DDS output folder: {outputFolder}")

    filename = os.path.basename(sourcePNG)
    if filename.endswith(".png"):
        sourceFile = os.path.splitext(filename)[0]
        suffix = sourceFile.split('_')[-1].rstrip('_')
        outputFile = os.path.join(outputFolder, sourceFile + ".dds")

        if suffix in ["B"]:
            format_option = "BC1_UNORM"
        elif suffix == "I":
            format_option = "BC3_UNORM"
        elif suffix in ["DirtMask", "CoatR"]:
            format_option = "BC4_UNORM"
        else:
            format_option = "BC5_UNORM"

        overwrite_option = "-y" if overwrite else ""
        texconv_cmd = [
            texconvPath, "-nologo", overwrite_option, "-o", outputFolder, "-f", format_option, sourcePNG
        ]

        try:
            subprocess.run(texconv_cmd, check=True)
            if log_widget:
                log_widget.append(f"Successfully converted {filename} to {outputFile}")
        except subprocess.CalledProcessError:
            if log_widget:
                log_widget.append(f"Failed to convert {filename}")

class Tm2020DDSPlugin:
    def __init__(self):
        self.export = True
        self.overwrite = True
        self.make_zip = True
        self.version = "0.0.3"
        self.TexConvPath = config_ini(False)
        self.DDSPath = None  # Will be updated after conversion

        # Create the UI
        self.log = QtWidgets.QTextEdit()
        self.window = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        sub_layout = QtWidgets.QHBoxLayout()

        # UI elements
        self.checkbox_zip = QtWidgets.QCheckBox("Make ZIP")
        self.checkbox_zip.setChecked(True)
        self.zip_name_field = QtWidgets.QLineEdit()
        self.zip_name_field.setPlaceholderText("Enter ZIP and DDS folder name (optional)")
        checkbox = QtWidgets.QCheckBox("Export DDS files")
        checkbox.setChecked(True)
        checkbox_overwrite = QtWidgets.QCheckBox("Overwrite DDS files")
        checkbox_overwrite.setChecked(True)
        button_clear = QtWidgets.QPushButton("Clear Log")
        self.button_export_textures = QtWidgets.QPushButton("Export Textures")
        version_label = QtWidgets.QLabel(f"Version: {self.version}")

        # Add widgets to layouts
        sub_layout.addWidget(checkbox)
        sub_layout.addWidget(self.checkbox_zip)
        sub_layout.addWidget(checkbox_overwrite)
        sub_layout.addWidget(button_clear)
        sub_layout.addWidget(self.button_export_textures)
        
        layout.addLayout(sub_layout)
        layout.addWidget(self.zip_name_field)  # Add the ZIP and DDS folder name input field
        layout.addWidget(self.log)
        layout.addWidget(version_label)

        self.window.setLayout(layout)
        self.window.setWindowTitle("TM2020 DDS Auto Converter")
        self.log.setReadOnly(True)

        # Event connections
        checkbox.stateChanged.connect(self.checkbox_export_change)
        checkbox_overwrite.stateChanged.connect(self.checkbox_overwrite_change)
        button_clear.clicked.connect(self.button_clear_clicked)
        self.button_export_textures.clicked.connect(self.open_export_textures_window)
        self.checkbox_zip.stateChanged.connect(self.checkbox_zip_change)

        # Add widget to Substance Painter UI
        substance_painter.ui.add_dock_widget(self.window)
        self.log.append(f"TexConv Path: {self.TexConvPath}")

        connections = {substance_painter.event.ExportTexturesEnded: self.on_export_finished}
        for event, callback in connections.items():
            substance_painter.event.DISPATCHER.connect(event, callback)

    def button_clear_clicked(self):
        self.log.clear()

    def checkbox_export_change(self, state):
        self.export = state == Qt.Checked

    def checkbox_overwrite_change(self, state):
        self.overwrite = state == Qt.Checked

    def checkbox_zip_change(self, state):
        self.make_zip = state == Qt.Checked

    def open_export_textures_window(self):
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_E, Qt.ControlModifier | Qt.ShiftModifier)
        QtWidgets.QApplication.sendEvent(substance_painter.ui.get_main_window(), event)

    def on_export_finished(self, res):
        if self.export:
            self.log.append(res.message)
            self.log.append("Exported files:")
            
            # Get custom name or use default
            dds_folder_name = self.zip_name_field.text().strip() or "TM2020_DDS"
            self.DDSPath = os.path.join(os.path.dirname(res.textures[list(res.textures.keys())[0]][0]), dds_folder_name)
            
            # Convert each exported file to DDS
            for file_list in res.textures.values():
                for file_path in file_list:
                    self.log.append(f"  Exported file: {file_path}")
                    convert_png_to_dds(self.TexConvPath, file_path, dds_folder_name, self.overwrite, self.log)

            # If make_zip is enabled, create a ZIP archive of the DDS files
            if self.make_zip:
                self.create_zip_archive(self.DDSPath)

    def create_zip_archive(self, folder_path):
        # Get the custom name for the ZIP file or use the DDS folder name
        zip_name = self.zip_name_field.text().strip() or "TM2020.zip"
        zip_path = os.path.join(folder_path, zip_name if zip_name.endswith(".zip") else zip_name + ".zip")

        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        if file.endswith(".dds"):
                            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))
            self.log.append(f"Created ZIP archive: {zip_path}")
        except Exception as e:
            self.log.append(f"Failed to create ZIP archive: {e}")

    def __del__(self):
        substance_painter.ui.delete_ui_element(self.log)
        substance_painter.ui.delete_ui_element(self.window)


TM2020_DDS_PLUGIN = None

def start_plugin():
    global TM2020_DDS_PLUGIN
    TM2020_DDS_PLUGIN = Tm2020DDSPlugin()

def close_plugin():
    global TM2020_DDS_PLUGIN
    del TM2020_DDS_PLUGIN

if __name__ == "__main__":
    start_plugin()
