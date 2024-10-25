from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtGui import QKeyEvent

import substance_painter.ui
import substance_painter.event

import os
import configparser
import subprocess

def config_ini(overwrite):
    # Get the path to the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the path to the TM2020-DDS-Exporter.ini file
    ini_file_path = os.path.join(script_dir, "TM2020-DDS-Exporter.ini")            
    
    # Define the path to the texconv.exe in the subfolder "TexconvLocation"
    TexConvPath = os.path.join(script_dir, "TexconvLocation", "texconv.exe")

    # Check if the INI file exists
    if os.path.exists(ini_file_path):
        # Create a ConfigParser object and read the INI file
        config = configparser.ConfigParser()
        config.read(ini_file_path)
        
        # Check if 'General' section and 'TexConvDirectory' key exist in the INI
        if 'General' not in config or 'TexConvDirectory' not in config['General']:
            # If section or key doesn't exist, create them and set the value
            config['General'] = {}
            config['General']['TexConvDirectory'] = TexConvPath
            with open(ini_file_path, 'w') as configfile:
                config.write(configfile)
            print("TM2020 DDS Exporter Plugin: TexConvDirectory value set in TM2020-DDS-Exporter.ini")
    else:
        # If the INI file doesn't exist, create it and set the value
        config = configparser.ConfigParser()
        config['General'] = {}
        config['General']['TexConvDirectory'] = TexConvPath
        with open(ini_file_path, 'w') as configfile:
            config.write(configfile)
        print("TM2020 DDS Exporter Plugin: TM2020-DDS-Exporter.ini created with TexConvDirectory")

    return TexConvPath


def convert_png_to_dds(texconvPath, sourcePNG, overwrite):
    # Replace backslashes with forward slashes in the provided paths
    texconvPath = texconvPath.replace('\\', '/')
    sourceFolder = os.path.dirname(sourcePNG)
    sourceFolder = sourceFolder.replace('\\', '/')
    outputFolder = sourceFolder + "/DDS/"

    isExist = os.path.exists(outputFolder)
    if not isExist:
        # Create the DDS directory if it does not exist
        os.makedirs(outputFolder)
        print("Created DDS subfolder")

    # for filename in os.listdir(sourceFolder):
    filename = sourcePNG
    if filename.endswith(".png"):
        sourceFile = os.path.splitext(filename)[0]
        suffix = sourceFile.split('_')[-1]
        suffix = suffix.rstrip('_')

        outputFile = sourceFile + ".dds"

        if suffix in ["B"]:
            format_option = "BC1_UNORM"
        elif suffix == "I":
            format_option = "BC3_UNORM"
        elif suffix in ["DirtMask", "CoatR"]:  # Check for both suffixes in a list
            format_option = "BC4_UNORM"
        # If for some reason it's using some other suffix that's not supported
        else:
            format_option = "BC5_UNORM"

        format_option = format_option.rstrip('"')
        if overwrite:
            overwrite_option = "-y"
        else:
            overwrite_option = ""

        if outputFile:
            texconv_cmd = [
                texconvPath,
                "-nologo", overwrite_option,
                "-o", outputFolder,
                "-f", format_option,
                os.path.join(sourceFolder, filename)
            ]
            texconv_cmd_str = subprocess.list2cmdline(texconv_cmd)

            try:
                subprocess.run(texconv_cmd_str, shell=True, check=True)
                print(f"Successfully converted {filename} to {outputFile}")
            except subprocess.CalledProcessError:
                print(f"Failed to convert {filename}")

