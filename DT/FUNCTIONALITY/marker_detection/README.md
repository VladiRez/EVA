Implementierung einer Marker-Erkennung mit der Zed2 Tiefenkamera. Das Ziel ist das Erkennen der Position der Platinen. Durch einen Abgleich mit der Soll-Position werden Fehler im Produktionsablauf erkannt.
Das Modul besteht aus zwei Teilen: Dem installierbaren python package marker_detection, das in andere Projekte eingebunden werden kann,
sowie das alleinstehende cli.py Skript/Tool, mit dem die Marker_Erkennung getestet bzw. marker und boards erstellt werden können.

# Voraussetzungen

Unter env_marker findet sich die virtualenv für das Projekt. Es wird Python Version 3.7.9 benutzt, da neuere Versionen von Python Probleme mit der ZED Python API verursachten. Die ZED Kamera braucht einen USB 3.0 Port.

[NVIDIA CUDA](https://developer.nvidia.com/cuda-downloads)

[ZED SDK 3.6](https://www.stereolabs.com/developers/)

[Zed Python API](https://github.com/stereolabs/zed-python-api) 
> Kein Download nötig, siehe Installation
> Die Installation von pyzed bringt folgende Packages mit:
> Cython, numpy, PyOpenGL, PyOpenGL-accelerate

[OpenCV Contrib Python](https://pypi.org/project/opencv-contrib-python/) `pip install opencv-contrib-python`

## ZED Python API installieren:
In virtualenv Umgebung (Mit Admin-Rechten bzw. sudo):
1. cd in ZED SDK Ordner (normalerweise C:\Program Files (x86)\ZED SDK)
2. `python3 get_python_api.py`
3. Sollte ein SSL Error auftreten, den Download-Link in der Error-Message in den Browser kopieren und die .wql mit pip installieren

# Python Package Installieren

Das package soll für Benutzung außerhalb des Command-Line Interfaces (cli.py) über pip installiert werden. Manuell muss dafür nur
vorher die ZED Python API installiert werden (siehe oben). Dann folgendes im Ordner mit der setup.cfg ausführen:
> python -m pip install .

Soll das package noch verändert werden, bietet es sich an, es im Development-Modus zu installieren:
> python -m pip install --editable .

Wird das package nun verändert, muss es nicht manuell geupdated werden.
Nun kann z.B. das Hauptsystem mit
> from marker_detection import md_system

importiert werden.

Zum Initialisieren des Marker-System muss die Kalibrationsdatei der Zed2 Kamera angegeben werden. Sie findet sich normalerweise 
unter Windows unter C:\ProgramData\StereoLabs\settings. Außerdem wird eine Einstellungsdatei im JSON Format benötigt. Sie hat die Form:

> {
>     "aruco": {
>         "dictionary": "DICT_5X5_50"
>     },
>     "charuco": {
>         "dictionary": "DICT_4X4_50",
>         "n_squares_x": 4,
>         "n_squares_y": 4,
>         "width_square": 0.0475,
>         "width_marker": 0.035
>     }
> }

# Command Line Interface: Standalone starten / Marker erstellen / "ausprobieren"

Um die Erkennung auszuprobieren steht das Command-Line Interface bereit. Die Hilfe dafür wird aufgerufen mit
> python cli.py --help

Um eine genaue Erkennung zu ermöglichen, muss die Kalibrationsdatei der Zed2 Kamera nach \cli_data\calibration.conf kopiert werden.
Sie findet sich normalerweise unter Windows unter C:\ProgramData\StereoLabs\settings. Die JSON Datei in \md_settings.json enthält
die wichtigen Konfigurationseinstellungen für die Marker-Erkennung.

Wichtig ist, dass Python 3.7(.9) verwendet wird. Von da aus können marker oder marker-boards erstellt und das Erkennungsprogramm gestartet werden.