class Tm2020DDSPlugin:
    def __init__(self):
        # Export boolean whether to add DDS creation or not
        self.export = True
        # Overwrites existing DDS files if checked
        self.overwrite = True
        # Plugin Version
        self.version = "0.0.2"

        # Create a dock widget to report plugin activity.
        self.log = QtWidgets.QTextEdit()
        self.window = QtWidgets.QWidget()
        self.TexConvPath = config_ini(False)

        layout = QtWidgets.QVBoxLayout()
        sub_layout = QtWidgets.QHBoxLayout()

        checkbox = QtWidgets.QCheckBox("Export DDS files")
        checkbox.setChecked(True)
        checkbox_overwrite = QtWidgets.QCheckBox("Overwrite DDS files")
        checkbox_overwrite.setChecked(True)
        button_clear = QtWidgets.QPushButton("Clear Log")
        self.button_export_textures = QtWidgets.QPushButton("Export Textures")
        version_label = QtWidgets.QLabel("Version: {}".format(self.version))

        # Adds buttons to sub-layout
        sub_layout.addWidget(checkbox)
        sub_layout.addWidget(checkbox_overwrite)
        sub_layout.addWidget(button_clear)
        sub_layout.addWidget(self.button_export_textures)
        # Adds all widgets to main layout
        layout.addLayout(sub_layout)
        layout.addWidget(self.log)
        layout.addWidget(version_label)

        self.window.setLayout(layout)
        self.window.setWindowTitle("TM2020 DDS Auto Converter")

        self.log.setReadOnly(True)

        # Connects buttons to click events
        checkbox.stateChanged.connect(self.checkbox_export_change)
        checkbox_overwrite.stateChanged.connect(self.checkbox_overwrite_change)
        button_clear.clicked.connect(self.button_clear_clicked)
        self.button_export_textures.clicked.connect(self.open_export_textures_window)
        # Adds Qt as dockable widget to Substance Painter
        substance_painter.ui.add_dock_widget(self.window)

        self.log.append("TexConv Path: {}".format(self.TexConvPath))

        connections = {
            substance_painter.event.ExportTexturesEnded: self.on_export_finished
        }
        for event, callback in connections.items():
            substance_painter.event.DISPATCHER.connect(event, callback)

    def button_texconv_clicked(self):
        self.TexConvPath = config_ini(True)
        self.log.append("New TexConv Path: {}".format(self.TexConvPath))

    def button_clear_clicked(self):
        self.log.clear()

    def checkbox_export_change(self,state):
        if state == Qt.Checked:
            self.export = True
        else:
            self.export = False

    def checkbox_overwrite_change(self,state):
        if state == Qt.Checked:
            self.overwrite = True
        else:
            self.overwrite = False

   # Function to simulate Ctrl+Shift+E to open the export window
    def open_export_textures_window(self):
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_E, Qt.ControlModifier | Qt.ShiftModifier)
        QtWidgets.QApplication.sendEvent(substance_painter.ui.get_main_window(), event)


    def __del__(self):
        # Remove all added UI elements.
        substance_painter.ui.delete_ui_element(self.log)
        substance_painter.ui.delete_ui_element(self.window)

    def on_export_finished(self, res):
        if(self.export):
            self.log.append(res.message)
            self.log.append("Exported files:")
            for file_list in res.textures.values():
                for file_path in file_list:
                    self.log.append("  {}".format(file_path))
                    
            self.log.append("Converting to DDS files:")
            for file_list in res.textures.values():
                for file_path in file_list:
                    convert_png_to_dds(self.TexConvPath,file_path,self.overwrite)
                    file_path = file_path[:-3]+"DDS"
                    self.log.append("  {}".format(file_path))

    def on_export_error(self, err):
        self.log.append("Export failed.")
        self.log.append(repr(err))

TM2020_DDS_PLUGIN = None

def start_plugin():
    """This method is called when the plugin is started."""
    print ("TM2020 DDS Exporter Plugin Initialized")
    global TM2020_DDS_PLUGIN
    TM2020_DDS_PLUGIN = Tm2020DDSPlugin()

def close_plugin():
    """This method is called when the plugin is stopped."""
    print ("TM2020 DDS Exporter Plugin Shutdown")
    global TM2020_DDS_PLUGIN
    del TM2020_DDS_PLUGIN

if __name__ == "__main__":
    start_plugin()
